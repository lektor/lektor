"""Unit tests for lektor.pluginsystem.
"""
from pathlib import Path
from unittest import mock

import pkg_resources
import pytest

from lektor.cli import cli
from lektor.context import Context
from lektor.packages import add_package_to_project
from lektor.pluginsystem import get_plugin
from lektor.pluginsystem import load_plugins
from lektor.pluginsystem import Plugin
from lektor.pluginsystem import PluginController


class DummyPlugin(Plugin):
    name = "Dummy Plugin"
    description = "For testing"

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


@pytest.fixture(autouse=True)
def dummy_plugin_calls(monkeypatch):
    """Reset list of DummyPlugin hook calls for each test."""
    monkeypatch.setattr(DummyPlugin, "calls", [])
    return DummyPlugin.calls


class DummyEntryPointMetadata:
    """Implement enough of `pkg_resources.IMetadataProvider` to convince a
    Distribution that it has an entry point.
    """

    # pylint: disable=no-self-use

    def __init__(self, entry_points_txt):
        self.entry_points_txt = entry_points_txt

    def has_metadata(self, name):
        return name == "entry_points.txt"

    def get_metadata(self, name):
        return self.entry_points_txt if name == "entry_points.txt" else ""

    def get_metadata_lines(self, name):
        return pkg_resources.yield_lines(self.get_metadata(name))


@pytest.fixture
def dummy_plugin_distribution_name():
    return "lektor-dummy-plugin"


@pytest.fixture
def dummy_plugin_distribution(dummy_plugin_distribution_name, save_sys_path):
    """Add a dummy plugin distribution to the current working_set."""
    dist = pkg_resources.Distribution(
        project_name=dummy_plugin_distribution_name,
        metadata=DummyEntryPointMetadata(
            f"""
            [lektor.plugins]
            dummy-plugin = {__name__}:DummyPlugin
            """
        ),
        version="1.23",
        location=__file__,
    )
    pkg_resources.working_set.add(dist)
    return dist


@pytest.fixture
def dummy_plugin(env):
    """Instantiate and register a dummy plugin in env"""
    env.plugin_controller.instanciate_plugin("dummy-plugin", DummyPlugin)
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
    def scratch_plugin(self, scratch_env):
        """Instantiate and register a dummy plugin with scratch_env"""
        scratch_env.plugin_controller.instanciate_plugin("dummy-plugin", DummyPlugin)
        return scratch_env.plugins["dummy-plugin"]

    def test_env(self, dummy_plugin, env):
        assert dummy_plugin.env is env

    def test_env_went_away(self):
        env = mock.Mock(name="env", spec=())
        plugin = DummyPlugin(env, "dummy-plugin")
        del env
        with pytest.raises(RuntimeError, match=r"Environment went away"):
            getattr(plugin, "env")

    def test_version(self, dummy_plugin, dummy_plugin_distribution):
        assert dummy_plugin.version == dummy_plugin_distribution.version

    def test_path(self, dummy_plugin):
        assert dummy_plugin.path == str(Path(__file__).parent)

    @pytest.mark.requiresinternet
    @pytest.mark.usefixtures("save_sys_path")
    def test_path_installed_plugin_is_none(self, scratch_project):
        # XXX: this test is slow and fragile. (It won't run
        # without an internet connection.)
        add_package_to_project(scratch_project, "webpack-support")
        env = scratch_project.make_env()
        plugin = get_plugin("webpack-support", env)
        assert plugin.path is None

    def test_import_name(self, dummy_plugin):
        assert dummy_plugin.import_name == "test_pluginsystem:DummyPlugin"

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
            "name": DummyPlugin.name,
            "description": DummyPlugin.description,
            "version": dummy_plugin_distribution.version,
            "import_name": "test_pluginsystem:DummyPlugin",
            "path": str(Path(__file__).parent),
        }


def test_load_plugins(dummy_plugin_distribution):
    assert load_plugins() == {"dummy-plugin": DummyPlugin}


@pytest.mark.parametrize("dummy_plugin_distribution_name", ["evil-dist-name"])
def test_load_plugins_bad_distname(dummy_plugin_distribution):
    with pytest.raises(RuntimeError, match=r"Disallowed distribution name"):
        load_plugins()


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
            getattr(plugin_controller, "env")

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
