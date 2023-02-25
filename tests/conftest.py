import importlib
import os
import shutil
import sys
import textwrap
from contextlib import contextmanager
from pathlib import Path

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


try:
    importlib.import_module("PIL.Image")
    have_pillow = True
except ModuleNotFoundError:
    have_pillow = False


def pytest_runtest_setup(item: pytest.Item):
    # skip tests marked with requirespillow if Pillow is not installed
    if not have_pillow:
        if item.get_closest_marker("requirespillow") is not None:
            pytest.skip("test requires Pillow")


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


@contextmanager
def restore_import_state():
    """Save `sys.path`, and `sys.modules` state on test
    entry, restore after test completion.

    Any test which constructs a `lektor.environment.Environment` instance
    or which runs any of the Lektor CLI commands should use this fixture
    to ensure that alterations made to `sys.path` do not interfere with
    other tests.

    Lektor's private package cache is added to `sys.path` by
    `lektor.packages.load_packages`.  This happens, for example,
    whenever a Lektor `Environment` is constructed (unless
    `load_plugins=False` is specified.)  Since all tests are run
    within an single invocation of the python interpreter, this can
    cause problems when different tests are using different private
    package caches.

    """
    save_path = sys.path
    sys.path = save_path.copy()

    # Restoring `sys.modules` is an attempt to unload any
    # modules loaded during the test so that they can be re-loaded for
    # the next test.  This is not guaranteed to work, since there are
    # numerous ways that a reference to a loaded module may still be held.

    # NB: some modules (e.g. pickle) appear to hold a reference to sys.modules,
    # so we have to be careful to manipulate sys.modules in place, rather than
    # using monkeypatch to swap it out.
    saved_modules = sys.modules.copy()

    # It's not clear that this is necessary, but it probably won't hurt.
    importlib.invalidate_caches()

    try:
        yield
    finally:
        for name in set(sys.modules).difference(saved_modules):
            del sys.modules[name]
        sys.modules.update(saved_modules)
        sys.path = save_path


@pytest.fixture
def save_sys_path():
    with restore_import_state():
        yield


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def built_demo(tmp_path_factory, project):
    output_path = tmp_path_factory.mktemp("demo-output")
    with restore_import_state():
        env = Environment(project)
        builder = Builder(env.new_pad(), os.fspath(output_path))
        builder.build_all()
    return output_path


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
    (e.g. git, ffmpeg)."""
    monkeypatch.setitem(os.environ, "PATH", "/dev/null")
    locate_executable.cache_clear()
    try:
        yield
    finally:
        locate_executable.cache_clear()
