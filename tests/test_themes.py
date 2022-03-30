import os
import shutil
import textwrap

import pytest

from lektor.builder import Builder
from lektor.db import Database
from lektor.environment import Environment
from lektor.project import Project

sep = os.path.sep


@pytest.fixture(scope="function")
def theme_project_tmpdir(tmp_path, data_path):
    """Copy themes-project to a temp dir, and copy demo-project content to it."""
    temp_dir = tmp_path / "temp/themes-project"
    temp_dir.parent.mkdir()
    shutil.copytree(data_path / "themes-project", temp_dir)
    shutil.copytree(data_path / "demo-project/content", temp_dir / "content")
    return temp_dir


@pytest.fixture(scope="function")
def theme_project(theme_project_tmpdir, request):
    """Return the theme project created in a temp dir.

    Could be parametrize, if request.param=False themes variables won't be set
    """
    try:
        with_themes_var = request.param
    except AttributeError:
        with_themes_var = True

    # Create the .lektorproject file
    lektorfile_text = textwrap.dedent(
        """
        [project]
        name = Themes Project
        {}
    """.format(
            "themes = blog_theme, project_theme" if with_themes_var else ""
        )
    )
    lektorfile = theme_project_tmpdir / "themes.lektorproject"
    lektorfile.write_text(lektorfile_text, "utf8")
    return Project.from_path(theme_project_tmpdir)


@pytest.fixture(scope="function")
def theme_env(theme_project):

    return Environment(theme_project)


@pytest.fixture(scope="function")
def theme_pad(theme_env):

    return Database(theme_env).new_pad()


@pytest.fixture(scope="function")
def theme_builder(theme_pad, tmpdir):

    return Builder(theme_pad, str(tmpdir.mkdir("output")))


@pytest.mark.parametrize(
    "theme_project, themes",
    [
        (True, ["blog_theme", "project_theme"]),
        # when themes variables isn't set themes are only loaded in the env
        (False, []),
    ],
    indirect=["theme_project"],
)
def test_loading_theme_variable(theme_project, themes):
    assert theme_project.themes == themes


@pytest.mark.parametrize("theme_project", (True,), indirect=True)
def test_loading_theme_path(theme_env):
    assert [os.path.basename(p) for p in theme_env.theme_paths] == [
        "blog_theme",
        "project_theme",
    ]


@pytest.mark.parametrize("theme_project", (False,), indirect=True)
def test_loading_theme_path_variable_dont_set(theme_env):
    """Themes will be loaded, but the order could change."""
    paths = [os.path.basename(p) for p in theme_env.theme_paths]
    assert len(paths) == 2
    for path in paths:
        assert path in ["blog_theme", "project_theme"]


@pytest.mark.parametrize(
    "asset_name, found_in",
    [
        # - themes-project/assets/asset.txt
        # only exist in themes-project assets will be loaded from there
        ("asset.txt", "root"),
        # - themes-project/assets/dummy.txt
        # - themes-project/themes/blog_theme/assets/dummy.txt
        # wil be loaded from themes-project assets not from blog_theme assets
        ("dummy.txt", "root"),
        # - themes-project/themes/blog_theme/static/blog.css
        # only exist in blog_theme assets will be loaded from there
        ("static/blog.css", "blog"),
        # - themes-project/themes/project_theme/static/project.css
        # only exist in project_theme assets will be loaded from there
        ("static/project.css", "project"),
        # - themes-project/themes/blog_theme/assets/dummy2.txt
        # - themes-project/themes/project_theme/assets/dummy2.txt
        # wil be loaded from blog_theme assets because is included first
        ("dummy2.txt", "blog"),
    ],
)
def test_theme_asset_loading(theme_pad, asset_name, found_in):
    """Test loading assets from theme project.

    Loading should take in account the order of the themes
    """
    path_list = theme_pad.get_asset(asset_name).source_filename.split(sep)
    path_list_from_url = theme_pad.resolve_url_path(asset_name).source_filename.split(
        sep
    )

    assert path_list == path_list_from_url

    assert (found_in == "root") == ("themes" not in path_list)
    assert (found_in == "blog") == ("blog_theme" in path_list)
    assert (found_in == "project") == ("project_theme" in path_list)


@pytest.mark.parametrize(
    "url, datamodel_name, found_in",
    [
        # - themes-project/themes/blog_theme/models/blog.ini
        # only exist in blog_theme will be loaded from there
        ("/blog", "Blog", "blog"),
        # - themes-project/themes/project_theme/models/projects.ini
        # only exist in project_theme will be loaded from there
        ("/projects", "Projects", "project"),
        # - themes-project/models/blog-post.ini
        # - themes-project/themes/blog_theme/models/blog-post.ini
        # will be loaded from themes-project models
        ("/blog/post1", "Blog Post", "root"),
        # - themes-project/models/page.ini
        # only exist in themes-project will be loaded from there
        ("/", "Page", "root"),
        # - themes-project/themes/blog_theme/models/project.ini
        # - themes-project/themes/project_theme/models/project.ini
        # wil be loaded from blog_theme assets because is included first
        ("/projects/bagpipe", "Project", "blog"),
    ],
)
def test_theme_models_loading(theme_pad, url, datamodel_name, found_in):
    """Test loading models from theme project.

    Loading should take in account the order of the themes
    """
    assert datamodel_name == theme_pad.get(url).datamodel.name

    path_list = theme_pad.get(url).datamodel.filename.split(sep)

    assert (found_in == "root") == ("themes" not in path_list)
    assert (found_in == "blog") == ("blog_theme" in path_list)
    assert (found_in == "project") == ("project_theme" in path_list)


@pytest.mark.parametrize(
    "template_name, found_in",
    [
        # - themes-project/templates/layout.html
        # - themes-project/themes/blog_theme/templates/layout.html
        # - themes-project/themes/project_theme/templates/layout.html
        # will be loaded from themes-project templates
        ("layout.html", "root"),
        # - themes-project/themes/blog_theme/templates/blog.html
        # only exist in blog_theme will be loaded from there
        ("blog.html", "blog"),
        # - themes-project/themes/project_theme/templates/project.html
        # only exist in project_theme will be loaded from there
        ("project.html", "project"),
        # - themes-project/templates/page.html
        # only exist in themes-project will be loaded from there
        ("page.html", "root"),
        # - themes-project/themes/blog_theme/templates/dummy.html
        # - themes-project/themes/project_theme/templates/dummy.html
        # wil be loaded from blog_theme assets because is included first
        ("dummy.html", "blog"),
    ],
)
def test_theme_templates_loading(theme_env, template_name, found_in):
    """Test loading templates from theme project.

    Loading should take in account the order of the themes
    """
    path_list = theme_env.jinja_env.get_template(template_name).filename.split(sep)

    assert (found_in == "root") == ("themes" not in path_list)
    assert (found_in == "blog") == ("blog_theme" in path_list)
    assert (found_in == "project") == ("project_theme" in path_list)
