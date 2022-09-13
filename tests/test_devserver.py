import shutil

import pytest

from lektor.devserver import DevTools


@pytest.mark.skipif(shutil.which("npm") is None, reason="npm not available")
def test_DevTools(env):
    devtools = DevTools(env)
    try:
        devtools.start()
    finally:
        devtools.stop()
