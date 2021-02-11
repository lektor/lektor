import pathlib
import tempfile
import textwrap

import pytest

from lektor import packages


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield pathlib.Path(temp_dir)


def create_plugin(package_dir, plugin_name, setup):
    plugin_dir = package_dir / plugin_name
    plugin_dir.mkdir(parents=True)
    setup_py = plugin_dir / "setup.py"
    setup_py.write_text(textwrap.dedent(setup))
    return plugin_dir


def test_install_local_package_with_dependency(temp_dir):
    packages_dir = temp_dir / "packages"
    plugin_dir = create_plugin(
        packages_dir,
        "dependency",
        setup="""
        from setuptools import setup

        setup(
            name='dependency',
            install_requires=['watching_testrunner']
        )
        """,
    )

    install_dir = temp_dir / "target"
    install_dir.mkdir()

    packages.install_local_package(install_dir.as_posix(), plugin_dir.as_posix())

    assert (install_dir / "dependency.egg-link").is_file()
    assert (install_dir / "watching_testrunner").is_dir()


def test_install_local_package_with_dependency_and_extras_require(temp_dir):
    packages_dir = temp_dir / "packages"
    plugin_dir = create_plugin(
        packages_dir,
        "dependency",
        setup="""
        from setuptools import setup

        setup(
            name='dependency',
            install_requires=['watching_testrunner'],
            extras_require={
                'test': ['pyexpect']
            }
        )
        """,
    )

    install_dir = temp_dir / "target"
    install_dir.mkdir()

    packages.install_local_package(install_dir.as_posix(), plugin_dir.as_posix())

    assert (install_dir / "dependency.egg-link").is_file()
    assert (install_dir / "watching_testrunner").is_dir()
    assert not (install_dir / "pyexpect").is_dir()


def test_install_local_package_with_only_extras_require(temp_dir):
    packages_dir = temp_dir / "packages"
    plugin_dir = create_plugin(
        packages_dir,
        "extras_require",
        setup="""
        from setuptools import setup

        setup(
            name='extras_require',
            extras_require={
                'test': ['pyexpect']
            }
        )
        """,
    )

    install_dir = temp_dir / "target"
    install_dir.mkdir()

    packages.install_local_package(install_dir.as_posix(), plugin_dir.as_posix())

    assert (install_dir / "extras-require.egg-link").is_file()
    assert not (install_dir / "pyexpect").is_dir()
