import os
from pathlib import Path

import pytest

from lektor.packages import add_site
from lektor.packages import install_local_package
from lektor.pluginsystem import load_plugins


@pytest.mark.usefixtures("save_sys_path")
def test_install_local_package(tmp_path):
    package_root = os.fspath(tmp_path / "package_root")
    dummy_plugin_path = os.fspath(Path(__file__).parent / "setup_py-dummy-plugin")
    install_local_package(package_root, dummy_plugin_path)
    add_site(package_root)
    plugins = load_plugins()
    assert plugins["dummy-plugin"].name == "dummy"
