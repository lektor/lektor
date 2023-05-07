from functools import partial

import pytest

from lektor.build_programs import FileAssetBuildProgram
from lektor.builder import Builder
from lektor.reporter import describe_build_func


@pytest.fixture
def build_state(pad, tmp_path):
    builder = Builder(pad, destination_path=tmp_path)
    return builder.new_build_state()


def dummy_build_func(*args):
    pass


def test_describe_build_func():
    assert describe_build_func(dummy_build_func) == "test_reporter.dummy_build_func"


def test_describe_build_func_describes_partial():
    build_func = partial(dummy_build_func, "dummy-arg")
    assert describe_build_func(build_func) == "test_reporter.dummy_build_func"


def test_describe_build_func_BuildProgram(pad, build_state):
    build_program = FileAssetBuildProgram(pad.get_asset("static/demo.css"), build_state)
    build_func = build_program.build_artifact
    assert (
        describe_build_func(build_func) == "lektor.build_programs.FileAssetBuildProgram"
    )


def test_describe_build_func_deals_with_garbage():
    garbage = object()
    assert isinstance(describe_build_func(garbage), str)
