import os
import textwrap

import pytest
from inifile import IniFile

from lektor._compat import PY2
from lektor.cli import cli
from lektor.quickstart import get_default_author
from lektor.quickstart import get_default_author_email


# new-plugin
def test_new_plugin(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-plugin"],
        input="Plugin Name\n" "\n" "Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Plugin?" in result.output
    assert result.exit_code == 0
    path = os.path.join("packages", "plugin-name")
    assert set(os.listdir(path)) == set(
        ["lektor_plugin_name.py", "setup.cfg", "setup.py", ".gitignore", "README.md"]
    )

    # gitignore
    gitignore_expected = textwrap.dedent(
        """
        dist
        build
        *.pyc
        *.pyo
        *.egg-info
    """
    ).strip()
    with open(os.path.join(path, ".gitignore")) as f:
        gitignore_contents = f.read().strip()
    assert gitignore_contents == gitignore_expected

    # README.md
    readme_expected = textwrap.dedent(
        """
        # Plugin Name

        This is where a description of your plugin goes.
        Provide usage instructions here.
    """
    ).strip()
    with open(os.path.join(path, "README.md")) as f:
        readme_contents = f.read().strip()
    assert readme_contents == readme_expected

    # setup.py
    setup_expected = textwrap.dedent(
        """
        import ast
        import io
        import re

        from setuptools import setup, find_packages

        with io.open('README.md', 'rt', encoding="utf8") as f:
            readme = f.read()

        _description_re = re.compile(r'description\\s+=\\s+(?P<description>.*)')

        with open('lektor_plugin_name.py', 'rb') as f:
            description = str(ast.literal_eval(_description_re.search(
                f.read().decode('utf-8')).group(1)))

        setup(
            author={}'Author Name',
            author_email='author@email.com',
            description=description,
            keywords='Lektor plugin',
            license='MIT',
            long_description=readme,
            long_description_content_type='text/markdown',
            name='lektor-plugin-name',
            packages=find_packages(),
            py_modules=['lektor_plugin_name'],
            # url='[link to your repository]',
            version='0.1',
            classifiers=[
                'Framework :: Lektor',
                'Environment :: Plugins',
            ],
            entry_points={{
                'lektor.plugins': [
                    'plugin-name = lektor_plugin_name:PluginNamePlugin',
                ]
            }}
        )
    """
    ).strip()
    if PY2:
        setup_expected = setup_expected.format("u")
    else:
        setup_expected = setup_expected.format("")
    with open(os.path.join(path, "setup.py")) as f:
        setup_contents = f.read().strip()
    assert setup_contents == setup_expected

    # plugin.py
    plugin_expected = textwrap.dedent(
        """
        # -*- coding: utf-8 -*-
        from lektor.pluginsystem import Plugin


        class PluginNamePlugin(Plugin):
            name = {}'Plugin Name'
            description = u'Add your description here.'

            def on_process_template_context(self, context, **extra):
                def test_function():
                    return 'Value from plugin %s' % self.name
                context['test_function'] = test_function
    """
    ).strip()
    if PY2:
        plugin_expected = plugin_expected.format("u")
    else:
        plugin_expected = plugin_expected.format("")
    with open(os.path.join(path, "lektor_plugin_name.py")) as f:
        plugin_contents = f.read().strip()
    assert plugin_contents == plugin_expected


def test_new_plugin_abort_plugin_exists(project_cli_runner):
    path = "packages"
    os.mkdir(path)
    os.mkdir(os.path.join(path, "plugin-name"))
    input = "Plugin Name\n\nAuthor Name\nauthor@email.com\ny\n"
    result = project_cli_runner.invoke(cli, ["dev", "new-plugin"], input=input)
    assert "Aborted!" in result.output
    assert result.exit_code == 1


def test_new_plugin_abort_cancel(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-plugin"],
        input="Plugin Name\n" "\n" "Author Name\n" "author@email.com\n" "n\n",
    )
    assert "Aborted!" in result.output
    assert result.exit_code == 1


def test_new_plugin_name_only(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-plugin"],
        input="Plugin Name\n" "\n" "\n" "\n" "y\n",
    )
    assert "Create Plugin?" in result.output
    assert result.exit_code == 0
    path = "packages"
    assert os.listdir(path) == ["plugin-name"]

    # setup.py
    author = get_default_author()
    author_email = get_default_author_email()
    setup_expected = textwrap.dedent(
        """
        import ast
        import io
        import re

        from setuptools import setup, find_packages

        with io.open('README.md', 'rt', encoding="utf8") as f:
            readme = f.read()

        _description_re = re.compile(r'description\\s+=\\s+(?P<description>.*)')

        with open('lektor_plugin_name.py', 'rb') as f:
            description = str(ast.literal_eval(_description_re.search(
                f.read().decode('utf-8')).group(1)))

        setup(
            author={}'{}',
            author_email='{}',
            description=description,
            keywords='Lektor plugin',
            license='MIT',
            long_description=readme,
            long_description_content_type='text/markdown',
            name='lektor-plugin-name',
            packages=find_packages(),
            py_modules=['lektor_plugin_name'],
            # url='[link to your repository]',
            version='0.1',
            classifiers=[
                'Framework :: Lektor',
                'Environment :: Plugins',
            ],
            entry_points={{
                'lektor.plugins': [
                    'plugin-name = lektor_plugin_name:PluginNamePlugin',
                ]
            }}
        )
    """
    ).strip()
    if PY2:
        setup_expected = setup_expected.format("u", author, author_email)
    else:
        setup_expected = setup_expected.format("", author, author_email)
    with open(os.path.join(path, "plugin-name", "setup.py")) as f:
        setup_contents = f.read().strip()
    assert setup_contents == setup_expected


def test_new_plugin_name_param(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-plugin", "plugin-name"],
        input="\n" "Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Plugin?" in result.output
    assert result.exit_code == 0
    path = "packages"
    assert os.listdir(path) == ["plugin-name"]


def test_new_plugin_path(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-plugin"],
        input="Plugin Name\n" "path\n" "Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Plugin?" in result.output
    assert result.exit_code == 0
    path = "path"
    assert set(os.listdir(path)) == set(
        ["lektor_plugin_name.py", "setup.cfg", "setup.py", ".gitignore", "README.md"]
    )


def test_new_plugin_path_param(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-plugin", "--path", "path"],
        input="Plugin Name\n" "Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Plugin?" in result.output
    assert result.exit_code == 0
    path = "path"
    assert set(os.listdir(path)) == set(
        ["lektor_plugin_name.py", "setup.cfg", "setup.py", ".gitignore", "README.md"]
    )


def test_new_plugin_path_and_name_params(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-plugin", "plugin-name", "--path", "path"],
        input="Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Plugin?" in result.output
    assert result.exit_code == 0
    path = "path"
    assert set(os.listdir(path)) == set(
        ["lektor_plugin_name.py", "setup.cfg", "setup.py", ".gitignore", "README.md"]
    )


# new-theme
def test_new_theme(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-theme"],
        input="Lektor Theme Name\n" "\n" "Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Theme?" in result.output
    assert result.exit_code == 0
    path = os.path.join("themes", "lektor-theme-name")
    assert set(os.listdir(path)) == set(
        ["example-site", "images", "README.md", "theme.ini"]
    )
    assert set(os.listdir(os.path.join(path, "images"))) == set(["homepage.png"])
    assert set(os.listdir(os.path.join(path, "example-site"))) == set(
        ["lektor-theme-name.lektorproject", "README.md", "themes"]
    )
    try:
        assert (
            os.readlink(os.path.join(path, "example-site/themes/lektor-theme-name"))
            == "../../../lektor-theme-name"
        )
    except AttributeError:
        pass

    theme_inifile = IniFile(os.path.join(path, "theme.ini"))
    assert theme_inifile["theme.name"] == "Lektor Theme Name"
    assert theme_inifile["author.email"] == "author@email.com"
    assert theme_inifile["author.name"] == "Author Name"

    with open(os.path.join(path, "README.md")) as f:
        readme_contents = f.read().strip()
    assert "Lektor Theme Name" in readme_contents


def test_new_theme_abort_theme_exists(project_cli_runner):
    path = "themes"
    os.mkdir(path)
    os.mkdir(os.path.join(path, "lektor-theme-name"))
    input = "Lektor Name\n\nAuthor Name\nauthor@email.com\ny\n"
    result = project_cli_runner.invoke(cli, ["dev", "new-theme"], input=input)
    assert "Aborted!" in result.output
    assert result.exit_code == 1


def test_new_theme_abort_cancel(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-theme"],
        input="Theme Name\n" "\n" "Author Name\n" "author@email.com\n" "n\n",
    )
    assert "Aborted!" in result.output
    assert result.exit_code == 1


def test_new_theme_name_only(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-theme"],
        input="Lektor Name Theme\n" "\n" "\n" "\n" "y\n",
    )
    assert "Create Theme?" in result.output
    assert result.exit_code == 0
    path = os.path.join("themes", "lektor-theme-name")
    assert set(os.listdir(path)) == set(
        ["example-site", "images", "README.md", "theme.ini"]
    )
    assert set(os.listdir(os.path.join(path, "images"))) == set(["homepage.png"])
    assert set(os.listdir(os.path.join(path, "example-site"))) == set(
        ["lektor-theme-name.lektorproject", "README.md", "themes"]
    )
    try:
        assert (
            os.readlink(os.path.join(path, "example-site/themes/lektor-theme-name"))
            == "../../../lektor-theme-name"
        )
    except AttributeError:
        pass

    theme_inifile = IniFile(os.path.join(path, "theme.ini"))
    assert theme_inifile["theme.name"] == "Lektor Name Theme"
    assert theme_inifile["author.email"] == get_default_author_email()
    assert theme_inifile["author.name"] == get_default_author()

    with open(os.path.join(path, "README.md")) as f:
        readme_contents = f.read().strip()
    assert "Lektor Name Theme" in readme_contents


def test_new_theme_name_param(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-theme", "theme-name"],
        input="\n" "Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Theme?" in result.output
    assert result.exit_code == 0
    path = "themes"
    assert os.listdir(path) == ["lektor-theme-name"]


def test_new_theme_path(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-theme"],
        input="Theme Name\n" "path\n" "Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Theme?" in result.output
    assert result.exit_code == 0
    path = "path"
    assert set(os.listdir(path)) == set(
        ["example-site", "images", "theme.ini", "README.md"]
    )


def test_new_theme_path_param(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-theme", "--path", "path"],
        input="Theme Name\n" "Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Theme?" in result.output
    assert result.exit_code == 0
    path = "path"
    assert set(os.listdir(path)) == set(
        ["example-site", "images", "theme.ini", "README.md"]
    )


def test_new_theme_path_and_name_params(project_cli_runner):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-theme", "theme-name", "--path", "path"],
        input="Author Name\n" "author@email.com\n" "y\n",
    )
    assert "Create Theme?" in result.output
    assert result.exit_code == 0
    path = "path"
    assert set(os.listdir(path)) == set(
        ["example-site", "images", "theme.ini", "README.md"]
    )


@pytest.mark.parametrize(
    ("theme_name", "expected_id"),
    (
        ("Lektor New Theme", "lektor-theme-new"),
        ("Lektor Theme", "lektor-theme-theme"),
        ("New Theme", "lektor-theme-new"),
        ("New", "lektor-theme-new"),
        ("Theme", "lektor-theme-theme"),
        ("Lektor", "lektor-theme-lektor"),
        ("Lektor Theme New", "lektor-theme-new"),
    ),
)
def test_new_theme_varying_names(project_cli_runner, theme_name, expected_id):
    result = project_cli_runner.invoke(
        cli,
        ["dev", "new-theme"],
        input="{}\n" "\n" "\n" "\n" "y\n".format(theme_name),
    )
    assert "Create Theme?" in result.output
    assert result.exit_code == 0
    assert expected_id in os.listdir("themes")
    path = os.path.join("themes", expected_id, "example-site")
    assert expected_id + ".lektorproject" in os.listdir(path)
