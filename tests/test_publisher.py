import gc
import os
import sys
import warnings
import weakref
from shutil import which

import pytest

from lektor.publisher import Command
from lektor.publisher import publish


def test_Command_triggers_no_warnings():
    # This excercises the issue where publishing via rsync resulted
    # in ResourceWarnings about unclosed streams.

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        # This is essentially how RsyncPublisher runs rsync.
        with Command([sys.executable, "-c", "print()"]) as client:
            for _ in client:
                pass

        # The ResourceWarnings regarding unclosed files we are checking for
        # are issued during finalization.  Without this extra effort,
        # finalization wouldn't happen until after the test completes.
        client_is_alive = weakref.ref(client)
        del client
        if client_is_alive():
            gc.collect()

    if client_is_alive():
        warnings.warn(
            "Unable to trigger garbage collection of Command instance, "
            "so unable to check for warnings issued during finalization."
        )


@pytest.mark.skipif(
    which("rsync") is None, reason="rsync is not available on this system"
)
@pytest.mark.parametrize("delete", ["yes", "no"])
def test_RsyncPublisher_integration(env, tmp_path, delete):
    # Integration test of local rsync deployment
    # Ensures that RsyncPublisher can successfully invoke rsync
    files = {"file.txt": "content\n"}
    output = tmp_path / "output"
    output.mkdir()
    for path, content in files.items():
        output.joinpath(path).write_text(content)

    target_path = tmp_path / "target"
    target_path.mkdir()
    target = f"rsync://{target_path.resolve()}?delete={delete}"

    event_iter = publish(env, target, output)
    for line in event_iter:
        print(line)

    target_files = {
        os.fspath(_.relative_to(target_path)): _.read_text()
        for _ in target_path.iterdir()
    }
    assert target_files == files
