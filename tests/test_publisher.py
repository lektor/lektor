from lektor.publisher import Command


def test_Command_triggers_no_warnings(recwarn):
    # This excercises the issue where publishing via rsync resulted
    # in ResourceWarnings about unclosed streams.

    # This is essentially how RsyncPublisher runs rsync.
    with Command(["echo"]) as client:
        for _ in client:
            pass
    # Delete our reference so that the Command instance gets garbage
    # collected here. Otherwise, gc will not happen until after the
    # test completes and warnings emitted during gc will not be captured
    # by the recwarn fixture.
    del client

    for warning in recwarn.list:
        print(warning)
    assert len(recwarn) == 0
