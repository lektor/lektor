import gc
import warnings
import weakref

import pytest

from lektor.publisher import Command


def test_Command_triggers_no_warnings():
    # This excercises the issue where publishing via rsync resulted
    # in ResourceWarnings about unclosed streams.

    with pytest.warns(None) as record:
        # This is essentially how RsyncPublisher runs rsync.
        with Command(["echo"]) as client:
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

    for warning in record.list:
        print(warning)
    assert len(record) == 0
