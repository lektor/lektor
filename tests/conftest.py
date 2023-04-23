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
    path = sys.path.copy()
    meta_path = sys.meta_path.copy()
    path_hooks = sys.path_hooks.copy()
    modules = sys.modules.copy()

    # Importlib_metadata, when it is imported, cripples the stdlib distribution finder
    # by deleting its find_distributions method.
    #
    # https://github.com/python/importlib_metadata/blob/705a7571ec7c5abec4d4b008da3a58df7e5c94e7/importlib_metadata/_compat.py#L31
    #
    def clone_class(cls):
        return type(cls)(cls.__name__, cls.__bases__, cls.__dict__.copy())

    sys.meta_path[:] = [
        clone_class(finder) if isinstance(finder, type) else finder
        for finder in meta_path
    ]

    try:
        yield
    finally:
        importlib.invalidate_caches()

        # NB: Restore sys.modules, sys.path, et. all. in place. (Some modules may hold
        # references to these — e.g. pickle appears to hold a reference to sys.modules.)
        for module in set(sys.modules).difference(modules):
            del sys.modules[module]
        sys.modules.update(modules)
        sys.path[:] = path
        sys.meta_path[:] = meta_path
        sys.path_hooks[:] = path_hooks
        sys.path_importer_cache.clear()


_initial_path_key = object()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    item.stash[_initial_path_key] = sys.path.copy()


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item):
    # Check that tests don't alter sys.path
    initial_path = item.stash[_initial_path_key]
    assert sys.path == initial_path


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
def child_sources_test_project_builder(tmp_path, data_path, save_sys_path):
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
