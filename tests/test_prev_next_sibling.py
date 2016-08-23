import os
import shutil

import pytest

from lektor.builder import Builder
from lektor.reporter import Reporter


@pytest.fixture(scope='function')
def pntest_project(request):
    from lektor.project import Project
    return Project.from_path(os.path.join(os.path.dirname(__file__),
                                          'dependency-test-project'))


@pytest.fixture(scope='function')
def pntest_env(request, pntest_project):
    from lektor.environment import Environment
    return Environment(pntest_project)


@pytest.fixture(scope='function')
def pntest_pad(request, pntest_env):
    from lektor.db import Database
    return Database(pntest_env).new_pad()


class DependencyReporter(Reporter):
    def __init__(self, *args, **kwargs):
        Reporter.__init__(self, *args, **kwargs)
        self.deps = {}

    def report_dependencies(self, dependencies):
        source_id = self.current_artifact.source_obj['_id']
        row = self.deps.setdefault(source_id, set())
        for (artifact_name, source_path, mtime, size, checksum,
             is_dir, is_primary) in dependencies:
            row.add(source_path)

    @property
    def artifact_ids(self):
        return set(self.deps.keys())

    def clear(self):
        self.deps = {}


@pytest.fixture(scope='function')
def pntest_reporter(request, pntest_env):
    reporter = DependencyReporter(pntest_env)
    reporter.push()
    request.addfinalizer(reporter.pop)
    return reporter


def test_prev_next_dependencies(request, tmpdir, pntest_env, pntest_reporter):
    env, reporter = pntest_env, pntest_reporter
    builder = Builder(env.new_pad(), str(tmpdir.mkdir("output")))
    builder.build_all()

    # We start with posts 1, 2, and 4. Posts 1 and 2 depend on each other,
    # posts 2 and 3 depend on each other, but posts 1 and 3 are independent.
    assert 'content/post2/contents.lr' in reporter.deps['post1']
    assert 'content/post3/contents.lr' not in reporter.deps['post1']
    assert '/post1@siblings' in reporter.deps['post1']

    assert 'content/post1/contents.lr' in reporter.deps['post2']
    assert 'content/post4/contents.lr' in reporter.deps['post2']
    assert '/post2@siblings' in reporter.deps['post2']

    assert 'content/post1/contents.lr' not in reporter.deps['post4']
    assert 'content/post2/contents.lr' in reporter.deps['post4']
    assert '/post4@siblings' in reporter.deps['post4']

    # Create post3, check that post2 and post4's dependencies are updated.
    post3_dir = os.path.join(env.project.tree, 'content', 'post3')

    def cleanup():
        try:
            shutil.rmtree(post3_dir)
        except (OSError, IOError):
            pass

    request.addfinalizer(cleanup)
    os.makedirs(post3_dir)
    open(os.path.join(post3_dir, 'contents.lr'), 'w+').close()

    reporter.clear()
    builder = Builder(env.new_pad(), builder.destination_path)
    builder.build_all()

    # post2, post3, and post4 had to be rebuilt, but not post1.
    assert set(['post2', 'post3', 'post4']) == set(reporter.artifact_ids)

    # post2 depends on post3 now, not post4.
    assert 'content/post3/contents.lr' in reporter.deps['post2']
    assert 'content/post4/contents.lr' not in reporter.deps['post2']

    # post4 depends on post3 now, not post2.
    assert 'content/post3/contents.lr' in reporter.deps['post4']
    assert 'content/post2/contents.lr' not in reporter.deps['post4']


def test_prev_next_virtual_resolver(pntest_pad):
    from lektor.context import Context
    from lektor.db import Siblings

    with Context(pad=pntest_pad):
        siblings = pntest_pad.get('post2@siblings')
        assert isinstance(siblings, Siblings)
        assert siblings.path == '/post2@siblings'
        assert siblings.record['_id'] == 'post2'
        assert siblings.prev_page['_id'] == 'post1'
        assert siblings.next_page['_id'] == 'post4'

        with pytest.raises(NotImplementedError):
            siblings.url_path
