import os
import shutil
import sys
import textwrap

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
def project():
    return Project.from_path(os.path.join(os.path.dirname(__file__), "demo-project"))


@pytest.fixture(scope="function")
def scratch_project_data(tmpdir):
    base = tmpdir.mkdir("scratch-proj")
    lektorfile_text = textwrap.dedent(
        """
        [project]
        name = Scratch

        [alternatives.en]
        primary = yes
        [alternatives.de]
        url_prefix = /de/
    """
    )
    base.join("Scratch.lektorproject").write_text(lektorfile_text, "utf8", ensure=True)
    content_text = textwrap.dedent(
        """
        _model: page
        ---
        title: Index
        ---
        body: *Hello World!*
    """
    )
    base.join("content", "contents.lr").write_text(content_text, "utf8", ensure=True)
    template_text = textwrap.dedent(
        """
        <h1>{{ this.title }}</h1>
        {{ this.body }}
    """
    )
    base.join("templates", "page.html").write_text(template_text, "utf8", ensure=True)
    model_text = textwrap.dedent(
        """
        [model]
        label = {{ this.title }}

        [fields.title]
        type = string
        [fields.body]
        type = markdown
    """
    )
    base.join("models", "page.ini").write_text(model_text, "utf8", ensure=True)

    return base


@pytest.fixture(scope="function")
def scratch_project(scratch_project_data):
    base = scratch_project_data
    return Project.from_path(str(base))


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
def builder(tmpdir, pad):
    return Builder(pad, str(tmpdir.mkdir("output")))


@pytest.fixture(scope="function")
def scratch_builder(tmpdir, scratch_pad):
    return Builder(scratch_pad, str(tmpdir.mkdir("output")))


# Builder for child-sources-test-project, a project to test that child sources
# are built even if they're filtered out by a pagination query.
@pytest.fixture(scope="function")
def child_sources_test_project_builder(tmpdir):
    project = Project.from_path(
        os.path.join(os.path.dirname(__file__), "child-sources-test-project")
    )
    env = Environment(project)
    pad = Database(env).new_pad()

    return Builder(pad, str(tmpdir.mkdir("output")))


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
