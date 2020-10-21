import os
import shutil
import textwrap

import pytest


@pytest.fixture(scope="function")
def project():
    from lektor.project import Project

    return Project.from_path(os.path.join(os.path.dirname(__file__), "demo-project"))


@pytest.fixture(scope="function")
def scratch_project_data(tmpdir):
    base = tmpdir.mkdir("scratch-proj")
    lektorfile_text = textwrap.dedent(
        u"""
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
        u"""
        _model: page
        ---
        title: Index
        ---
        body: *Hello World!*
    """
    )
    base.join("content", "contents.lr").write_text(content_text, "utf8", ensure=True)
    template_text = textwrap.dedent(
        u"""
        <h1>{{ this.title }}</h1>
        {{ this.body }}
    """
    )
    base.join("templates", "page.html").write_text(template_text, "utf8", ensure=True)
    model_text = textwrap.dedent(
        u"""
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
    from lektor.project import Project

    base = scratch_project_data
    return Project.from_path(str(base))


@pytest.fixture(scope="function")
def env(project):
    from lektor.environment import Environment

    return Environment(project)


@pytest.fixture(scope="function")
def scratch_env(scratch_project):
    from lektor.environment import Environment

    return Environment(scratch_project)


@pytest.fixture(scope="function")
def pad(env):
    from lektor.db import Database

    return Database(env).new_pad()


@pytest.fixture(scope="function")
def scratch_pad(scratch_env):
    from lektor.db import Database

    return Database(scratch_env).new_pad()


@pytest.fixture(scope="function")
def scratch_tree(scratch_pad):
    from lektor.db import Tree

    return Tree(scratch_pad)


@pytest.fixture(scope="function")
def builder(tmpdir, pad):
    from lektor.builder import Builder

    return Builder(pad, str(tmpdir.mkdir("output")))


@pytest.fixture(scope="function")
def scratch_builder(tmpdir, scratch_pad):
    from lektor.builder import Builder

    return Builder(scratch_pad, str(tmpdir.mkdir("output")))


# Builder for child-sources-test-project, a project to test that child sources
# are built even if they're filtered out by a pagination query.
@pytest.fixture(scope="function")
def child_sources_test_project_builder(tmpdir):
    from lektor.db import Database
    from lektor.environment import Environment
    from lektor.project import Project
    from lektor.builder import Builder

    project = Project.from_path(
        os.path.join(os.path.dirname(__file__), "child-sources-test-project")
    )
    env = Environment(project)
    pad = Database(env).new_pad()

    return Builder(pad, str(tmpdir.mkdir("output")))


@pytest.fixture(scope="function")
def F():
    from lektor.db import F

    return F


@pytest.fixture(scope="function")
def eval_expr(env):
    from lektor.environment import Expression

    def eval_expr(expr, **kwargs):
        expr = Expression(env, expr)
        return expr.evaluate(**kwargs)

    return eval_expr


@pytest.fixture(scope="function")
def reporter(request, env):
    from lektor.reporter import BufferReporter

    reporter = BufferReporter(env)
    reporter.push()
    request.addfinalizer(reporter.pop)
    return reporter


@pytest.fixture(scope="function")
def os_user(monkeypatch):
    if os.name == "nt":
        import getpass  # pylint: disable=unused-import # noqa

        monkeypatch.setattr("getpass.getuser", lambda: "Lektor Test")
        return "lektortest"

    # we disable pylint, because there is no such
    # modules on windows & it's false positive
    import pwd  # pylint: disable=import-error

    struct = pwd.struct_passwd(
        (
            "lektortest",  # pw_name
            "lektorpass",  # pw_passwd
            9999,  # pw_uid
            9999,  # pw_gid
            "Lektor Test",  # pw_gecos
            "/tmp/lektortest",  # pw_dir
            "/bin/lektortest",  # pw_shell
        )
    )
    monkeypatch.setattr("pwd.getpwuid", lambda id: struct)
    monkeypatch.setenv("USER", "lektortest")
    return "lektortest"


@pytest.fixture(scope="function")
def project_cli_runner(isolated_cli_runner, project):
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
