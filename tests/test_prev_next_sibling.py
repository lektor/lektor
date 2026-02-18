import os
import shutil

import pytest

from lektor.builder import Builder
from lektor.context import Context
from lektor.db import Database
from lektor.db import Siblings
from lektor.environment import Environment
from lektor.project import Project
from lektor.reporter import Reporter


@pytest.fixture(scope="function")
def pntest_project(tmp_path, data_path):
    src = data_path / "dependency-test-project"
    tmp_project = tmp_path / "project"
    shutil.copytree(src, tmp_project)
    return Project.from_path(tmp_project)


@pytest.fixture
def pntest_env(pntest_project, save_sys_path):
    return Environment(pntest_project)


@pytest.fixture
def pntest_pad(pntest_env):
    return Database(pntest_env).new_pad()


class DependencyReporter(Reporter):
    def __init__(self, *args, **kwargs):
        Reporter.__init__(self, *args, **kwargs)
        self.deps = {}

    def report_dependencies(self, dependencies):
        source_id = self.current_artifact.source_obj["_id"]
        row = self.deps.setdefault(source_id, set())
        for _artifact_name, source_path, *_rest in dependencies:
            row.add(source_path)

    @property
    def artifact_ids(self):
        return set(self.deps.keys())

    def clear(self):
        self.deps = {}


@pytest.fixture
def pntest_reporter(pntest_env):
    reporter = DependencyReporter(pntest_env)
    reporter.push()
    try:
        yield reporter
    finally:
        reporter.pop()


def test_prev_next_dependencies(tmp_path, pntest_env, pntest_reporter):
    env, reporter = pntest_env, pntest_reporter
    builder = Builder(env.new_pad(), tmp_path / "output")
    builder.build_all()

    # We start with posts 1, 2, and 4. Posts 1 and 2 depend on each other,
    # posts 2 and 3 depend on each other, but posts 1 and 3 are independent.
    assert "content/post2/contents.lr" in reporter.deps["post1"]
    assert "content/post3/contents.lr" not in reporter.deps["post1"]
    assert "/post1@siblings" in reporter.deps["post1"]

    assert "content/post1/contents.lr" in reporter.deps["post2"]
    assert "content/post4/contents.lr" in reporter.deps["post2"]
    assert "/post2@siblings" in reporter.deps["post2"]

    assert "content/post1/contents.lr" not in reporter.deps["post4"]
    assert "content/post2/contents.lr" in reporter.deps["post4"]
    assert "/post4@siblings" in reporter.deps["post4"]

    # Create post3, check that post2 and post4's dependencies are updated.
    post3_dir = os.path.join(env.project.tree, "content", "post3")

    os.makedirs(post3_dir)
    with open(os.path.join(post3_dir, "contents.lr"), "w+", encoding="utf-8"):
        pass

    reporter.clear()
    builder = Builder(env.new_pad(), builder.destination_path)
    builder.build_all()

    # post2, post3, and post4 had to be rebuilt, but not post1.
    assert {"post2", "post3", "post4"} == set(reporter.artifact_ids)

    # post2 depends on post3 now, not post4.
    assert "content/post3/contents.lr" in reporter.deps["post2"]
    assert "content/post4/contents.lr" not in reporter.deps["post2"]

    # post4 depends on post3 now, not post2.
    assert "content/post3/contents.lr" in reporter.deps["post4"]
    assert "content/post2/contents.lr" not in reporter.deps["post4"]


def test_prev_next_virtual_resolver(pntest_pad):
    with Context(pad=pntest_pad):
        siblings = pntest_pad.get("post2@siblings")
        assert isinstance(siblings, Siblings)
        assert siblings.path == "/post2@siblings"
        assert siblings.record["_id"] == "post2"
        assert siblings.prev_page["_id"] == "post1"
        assert siblings.next_page["_id"] == "post4"

        with pytest.raises(NotImplementedError):
            _ = siblings.url_path
