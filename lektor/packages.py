import os
import sys
import site
import errno
import click
import shutil
import tempfile
import requests
import pkg_resources
from subprocess import PIPE

from .utils import portable_popen
from lektor._compat import iteritems


class PackageException(Exception):
    pass


def _get_package_version_from_project(cfg, name):
    choices = (name.lower(), 'lektor-' + name.lower())
    for pkg, version in iteritems(cfg.section_as_dict('packages')):
        if pkg.lower() in choices:
            return {
                'name': pkg,
                'version': version
            }


def add_package_to_project(project, req):
    """Given a pacakge requirement this returns the information about this
    plugin.
    """
    if '@' in req:
        name, version = req.split('@', 1)
        version_hint = version
    else:
        name = req
        version = None
        version_hint = 'latest release'

    cfg = project.open_config()
    info = _get_package_version_from_project(cfg, name)
    if info is not None:
        raise RuntimeError('The package was already added to the project.')

    for choice in name, 'lektor-' + name:
        rv = requests.get('https://pypi.python.org/pypi/%s/json' % choice)
        if rv.status_code != 200:
            continue

        data = rv.json()
        canonical_name = data['info']['name']
        if version is None:
            version = data['info']['version']
        version_info = data['releases'].get(version)
        if version_info is None:
            raise RuntimeError('Latest requested version (%s) could not '
                               'be found' % version_hint)

        cfg['packages.%s' % canonical_name] = version
        cfg.save()
        return {
            'name': canonical_name,
            'version': version
        }

    raise RuntimeError('The package could not be found on PyPI')


def remove_package_from_project(project, name):
    cfg = project.open_config()
    choices = (name.lower(), 'lektor-' + name.lower())
    for pkg, version in iteritems(cfg.section_as_dict('packages')):
        if pkg.lower() in choices:
            del cfg['packages.%s' % pkg]
            cfg.save()
            return {
                'name': pkg,
                'version': version
            }


def download_and_install_package(package_root, package=None, version=None,
                                 requirements_file=None):
    """This downloads and installs a specific version of a package."""
    # XXX: windows
    env = dict(os.environ)

    args = [
        sys.executable,
        '-m', 'pip', 'install', '--target', package_root,
    ]

    if package is not None:
        args.append('%s%s%s' % (package, version and '==' or '',
                                version or ''))
    if requirements_file is not None:
        args.extend(('-r', requirements_file))

    rv = portable_popen(args, env=env).wait()
    if rv != 0:
        raise RuntimeError('Failed to install dependency package.')


def install_local_package(package_root, path):
    """This installs a local dependency of a package."""
    # XXX: windows
    env = dict(os.environ)
    env['PYTHONPATH'] = package_root

    # Step 1: generate egg info and link us into the target folder.
    rv = portable_popen([
        sys.executable,
        '-m', 'pip',
        'install', '--editable', path,
        '--install-option=--install-dir=%s' % package_root,
        '--no-deps'
    ], env=env).wait()
    if rv != 0:
        raise RuntimeError('Failed to install local package')

    # Step 2: generate the egg info into a temp folder to find the
    # requirements.
    tmp = tempfile.mkdtemp()
    try:
        rv = portable_popen([
            sys.executable,
            'setup.py', '--quiet', 'egg_info', '--quiet',
            '--egg-base', tmp
        ], cwd=path).wait()
        dirs = os.listdir(tmp)
        if rv != 0 or len(dirs) != 1:
            raise RuntimeError('Failed to create egg info for local package.')
        requires = os.path.join(tmp, dirs[0], 'requires.txt')

        # We have dependencies, install them!
        if os.path.isfile(requires):
            download_and_install_package(package_root,
                                         requirements_file=requires)
    finally:
        shutil.rmtree(tmp)


def get_package_info(path):
    """Returns the name of a package at a path."""
    rv = portable_popen([
        sys.executable,
        'setup.py', '--quiet', '--name', '--author', '--author-email',
        '--license', '--url',
    ], cwd=path, stdout=PIPE).communicate()[0].splitlines()
    def _process(value):
        value = value.strip()
        if value == 'UNKNOWN':
            return None
        return value.decode('utf-8', 'replace')
    return {
        'name': _process(rv[0]),
        'author': _process(rv[1]),
        'author_email': _process(rv[2]),
        'license': _process(rv[3]),
        'url': _process(rv[4]),
        'path': path,
    }


def register_package(path):
    """Registers the plugin at the given path."""
    portable_popen([
        sys.executable,
        'setup.py', 'register'
    ], cwd=path).wait()


def publish_package(path):
    """Registers the plugin at the given path."""
    portable_popen([
        sys.executable,
        'setup.py', 'sdist', 'bdist_wheel', 'upload'
    ], cwd=path).wait()


def load_manifest(filename):
    rv = {}
    try:
        with open(filename) as f:
            for line in f:
                if line[:1] == '@':
                    rv[line.strip()] = None
                    continue
                line = line.strip().split('=', 1)
                if len(line) == 2:
                    key = line[0].strip()
                    value = line[1].strip()
                    rv[key] = value
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise
    return rv


def write_manifest(filename, packages):
    with open(filename, 'w') as f:
        for package, version in sorted(packages.items()):
            if package[:1] == '@':
                f.write('%s\n' % package)
            else:
                f.write('%s=%s\n' % (package, version))


def list_local_packages(path):
    """Lists all local packages below a path that could be installed."""
    rv = []
    try:
        for filename in os.listdir(path):
            if os.path.isfile(os.path.join(path, filename, 'setup.py')):
                rv.append('@' + filename)
    except OSError:
        pass
    return rv


def update_cache(package_root, remote_packages, local_package_path,
                 refresh=False):
    """Updates the package cache at package_root for the given dictionary
    of packages as well as packages in the given local package path.
    """
    requires_wipe = False
    if refresh:
        click.echo('Force package cache refresh.')
        requires_wipe = True

    manifest_file = os.path.join(package_root, 'lektor-packages.manifest')
    local_packages = list_local_packages(local_package_path)

    old_manifest = load_manifest(manifest_file)
    to_install = []

    all_packages = dict(remote_packages)
    all_packages.update((x, None) for x in local_packages)

    # step 1: figure out which remote packages to install.
    for package, version in iteritems(remote_packages):
        old_version = old_manifest.pop(package, None)
        if old_version is None:
            to_install.append((package, version))
        elif old_version != version:
            requires_wipe = True

    # step 2: figure out which local packages to install
    for package in local_packages:
        if old_manifest.pop(package, False) is False:
            to_install.append((package, None))

    # Bad news, we need to wipe everything
    if requires_wipe or old_manifest:
        try:
            shutil.rmtree(package_root)
        except OSError:
            pass
        to_install = iteritems(all_packages)

    if to_install:
        click.echo('Updating packages in %s for project' % package_root)
        try:
            os.makedirs(package_root)
        except OSError:
            pass
        for package, version in to_install:
            if package[:1] == '@':
                install_local_package(package_root,
                    os.path.join(local_package_path, package[1:]))
            else:
                download_and_install_package(package_root, package, version)
        write_manifest(manifest_file, all_packages)


def add_site(path):
    """This adds a path to as proper site packages to all associated import
    systems.  Primarily it invokes `site.addsitedir` and also configures
    pkg_resources' metadata accordingly.
    """
    site.addsitedir(path)
    ws = pkg_resources.working_set
    ws.entry_keys.setdefault(path, [])
    ws.entries.append(path)
    for dist in pkg_resources.find_distributions(path, False):
        ws.add(dist, path, insert=True)


def load_packages(env, reinstall=False):
    """This loads all the packages of a project.  What this does is updating
    the current cache in ``root/package-cache`` and then add the Python
    modules there to the load path as a site directory and register it
    appropriately with pkg_resource's workingset.

    Afterwards all entry points should function as expected and imports
    should be possible.
    """
    config = env.load_config()
    package_root = env.project.get_package_cache_path()
    update_cache(package_root, config['PACKAGES'],
                 os.path.join(env.root_path, 'packages'),
                 refresh=reinstall)
    add_site(package_root)


def wipe_package_cache(env):
    """Wipes the entire package cache."""
    package_root = env.project.get_package_cache_path()
    try:
        shutil.rmtree(package_root)
    except (OSError, IOError):
        pass
