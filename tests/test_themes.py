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


def test_themes(theme_builder):
    assert theme_builder
