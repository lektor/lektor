import os
import sys
import hashlib
from inifile import IniFile
from werkzeug.utils import cached_property

from lektor.utils import untrusted_to_os_path, get_cache_dir, comma_delimited


class Project(object):

    def __init__(self, name, project_file, tree):
        self.name = name
        self.project_file = project_file
        self.tree = os.path.normpath(tree)
        self.id = hashlib.md5(self.tree.encode('utf-8')).hexdigest()

    def open_config(self):
        if self.project_file is None:
            raise RuntimeError('This project has no project file.')
        return IniFile(self.project_file)

    @classmethod
    def from_file(cls, filename):
        """Reads a project from a project file."""
        inifile = IniFile(filename)
        if inifile.is_new:
            return None

        name = inifile.get('project.name') or os.path.basename(
            filename).rsplit('.')[0].title()
        path = os.path.join(os.path.dirname(filename),
                            untrusted_to_os_path(
                                inifile.get('project.path') or '.'))
        return cls(
            name=name,
            project_file=filename,
            tree=path,
        )

    @classmethod
    def from_path(cls, path, extension_required=False):
        """Locates the project for a path."""
        path = os.path.abspath(path)
        if os.path.isfile(path) and (not extension_required or
                                     path.endswith('.lektorproject')):
            return cls.from_file(path)

        try:
            files = [x for x in os.listdir(path)
                     if x.lower().endswith('.lektorproject')]
        except OSError:
            return None

        if len(files) == 1:
            return cls.from_file(os.path.join(path, files[0]))

        if os.path.isdir(path) and \
           os.path.isfile(os.path.join(path, 'content/contents.lr')):
            return cls(
                name=os.path.basename(path),
                project_file=None,
                tree=path,
            )

    @classmethod
    def discover(cls, base=None):
        """Auto discovers the closest project."""
        if base is None:
            base = os.getcwd()
        here = base
        while 1:
            project = cls.from_path(here, extension_required=True)
            if project is not None:
                return project
            node = os.path.dirname(here)
            if node == here:
                break
            here = node

    @property
    def project_path(self):
        return self.project_file or self.tree

    def get_output_path(self):
        """The path where output files are stored."""
        return os.path.join(get_cache_dir(), 'builds', self.id)

    def get_package_cache_path(self):
        """The path where plugin packages are stored."""
        h = hashlib.md5()
        h.update(self.id.encode('utf-8'))
        h.update(sys.version.encode('utf-8'))
        h.update(sys.prefix.encode('utf-8'))
        return os.path.join(get_cache_dir(), 'packages', h.hexdigest())

    def content_path_from_filename(self, filename):
        """Given a filename returns the content path or None if
        not in project.
        """
        dirname, basename = os.path.split(os.path.abspath(filename))
        if basename == 'contents.lr':
            path = dirname
        elif basename.endswith('.lr'):
            path = os.path.join(dirname, basename[:-3])
        else:
            return None

        content_path = os.path.normpath(self.tree).split(os.path.sep) + ['content']
        file_path = os.path.normpath(path).split(os.path.sep)
        prefix = os.path.commonprefix([content_path, file_path])
        if prefix == content_path:
            return '/' + '/'.join(file_path[len(content_path):])

    def make_env(self, load_plugins=True):
        """Create a new environment for this project."""
        from lektor.environment import Environment
        return Environment(self, load_plugins=load_plugins)

    @cached_property
    def excluded_assets(self):
        """List of glob patterns matching filenames of excluded assets.

        Combines with default EXCLUDED_ASSETS.
        """
        config = self.open_config()
        return list(comma_delimited(config.get('project.excluded_assets', '')))

    @cached_property
    def included_assets(self):
        """List of glob patterns matching filenames of included assets.

        Overrides both excluded_assets and the default excluded patterns.
        """
        config = self.open_config()
        return list(comma_delimited(config.get('project.included_assets', '')))

    def to_json(self):
        return {
            'name': self.name,
            'project_file': self.project_file,
            'project_path': self.project_path,
            'default_output_path': self.get_output_path(),
            'id': self.id,
            'tree': self.tree,
        }
