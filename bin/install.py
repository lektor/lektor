#!/usr/bin/env python

import math
import os
import shutil
import sys
import tempfile
from subprocess import call


_is_win = sys.platform == 'win32'

if not _is_win:
    sys.stdin = open('/dev/tty', 'r')

if sys.version_info[0] == 2:
    input = raw_input

prompt = os.environ.get('LEKTOR_SILENT') is None

def get_confirmation():
    if prompt is False:
        return

    while True:
        user_input = input('Continue? [Yn] ').lower().strip()

        if user_input in ('', 'y'):
            print('')
            return

        if user_input == 'n':
            print('')
            print('Aborted!')
            sys.exit()

def fail(message):
    print('Error: %s' % message)
    sys.exit(1)

def multiprint(*lines):
    for line in lines:
        print(line)


class Installer(object):
    APP_NAME = 'lektor'
    VIRTUALENV_URL = 'https://bootstrap.pypa.io/virtualenv.pyz'

    def __init__(self):
        multiprint('',
                   'Welcome to Lektor',
                   '',
                   'This script will install Lektor on your computer.',
                   '')

        self.compute_location()

        self.prompt_installation()
        get_confirmation()

        if self.check_installation():
            self.prompt_wipe()
            get_confirmation()

            self.wipe_installation()

        self.create_virtualenv()
        self.install_lektor()

        multiprint('',
                   'All done!')

    def compute_location(self):
        # this method must set self.lib_dir
        raise NotImplementedError()

    def check_installation(self):
        raise NotImplementedError()

    def wipe_installation(self):
        raise NotImplementedError()

    def prompt_installation(self):
        raise NotImplementedError()

    def prompt_wipe(self):
        raise NotImplementedError()

    def create_virtualenv(self):
        self.mkvirtualenv(self.lib_dir)

    def install_lektor(self):
        call([self.get_pip(), 'install', '--upgrade', 'Lektor'])

    def get_pip(self):
        raise NotImplementedError()

    @classmethod
    def mkvirtualenv(cls, target_dir):
        """
        Tries to create a virtualenv by using the built-in `venv` module,
        or using the `virtualenv` executable if present, or falling back
        to downloading the official zipapp.
        """

        created = False

        try:
            from venv import EnvBuilder
        except ImportError:
            pass
        else:
            try:
                # TODO: design decision needed:
                # on Debian and Ubuntu systems Python is missing `ensurepip`,
                # prompting the user to install `python3-venv` instead.
                # we could do the same, or go the download route...
                import ensurepip
            except ImportError:
                pass
            else:
                venv = EnvBuilder(with_pip=True,
                                  symlinks=False if _is_win else True)
                venv.create(target_dir)
                created = True

        if not created:
            try:
                from shutil import which
            except ImportError:
                from distutils.spawn import find_executable as which

            venv_exec = which("virtualenv")
            if venv_exec:
                retval = call([venv_exec, '-p', sys.executable, target_dir])
                if retval:
                    sys.exit(1)
                created = True

        if not created:
            zipapp = cls.fetch_virtualenv()
            retval = call([sys.executable, zipapp, target_dir])
            os.unlink(zipapp)
            if retval:
                sys.exit(1)

    @classmethod
    def fetch_virtualenv(cls):
        try:
            from urllib.request import urlretrieve
        except ImportError:
            from urllib import urlretrieve

        fname = os.path.basename(cls.VIRTUALENV_URL)
        root, ext = os.path.splitext(fname)

        zipapp = tempfile.mktemp(prefix=root+"-", suffix=ext)

        with Progress() as hook:
            sys.stdout.write("Downloading virtualenv: ")
            urlretrieve(cls.VIRTUALENV_URL, zipapp, reporthook=hook)

        return zipapp

    @staticmethod
    def deletion_error(func, path, excinfo):
        print('Problem deleting {}'.format(path))
        print('Please try and delete {} manually'.format(path))
        print('Aborted!')
        sys.exit(1)


_home = os.environ.get('HOME')

class PosixInstaller(Installer):
    KNOWN_BIN_PATHS = ['/usr/local/bin', '/opt/local/bin']
    if _home: # this is always true, but it needs not blow up on windows
        KNOWN_BIN_PATHS.extend([
            os.path.join(_home, '.bin'),
            os.path.join(_home, '.local', 'bin'),
        ])

    def prompt_installation(self):
        multiprint('Installing at:',
                   '  bin: %s' % self.bin_dir,
                   '  app: %s' % self.lib_dir,
                   '')

    def prompt_wipe(self):
        multiprint('Lektor seems to be installed already.',
                   'Continuing will delete:',
                   '  %s' % self.lib_dir,
                   'and remove this symlink:',
                   '  %s' % self.symlink_path,
                   '')

    def compute_location(self):
        """
        Finds the preferred directory in the user's $PATH,
        and derives the lib dir from it.
        """

        paths = [
            item for item in os.environ['PATH'].split(':')
            if not item.endswith('/sbin') and os.access(item, os.W_OK)
        ]

        if not paths:
            fail('None of the items in $PATH are writable. Run with '
                 'sudo or add a $PATH item that you have access to.')

        def _sorter(path):
            try:
                return self.KNOWN_BIN_PATHS.index(path)
            except ValueError:
                return float('inf')

        paths.sort(key=_sorter)

        lib_dir = None

        home = os.environ['HOME']
        for path in paths:
            if path.startswith(home):
                lib_dir = os.path.join(home, '.local', 'lib', self.APP_NAME)
                break

            if path.endswith('/bin'):
                parent = os.path.dirname(path)
                lib_dir = os.path.join(parent, 'lib', self.APP_NAME)
                break

        if lib_dir is None:
            fail('Could not determine installation location for Lektor.')

        self.bin_dir = path
        self.lib_dir = lib_dir

    @property
    def symlink_path(self):
        return os.path.join(self.bin_dir, self.APP_NAME)

    def check_installation(self):
        return os.path.exists(self.lib_dir) \
            or os.path.lexists(self.symlink_path)

    def wipe_installation(self):
        if os.path.lexists(self.symlink_path):
            os.remove(self.symlink_path)
        if os.path.exists(self.lib_dir):
            shutil.rmtree(self.lib_dir, onerror=self.deletion_error)

    def get_pip(self):
        return os.path.join(self.lib_dir, 'bin', 'pip')

    def install_lektor(self):
        import pdb
        super(PosixInstaller, self).install_lektor()

        bin = os.path.join(self.lib_dir, 'bin', 'lektor')
        os.symlink(bin, self.symlink_path)


class WindowsInstaller(Installer):
    APP_NAME = 'lektor-cli' # backwards-compatibility with previous installer
    LIB_DIR = 'lib'

    def prompt_installation(self):
        multiprint('Installing at:',
                   '  %s' % self.install_dir,
                   '')

    def prompt_wipe(self):
        multiprint('Lektor seems to be installed already.',
                   'Continuing will delete:',
                   '  %s' % self.install_dir,
                   '')

    def compute_location(self):
        install_dir = os.path.join(os.environ['LocalAppData'], self.APP_NAME)
        lib_dir = os.path.join(install_dir, self.LIB_DIR)

        self.install_dir = install_dir
        self.lib_dir = lib_dir

    def check_installation(self):
        return os.path.exists(self.install_dir)

    def wipe_installation(self):
        shutil.rmtree(self.install_dir, onerror=self.deletion_error)

    def get_pip(self):
        return os.path.join(self.lib_dir, 'Scripts', 'pip.exe')

    def install_lektor(self):
        super(WindowsInstaller, self).install_lektor()

        exe = os.path.join(self.lib_dir, 'Scripts', 'lektor.exe')
        link = os.path.join(self.install_dir, 'lektor.cmd')

        with open(link, 'w') as link_file:
            link_file.write('@echo off\n')
            link_file.write('"%s" %%*' % exe)

        self.add_to_path(self.install_dir)

    @staticmethod
    def add_to_path(location):
        try:
            from winreg import (
                OpenKey, CloseKey, QueryValueEx, SetValueEx,
                HKEY_CURRENT_USER, KEY_ALL_ACCESS, REG_EXPAND_SZ,
            )
        except ImportError: # py2
            from _winreg import (
                OpenKey, CloseKey, QueryValueEx, SetValueEx,
                HKEY_CURRENT_USER, KEY_ALL_ACCESS, REG_EXPAND_SZ,
            )
        import ctypes
        from ctypes.wintypes import HWND, UINT, WPARAM, LPARAM, LPVOID

        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x1A

        reg_key = OpenKey(HKEY_CURRENT_USER, 'Environment', 0, KEY_ALL_ACCESS)

        try:
            path_value, _ = QueryValueEx(reg_key, 'Path')
        except WindowsError:
            path_value = ''

        paths = path_value.split(';')
        if location not in paths:
            paths.append(location)
            path_value = ';'.join(paths)
            SetValueEx(reg_key, 'Path', 0, REG_EXPAND_SZ, path_value)

        SendMessage = ctypes.windll.user32.SendMessageW
        SendMessage.argtypes = HWND, UINT, WPARAM, LPVOID
        SendMessage.restype = LPARAM
        SendMessage(HWND_BROADCAST, WM_SETTINGCHANGE, 0, u'Environment')


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

        out.write("%3d" % progress + "%")
        out.flush()

        self.started = True

    def finish(self):
        sys.stdout.write("\n")

    def __enter__(self):
        return self.progress

    def __exit__(self, exc_type, exc_value, traceback):
        self.finish()


install = WindowsInstaller if _is_win \
    else PosixInstaller


if __name__ == '__main__':
    install()
