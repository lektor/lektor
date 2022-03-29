import os
import re
import sys

import pytest

from lektor.buildfailures import BuildFailure
from lektor.buildfailures import FailureController


@pytest.fixture
def output_path(tmp_path):
    return tmp_path.__fspath__()


@pytest.fixture
def failure_controller(pad, output_path):
    return FailureController(pad, output_path)


def test_BuildFailure_from_exc_info():
    def throw_exception():
        x = {}
        try:
            x["somekey"]
        except KeyError:
            raise RuntimeError("test error")  # pylint: disable=raise-missing-from

    artifact_name = "test_artifact"
    try:
        throw_exception()
    except Exception:
        failure = BuildFailure.from_exc_info(artifact_name, sys.exc_info())

    assert failure.data["artifact"] == artifact_name
    assert failure.data["exception"] == "RuntimeError: test error"
    traceback = failure.data["traceback"]
    print(traceback)
    patterns = [
        r'x\["somekey"\]',
        r"KeyError: .somekey.",
        r"During handling of the above exception, another exception occurred",
        r"throw_exception\(\)",
        r'raise RuntimeError\("test error"\)',
        r"RuntimeError: test error",
    ]
    for pattern in patterns:
        assert re.search(pattern, traceback)


def test_failure_controller(failure_controller):
    try:
        raise RuntimeError("test exception")
    except Exception:
        failure_controller.store_failure("artifact_name", sys.exc_info())

    failure = failure_controller.lookup_failure("artifact_name")
    assert failure.data["exception"] == "RuntimeError: test exception"

    failure_controller.clear_failure("artifact_name")
    assert failure_controller.lookup_failure("artifact_name") is None


def test_failure_controller_clear_lookup_missing(failure_controller):
    assert failure_controller.lookup_failure("missing_artifact") is None


def test_failure_controller_clear_missing(failure_controller):
    failure_controller.clear_failure("missing_artifact")
    assert failure_controller.lookup_failure("missing_artifact") is None


def test_failure_controller_fs_exceptions(failure_controller):
    # Create a directory in the location that FailureController wants
    # a file stored to trigger unexpected OSErrors.
    filename = failure_controller.get_filename("broken")
    os.makedirs(filename)

    with pytest.raises(OSError):
        failure_controller.lookup_failure("broken")
    with pytest.raises(OSError):
        failure_controller.clear_failure("broken")
    with pytest.raises(OSError):
        try:
            assert False
        except Exception:
            failure_controller.store_failure("broken", sys.exc_info())
