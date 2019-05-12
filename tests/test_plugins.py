import textwrap
import os
import shutil

import pytest

from lektor._compat import PY2
from lektor.cli import cli


clean_events = ["before_prune", "after_prune", "setup_env"]
build_events = clean_events + [
    "before_build",
    "before_build_all",
    "after_build",
    "after_build_all",
    "markdown_meta_init",
    "markdown_meta_postprocess",
    "process_template_context",
]
all_events = build_events + [
    # Only during creation of markdown threadlocal object. I.e. only emitted on build
    # on the first render of the *entire* test suite, or else a lot of lib load hacking.
    "markdown_config",
    "markdown_lexer_config",
    # Only during `lektor server` command, never on build or other commands.
    "server_spawn",
    "server_stop",
]


@pytest.fixture(scope="function")
def scratch_project_with_plugin(scratch_project_data, request, isolated_cli_runner):
    """Create a scratch project and add a plugin that has the named event listener.

    Return (project, current event, and attached cli_runner).
    """
    base = scratch_project_data

    # Minimum viable setup.py
    current_test_index = (request.param_index,) * 4
    setup_text = textwrap.dedent(
        u"""
        from setuptools import setup

        setup(
            name='lektor-event-test{}',
            entry_points={{
                'lektor.plugins': [
                    'event-test{} = lektor_event_test{}:EventTestPlugin{}',
                ]
            }}
        )
    """
    ).format(*current_test_index)
    base.join(
        "packages", "event-test{}".format(request.param_index), "setup.py"
    ).write_text(setup_text, "utf8", ensure=True)

    # Minimum plugin code
    plugin_text = textwrap.dedent(
        u"""
        from lektor.pluginsystem import Plugin
        import os

        class EventTestPlugin{}(Plugin):
            name = 'Event Test'
            description = u'Non-empty string'

            def on_{}(self, **extra):
                print("event on_{}", extra['extra_flags'])
                return extra
    """
    ).format(request.param_index, request.param, request.param)
    base.join(
        "packages",
        "event-test{}".format(request.param_index),
        "lektor_event_test{}.py".format(request.param_index),
    ).write_text(plugin_text, "utf8", ensure=True)

    template_text = textwrap.dedent(
        u"""
        <h1>{{ "**Title**"|markdown }}</h1>
        {{ this.body }}
    """
    )
    base.join("templates", "page.html").write_text(template_text, "utf8", ensure=True)

    # Move into isolated path.
    for entry in os.listdir(str(base)):
        entry_path = os.path.join(str(base), entry)
        if os.path.isdir(entry_path):
            shutil.copytree(entry_path, entry)
        else:
            shutil.copy2(entry_path, entry)

    from lektor.project import Project

    yield (Project.from_path(str(base)), request.param, isolated_cli_runner)


@pytest.mark.parametrize("scratch_project_with_plugin", build_events, indirect=True)
def test_plugin_build_events_via_cli(scratch_project_with_plugin):
    """Test whether a plugin with a given event can successfully use an extra flag.
    """
    proj, event, cli_runner = scratch_project_with_plugin

    result = cli_runner.invoke(cli, ["build", "-f", "EXTRA"])
    assert result.exit_code == 0

    # Test that the event was triggered and the current extra flag was passed.
    output_lines = result.output.split("\n")

    # XXX - take a closer look at result.output
    # The setuptools working_set that keeps track of plugin installations is initialized
    # at the first import of pkg_resources, and then plugins are added to the
    # working_set as they are loaded into Lektor. Since pytest runs a single process,
    # these previous plugins are never removed. So while this does test what it says it
    # does, it also hooks previously generated plugins. Avoiding this with a succint
    # teardown is currently not possible AFAICT, since setuptools provides no clear way
    # of removing entry_points. I choose this comment over what would be a convoluted and
    # very hacky teardown function. The extra computation time is negligible.
    # See https://github.com/pypa/setuptools/issues/1759

    hits = [r for r in output_lines if "event on_{}".format(event) in r]

    for hit in hits:
        if PY2:
            assert "{u'EXTRA': u'EXTRA'}" in hit
        else:
            assert "{'EXTRA': 'EXTRA'}" in hit

    assert len(hits) != 0


@pytest.mark.parametrize("scratch_project_with_plugin", clean_events, indirect=True)
def test_plugin_clean_events_via_cli(scratch_project_with_plugin):
    """Test whether a plugin with a given event can successfully use an extra flag.
    """
    proj, event, cli_runner = scratch_project_with_plugin

    # See comment in test_plugin_build_events_via_cli
    result = cli_runner.invoke(cli, ["clean", "--yes", "-f", "EXTRA"])
    assert result.exit_code == 0

    # Test that the event was triggered and the current extra flag was passed.
    output_lines = result.output.split("\n")

    hits = [r for r in output_lines if "event on_{}".format(event) in r]

    for hit in hits:
        if PY2:
            assert "{u'EXTRA': u'EXTRA'}" in hit
        else:
            assert "{'EXTRA': 'EXTRA'}" in hit

    assert len(hits) != 0


@pytest.mark.parametrize("scratch_project_with_plugin", all_events, indirect=True)
def test_env_extra_flag_passthrough(scratch_project_with_plugin):
    """Test whether setting extra_flags passes through to each plugin event.
    """
    from lektor.environment import Environment

    proj, event, cli_runner = scratch_project_with_plugin

    extra = {"extra": "extra"}
    env = Environment(proj, extra_flags=extra)
    plugin_return = env.plugin_controller.emit(event)
    for plugin in plugin_return:
        assert plugin_return[plugin]["extra_flags"] == extra


@pytest.mark.parametrize("scratch_project_with_plugin", ["setup_env"], indirect=True)
def test_multiple_extra_flags(scratch_project_with_plugin):
    """Test whether setting extra_flags passes through to each plugin event.
    """
    proj, event, cli_runner = scratch_project_with_plugin

    # See comment in test_plugin_build_events_via_cli
    result = cli_runner.invoke(cli, ["build", "-f", "EXTRA", "-f", "ANOTHER"])
    assert result.exit_code == 0

    # Test that the event was triggered and the current extra flag was passed.
    output_lines = result.output.split("\n")

    hits = [r for r in output_lines if "event on_{}".format(event) in r]

    for hit in hits:
        assert "EXTRA" in hit
        assert "ANOTHER" in hit

    assert len(hits) != 0
