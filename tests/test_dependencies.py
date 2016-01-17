import os

import pytest

from conftest import make_builder
from lektor.reporter import Reporter


@pytest.fixture(scope='function')
def deptest_project(request):
    from lektor.project import Project
    return Project.from_path(os.path.join(os.path.dirname(__file__),
                                          'dependency-test-project'))


@pytest.fixture(scope='function')
def deptest_env(request, deptest_project):
    from lektor.environment import Environment
    return Environment(deptest_project)


@pytest.fixture(scope='function')
def deptest_pad(request, deptest_env):
    from lektor.db import Database
    return Database(deptest_env).new_pad()


@pytest.fixture(scope='function')
def deptest_builder(request, deptest_pad):
    return make_builder(request, deptest_pad)


class DependencyReporter(Reporter):
    def __init__(self, *args, **kwargs):
        Reporter.__init__(self, *args, **kwargs)
        self.dependency_map = {}

    def report_dependencies(self, dependencies):
        row = self.dependency_map.setdefault(self.current_artifact, set())
        for (artifact_name, source_path, mtime, size, checksum,
             is_dir, is_primary) in dependencies:
            row.add(source_path)


@pytest.fixture(scope='function')
def deptest_reporter(request, deptest_env):
    reporter = DependencyReporter(deptest_env)
    reporter.push()
    request.addfinalizer(reporter.pop)
    return reporter


def test_category_dependencies(deptest_pad, deptest_builder, deptest_reporter):
    pad, builder, reporter = deptest_pad, deptest_builder, deptest_reporter

    post1 = pad.get('post1')
    prog, _ = builder.build(post1)
    post_artifact = prog.artifacts[0]
    post1_deps = reporter.dependency_map[post_artifact]
    print post1_deps

    assert 'content/post3/contents.lr' not in post1_deps
