"""Tests for the hatch build hooks in ../build_frontend.py."""
import os
import shutil
import sys
from importlib.util import module_from_spec
from importlib.util import spec_from_file_location
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture(scope="session")
def frontend_build_module():
    return import_module_from_file("build_frontend", "../build_frontend.py")


@pytest.fixture
def tmp_root(tmp_path):
    root = tmp_path / "root"
    lektor_admin = root / "lektor/admin"
    lektor_admin.mkdir(parents=True)
    return root


@pytest.fixture
def frontend_src(tmp_root):
    """Copy the frontend source to tmp_root"""
    top = Path(__file__).parent / ".."
    for path in "frontend", "lektor/translations":
        dst = tmp_root / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(top / path, dst, ignore=shutil.ignore_patterns("node_modules"))


@pytest.fixture
def compiled_output(tmp_root):
    app_js = tmp_root / "lektor/admin/static/app.js"
    app_js.parent.mkdir(parents=True, exist_ok=True)
    app_js.touch()
    return app_js


@pytest.fixture
def frontend_build_hook(frontend_build_module, tmp_root, tmp_path):
    return frontend_build_module.FrontendBuildHook(
        root=tmp_root,
        config={},
        build_config=Mock(name="BuilderConfig"),
        metadata=Mock(name="ProjectMetadata"),
        directory=tmp_path / "dist",
        target_name="wheel",
    )


@pytest.mark.usefixtures("frontend_src")
def test_clean(frontend_build_hook, compiled_output):
    frontend_build_hook.clean(("standard",))
    assert not compiled_output.parent.exists()


@pytest.mark.usefixtures("frontend_src")
def test_clean_idempotent(frontend_build_hook, compiled_output):
    frontend_build_hook.clean(("standard",))
    assert not compiled_output.parent.exists()
    frontend_build_hook.clean(("standard",))
    assert not compiled_output.parent.exists()


def test_clean_skipped_if_no_frontend(frontend_build_hook, compiled_output):
    frontend_build_hook.clean(("standard",))
    assert compiled_output.parent.exists()


@pytest.mark.usefixtures("frontend_src")
def test_initialize_skips_build_if_output_exists(
    frontend_build_hook, compiled_output, mocker
):
    mocker.patch("shutil.which").return_value = None
    frontend_build_hook.initialize("standard", build_data={})
    assert compiled_output.exists()


@pytest.mark.usefixtures("frontend_src")
def test_initialize_aborts_if_no_npm(
    frontend_build_hook, frontend_build_module, monkeypatch
):
    monkeypatch.setitem(os.environ, "PATH", "")
    with pytest.raises(SystemExit) as exc_info:
        frontend_build_hook.initialize("standard", build_data={})
    assert exc_info.value.args[0] == 1


def test_initialize_aborts_if_no_source(frontend_build_hook, mocker):
    mocker.patch("shutil.which").return_value = "/bin/false"
    with pytest.raises(SystemExit) as exc_info:
        frontend_build_hook.initialize("standard", build_data={})
    assert exc_info.value.args[0] == 1


@pytest.mark.skipif(shutil.which("npm") is None, reason="npm not installed")
@pytest.mark.requiresinternet
@pytest.mark.slowtest
@pytest.mark.usefixtures("frontend_src")
def test_initialize_builds_frontend(frontend_build_hook, tmp_root):
    frontend_build_hook.initialize("standard", build_data={})
    app_js = tmp_root / "lektor/admin/static/app.js"
    assert app_js.stat().st_size > 1024


def import_module_from_file(module_name: str, path: str) -> None:
    """Import a module or package from a specific source (``.py``) file

    This bypasses the normal search of ``sys.path``, etc., directly
    importing the module from the specified python source file.

    The imported module is registered, as usual, in ``sys.modules``.

    If the path to the source file is relative, it is interpreted
    relative to the directory containing this script.

    """
    # Copied more-or-less verbatim from:
    # https://docs.python.org/3/library/importlib.html?highlight=import#importing-a-source-file-directly
    here = Path(__file__).parent
    spec = spec_from_file_location(module_name, here / path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(f"Can not find {module_name}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
