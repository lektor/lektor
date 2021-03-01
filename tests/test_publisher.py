import os
import queue
import threading
from itertools import chain

import pytest

from lektor.publisher import _join_pipes_using_select
from lektor.publisher import _join_pipes_using_threads
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


def iter_in_thread(it):
    """Iterate iterable in a separate thread.

    This is a generator which yields the results of the iterable.
    I.e. mostly, it's transparent.

    The results are passed back to the calling thread via a queue.  If
    the queue remains empty for a bit of time, a marker ("[TIMED
    OUT]") will be yielded.

    Reading the iterable in a separate thread prevents possible
    deadlock that might happen if a single thread were reading/writing
    both sides of a pipe.

    The timeout prevents the test from getting hung when expected
    results are not forthcoming.

    """

    q = queue.Queue()
    eof = object()

    def run():
        for item in chain(it, [eof]):
            q.put(item)

    threading.Thread(target=run, daemon=True).start()
    while True:
        try:
            item = q.get(timeout=0.1)
        except queue.Empty:
            item = "[TIMED OUT]"
        else:
            if item is eof:
                break
        yield item


@pytest.fixture(params=[_join_pipes_using_threads, _join_pipes_using_select])
def join_pipes(request):
    if request.param is _join_pipes_using_select and os.name == "nt":
        pytest.skip("_join_pipes_using_select does not work on Windows")
    return request.param


@pytest.fixture
def pipes():
    class Streams(tuple):
        def close(self):
            for stream in self:
                if not stream.closed:
                    stream.close()

    pipes = [os.pipe() for n in range(2)]
    readers = Streams(open(r, "rb") for r, w in pipes)
    writers = Streams(open(w, "wb", buffering=0) for r, w in pipes)
    try:
        yield readers, writers
    finally:
        writers.close()
        readers.close()


def test_join_pipes_joins_pipes(join_pipes, pipes):
    readers, writers = pipes

    output = iter_in_thread(join_pipes(*readers))

    writers[0].write(b"a\n")
    writers[1].write(b"b\n")
    assert {next(output), next(output)} == {b"a\n", b"b\n"}

    writers.close()
    assert next(output, "EOF") == "EOF"


def test_join_pipes_prevents_partial_line_deadlock(join_pipes, pipes):
    readers, writers = pipes

    output = iter_in_thread(join_pipes(*readers))

    # exercise bug where we got stuck blocked in .readline() on partial line
    for line in (b"line1\n", b"line2\n"):
        writers[0].write(b"x")
        writers[1].write(line)
        assert next(output) == line
    writers.close()
    assert next(output) == b"xx"
    assert next(output, "EOF") == "EOF"
