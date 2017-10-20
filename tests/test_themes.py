import os
import textwrap
import shutil
import pytest

sep = os.path.sep

@pytest.fixture(scope='function')
def theme_project_tmpdir(tmpdir):
    """Copy themes-project to a temp dir, and copy demo-project content to it"""

    themes_dir = os.path.join(os.path.dirname(__file__), 'themes-project')
    content_dir = os.path.join(os.path.dirname(__file__), 'demo-project', 'content')

    temp_dir = tmpdir.mkdir("temp").join('themes-project')

    shutil.copytree(themes_dir, str(temp_dir))
    shutil.copytree(content_dir, str(temp_dir.join('content')))

    return temp_dir


@pytest.fixture(scope='function')
def theme_project(theme_project_tmpdir):
    """Return the theme project created in a temp dir."""
    from lektor.project import Project

    # Create the .lektorproject file
    lektorfile_text = textwrap.dedent(u"""
        [project]
        name = Themes Project
        themes = blog_theme, project_theme
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
    assert theme_project.themes == ['blog_theme', 'project_theme']


def test_loading_theme_path(theme_env):
    assert [os.path.basename(p) for p in theme_env.theme_paths] == ['blog_theme', 'project_theme']


def test_loading_theme_path_if_not_setted(theme_project_tmpdir):
    """When project doesn't have theme variable,
    the themes found in the themes folder will be loaded.
    """
    from lektor.project import Project

    lektorfile_text = textwrap.dedent(u"""
        [project]
        name = Themes Project
    """)
    theme_project_tmpdir.join("themes.lektorproject").write_text(lektorfile_text,
                                                                 "utf8",
                                                                 ensure=True)

    project = Project.from_path(str(theme_project_tmpdir))
    env = theme_env(project)
    assert [os.path.basename(path) for path in env.theme_paths] == ['blog_theme', 'project_theme']


def test_theme_assest_loading(theme_pad):
    # - themes-project/assets/dummy.txt
    # - themes-project/themes/blog_theme/assets/dummy.txt
    # wil be loaded from themes-project assets not from blog_theme assets
    assert "themes" not in theme_pad.get_asset('dummy.txt').source_filename.split(sep)

    # - themes-project/themes/blog_theme/static/blog.css
    # only exist in blog_theme assets will be loaded from there
    assert "blog_theme" in theme_pad.get_asset('static/blog.css').source_filename.split(sep)


def test_theme_models_loading(theme_pad):
    # - themes-project/themes/blog_theme/models/blog.ini
    # only exist in blog_theme will be loaded from there
    assert "blog_theme" in theme_pad.get('/blog').datamodel.filename.split(sep)

    # - themes-project/models/blog-post.ini
    # - themes-project/themes/blog_theme/models/blog-post.ini
    # will be loaded from themes-project models
    assert theme_pad.get('/blog/post1').datamodel.name == 'Blog Post'
    assert "themes" not in theme_pad.get('/blog/post1').datamodel.filename.split(sep)

    # - themes-project/models/page.ini
    # only exist in themes-project will be loaded from there
    assert "themes" not in theme_pad.get('/').datamodel.filename.split(sep)


def test_theme_templates_loading(theme_env):
    # - themes-project/templates/layout.html
    # - themes-project/themes/blog_theme/templates/layout.html
    # will be loaded from themes-project templates
    assert "themes" not in theme_env.jinja_env.get_template("layout.html").filename.split(sep)

    # - themes-project/themes/blog_theme/templates/blog.html
    # only exist in blog_theme will be loaded from there
    assert "blog_theme" in theme_env.jinja_env.get_template("blog.html").filename.split(sep)

    # - themes-project/templates/page.html
    # only exist in themes-project will be loaded from there
    assert "themes" not in theme_env.jinja_env.get_template("page.html").filename.split(sep)
