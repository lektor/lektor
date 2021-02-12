import textwrap

from lektor import packages


def create_plugin(package_dir, plugin_name, setup):
    plugin_dir = package_dir / plugin_name
    plugin_dir.mkdir(parents=True)
    setup_py = plugin_dir / "setup.py"
    setup_py.write_text(textwrap.dedent(setup))
    return plugin_dir


def test_install_local_package_with_dependency(tmp_path):
    packages_dir = tmp_path / "packages"
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

    install_dir = tmp_path / "target"
    install_dir.mkdir()

    packages.install_local_package(install_dir.as_posix(), plugin_dir.as_posix())

    assert (install_dir / "dependency.egg-link").is_file()
    assert (install_dir / "watching_testrunner.py").is_file()


def test_install_local_package_with_dependency_and_extras_require(tmp_path):
    packages_dir = tmp_path / "packages"
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

    install_dir = tmp_path / "target"
    install_dir.mkdir()

    packages.install_local_package(install_dir.as_posix(), plugin_dir.as_posix())

    assert (install_dir / "dependency.egg-link").is_file()
    assert (install_dir / "watching_testrunner.py").is_file()
    assert not (install_dir / "pyexpect").is_dir()


def test_install_local_package_with_only_extras_require(tmp_path):
    packages_dir = tmp_path / "packages"
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

    install_dir = tmp_path / "target"
    install_dir.mkdir()

    packages.install_local_package(install_dir.as_posix(), plugin_dir.as_posix())

    assert (install_dir / "extras-require.egg-link").is_file()
    assert not (install_dir / "pyexpect").is_dir()
