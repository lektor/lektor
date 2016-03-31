import os
import sys
import pkg_resources

from weakref import ref as weakref
from inifile import IniFile

from lektor._compat import iteritems, itervalues
from lektor.context import get_ctx


def get_plugin(plugin_id_or_class, env=None):
    """Looks up the plugin instance by id or class."""
    if env is None:
        ctx = get_ctx()
        if ctx is None:
            raise RuntimeError('Context is unavailable and no environment '
                               'was passed to the function.')
        env = ctx.env
    plugin_id = env.plugin_ids_by_class.get(plugin_id_or_class,
                                            plugin_id_or_class)
    try:
        return env.plugins[plugin_id]
    except KeyError:
        raise LookupError('Plugin %r not found' % plugin_id)


class Plugin(object):
    """This needs to be subclassed for custom plugins."""
    name = 'Your Plugin Name'
    description = 'Description goes here'

    def __init__(self, env, id):
        self._env = weakref(env)
        self.id = id

    @property
    def env(self):
        rv = self._env()
        if rv is None:
            raise RuntimeError('Environment went away')
        return rv

    @property
    def version(self):
        from pkg_resources import get_distribution
        return get_distribution('lektor-' + self.id).version

    @property
    def path(self):
        mod = sys.modules[self.__class__.__module__.split('.')[0]]
        path = os.path.abspath(os.path.dirname(mod.__file__))
        if not path.startswith(self.env.project.get_package_cache_path()):
            return path

    @property
    def import_name(self):
        return self.__class__.__module__ + ':' + self.__class__.__name__

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
        return os.path.join(self.env.root_path, 'configs', self.id + '.ini')

    def get_config(self, fresh=False):
        """Returns the config specific for this plugin.  By default this
        will be cached for the current build context but this can be
        disabled by passing ``fresh=True``.
        """
        ctx = get_ctx()
        if ctx is not None and not fresh:
            cache = ctx.cache.setdefault(__name__ + ':configs', {})
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
        return self.env.pluginsystem.emit(self.id + '-' + event, **kwargs)

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'path': self.path,
            'import_name': self.import_name,
        }


def load_plugins():
    """Loads all available plugins and returns them."""
    rv = {}
    for ep in pkg_resources.iter_entry_points('lektor.plugins'):
        match_name = 'lektor-' + ep.name.lower()
        if match_name != ep.dist.project_name.lower():
            raise RuntimeError('Mismatching entry point name.  Found '
                               '"%s" but expected "%s" for package "%s".'
                               % (ep.name, ep.dist.project_name[7:],
                                  ep.dist.project_name))
        rv[ep.name] = ep.load()
    return rv


def initialize_plugins(env):
    """Initializes the plugins for the environment."""
    plugins = load_plugins()
    for plugin_id, plugin_cls in iteritems(plugins):
        env.plugin_controller.instanciate_plugin(plugin_id, plugin_cls)
    env.plugin_controller.emit('setup-env')


class PluginController(object):
    """Helper management class that is used to control plugins through
    the environment.
    """

    def __init__(self, env):
        self._env = weakref(env)

    @property
    def env(self):
        rv = self._env()
        if rv is None:
            raise RuntimeError('Environment went away')
        return rv

    def instanciate_plugin(self, plugin_id, plugin_cls):
        env = self.env
        if plugin_id in env.plugins:
            raise RuntimeError('Plugin "%s" is already registered'
                               % plugin_id)
        env.plugins[plugin_id] = plugin_cls(env, plugin_id)
        env.plugin_ids_by_class[plugin_cls] = plugin_id

    def iter_plugins(self):
        # XXX: sort?
        return itervalues(self.env.plugins)

    def emit(self, event, **kwargs):
        rv = {}
        funcname = 'on_' + event.replace('-', '_')
        for plugin in self.iter_plugins():
            handler = getattr(plugin, funcname, None)
            if handler is not None:
                rv[plugin.id] = handler(**kwargs)
        return rv
