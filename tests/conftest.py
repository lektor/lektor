import os
import pytest
import shutil
import tempfile


@pytest.fixture(scope='function')
def project(request):
    from lektor.project import Project
    return Project.from_path(os.path.join(os.path.dirname(__file__),
                                          'demo-project'))


@pytest.fixture(scope='function')
def scratch_project(request):
    base = tempfile.mkdtemp()
    with open(os.path.join(base, 'Scratch.lektorproject'), 'w') as f:
        f.write(
            '[project]\n'
            'name = Scratch\n\n'
            '[alternatives.en]\n'
            'primary = yes\n'
            '[alternatives.de]\n'
            'url_prefix = /de/\n'
        )

    os.mkdir(os.path.join(base, 'content'))
    with open(os.path.join(base, 'content', 'contents.lr'), 'w') as f:
        f.write(
            '_model: page\n'
            '---\n'
            'title: Index\n'
            '---\n'
            'body: Hello World!\n'
        )
    os.mkdir(os.path.join(base, 'templates'))
    with open(os.path.join(base, 'templates', 'page.html'), 'w') as f:
        f.write('<h1>{{ this.title }}</h1>\n{{ this.body }}\n')
    os.mkdir(os.path.join(base, 'models'))
    with open(os.path.join(base, 'models', 'page.ini'), 'w') as f:
        f.write(
            '[model]\n'
            'label = {{ this.title }}\n\n'
            '[fields.title]\n'
            'type = string\n'
            '[fields.body]\n'
            'type = markdown\n'
        )

    def cleanup():
        try:
            shutil.rmtree(base)
        except (OSError, IOError):
            pass
    request.addfinalizer(cleanup)

    from lektor.project import Project
    return Project.from_path(base)


@pytest.fixture(scope='function')
def env(request, project):
    from lektor.environment import Environment
    return Environment(project)


@pytest.fixture(scope='function')
def scratch_env(request, scratch_project):
    from lektor.environment import Environment
    return Environment(scratch_project)


@pytest.fixture(scope='function')
def pad(request, env):
    from lektor.db import Database
    return Database(env).new_pad()


@pytest.fixture(scope='function')
def scratch_pad(request, scratch_env):
    from lektor.db import Database
    return Database(scratch_env).new_pad()


@pytest.fixture(scope='function')
def scratch_tree(request, scratch_pad):
    from lektor.db import Tree
    return Tree(scratch_pad)


def make_builder(request, pad):
    from lektor.builder import Builder
    out = tempfile.mkdtemp()
    builder = Builder(pad, out)
    def cleanup():
        try:
            shutil.rmtree(out)
        except (OSError, IOError):
            pass
    request.addfinalizer(cleanup)
    return builder


@pytest.fixture(scope='function')
def builder(request, pad):
    return make_builder(request, pad)


@pytest.fixture(scope='function')
def scratch_builder(request, scratch_pad):
    return make_builder(request, scratch_pad)


# Builder for always-build-option-project, a project to test "_always_build".
@pytest.fixture(scope='function')
def always_build_builder(request):
    from lektor.db import Database
    from lektor.environment import Environment
    from lektor.project import Project

    project = Project.from_path(os.path.join(os.path.dirname(__file__),
                                             'always-build-option-project'))
    env = Environment(project)
    pad = Database(env).new_pad()

    return make_builder(request, pad)


@pytest.fixture(scope='function')
def F():
    from lektor.db import F
    return F


@pytest.fixture(scope='function')
def eval_expr(env):
    from lektor.environment import Expression
    def eval_expr(expr, **kwargs):
        expr = Expression(env, expr)
        return expr.evaluate(**kwargs)
    return eval_expr


@pytest.fixture(scope='function')
def reporter(request, env):
    from lektor.reporter import BufferReporter
    reporter = BufferReporter(env)
    reporter.push()
    request.addfinalizer(reporter.pop)
    return reporter


@pytest.fixture(scope='function')
def webui(request, env, pad):
    from lektor.admin.webui import WebUI
    output_path = tempfile.mkdtemp()

    def cleanup():
        try:
            shutil.rmtree(output_path)
        except (OSError, IOError):
            pass
    request.addfinalizer(cleanup)

    return WebUI(env, output_path=output_path)
