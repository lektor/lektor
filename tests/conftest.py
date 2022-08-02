import os
import shutil
import sys
import textwrap
from pathlib import Path

import pkg_resources
import pytest
from _pytest.monkeypatch import MonkeyPatch

import lektor.project
from lektor.builder import Builder
from lektor.db import Database
from lektor.db import Tree
from lektor.environment import Environment
from lektor.environment.expressions import Expression
from lektor.project import Project
from lektor.reporter import BufferReporter
from lektor.utils import locate_executable


@pytest.fixture(scope="session")
def data_path():
    """Path to directory which contains test data.

    Current this data lives in the ``tests`` directory.
    """
    return Path(__file__).parent


@pytest.fixture(scope="session", autouse=True)
def temporary_lektor_cache(tmp_path_factory):
    """Get Lektor to use a temporary cache directory.

    This prevents the tests from leaving scats behind in the
    user’s real cache directory.

    """
    cache_dir = tmp_path_factory.mktemp("lektor_cache")

    # The stock monkeypatch fixture is function-scoped and so can not
    # be used in a session-scoped fixture.
    # Workaround from:
    # https://github.com/pytest-dev/pytest/issues/363#issuecomment-406536200

    def get_cache_dir():
        return str(cache_dir)

    mp = MonkeyPatch()
    mp.setattr(lektor.project, "get_cache_dir", get_cache_dir)
    yield cache_dir
    mp.undo()


@pytest.fixture
def save_sys_path(monkeypatch):
    """Save `sys.path`, `sys.modules`, and `pkg_resources` state on test
    entry, restore after test completion.

    Any test which constructs a `lektor.environment.Environment` instance
    or which runs any of the Lektor CLI commands should use this fixture
    to ensure that alternations made to `sys.path` do not interfere with
    other tests.

    Lektor's private package cache is added to `sys.path` by
    `lektor.packages.load_packages`.  This happens, for example,
    whenever a Lektor `Environment` is constructed (unless
    `load_plugins=False` is specified.)  Since all tests are run
    within an single invocation of the python interpreter, this can
    cause problems when different tests are using different private
    package caches.

    """
    monkeypatch.setattr(sys, "path", sys.path.copy())

    # Restoring `sys.modules` is an attempt to unload any
    # modules loaded during the test so that they can be re-loaded for
    # the next test.  This is not guaranteed to work, since there are
    # numerous ways that a reference to a loaded module may still be held.
    monkeypatch.setattr(sys, "modules", sys.modules.copy())

    # While pkg_resources.__getstate__ and pkg_resources.__setstate__
    # do not appear to be a documented part of the pkg_resources API,
    # they are used in setuptools' own tests, and appear to have been
    # a stable feature since 2011.
    saved_state = pkg_resources.__getstate__()
    yield
    pkg_resources.__setstate__(saved_state)


@pytest.fixture(scope="function")
def project(data_path):
    return Project.from_path(data_path / "demo-project")


@pytest.fixture(scope="function")
def scratch_project_data(tmp_path):
    base = tmp_path / "scratch-proj"

    def write_text(path, text):
        filename = base / path
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_text(textwrap.dedent(text), "utf-8")

    write_text(
        "Scratch.lektorproject",
        """
        [project]
        name = Scratch

        [alternatives.en]
        primary = yes
        [alternatives.de]
        url_prefix = /de/
        """,
    )
    write_text(
        "content/contents.lr",
        """
        _model: page
        ---
        title: Index
        ---
        body: *Hello World!*
        """,
    )
    write_text(
        "templates/page.html",
        """
        <h1>{{ this.title }}</h1>
        {{ this.body }}
        """,
    )
    write_text(
        "models/page.ini",
        """
        [model]
        label = {{ this.title }}

        [fields.title]
        type = string
        [fields.body]
        type = markdown
        """,
    )

    return base


@pytest.fixture(scope="function")
def scratch_project(scratch_project_data):
    return Project.from_path(scratch_project_data)


@pytest.fixture(scope="function")
def env(project, save_sys_path):
    return Environment(project)


@pytest.fixture(scope="function")
def scratch_env(scratch_project, save_sys_path):
    return Environment(scratch_project)


@pytest.fixture(scope="function")
def pad(env):
    return Database(env).new_pad()


@pytest.fixture(scope="function")
def scratch_pad(scratch_env):
    return Database(scratch_env).new_pad()


@pytest.fixture(scope="function")
def scratch_tree(scratch_pad):
    return Tree(scratch_pad)


@pytest.fixture(scope="function")
def builder(tmp_path, pad):
    output_path = tmp_path / "output"
    output_path.mkdir()
    return Builder(pad, str(output_path))


@pytest.fixture(scope="function")
def scratch_builder(tmp_path, scratch_pad):
    output_path = tmp_path / "output"
    output_path.mkdir()
    return Builder(scratch_pad, str(output_path))


# Builder for child-sources-test-project, a project to test that child sources
# are built even if they're filtered out by a pagination query.
@pytest.fixture(scope="function")
def child_sources_test_project_builder(tmp_path, data_path):
    output_path = tmp_path / "output"
    output_path.mkdir()
    project = Project.from_path(data_path / "child-sources-test-project")
    pad = project.make_env().new_pad()
    return Builder(pad, str(output_path))


@pytest.fixture(scope="function")
def eval_expr(env):
    def eval_expr(expr, **kwargs):
        expr = Expression(env, expr)
        return expr.evaluate(**kwargs)

    return eval_expr


@pytest.fixture(scope="function")
def reporter(request, env):
    reporter = BufferReporter(env)
    reporter.push()
    request.addfinalizer(reporter.pop)
    return reporter


@pytest.fixture(scope="function")
def project_cli_runner(isolated_cli_runner, project, save_sys_path):
    """
    Copy the project files into the isolated file system used by the
    Click test runner.
    """
    for entry in os.listdir(project.tree):
        entry_path = os.path.join(project.tree, entry)
        if os.path.isdir(entry_path):
            shutil.copytree(entry_path, entry)
        else:
            shutil.copy2(entry_path, entry)
    return isolated_cli_runner


@pytest.fixture
def no_utils(monkeypatch):
    """Monkeypatch $PATH to hide any installed external utilities
    (e.g. git, imagemagick)."""
    monkeypatch.setitem(os.environ, "PATH", "/dev/null")
    locate_executable.cache_clear()
    try:
        yield
    finally:
        locate_executable.cache_clear()
