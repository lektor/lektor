import textwrap
import os

from lektor._compat import PY2
from lektor.cli import cli
from lektor.quickstart import get_default_author, get_default_author_email

def test_new_plugin(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["dev", "new-plugin"],
                                       input='Plugin Name\n'
                                       '\n'
                                       'Author Name\n'
                                       'author@email.com\n'
                                       'y\n'
    )
    assert "Create Plugin?" in result.output
    path = os.path.join(os.path.abspath('packages'), 'plugin-name')
    assert set(os.listdir(path)) == set(['lektor_plugin_name.py', 'setup.py', '.gitignore'])
    assert result.exit_code == 0

    # gitignore
    gitignore_expected = textwrap.dedent("""
        dist
        build
        *.pyc
        *.pyo
        *.egg-info
    """).strip()
    with open(os.path.join(path, '.gitignore')) as f:
        gitignore_contents = f.read().strip()
    assert gitignore_contents == gitignore_expected

    # setup.py
    setup_expected = textwrap.dedent("""
        from setuptools import setup

        setup(
            name='lektor-plugin-name',
            version='0.1',
            author={}'Author Name',
            author_email='author@email.com',
            license='MIT',
            py_modules=['lektor_plugin_name'],
            entry_points={{
                'lektor.plugins': [
                    'plugin-name = lektor_plugin_name:PluginNamePlugin',
                ]
            }}
        )
    """).strip()
    if PY2:
        setup_expected = setup_expected.format("u")
    else:
        setup_expected = setup_expected.format("")
    with open(os.path.join(path, 'setup.py')) as f:
        setup_contents = f.read().strip()
    assert setup_contents == setup_expected

    # plugin.py
    plugin_expected = textwrap.dedent("""
        # -*- coding: utf-8 -*-
        from lektor.pluginsystem import Plugin


        class PluginNamePlugin(Plugin):
            name = 'Plugin Name'
            description = u'Add your description here.'

            def on_process_template_context(self, context, **extra):
                def test_function():
                    return 'Value from plugin %s' % self.name
                context['test_function'] = test_function
    """).strip()
    with open(os.path.join(path, 'lektor_plugin_name.py')) as f:
        plugin_contents = f.read().strip()
    assert plugin_contents == plugin_expected


def test_new_plugin_abort_plugin_exists(project_cli_runner):
    path = os.path.abspath('packages')
    os.mkdir(path)
    os.mkdir(os.path.join(path, 'plugin-name'))
    result = project_cli_runner.invoke(cli, ["dev", "new-plugin"],
                                       input='Plugin Name\n'
                                       '\n'
                                       'Author Name\n'
                                       'author@email.com\n'
                                       'y\n'
    )
    assert "Aborted!" in result.output
    assert result.exit_code == 1


def test_new_plugin_abort_cancel(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["dev", "new-plugin"],
                                       input='Plugin Name\n'
                                       '\n'
                                       'Author Name\n'
                                       'author@email.com\n'
                                       'n\n'
    )
    assert "Aborted!" in result.output
    assert result.exit_code == 1


def test_new_plugin_name_only(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["dev", "new-plugin"],
                                       input='Plugin Name\n'
                                       '\n'
                                       '\n'
                                       '\n'
                                       'y\n'
    )
    path = os.path.abspath('packages')
    assert os.listdir(path) == ['plugin-name']
    assert result.exit_code == 0

    # setup.py
    author = get_default_author()
    author_email = get_default_author_email()
    setup_expected = textwrap.dedent("""
        from setuptools import setup

        setup(
            name='lektor-plugin-name',
            version='0.1',
            author={}'{}',
            author_email='{}',
            license='MIT',
            py_modules=['lektor_plugin_name'],
            entry_points={{
                'lektor.plugins': [
                    'plugin-name = lektor_plugin_name:PluginNamePlugin',
                ]
            }}
        )
    """).strip()
    if PY2:
        setup_expected = setup_expected.format("u", author, author_email)
    else:
        setup_expected = setup_expected.format("", author, author_email)
    with open(os.path.join(path, 'plugin-name', 'setup.py')) as f:
        setup_contents = f.read().strip()
    assert setup_contents == setup_expected


def test_new_plugin_name_param(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["dev", "new-plugin", "plugin-name"],
                                       input='\n'
                                       'Author Name\n'
                                       'author@email.com\n'
                                       'y\n'
    )
    path = os.path.abspath('packages')
    assert os.listdir(path) == ['plugin-name']
    assert result.exit_code == 0


def test_new_plugin_path(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["dev", "new-plugin"],
                                       input='Plugin Name\n'
                                       'path\n'
                                       'Author Name\n'
                                       'author@email.com\n'
                                       'y\n'
    )
    path = os.path.abspath('path')
    assert set(os.listdir(path)) == set(['lektor_plugin_name.py', 'setup.py', '.gitignore'])
    assert result.exit_code == 0


def test_new_plugin_path_param(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["dev", "new-plugin", "--path", "path"],
                                       input='Plugin Name\n'
                                       'Author Name\n'
                                       'author@email.com\n'
                                       'y\n'
    )
    path = os.path.abspath('path')
    assert set(os.listdir(path)) == set(['lektor_plugin_name.py', 'setup.py', '.gitignore'])
    assert result.exit_code == 0


def test_new_plugin_path_and_name_params(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["dev", "new-plugin", "plugin-name", "--path", "path"],
                                       input='Author Name\n'
                                       'author@email.com\n'
                                       'y\n'
    )
    path = os.path.abspath('path')
    assert set(os.listdir(path)) == set(['lektor_plugin_name.py', 'setup.py', '.gitignore'])
    assert result.exit_code == 0
