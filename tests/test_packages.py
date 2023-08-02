import inspect
import os
import re
import sys
import sysconfig
from pathlib import Path
from subprocess import PIPE
from subprocess import run

import pytest
from pytest_mock import MockerFixture

from lektor.environment import Environment
from lektor.packages import load_packages
from lektor.packages import Requirements
from lektor.packages import update_cache
from lektor.packages import VirtualEnv
from lektor.project import Project


@pytest.fixture(scope="module")
def nested_venv(tmp_path_factory: pytest.TempPathFactory) -> VirtualEnv:
    """Create a lighweight nested virtual environment.

    The created venv does not have anything installed in it — not even pip. It does,
    however, have our ``site-packages`` directory added to its ``sys.path``, so it
    should have access to a working ``pip`` that way.

    This lightweight venv is relative quick to create.  Creating a full independent
    venv involves running ``python -m ensurepip`` and potential network requests
    to PyPI.
    """
    tmp_path = tmp_path_factory.mktemp("nested_venv")
    venv = VirtualEnv(tmp_path)
    # venv creation is very quick without installing/upgrading pip
    venv.create(with_pip=False, upgrade_deps=False)

    # add our site-packages to the venv's sys.path
    venv.addsitedir(sysconfig.get_path("purelib"))
    return venv


def test_VirtualEnv_creates_site_packages(tmp_path: Path) -> None:
    venv = VirtualEnv(tmp_path)
    # venv creation is very quick without installing/upgrading pip
    venv.create(with_pip=False, upgrade_deps=False)
    assert Path(venv.site_packages).is_dir()


def test_VirtualEnv_addsitedir(nested_venv: VirtualEnv) -> None:
    # check that we can run pytest (presumably from our site-packages)
    proc = run((nested_venv.executable, "-m", "pytest", "--version"), check=False)
    assert proc.returncode == 0


@pytest.mark.skipif(os.name == "nt", reason="Windows")
def test_VirtualEnv_uses_symlinks(nested_venv: VirtualEnv) -> None:
    executable = Path(nested_venv.executable)
    assert executable.resolve(strict=True).parent != executable.parent


@pytest.mark.requiresinternet
@pytest.mark.slowtest
def test_VirtualEnv_run_pip_install(tmp_path: Path) -> None:
    # XXX: slow test
    venv = VirtualEnv(tmp_path)
    venv.create()

    # install a dummy plugin
    plugin_path = Path(__file__).parent / "pep660-dummy-plugin"
    dummy_plugin_path = os.fspath(plugin_path.resolve())
    venv.run_pip_install(f"--editable={dummy_plugin_path}")

    # Make our lektor available to the installed plugin
    venv.addsitedir(sysconfig.get_path("purelib"))

    # Check that we can load the plugin entry point
    prog = inspect.cleandoc(
        """
        import sys
        if sys.version_info < (3, 10):
            # need "selectable" entry_points
            import importlib_metadata as metadata
        else:
            from importlib import metadata

        for ep in metadata.entry_points(group="lektor.plugins", name="dummy"):
            print(ep.load().__name__)
    """
    )
    proc = run((venv.executable, "-c", prog), stdout=PIPE, text=True, check=True)
    assert proc.stdout.strip() == "DummyPlugin"


def test_VirtualEnv_run_pip_install_raises_runtime_error(
    nested_venv: VirtualEnv, capfd: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(RuntimeError) as excinfo:
        nested_venv.run_pip_install("--unknown-option")
    assert excinfo.match("Failed to install")
    assert "no such option" in capfd.readouterr().err


def test_VirtualEnv_site_packages(tmp_path: Path) -> None:
    site_packages = VirtualEnv(tmp_path).site_packages
    relpath = os.fspath(Path(site_packages).relative_to(tmp_path))
    assert re.match(r"(?i)lib(?=[/\\]).*[/\\]site-packages\Z", relpath)


def test_VirtualEnv_executable(tmp_path: Path) -> None:
    executable = Path(VirtualEnv(tmp_path).executable)
    scripts_dir = os.fspath(executable.parent.relative_to(tmp_path))
    assert scripts_dir in {"bin", "Scripts"}
    assert executable.name == Path(sys.executable).name


def test_Requirements_add_requirement() -> None:
    requirements = Requirements()
    requirements.add_requirement("foo", "1.2")
    requirements.add_requirement("bar")
    assert len(requirements) == 2
    assert set(requirements) == {"foo==1.2", "bar"}


def test_Requirements_add_local_requirement() -> None:
    requirements = Requirements()
    plugin_path = Path(__file__).parent / "pep660-dummy-plugin"
    requirements.add_local_requirement(plugin_path)
    assert set(requirements) == {f"--editable={os.fspath(plugin_path.resolve())}"}


def test_Requirements_add_local_requirements_from(tmp_path: Path) -> None:
    for fn in ["plugin1/pyproject.toml", "plugin2/setup.py", "notaplugin/README.md"]:
        path = tmp_path / fn
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    requirements = Requirements()
    requirements.add_local_requirements_from(tmp_path)
    assert len(requirements) == 2
    assert {req.rpartition(os.sep)[2] for req in requirements} == {"plugin1", "plugin2"}


def test_Requirements_add_local_requirements_from_missing_dir(tmp_path: Path) -> None:
    requirements = Requirements()
    requirements.add_local_requirements_from(tmp_path / "missing")
    assert len(requirements) == 0
    assert not requirements


def test_Requirements_hash() -> None:
    requirements = Requirements()
    assert requirements.hash() == "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    requirements.add_requirement("foo", "42")
    assert requirements.hash() == "a44f078eab8bc1aa1ddfd111d63e24ff65131b4b"


def test_update_cache_installs_requirements(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    venv_path = tmp_path / "cache"
    venv_path.mkdir()
    VirtualEnv = mocker.patch("lektor.packages.VirtualEnv")
    update_cache(venv_path, {"foo": "42"}, tmp_path / "packages")
    assert mocker.call().run_pip_install("foo==42") in VirtualEnv.mock_calls
    hash_file = venv_path / "lektor-requirements-hash.txt"
    assert hash_file.read_text().strip() == "a44f078eab8bc1aa1ddfd111d63e24ff65131b4b"


def test_update_cache_skips_install_if_up_to_date(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    venv_path = tmp_path / "cache"
    venv_path.mkdir()
    venv_path.joinpath("lektor-requirements-hash.txt").write_text(
        "a44f078eab8bc1aa1ddfd111d63e24ff65131b4b\n"
    )
    VirtualEnv = mocker.patch("lektor.packages.VirtualEnv")
    update_cache(venv_path, {"foo": "42"}, tmp_path / "packages")
    assert VirtualEnv.mock_calls == []


def test_update_cache_removes_package_cache_if_no_requirements(tmp_path: Path) -> None:
    venv_path = tmp_path / "cache"
    venv_path.mkdir()

    update_cache(venv_path, {}, tmp_path / "missing")
    assert not venv_path.exists()


def test_load_packages_add_package_cache_to_sys_path(env: Environment) -> None:
    load_packages(env)
    venv_path = env.project.get_package_cache_path()
    site_packages = VirtualEnv(venv_path).site_packages
    assert site_packages in sys.path


PackageCacheType = Project.PackageCacheType


@pytest.mark.parametrize("cache_type", PackageCacheType)
def test_load_packages_reinstall_wipes_cache(
    env: Environment, cache_type: PackageCacheType
) -> None:
    project = env.project
    cache_path = project.get_package_cache_path(cache_type)
    cache_path.mkdir(parents=True, exist_ok=False)

    load_packages(env, reinstall=True)
    assert not cache_path.exists()
