"""Unit tests for lektor.pluginsystem."""

from __future__ import annotations

import inspect
import sys
from importlib import metadata
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from pathlib import Path
from unittest import mock

import pytest

from lektor.cli import cli
from lektor.context import Context
from lektor.packages import add_package_to_project
from lektor.pluginsystem import _check_dist_name
from lektor.pluginsystem import get_plugin
from lektor.pluginsystem import Plugin
from lektor.pluginsystem import PluginController


class DummyPlugin(Plugin):
    # DummyPlugin.calls is test-local (see fixture dummy_plugin_calls, below)
    calls = []

    def __getattr__(self, name):
        if not name.startswith("on_"):
            raise AttributeError(name)

        event = name[3:].replace("_", "-")

        def hook(extra_flags, **kwargs):
            call = {
                "event": event,
                "extra_flags": extra_flags,
                "kwargs": kwargs,
            }
            self.calls.append(call)
            return f"{event} return value"

        return hook

    def on_legacy_event(self):
        self.calls.append({"event": "legacy-event"})
        return "legacy-event return value"

    def on_one_type_error(self, **kwargs):
        """Raises TypeError only on the first call."""
        self.calls.append({"event": "one-type-error"})
        if len(self.calls) == 1:
            raise TypeError("test")
        return "one-type-error return value"


@pytest.fixture(autouse=True)
def dummy_plugin_calls(monkeypatch):
    """Reset list of DummyPlugin hook calls for each test."""
    monkeypatch.setattr(DummyPlugin, "calls", [])
    return DummyPlugin.calls


class DummyDistribution(metadata.Distribution):
    _files = {
        "top_level.txt": f"{__name__}\n",
        "entry_points.txt": inspect.cleandoc(
            f"""
            [lektor.plugins]
            dummy-plugin = {__name__}:DummyPlugin
            """
        ),
    }

    # Allow overriding inherited properties with class attributes
    metadata = None

    def __init__(self, metadata):
        self.metadata = metadata

    def read_text(self, filename):
        return self._files.get(filename)

    def locate_file(self, path):  # pylint: disable=no-self-use
        return None


class DummyPluginLoader(Loader):
    # pylint: disable=abstract-method
    # pylint: disable=no-self-use

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.DummyPlugin = DummyPlugin


class DummyPluginFinder(metadata.DistributionFinder):
    def __init__(self, module: str, distribution: metadata.Distribution):
        self.module = module
        self.distribution = distribution

    def find_spec(self, fullname, path, target=None):
        if fullname == self.module and path is None:
            return ModuleSpec(fullname, DummyPluginLoader())
        return None

    def find_distributions(
        self, context: metadata.DistributionFinder.Context | None = None
    ):
        return [self.distribution]


@pytest.fixture
def dummy_plugin_distribution(save_sys_path):
    """Add a dummy plugin distribution to the current working_set."""
    dist = DummyDistribution(
        {
            "Name": "lektor-dummy-plugin",
            "Summary": "The description.",
            "Version": "1.23",
        }
    )
    finder = DummyPluginFinder(__name__, dist)
    # The save_sys_path fixture will restore meta_path at end of test
    sys.meta_path.insert(0, finder)
    return dist


@pytest.fixture
def dummy_plugin(env, dummy_plugin_distribution):
    """Instantiate and register a dummy plugin in env"""
    env.plugin_controller.instanciate_plugin(
        "dummy-plugin", DummyPlugin, dummy_plugin_distribution
    )
    return env.plugins["dummy-plugin"]


def test_get_plugin(env, dummy_plugin):
    assert get_plugin("dummy-plugin", env) == dummy_plugin


def test_get_plugin_from_context(env, dummy_plugin):
    with Context(pad=env.new_pad()):
        assert get_plugin("dummy-plugin") == dummy_plugin


def test_get_plugin_missing(env):
    with pytest.raises(LookupError, match=r"Plugin .* not found"):
        get_plugin("dummy-plugin", env)


def test_get_plugin_no_env_or_ctx(dummy_plugin):
    with pytest.raises(RuntimeError, match=r"Context is unavailable"):
        get_plugin("dummy-plugin")


class TestPlugin:
    # pylint: disable=no-self-use

    @pytest.fixture
    def scratch_project_data(self, scratch_project_data):
        """Add plugin config file to scratch project."""
        plugin_ini = scratch_project_data / "configs/dummy-plugin.ini"
        plugin_ini.parent.mkdir(exist_ok=True)
        plugin_ini.write_text("test_setting = test value\n", "utf-8")
        return scratch_project_data

    @pytest.fixture
    def scratch_plugin(self, scratch_env, dummy_plugin_distribution):
        """Instantiate and register a dummy plugin with scratch_env"""
        scratch_env.plugin_controller.instanciate_plugin(
            "dummy-plugin", DummyPlugin, dummy_plugin_distribution
        )
        return scratch_env.plugins["dummy-plugin"]

    def test_env(self, dummy_plugin, env):
        assert dummy_plugin.env is env

    def test_env_went_away(self):
        env = mock.Mock(name="env", spec=())
        plugin = DummyPlugin(env, "dummy-plugin")
        del env
        with pytest.raises(RuntimeError, match=r"Environment went away"):
            _ = plugin.env

    def test_name(self, dummy_plugin, dummy_plugin_distribution):
        assert dummy_plugin.name == "Dummy"

    def test_description(self, dummy_plugin, dummy_plugin_distribution):
        assert dummy_plugin.description == dummy_plugin_distribution.metadata["Summary"]

    def test_description_fallback(self, env):
        # Create a plugin with no associated distribution.
        # (This shouldn't happen in real Lektor runs.)
        plugin = DummyPlugin(env, "dummy")
        assert "no description available" in plugin.description

    def test_version(self, dummy_plugin, dummy_plugin_distribution):
        assert dummy_plugin.version == dummy_plugin_distribution.version

    def test_version_missing(self, env):
        # Instantiate plugin without specifying distribution
        env.plugin_controller.instanciate_plugin("dummy-plugin", DummyPlugin)
        plugin = env.plugins["dummy-plugin"]
        assert plugin.version is None

    def test_path(self, dummy_plugin):
        assert dummy_plugin.path == str(Path(__file__).parent)

    @pytest.mark.requiresinternet
    @pytest.mark.slowtest
    @pytest.mark.usefixtures("save_sys_path")
    def test_path_installed_plugin_is_none(self, scratch_project):
        # XXX: this test is slow and fragile. (It won't run
        # without an internet connection.)
        add_package_to_project(scratch_project, "webpack-support")
        env = scratch_project.make_env()
        plugin = get_plugin("webpack-support", env)
        assert plugin.path is None

    def test_import_name(self, dummy_plugin):
        assert dummy_plugin.import_name == f"{__name__}:DummyPlugin"

    def test_get_lektor_config(self, dummy_plugin):
        cfg = dummy_plugin.get_lektor_config()
        assert cfg["PROJECT"]["name"] == "Demo Project"

    def test_get_lektor_config_from_context(self, dummy_plugin, env):
        with Context(pad=env.new_pad()):
            cfg = dummy_plugin.get_lektor_config()
        assert cfg["PROJECT"]["name"] == "Demo Project"

    def test_config_filename(self, dummy_plugin, env):
        configdir = Path(env.root_path) / "configs"
        assert dummy_plugin.config_filename == str(configdir / "dummy-plugin.ini")

    def test_get_config(self, scratch_plugin):
        cfg = scratch_plugin.get_config()
        assert cfg["test_setting"] == "test value"

    def test_get_config_records_dependency(self, scratch_plugin, scratch_env):
        with Context(pad=scratch_env.new_pad()) as ctx:
            scratch_plugin.get_config()
        assert scratch_plugin.config_filename in ctx.referenced_dependencies

    def test_get_config_returns_cached_value(self, scratch_plugin, scratch_env):
        with Context(pad=scratch_env.new_pad()):
            cfg = scratch_plugin.get_config()
            cfg["is_cached"] = "indeed"
            cfg = scratch_plugin.get_config()
        assert "is_cached" in cfg

    def test_get_config_fresh(self, scratch_plugin, scratch_env):
        with Context(pad=scratch_env.new_pad()):
            cfg = scratch_plugin.get_config()
            cfg["is_cached"] = "indeed"
            cfg = scratch_plugin.get_config(fresh=True)
        assert "is_cached" not in cfg

    def test_emit(self, dummy_plugin):
        rv = dummy_plugin.emit("subevent")
        assert rv == {"dummy-plugin": "dummy-plugin-subevent return value"}
        events = [call["event"] for call in dummy_plugin.calls]
        assert events == ["dummy-plugin-subevent"]

    def test_to_json(self, dummy_plugin, dummy_plugin_distribution):
        assert dummy_plugin.to_json() == {
            "id": "dummy-plugin",
            "name": dummy_plugin.name,
            "description": dummy_plugin.description,
            "version": dummy_plugin_distribution.version,
            "import_name": f"{__name__}:DummyPlugin",
            "path": str(Path(__file__).parent),
        }


@pytest.mark.parametrize(
    "dist_name, plugin_id",
    [
        ("Lektor-FOO", "Foo"),
    ],
)
def test_check_dist_name(dist_name, plugin_id):
    _check_dist_name(dist_name, plugin_id)


@pytest.mark.parametrize(
    "dist_name, plugin_id",
    [
        ("NotLektor-FOO", "Foo"),
    ],
)
def test_check_dist_name_raises(dist_name, plugin_id):
    with pytest.raises(RuntimeError):
        _check_dist_name(dist_name, plugin_id)


class TestPluginController:
    # pylint: disable=no-self-use

    @pytest.fixture
    def extra_flags(self):
        return {"flag": "value"}

    @pytest.fixture
    def plugin_controller(self, env, extra_flags):
        return PluginController(env, extra_flags)

    def test_env(self, plugin_controller, env):
        assert plugin_controller.env is env

    def test_env_went_away(self):
        env = mock.Mock(name="env", spec=())
        plugin_controller = PluginController(env)
        del env
        with pytest.raises(RuntimeError, match=r"Environment went away"):
            _ = plugin_controller.env

    def test_instantiate_plugin(self, plugin_controller, env):
        plugin_controller.instanciate_plugin("plugin-id", DummyPlugin)
        assert isinstance(env.plugins["plugin-id"], DummyPlugin)
        assert env.plugin_ids_by_class[DummyPlugin] == "plugin-id"

    def test_instantiate_plugin_error(self, plugin_controller, dummy_plugin):
        with pytest.raises(RuntimeError, match=r"already registered"):
            plugin_controller.instanciate_plugin(dummy_plugin.id, DummyPlugin)

    def test_iter_plugins(self, plugin_controller, dummy_plugin):
        assert list(plugin_controller.iter_plugins()) == [dummy_plugin]

    def test_emit(self, plugin_controller, dummy_plugin, extra_flags):
        rv = plugin_controller.emit("test-event")
        assert rv == {dummy_plugin.id: "test-event return value"}
        (call,) = dummy_plugin.calls
        assert call["extra_flags"] == extra_flags

    def test_emit_with_kwargs(self, plugin_controller, dummy_plugin):
        rv = plugin_controller.emit("another-test-event", another_arg="x")
        assert rv == {dummy_plugin.id: "another-test-event return value"}
        (call,) = dummy_plugin.calls
        assert call["kwargs"] == {"another_arg": "x"}

    def test_emit_deprecation_warning(self, plugin_controller, dummy_plugin):
        with pytest.deprecated_call():
            rv = plugin_controller.emit("legacy-event")
        assert rv == {dummy_plugin.id: "legacy-event return value"}

    def test_emit_is_not_confused_by_type_error(self, plugin_controller, dummy_plugin):
        # Excercises https://github.com/lektor/lektor/issues/1085
        with pytest.raises(TypeError):
            plugin_controller.emit("one-type-error")
        rv = plugin_controller.emit("one-type-error")
        assert rv == {dummy_plugin.id: "one-type-error return value"}


@pytest.mark.usefixtures("dummy_plugin_distribution")
def test_cli_integration(project, cli_runner, monkeypatch):
    """Check that plugin hooks receive extra_flags from command line."""
    # chdir to tests/demo-project
    monkeypatch.chdir(project.tree)
    result = cli_runner.invoke(
        cli, ["clean", "--yes", "-f", "flag1", "--extra-flag", "flag2:value2"]
    )
    print(result.output)
    assert result.exit_code == 0
    assert {"before-prune", "after-prune", "setup-env"}.issubset(
        call["event"] for call in DummyPlugin.calls
    )
    for call in DummyPlugin.calls:
        assert call["extra_flags"] == {"flag1": "flag1", "flag2": "value2"}
