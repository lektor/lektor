from __future__ import annotations

import hashlib
import os
import shutil
import site
import subprocess
import sys
import sysconfig
from collections.abc import Sized
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Iterator
from typing import TYPE_CHECKING
from venv import EnvBuilder

import click
import requests


if TYPE_CHECKING:
    from _typeshed import StrPath
    from lektor.environment import Environment  # circ dependency
else:
    StrPath = object


def _get_package_version_from_project(cfg, name):
    choices = (name.lower(), "lektor-" + name.lower())
    for pkg, version in cfg.section_as_dict("packages").items():
        if pkg.lower() in choices:
            return {"name": pkg, "version": version}
    return None


def add_package_to_project(project, req):
    """Given a package requirement this returns the information about this
    plugin.
    """
    if "@" in req:
        name, version = req.split("@", 1)
        version_hint = version
    else:
        name = req
        version = None
        version_hint = "latest release"

    cfg = project.open_config()
    info = _get_package_version_from_project(cfg, name)
    if info is not None:
        raise RuntimeError("The package was already added to the project.")

    for choice in name, "lektor-" + name:
        rv = requests.get(f"https://pypi.python.org/pypi/{choice}/json", timeout=10)
        if rv.status_code != 200:
            continue

        data = rv.json()
        canonical_name = data["info"]["name"]
        if version is None:
            version = data["info"]["version"]
        version_info = data["releases"].get(version)
        if version_info is None:
            raise RuntimeError(
                f"Latest requested version ({version_hint}) could not be found"
            )

        cfg["packages.%s" % canonical_name] = version
        cfg.save()
        return {"name": canonical_name, "version": version}

    raise RuntimeError("The package could not be found on PyPI")


def remove_package_from_project(project, name):
    cfg = project.open_config()
    choices = (name.lower(), "lektor-" + name.lower())
    for pkg, version in cfg.section_as_dict("packages").items():
        if pkg.lower() in choices:
            del cfg["packages.%s" % pkg]
            cfg.save()
            return {"name": pkg, "version": version}
    return None


if os.name == "nt":
    _default_venv_symlinks = False
else:
    _default_venv_symlinks = True


class VirtualEnv:
    """A helper for manipulating our private package cache virtual environment.

    Parameters:

    path — The path to the virtual environment to manage.  This can be an existing
    environment or not.

    """

    def __init__(self, path: StrPath):
        self.path = Path(path)

    def create(
        self,
        with_pip: bool = True,
        upgrade_deps: bool = True,
        symlinks: bool = _default_venv_symlinks,
    ) -> None:
        """(Re-)Create a new virtual environment.

        This will remove any existing virtual environment and create a new one.

        The parameters ``with_pip`` and ``upgrade_deps`` should probably be left at
        their default values in normal usage.  They are provided here mostly for use in
        tests. They work as described for ``venv.EnvBuilder`` from the standard library.
        (Though ``upgrade_deps`` is only supported by EnvBuilder`` in py39+, here we
        emulate it's behavior if running under older pythons.)

        """
        # Right now, by default, we always install and upgrade pip to
        # the latest available version.
        #
        # We could optimize by not installing (and not upgrading) pip if
        # the system pip is sufficient to our needs.
        #
        # Note that, e.g., pip>=21.3 is required to support PEP660 editable
        # installs.
        options: dict[str, Any] = {
            "clear": True,
            "with_pip": with_pip,
            "symlinks": symlinks,
        }
        if sys.version_info >= (3, 9):
            EnvBuilder(upgrade_deps=upgrade_deps, **options).create(self.path)
        else:
            EnvBuilder(**options).create(self.path)
            if upgrade_deps:
                self.run_pip_install("--upgrade", "pip", "setuptools")

    def addsitedir(self, sitedir: str) -> None:
        """Add an additional sitedir to sys.path for virtual environment.

        Packages installed in ``sitedir`` will be made available to any invocations
        of python running within the virtual environment.
        """
        with Path(self.site_packages, "_lektor.pth").open("a", encoding="utf-8") as fp:
            fp.write(f"import site; site.addsitedir({sitedir!r})\n")

    def run_pip_install(self, *args: str) -> None:
        """Run `pip install` in the virtual environment.

        ``Args`` are appended to the command line (following ``pip install``). They
        should specify how and which packages to install.

        """
        try:
            subprocess.run((self.executable, "-m", "pip", "install", *args), check=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Failed to install dependency package.") from exc

    @property
    def site_packages(self) -> str:
        """The path to the virtual environments ``site-packages`` directory."""
        return self._get_path("purelib")

    @property
    def executable(self) -> str:
        """The path to the python interpreter for the virtual environment."""
        script_path = Path(self._get_path("scripts"))
        executable_name = Path(sys.executable).name
        return os.fspath(script_path / executable_name)

    def _get_path(self, name: str) -> str:
        vars = {"base": os.fspath(self.path)}
        return sysconfig.get_path(name, vars=vars)


class Requirements(Iterable[str], Sized):
    """Manage package requirements."""

    requirements: set[str]

    def __init__(self) -> None:
        self.requirements = set()

    def __len__(self) -> int:
        return len(self.requirements)

    def __iter__(self) -> Iterator[str]:
        """The requirements.

        These requirements are in the form of arguments that can be passed to ``pip
        install``.
        """
        return iter(self.requirements)

    def add_requirement(self, package: str, version: str | None = None) -> None:
        """Add a (remote) distribution to the requirements."""
        self.requirements.add(f"{package}=={version}" if version else f"{package}")

    def add_local_requirement(self, path: StrPath) -> None:
        """Add a local distribution source directory to the requirements.

        The distribution source at ``path`` (which should be a legacy `setup.py` or
        modern PEP660-compatible project) will be installed in editable mode.

        """
        srcdir = os.fspath(Path(path).resolve())
        self.requirements.add(f"--editable={srcdir}")

    _DIST_FILES = ("setup.py", "pyproject.toml")

    def add_local_requirements_from(self, packages_path: StrPath) -> None:
        """Add sub-directories of path that look like local distribution sources.

        Any direct sub-directories of ``packages_path`` which appear to be distribution
        source code will be added to the requirements in local (editable) mode.

        """
        try:
            for path in Path(packages_path).iterdir():
                if any(path.joinpath(fn).is_file() for fn in self._DIST_FILES):
                    self.add_local_requirement(path)
        except OSError:
            pass

    def hash(self) -> str:
        """Compute a hash of the requirement set."""
        hash = hashlib.sha1()
        for requirement in sorted(self.requirements):
            hash.update(requirement.encode("utf-8"))
            hash.update(b"\0")
        return hash.hexdigest()


def update_cache(
    venv_path: Path,
    remote_packages: dict[str, str],
    local_package_path: Path,
) -> None:
    """Ensure the package cache at venv_path is up-to-date.

    ``Remote_packages`` is a dictionary (mapping package names to required versions)
    that specifies remote packages (to be installed from PyPI).

    ``Local_package_page`` is a path to a directory whose sub-directories may contain
    local plugin source.  Any such source directories will be installed in "editable"
    mode.

    """
    requirements = Requirements()
    for package, version in remote_packages.items():
        requirements.add_requirement(package, version)
    requirements.add_local_requirements_from(local_package_path)

    if len(requirements) == 0:
        shutil.rmtree(venv_path, ignore_errors=True)
    else:
        hash_file = venv_path / "lektor-requirements-hash.txt"
        try:
            is_stale = hash_file.read_text().strip() != requirements.hash()
        except FileNotFoundError:
            is_stale = True

        if is_stale:
            venv = VirtualEnv(venv_path)
            venv.create()
            # Add our site-packages to venv's sys.path
            our_site_packages = sysconfig.get_path("purelib")
            venv.addsitedir(our_site_packages)

            venv.run_pip_install(*requirements)
            hash_file.write_text(f"{requirements.hash()}\n", encoding="ascii")


def load_packages(env: Environment, reinstall: bool = False) -> None:
    """Import all of our managed plugins into our ``sys.path``

    This first ensures that our private package cache is up-to-date, then
    adds it to ``sys.path``.

    After ``load_packages`` is called, the entry points defined in by
    plugins that we manage will be available.
    """
    if reinstall:
        click.echo("Force package cache refresh.")
        wipe_package_cache(env)

    config = env.load_config()
    venv_path = env.project.get_package_cache_path()
    update_cache(venv_path, config["PACKAGES"], Path(env.root_path, "packages"))
    site.addsitedir(VirtualEnv(venv_path).site_packages)


def wipe_package_cache(env: Environment) -> None:
    """Remove the entire package cache."""
    project = env.project
    # Remove the legacy flat package cache, too
    for cache_type in project.PackageCacheType:
        shutil.rmtree(project.get_package_cache_path(cache_type), ignore_errors=True)
