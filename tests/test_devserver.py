import re
import shutil

import pytest

from lektor.devserver import DevTools


@pytest.mark.skipif(shutil.which("npm") is None, reason="npm not available")
def test_DevTools(env):
    devtools = DevTools(env)
    try:
        devtools.start()
        # check that starting again is ignored
        watcher = devtools.watcher
        devtools.start()
        assert devtools.watcher is watcher
    finally:
        devtools.stop()
        # check that stop is idempotent
        devtools.stop()


def test_DevTools_no_frontend_src(env, monkeypatch, tmp_path):
    monkeypatch.setattr(DevTools, "frontend_path", tmp_path / "missing")
    devtools = DevTools(env)
    devtools.start()
    assert devtools.watcher is None


def test_DevTools_no_npm(env, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(DevTools, "frontend_path", tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _: None)
    devtools = DevTools(env)
    devtools.start()
    assert devtools.watcher is None
    std = capsys.readouterr()
    assert re.search(r"Can not find .* command", std.out)


def test_DevTools_npm_install_failure(env, mocker, capsys, tmp_path):
    mocker.patch.object(DevTools, "frontend_path", tmp_path)
    mocker.patch("shutil.which").return_value = "npm"
    mocker.patch("subprocess.run").return_value.returncode = 1
    devtools = DevTools(env)
    devtools.start()
    assert devtools.watcher is None
    std = capsys.readouterr()
    assert re.search(r"Command .npm install. failed", std.out)
