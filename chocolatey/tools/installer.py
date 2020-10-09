#!/usr/bin/env python

from __future__ import print_function
import math
import os
import shutil
import sys
import tempfile
from subprocess import call

try:
    from shutil import which
except ImportError:
    from distutils.spawn import find_executable as which

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

IS_WIN = sys.platform == "win32"

if IS_WIN:
    try:
        import winreg
    except ImportError:
        import _winreg as winreg
    from ctypes import windll, wintypes


VIRTUALENV_URL = "https://bootstrap.pypa.io/virtualenv.pyz"

# this difference is for backwards-compatibility with the previous installer
APP_NAME = "lektor" if not IS_WIN else "lektor-cli"

# where to search for a writable bin directory on *nix.
# this order makes sure we try a system install first.
POSIX_BIN_DIRS = [
    "/usr/local/bin", "/opt/local/bin",
    "{home}/.bin", "{home}/.local/bin",
]

SILENT = (
    os.environ.get("LEKTOR_SILENT", "").lower()
    not in ("", "0", "off", "false")
)

if not os.isatty(sys.stdin.fileno()):
    # the script is being piped, we need to reset stdin
    sys.stdin = open("CON:" if IS_WIN else "/dev/tty")

if sys.version_info.major == 2:
    input = raw_input


def get_confirmation():
    if SILENT:
        return

    while True:
        user_input = 'y'

        if user_input in ("", "y"):
            print()
            return


def fail(message):
    print("Error: %s" % message, file=sys.stderr)
    sys.exit(1)


def multiprint(*lines, **kwargs):
    for line in lines:
        print(line, **kwargs)


def rm_recursive(*paths):
    def _error(path):
        multiprint(
            "Problem deleting {}".format(path),
            "Please try and delete {} manually".format(path),
            "Aborted!",
            file=sys.stderr,
        )
        sys.exit(1)

    def _rm(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    for path in paths:
        if not os.path.lexists(path):
            continue
        try:
            _rm(path)
        except:
            _error(path)


class Progress(object):
    "A context manager to be used as a urlretrieve reporthook."

    def __init__(self):
        self.started = False

    def progress(self, count, bsize, total):
        size = count * bsize

        if size > total:
            progress = 100
        else:
            progress = math.floor(100 * size / total)

        out = sys.stdout
        if self.started:
            out.write("\b" * 4)

        out.write("{:3d}%".format(progress))
        out.flush()

        self.started = True

    def finish(self):
        sys.stdout.write("\n")

    def __enter__(self):
        return self.progress

    def __exit__(self, exc_type, exc_value, traceback):
        self.finish()


class FetchTemp(object):
    """
    Fetches the given URL into a temporary file.
    To be used as a context manager.
    """

    def __init__(self, url):
        self.url = url

        fname = os.path.basename(url)
        root, ext = os.path.splitext(fname)
        self.filename = tempfile.mktemp(prefix=root + "-", suffix=ext)

    def fetch(self):
        with self.Progress() as hook:
            urlretrieve(self.url, self.filename, reporthook=hook)

    def cleanup(self):
        os.remove(self.filename)

    def __enter__(self):
        self.fetch()

        return self.filename

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()


def create_virtualenv(target_dir):
    """
    Tries to create a virtualenv by using the built-in `venv` module,
    or using the `virtualenv` executable if present, or falling back
    to downloading the official zipapp.
    """

    def use_venv():
        try:
            import venv
        except ImportError:
            return

        # on Debian and Ubuntu systems Python is missing `ensurepip`,
        # prompting the user to install `python3-venv` instead.
        #
        # we could handle this, but we'll just let the command fail
        # and have the users install the package themselves.

        return call([sys.executable, "-m", "venv", target_dir])

    def use_virtualenv():
        venv_exec = which("virtualenv")
        if not venv_exec:
            return

        return call([venv_exec, "-p", sys.executable, target_dir])

    def use_zipapp():
        print("Downloading virtualenv: ", end="")
        with FetchTemp(VIRTUALENV_URL) as zipapp:
            return call([sys.executable, zipapp, target_dir])

    print("Installing virtual environment...")
    for func in use_venv, use_virtualenv, use_zipapp:
        retval = func()
        if retval is None:
            # command did not run
            continue
        if retval == 0:
            # command successful
            return
        # else...
        sys.exit(1)


def get_pip(lib_dir):
    return (
        os.path.join(lib_dir, "Scripts", "pip.exe") if IS_WIN
        else os.path.join(lib_dir, "bin", "pip")
    )


def install_lektor(lib_dir):
    create_virtualenv(lib_dir)

    pip = get_pip(lib_dir)

    args = [pip, "install"]
    if IS_WIN:
        # avoid fail due to PEP 517 on windows
        args.append("--prefer-binary")
    args.extend(["--upgrade", "Lektor"])

    return call(args)


def posix_find_bin_dir():
    home = os.environ["HOME"]
    preferred = [d.format(home=home) for d in POSIX_BIN_DIRS]

    # look for writable directories in the user's $PATH
    # (that are not sbin)
    dirs = [
        item
        for item in os.environ["PATH"].split(":")
        if not item.endswith("/sbin") and os.access(item, os.W_OK)
    ]

    if not dirs:
        fail(
            "None of the items in $PATH are writable. Run with "
            "sudo or add a $PATH item that you have access to."
        )

    # ... and prioritize them according to our preferences
    def _sorter(path):
        try:
            return preferred.index(path)
        except ValueError:
            return float("inf")

    dirs.sort(key=_sorter)
    return dirs[0]


def posix_find_lib_dir(bin_dir):
    # the chosen lib_dir depends on the bin_dir found:
    home = os.environ["HOME"]

    if bin_dir.startswith(home):
        # this is a local install
        return os.path.join(home, ".local", "lib", APP_NAME)

    # else, it's a system install
    parent = os.path.dirname(bin_dir)
    return os.path.join(parent, "lib", APP_NAME)


def windows_create_link(lib_dir, target_dir):
    exe = os.path.join(lib_dir, "Scripts", "lektor.exe")
    link = os.path.join(target_dir, "lektor.cmd")

    with open(link, "w") as link_file:
        link_file.write("@echo off\n")
        link_file.write('"{}" %*'.format(exe))


def windows_add_to_path(location):
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x1A

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS
    )

    try:
        value, _ = winreg.QueryValueEx(key, "Path")
    except WindowsError:
        value = ""

    paths = [path for path in value.split(";") if path != ""]

    if location not in paths:
        paths.append(location)
        value = ";".join(paths)
        winreg.SetValueEx(
            key, "Path", 0, winreg.REG_EXPAND_SZ, value
        )

        SendMessage = windll.user32.SendMessageW
        SendMessage.argtypes = (
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPVOID
        )
        SendMessage.restype = wintypes.LPARAM
        SendMessage(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")

        # also add the path to the environment,
        # so it's available in the current console
        os.environ['Path'] += ";%s" % location

    key.Close()


def posix_install():
    bin_dir = posix_find_bin_dir()
    lib_dir = posix_find_lib_dir(bin_dir)
    symlink_path = os.path.join(bin_dir, APP_NAME)

    multiprint(
        "Installing at:",
        "  bin: %s" % bin_dir,
        "  app: %s" % lib_dir,
        "",
    )

    if os.path.exists(lib_dir) or os.path.lexists(symlink_path):
        multiprint(
            "An existing installation was detected. This will be removed!",
            "",
        )

    get_confirmation()
    rm_recursive(lib_dir, symlink_path)
    install_lektor(lib_dir)

    os.symlink(os.path.join(lib_dir, "bin", "lektor"), symlink_path)


def windows_install():
    install_dir = os.path.join(os.environ["LocalAppData"], APP_NAME)
    lib_dir = os.path.join(install_dir, "lib")

    multiprint(
        "Installing at:",
        "  %s" % install_dir,
        "",
    )

    if os.path.exists(install_dir):
        multiprint(
            "An existing installation was detected. This will be removed!",
            "",
        )

    get_confirmation()
    rm_recursive(install_dir)
    install_lektor(lib_dir)

    windows_create_link(lib_dir, install_dir)
    windows_add_to_path(install_dir)


def install():
    multiprint(
        "",
        "Welcome to Lektor",
        "This script will install Lektor on your computer.",
        "",
    )

    if IS_WIN:
        windows_install()
    else:
        posix_install()

    multiprint(
        "",
        "All done!",
    )


if __name__ == "__main__":
    install()
