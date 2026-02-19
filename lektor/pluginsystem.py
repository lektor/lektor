from __future__ import annotations

import inspect
import os
import sys
import warnings
from importlib import metadata
from pathlib import Path
from weakref import ref as weakref

from inifile import IniFile

from lektor.context import get_ctx
from lektor.utils import process_extra_flags


def get_plugin(plugin_id_or_class, env=None):
    """Looks up the plugin instance by id or class."""
    if env is None:
        ctx = get_ctx()
        if ctx is None:
            raise RuntimeError(
                "Context is unavailable and no environment was passed to the function."
            )
        env = ctx.env
    plugin_id = env.plugin_ids_by_class.get(plugin_id_or_class, plugin_id_or_class)
    try:
        return env.plugins[plugin_id]
    except KeyError as error:
        raise LookupError(f"Plugin {plugin_id!r} not found") from error


class Plugin:
    """This needs to be subclassed for custom plugins."""

    name = "Your Plugin Name"
    description = "Description goes here"

    __dist: metadata.Distribution | None = None

    def __init__(self, env, id):
        self._env = weakref(env)
        self.id = id

    @property
    def env(self):
        rv = self._env()
        if rv is None:
            raise RuntimeError("Environment went away")
        return rv

    @property
    def version(self):
        if self.__dist is not None:
            return self.__dist.version
        return None

    @property
    def path(self) -> str:
        mod = sys.modules[self.__class__.__module__.split(".", maxsplit=1)[0]]
        path = Path(mod.__file__).resolve().parent
        package_cache = self.env.project.get_package_cache_path()
        try:
            # We could use Path.is_relative_to(), except that's py39+ only
            path.relative_to(package_cache)
            # We're only interested in local, editable packages. This is not one.
            return None
        except ValueError:
            pass
        return os.fspath(path)

    @property
    def import_name(self):
        return self.__class__.__module__ + ":" + self.__class__.__name__

    def get_lektor_config(self):
        """Returns the global config."""
        ctx = get_ctx()
        if ctx is not None:
            cfg = ctx.pad.db.config
        else:
            cfg = self.env.load_config()
        return cfg

    @property
    def config_filename(self):
        """The filename of the plugin specific config file."""
        return os.path.join(self.env.root_path, "configs", self.id + ".ini")

    def get_config(self, fresh=False):
        """Returns the config specific for this plugin.  By default this
        will be cached for the current build context but this can be
        disabled by passing ``fresh=True``.
        """
        ctx = get_ctx()
        if ctx is not None and not fresh:
            cache = ctx.cache.setdefault(__name__ + ":configs", {})
            cfg = cache.get(self.id)
            if cfg is None:
                cfg = IniFile(self.config_filename)
                cache[self.id] = cfg
        else:
            cfg = IniFile(self.config_filename)
        if ctx is not None:
            ctx.record_dependency(self.config_filename)
        return cfg

    def emit(self, event, **kwargs):
        return self.env.plugin_controller.emit(self.id + "-" + event, **kwargs)

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "path": self.path,
            "import_name": self.import_name,
        }


def _check_dist_name(dist_name, plugin_id):
    """Check that plugin comes from a validly named distribution.

    Raises RuntimeError if distribution name is not of the form
    ``lektor-``*<plugin_id>*.
    """
    # XXX: Do we really need to be so strict about distribution names?
    # Ref: https://github.com/lektor/lektor/issues/875
    match_name = "lektor-" + plugin_id.lower()
    if match_name != dist_name.lower():
        raise RuntimeError(
            "Disallowed distribution name: distribution name for "
            f"plugin {plugin_id!r} must be {match_name!r} (not {dist_name!r})."
        )


def initialize_plugins(env):
    """Initializes the plugins for the environment."""
    for ep in metadata.entry_points(group="lektor.plugins"):
        if ep.dist is not None:
            _check_dist_name(ep.dist.metadata["Name"], ep.name)
        plugin_id = ep.name
        plugin_cls = ep.load()
        env.plugin_controller.instanciate_plugin(plugin_id, plugin_cls, ep.dist)
    env.plugin_controller.emit("setup-env")


class PluginController:
    """Helper management class that is used to control plugins through
    the environment.
    """

    def __init__(self, env, extra_flags=None):
        self._env = weakref(env)
        self.extra_flags = extra_flags

    @property
    def env(self):
        rv = self._env()
        if rv is None:
            raise RuntimeError("Environment went away")
        return rv

    def instanciate_plugin(
        self,
        plugin_id: str,
        plugin_cls: type[Plugin],
        dist: metadata.Distribution | None = None,
    ) -> None:
        env = self.env
        if plugin_id in env.plugins:
            raise RuntimeError(f'Plugin "{plugin_id}" is already registered')
        plugin = plugin_cls(env, plugin_id)
        # Plugin.version needs the source distribution to be able to cleanly determine
        # the plugin version.  For reasons of backward compatibility, we don't want to
        # change the signature of the constructor, so we stick it in a private attribute
        # here.
        plugin._Plugin__dist = dist
        env.plugins[plugin_id] = plugin
        env.plugin_ids_by_class[plugin_cls] = plugin_id

    def iter_plugins(self):
        # XXX: sort?
        return self.env.plugins.values()

    def emit(self, event, **kwargs):
        """Invoke event hook for all plugins that support it.

        Any ``kwargs`` are passed to the hook methods.

        Returns a dict mapping plugin ids to hook method return values.
        """
        rv = {}
        extra_flags = process_extra_flags(self.extra_flags)
        funcname = "on_" + event.replace("-", "_")
        for plugin in self.iter_plugins():
            handler = getattr(plugin, funcname, None)
            if handler is not None:
                kw = {**kwargs, "extra_flags": extra_flags}
                try:
                    inspect.signature(handler).bind(**kw)
                except TypeError:
                    del kw["extra_flags"]
                rv[plugin.id] = handler(**kw)
                if "extra_flags" not in kw:
                    warnings.warn(
                        # deprecated since 3.2.0
                        f"The plugin {plugin.id!r} function {funcname!r} does not "
                        "accept extra_flags. "
                        "It should be updated to accept `**extra` so that it will "
                        "not break if new parameters are passed to it by newer "
                        "versions of Lektor.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
        return rv
