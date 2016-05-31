import copy
import fnmatch
import os
import re
import uuid
from functools import update_wrapper
from collections import OrderedDict

import jinja2
from babel import dates
from inifile import IniFile
from jinja2.loaders import split_template_path
from lektor.markdown import Markdown
from werkzeug.urls import url_parse
from werkzeug.utils import cached_property

from lektor._compat import iteritems, string_types
from lektor.context import (config_proxy, get_asset_url, get_ctx, get_locale,
    site_proxy, url_to)
from lektor.i18n import get_i18n_block
from lektor.pluginsystem import PluginController
from lektor.utils import (bool_from_string, format_lat_long, secure_url,
    tojson_filter)


# Special value that identifies a target to the primary alt
PRIMARY_ALT = '_primary'
DEFAULT_CONFIG = {
    'IMAGEMAGICK_EXECUTABLE': None,
    'EPHEMERAL_RECORD_CACHE_SIZE': 500,
    'ATTACHMENT_TYPES': {
        # Only enable image formats here that we can handle in imagetools.
        # Right now this is limited to jpg, png and gif because this is
        # the only thing we compile into imagemagick on OS X distributions
        # as those are what browsers also support.  Thers is no point in
        # adding others here as we do not force convert images (yet?) but
        # only use it for thumbnailing.  However an image should be
        # visible even without thumbnailing.
        '.jpg': 'image',
        '.jpeg': 'image',
        '.png': 'image',
        '.gif': 'image',
        '.svg': 'image',

        '.avi': 'video',
        '.mpg': 'video',
        '.mpeg': 'video',
        '.wmv': 'video',
        '.ogv': 'video',

        '.mp3': 'audio',
        '.wav': 'audio',
        '.ogg': 'audio',

        '.pdf': 'document',
        '.doc': 'document',
        '.docx': 'document',
        '.htm': 'document',
        '.html': 'document',

        '.txt': 'text',
        '.log': 'text',
    },
    'PROJECT': {
        'name': None,
        'locale': 'en_US',
        'url': None,
        'url_style': 'relative',
    },
    'PACKAGES': {},
    'ALTERNATIVES': OrderedDict(),
    'PRIMARY_ALTERNATIVE': None,
    'SERVERS': {},
}


def _pass_locale(func):
    def new_func(*args, **kwargs):
        if kwargs.get('locale', None) is None:
            kwargs['locale'] = get_locale('en_US')
        return func(*args, **kwargs)
    return update_wrapper(new_func, func)


def update_config_from_ini(config, inifile):
    def set_simple(target, source_path):
        rv = config.get(source_path)
        if rv is not None:
            config[target] = rv

    set_simple(target='IMAGEMAGICK_EXECUTABLE',
               source_path='env.imagemagick_executable')
    set_simple(target='LESSC_EXECUTABLE',
               source_path='env.lessc_executable')

    config['ATTACHMENT_TYPES'].update(
        (k.encode('ascii', 'replace'), v.encode('ascii', 'replace'))
        for k, v in inifile.section_as_dict('attachment_types'))

    config['PROJECT'].update(inifile.section_as_dict('project'))
    config['PACKAGES'].update(inifile.section_as_dict('packages'))

    for sect in inifile.sections():
        if sect.startswith('servers.'):
            server_id = sect.split('.')[1]
            config['SERVERS'][server_id] = inifile.section_as_dict(sect)
        elif sect.startswith('alternatives.'):
            alt = sect.split('.')[1]
            config['ALTERNATIVES'][alt] = {
                'name': get_i18n_block(inifile, 'alternatives.%s.name' % alt),
                'url_prefix': inifile.get('alternatives.%s.url_prefix' % alt),
                'url_suffix': inifile.get('alternatives.%s.url_suffix' % alt),
                'primary': inifile.get_bool('alternatives.%s.primary' % alt),
                'locale': inifile.get('alternatives.%s.locale' % alt, 'en_US'),
            }

    for alt, alt_data in iteritems(config['ALTERNATIVES']):
        if alt_data['primary']:
            config['PRIMARY_ALTERNATIVE'] = alt
            break
    else:
        if config['ALTERNATIVES']:
            raise RuntimeError('Alternatives defined but no primary set.')


# Special files that should always be ignored.
IGNORED_FILES = ['thumbs.db', 'desktop.ini', 'Icon\r']

# These files are important for artifacts and must not be ignored when
# they are built even though they start with dots.
SPECIAL_ARTIFACTS = ['.htaccess', '.htpasswd']

# Default glob pattern of ignored files.
EXCLUDED_ASSETS = ['_*', '.*']

# Default glob pattern of included files (higher-priority than EXCLUDED_ASSETS).
INCLUDED_ASSETS = []


def any_fnmatch(filename, patterns):
    for pat in patterns:
        if fnmatch.fnmatch(filename, pat):
            return True

    return False


class ServerInfo(object):

    def __init__(self, id, name_i18n, target, enabled=True, default=False,
                 extra=None):
        self.id = id
        self.name_i18n = name_i18n
        self.target = target
        self.enabled = enabled
        self.default = default
        self.extra = extra or {}

    @property
    def name(self):
        return self.name_i18n.get('en') or self.id

    @property
    def short_target(self):
        match = re.match(r'([a-z]+)://([^/]+)', self.target)
        if match is not None:
            protocol, server = match.groups()
            return '%s via %s' % (server, protocol)
        return self.target

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_i18n': self.name_i18n,
            'target': self.target,
            'short_target': self.short_target,
            'enabled': self.enabled,
            'default': self.default,
            'extra': self.extra,
        }


class Expression(object):

    def __init__(self, env, expr):
        self.env = env
        self.tmpl = env.jinja_env.from_string('{{ __result__(%s) }}' % expr)

    def evaluate(self, pad=None, this=None, values=None, alt=None):
        result = []
        def result_func(value):
            result.append(value)
            return u''
        values = self.env.make_default_tmpl_values(pad, this, values, alt)
        values['__result__'] = result_func
        self.tmpl.render(values)
        return result[0]


class FormatExpression(object):

    def __init__(self, env, expr):
        self.env = env
        self.tmpl = env.jinja_env.from_string(expr)

    def evaluate(self, pad=None, this=None, values=None, alt=None):
        values = self.env.make_default_tmpl_values(pad, this, values, alt)
        return self.tmpl.render(values)


class CustomJinjaEnvironment(jinja2.Environment):

    def _load_template(self, name, globals):
        ctx = get_ctx()

        try:
            rv = jinja2.Environment._load_template(self, name, globals)
            if ctx is not None:
                ctx.record_dependency(rv.filename)
            return rv
        except jinja2.TemplateSyntaxError as e:
            if ctx is not None:
                ctx.record_dependency(e.filename)
            raise
        except jinja2.TemplateNotFound as e:
            if ctx is not None:
                # If we can't find the template we want to record at what
                # possible locations the template could exist.  This will help
                # out watcher to pick up templates that will appear in the
                # future.  This assumes the loader is a file system loader.
                for template_name in e.templates:
                    pieces = split_template_path(template_name)
                    for base in self.loader.searchpath:
                        ctx.record_dependency(os.path.join(base, *pieces))
            raise


class Config(object):

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
        return self.values['PROJECT']['locale']

    def get_servers(self, public=False):
        """Returns a list of servers."""
        rv = {}
        for server in self.values['SERVERS']:
            server_info = self.get_server(server, public=public)
            if server_info is None:
                continue
            rv[server] = server_info
        return rv

    def get_default_server(self, public=False):
        """Returns the default server."""
        choices = []
        for server in self.values['SERVERS']:
            server_info = self.get_server(server, public=public)
            if server_info is not None:
                if server_info.default:
                    return server_info
                choices.append(server_info)
        if len(choices) == 1:
            return choices[0]

    def get_server(self, name, public=False):
        """Looks up a server info by name."""
        info = self.values['SERVERS'].get(name)
        if info is None or 'target' not in info:
            return None
        info = info.copy()
        target = info.pop('target')
        if public:
            target = secure_url(target)
        return ServerInfo(
            id=name,
            name_i18n=get_i18n_block(info, 'name', pop=True),
            target=target,
            enabled=bool_from_string(info.pop('enabled', None), True),
            default=bool_from_string(info.pop('default', None), False),
            extra=info
        )

    def is_valid_alternative(self, alt):
        """Checks if an alternative ID is known."""
        if alt == PRIMARY_ALT:
            return True
        return alt in self.values['ALTERNATIVES']

    def list_alternatives(self):
        """Returns a sorted list of alternative IDs."""
        return sorted(self.values['ALTERNATIVES'])

    def iter_alternatives(self):
        """Iterates over all alterantives.  If the system is disabled this
        yields '_primary'.
        """
        found = False
        for alt in self.values['ALTERNATIVES']:
            if alt != PRIMARY_ALT:
                yield alt
                found = True
        if not found:
            yield PRIMARY_ALT

    def get_alternative(self, alt):
        """Returns the config setting of the given alt."""
        if alt == PRIMARY_ALT:
            alt = self.primary_alternative
        return self.values['ALTERNATIVES'].get(alt)

    def get_alternative_url_prefixes(self):
        """Returns a list of alternative url prefixes by length."""
        items = [(v['url_prefix'].lstrip('/'), k)
                 for k, v in iteritems(self.values['ALTERNATIVES'])
                 if v['url_prefix']]
        items.sort(key=lambda x: -len(x[0]))
        return items

    def get_alternative_url_suffixes(self):
        """Returns a list of alternative url suffixes by length."""
        items = [(v['url_suffix'].rstrip('/'), k)
                 for k, v in iteritems(self.values['ALTERNATIVES'])
                 if v['url_suffix']]
        items.sort(key=lambda x: -len(x[0]))
        return items

    def get_alternative_url_span(self, alt=PRIMARY_ALT):
        """Returns the URL span (prefix, suffix) for an alt."""
        if alt == PRIMARY_ALT:
            alt = self.primary_alternative
        cfg = self.values['ALTERNATIVES'].get(alt)
        if cfg is not None:
            return cfg['url_prefix'] or '', cfg['url_suffix'] or ''
        return '', ''

    @cached_property
    def primary_alternative_is_rooted(self):
        """`True` if the primary alternative is sitting at the root of
        the URL handler.
        """
        primary = self.primary_alternative
        if primary is None:
            return True

        cfg = self.values['ALTERNATIVES'].get(primary)
        if not (cfg['url_prefix'] or '').lstrip('/') and \
           not (cfg['url_suffix'] or '').rstrip('/'):
            return True

        return False

    @property
    def primary_alternative(self):
        """The identifier that acts as primary alternative."""
        return self.values['PRIMARY_ALTERNATIVE']

    @cached_property
    def base_url(self):
        """The external base URL."""
        url = self.values['PROJECT'].get('url')
        if url and url_parse(url).scheme:
            return url.rstrip('/') + '/'

    @cached_property
    def base_path(self):
        """The base path of the URL."""
        url = self.values['PROJECT'].get('url')
        if url:
            return url_parse(url).path.rstrip('/') + '/'
        return '/'

    @cached_property
    def url_style(self):
        """The intended URL style."""
        style = self.values['PROJECT'].get('url_style')
        if style in ('relative', 'absolute', 'external'):
            return style
        return 'relative'


def lookup_from_bag(*args):
    pieces = '.'.join(x for x in args if x)
    return site_proxy.databags.lookup(pieces)


class Environment(object):

    def __init__(self, project, load_plugins=True):
        self.project = project
        self.root_path = os.path.abspath(project.tree)

        self.jinja_env = CustomJinjaEnvironment(
            autoescape=self.select_jinja_autoescape,
            extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_'],
            loader=jinja2.FileSystemLoader(
                os.path.join(self.root_path, 'templates'))
        )

        from lektor.db import F, get_alts
        self.jinja_env.filters.update(
            tojson=tojson_filter,
            latformat=lambda x, secs=True: format_lat_long(lat=x, secs=secs),
            longformat=lambda x, secs=True: format_lat_long(long=x, secs=secs),
            latlongformat=lambda x, secs=True: format_lat_long(secs=secs, *x),
            # By default filters need to be side-effect free.  This is not
            # the case for this one, so we need to make it as a dummy
            # context filter so that jinja2 will not inline it.
            url=jinja2.contextfilter(
                lambda ctx, *a, **kw: url_to(*a, **kw)),
            asseturl=jinja2.contextfilter(
                lambda ctx, *a, **kw: get_asset_url(*a, **kw)),
            markdown=jinja2.contextfilter(
                lambda ctx, *a, **kw: Markdown(*a, **kw)),
        )
        self.jinja_env.globals.update(
            F=F,
            url_to=url_to,
            site=site_proxy,
            config=config_proxy,
            bag=lookup_from_bag,
            get_alts=get_alts,
            get_random_id=lambda: uuid.uuid4().hex,
        )
        self.jinja_env.filters.update(
            datetimeformat=_pass_locale(dates.format_datetime),
            dateformat=_pass_locale(dates.format_date),
            timeformat=_pass_locale(dates.format_time),
        )

        from lektor.types import builtin_types
        self.types = builtin_types.copy()

        from lektor.publisher import builtin_publishers
        self.publishers = builtin_publishers.copy()

        # The plugins that are loaded for this environment.  This is
        # modified by the plugin controller and registry methods on the
        # environment.
        self.plugin_controller = PluginController(self)
        self.plugins = {}
        self.plugin_ids_by_class = {}
        self.build_programs = []
        self.special_file_assets = {}
        self.special_file_suffixes = {}
        self.custom_url_resolvers = []
        self.custom_generators = []
        self.virtual_sources = {}

        if load_plugins:
            self.load_plugins()

        from lektor.db import siblings_resolver
        self.virtualpathresolver('siblings')(siblings_resolver)

    @property
    def asset_path(self):
        return os.path.join(self.root_path, 'assets')

    @property
    def temp_path(self):
        return os.path.join(self.root_path, 'temp')

    def load_plugins(self):
        """Loads the plugins."""
        from .packages import load_packages
        from .pluginsystem import initialize_plugins
        load_packages(self)
        initialize_plugins(self)

    def load_config(self):
        """Loads the current config."""
        return Config(self.project.project_file)

    def new_pad(self):
        """Convenience function to create a database and pad."""
        from lektor.db import Database
        return Database(self).new_pad()

    def is_uninteresting_source_name(self, filename):
        """These files are ignored when sources are built into artifacts."""
        fn = filename.lower()
        if fn in SPECIAL_ARTIFACTS:
            return False

        proj = self.project
        if any_fnmatch(filename, INCLUDED_ASSETS + proj.included_assets):
            # Included by the user's project config, thus not uninteresting.
            return False
        return any_fnmatch(filename, EXCLUDED_ASSETS + proj.excluded_assets)

    def is_ignored_artifact(self, asset_name):
        """This is used by the prune tool to figure out which files in the
        artifact folder should be ignored.
        """
        fn = asset_name.lower()
        if fn in SPECIAL_ARTIFACTS:
            return False
        return fn[:1] == '.' or fn in IGNORED_FILES

    def render_template(self, name, pad=None, this=None, values=None, alt=None):
        ctx = self.make_default_tmpl_values(pad, this, values, alt,
                                            template=name)
        return self.jinja_env.get_or_select_template(name).render(ctx)

    def make_default_tmpl_values(self, pad=None, this=None, values=None, alt=None,
                                 template=None):
        values = dict(values or ())

        # If not provided, pick the alt from the provided "this" object.
        # As there is no mandatory format for it, we make sure that we can
        # deal with a bad attribute there.
        if alt is None:
            if this is not None:
                alt = getattr(this, 'alt', None)
                if not isinstance(alt, string_types):
                    alt = None
            if alt is None:
                alt = PRIMARY_ALT

        # This is already a global variable but we can inject it as a
        # local override if available.
        if pad is None:
            ctx = get_ctx()
            if ctx is not None:
                pad = ctx.pad
        if pad is not None:
            values['site'] = pad
        if this is not None:
            values['this'] = this
        if alt is not None:
            values['alt'] = alt
        self.plugin_controller.emit('process-template-context',
                                    context=values, template=template)
        return values

    def select_jinja_autoescape(self, filename):
        if filename is None:
            return False
        return filename.endswith(('.html', '.htm', '.xml', '.xhtml'))

    def resolve_custom_url_path(self, obj, url_path):
        for resolver in self.custom_url_resolvers:
            rv = resolver(obj, url_path)
            if rv is not None:
                return rv

    # -- methods for the plugin system

    def add_build_program(self, cls, program):
        self.build_programs.append((cls, program))

    def add_asset_type(self, asset_cls, build_program):
        self.build_programs.append((asset_cls, build_program))
        self.special_file_assets[asset_cls.source_extension] = asset_cls
        if asset_cls.artifact_extension:
            cext = asset_cls.source_extension + asset_cls.artifact_extension
            self.special_file_suffixes[cext] = asset_cls.source_extension

    def add_publisher(self, scheme, publisher):
        if scheme in self.publishers:
            raise RuntimeError('Scheme "%s" is already registered.' % scheme)
        self.publishers[scheme] = publisher

    def add_type(self, type):
        name = type.name
        if name in self.types:
            raise RuntimeError('Type "%s" is already registered.' % name)
        self.types[name] = type

    def virtualpathresolver(self, prefix):
        def decorator(func):
            if prefix in self.virtual_sources:
                raise RuntimeError('Prefix "%s" is already registered.'
                                   % prefix)
            self.virtual_sources[prefix] = func
            return func
        return decorator

    def urlresolver(self, func):
        self.custom_url_resolvers.append(func)
        return func

    def generator(self, func):
        self.custom_generators.append(func)
        return func
