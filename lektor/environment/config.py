import copy
import os
import re
from collections import OrderedDict

from inifile import IniFile
from werkzeug.urls import url_parse
from werkzeug.utils import cached_property

from lektor.constants import PRIMARY_ALT
from lektor.i18n import get_i18n_block
from lektor.utils import bool_from_string
from lektor.utils import secure_url


DEFAULT_CONFIG = {
    "IMAGEMAGICK_EXECUTABLE": None,
    "EPHEMERAL_RECORD_CACHE_SIZE": 500,
    "ATTACHMENT_TYPES": {
        # Only enable image formats here that we can handle in imagetools.
        # Right now this is limited to jpg, png and gif because this is
        # the only thing we compile into imagemagick on OS X distributions
        # as those are what browsers also support.  Thers is no point in
        # adding others here as we do not force convert images (yet?) but
        # only use it for thumbnailing.  However an image should be
        # visible even without thumbnailing.
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".gif": "image",
        ".svg": "image",
        ".avi": "video",
        ".mpg": "video",
        ".mpeg": "video",
        ".wmv": "video",
        ".ogv": "video",
        ".mp4": "video",
        ".mp3": "audio",
        ".wav": "audio",
        ".ogg": "audio",
        ".pdf": "document",
        ".doc": "document",
        ".docx": "document",
        ".htm": "document",
        ".html": "document",
        ".txt": "text",
        ".log": "text",
    },
    "PROJECT": {
        "name": None,
        "locale": "en_US",
        "url": None,
        "url_style": "relative",
    },
    "THEME_SETTINGS": {},
    "PACKAGES": {},
    "ALTERNATIVES": OrderedDict(),
    "PRIMARY_ALTERNATIVE": None,
    "SERVERS": {},
}


def update_config_from_ini(config, inifile):
    def set_simple(target, source_path):
        rv = config.get(source_path)
        if rv is not None:
            config[target] = rv

    set_simple(
        target="IMAGEMAGICK_EXECUTABLE", source_path="env.imagemagick_executable"
    )
    set_simple(target="LESSC_EXECUTABLE", source_path="env.lessc_executable")

    for section_name in ("ATTACHMENT_TYPES", "PROJECT", "PACKAGES", "THEME_SETTINGS"):
        section_config = inifile.section_as_dict(section_name.lower())
        config[section_name].update(section_config)

    for sect in inifile.sections():
        if sect.startswith("servers."):
            server_id = sect.split(".")[1]
            config["SERVERS"][server_id] = inifile.section_as_dict(sect)
        elif sect.startswith("alternatives."):
            alt = sect.split(".")[1]
            config["ALTERNATIVES"][alt] = {
                "name": get_i18n_block(inifile, "alternatives.%s.name" % alt),
                "url_prefix": inifile.get("alternatives.%s.url_prefix" % alt),
                "url_suffix": inifile.get("alternatives.%s.url_suffix" % alt),
                "primary": inifile.get_bool("alternatives.%s.primary" % alt),
                "locale": inifile.get("alternatives.%s.locale" % alt, "en_US"),
            }

    for alt, alt_data in config["ALTERNATIVES"].items():
        if alt_data["primary"]:
            config["PRIMARY_ALTERNATIVE"] = alt
            break
    else:
        if config["ALTERNATIVES"]:
            raise RuntimeError("Alternatives defined but no primary set.")


class ServerInfo:
    def __init__(self, id, name_i18n, target, enabled=True, default=False, extra=None):
        self.id = id
        self.name_i18n = name_i18n
        self.target = target
        self.enabled = enabled
        self.default = default
        self.extra = extra or {}

    @property
    def name(self):
        return self.name_i18n.get("en") or self.id

    @property
    def short_target(self):
        match = re.match(r"([a-z]+)://([^/]+)", self.target)
        if match is not None:
            protocol, server = match.groups()
            return "%s via %s" % (server, protocol)
        return self.target

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_i18n": self.name_i18n,
            "target": self.target,
            "short_target": self.short_target,
            "enabled": self.enabled,
            "default": self.default,
            "extra": self.extra,
        }


class Config:
    def __init__(self, filename=None):
        self.filename = filename
        self.values = copy.deepcopy(DEFAULT_CONFIG)

        if filename is not None and os.path.isfile(filename):
            inifile = IniFile(filename)
            update_config_from_ini(self.values, inifile)

    def __getitem__(self, name):
        return self.values[name]

    @property
    def site_locale(self):
        """The locale of this project."""
        return self.values["PROJECT"]["locale"]

    def get_servers(self, public=False):
        """Returns a list of servers."""
        rv = {}
        for server in self.values["SERVERS"]:
            server_info = self.get_server(server, public=public)
            if server_info is None:
                continue
            rv[server] = server_info
        return rv

    def get_default_server(self, public=False):
        """Returns the default server."""
        choices = []
        for server in self.values["SERVERS"]:
            server_info = self.get_server(server, public=public)
            if server_info is not None:
                if server_info.default:
                    return server_info
                choices.append(server_info)
        if len(choices) == 1:
            return choices[0]
        return None

    def get_server(self, name, public=False):
        """Looks up a server info by name."""
        info = self.values["SERVERS"].get(name)
        if info is None or "target" not in info:
            return None
        info = info.copy()
        target = info.pop("target")
        if public:
            target = secure_url(target)
        return ServerInfo(
            id=name,
            name_i18n=get_i18n_block(info, "name", pop=True),
            target=target,
            enabled=bool_from_string(info.pop("enabled", None), True),
            default=bool_from_string(info.pop("default", None), False),
            extra=info,
        )

    def is_valid_alternative(self, alt):
        """Checks if an alternative ID is known."""
        if alt == PRIMARY_ALT:
            return True
        return alt in self.values["ALTERNATIVES"]

    def list_alternatives(self):
        """Returns a sorted list of alternative IDs."""
        return sorted(self.values["ALTERNATIVES"])

    def iter_alternatives(self):
        """Iterates over all alterantives.  If the system is disabled this
        yields '_primary'.
        """
        found = False
        for alt in self.values["ALTERNATIVES"]:
            if alt != PRIMARY_ALT:
                yield alt
                found = True
        if not found:
            yield PRIMARY_ALT

    def get_alternative(self, alt):
        """Returns the config setting of the given alt."""
        if alt == PRIMARY_ALT:
            alt = self.primary_alternative
        return self.values["ALTERNATIVES"].get(alt)

    def get_alternative_url_prefixes(self):
        """Returns a list of alternative url prefixes by length."""
        items = [
            (v["url_prefix"].lstrip("/"), k)
            for k, v in self.values["ALTERNATIVES"].items()
            if v["url_prefix"]
        ]
        items.sort(key=lambda x: -len(x[0]))
        return items

    def get_alternative_url_suffixes(self):
        """Returns a list of alternative url suffixes by length."""
        items = [
            (v["url_suffix"].rstrip("/"), k)
            for k, v in self.values["ALTERNATIVES"].items()
            if v["url_suffix"]
        ]
        items.sort(key=lambda x: -len(x[0]))
        return items

    def get_alternative_url_span(self, alt=PRIMARY_ALT):
        """Returns the URL span (prefix, suffix) for an alt."""
        if alt == PRIMARY_ALT:
            alt = self.primary_alternative
        cfg = self.values["ALTERNATIVES"].get(alt)
        if cfg is not None:
            return cfg["url_prefix"] or "", cfg["url_suffix"] or ""
        return "", ""

    @cached_property
    def primary_alternative_is_rooted(self):
        """`True` if the primary alternative is sitting at the root of
        the URL handler.
        """
        primary = self.primary_alternative
        if primary is None:
            return True

        cfg = self.values["ALTERNATIVES"].get(primary)
        if not (cfg["url_prefix"] or "").lstrip("/") and not (
            cfg["url_suffix"] or ""
        ).rstrip("/"):
            return True

        return False

    @property
    def primary_alternative(self):
        """The identifier that acts as primary alternative."""
        return self.values["PRIMARY_ALTERNATIVE"]

    @cached_property
    def base_url(self):
        """The external base URL."""
        url = self.values["PROJECT"].get("url")
        if url and url_parse(url).scheme:
            return url.rstrip("/") + "/"
        return None

    @cached_property
    def base_path(self):
        """The base path of the URL."""
        url = self.values["PROJECT"].get("url")
        if url:
            return url_parse(url).path.rstrip("/") + "/"
        return "/"

    @cached_property
    def url_style(self):
        """The intended URL style."""
        style = self.values["PROJECT"].get("url_style")
        if style in ("relative", "absolute", "external"):
            return style
        return "relative"
