import os
import textwrap
import shutil
import pytest


@pytest.fixture(scope='function')
def theme_project_tmpdir(tmpdir):

    # Copy themes-project to a temp dir, and copy demo-project content to it
    themes_dir = os.path.join(os.path.dirname(__file__), 'themes-project')
    content_dir = os.path.join(os.path.dirname(__file__), 'demo-project', 'content')

    temp_dir = tmpdir.mkdir("temp").join('themes-project')

    shutil.copytree(themes_dir, str(temp_dir))
    shutil.copytree(content_dir, str(temp_dir.join('content')))

    return temp_dir


@pytest.fixture(scope='function')
def theme_project(theme_project_tmpdir):
    from lektor.project import Project

    # Create the .lektorproject file
    lektorfile_text = textwrap.dedent(u"""
        [project]
        name = Themes Project
        theme = blog_theme
    """)
    theme_project_tmpdir.join("themes.lektorproject").write_text(lektorfile_text,
                                                                 "utf8",
                                                                 ensure=True)

    return Project.from_path(str(theme_project_tmpdir))


@pytest.fixture(scope='function')
def theme_env(theme_project):
    from lektor.environment import Environment
    return Environment(theme_project)


@pytest.fixture(scope='function')
def theme_pad(theme_env):
    from lektor.db import Database
    return Database(theme_env).new_pad()


@pytest.fixture(scope='function')
def theme_builder(theme_pad, tmpdir):
    from lektor.builder import Builder
    return Builder(theme_pad, str(tmpdir.mkdir("output")))


def test_loading_theme_variable(theme_project):
    assert theme_project.theme == 'blog_theme'


def test_loading_theme_path(theme_env):
    assert os.path.basename(theme_env.theme_path) == 'blog_theme'


def test_loading_theme_path_if_not_setted(theme_project_tmpdir):
    """When project doesn't have theme,
    the first theme found in the themes folder will be loaded.

    So removing blog_theme will cause project_theme to be loaded.
    """
    from lektor.project import Project

    lektorfile_text = textwrap.dedent(u"""
        [project]
        name = Themes Project
    """)
    theme_project_tmpdir.join("themes.lektorproject").write_text(lektorfile_text,
                                                                 "utf8",
                                                                 ensure=True)

    shutil.rmtree(str(theme_project_tmpdir.join('themes', 'blog_theme')))
    project = Project.from_path(str(theme_project_tmpdir))
    env = theme_env(project)
    assert os.path.basename(env.theme_path) == 'project_theme'
