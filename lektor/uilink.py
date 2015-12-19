import os
import subprocess


RUN_FROM_UI = os.environ.get('LEKTOR_RUN_FROM_UI') == '1'

RESOURCE_PATH = os.environ.get('LEKTOR_RESOURCES') or None
BUNDLE_BIN_PATH = None
BUNDLE_LOCAL_ROOT = None
UI_LANG = None

if RUN_FROM_UI:
    UI_LANG = os.environ.get('LEKTOR_UI_LANG') or None

if RESOURCE_PATH:
    BUNDLE_LOCAL_ROOT = os.path.join(RESOURCE_PATH, 'local')
    BUNDLE_BIN_PATH = os.path.join(BUNDLE_LOCAL_ROOT, 'bin')


def get_user_path():
    """Returns the PATH variable as a user would see it spawning a fresh
    login.  Primarily this is only useful for OS X when lektor is run
    from within a bundle where the PATH variables are not available if
    they are set from the shell profile.

    On Windows this always returns the current path.
    """
    if os.name == 'nt':
        return os.environ['PATH'].split(';')
    return subprocess.Popen(
        ['bash', '--login', '-c', 'echo $PATH'],
        stdout=subprocess.PIPE).communicate()[0].split(':')


EXTRA_PATHS = []
if RUN_FROM_UI and os.name == 'darwin':
    EXTRA_PATHS.extend(get_user_path())


def main():
    """The main function for when invoked from an UI bundle."""
    from .cli import main
    main(prog_name='lektor')


if __name__ == '__main__':
    main()
