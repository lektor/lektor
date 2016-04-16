import os
import sys
import stat
import errno
import codecs
import shutil
import posixpath
from contextlib import contextmanager

from werkzeug.posixemulation import rename

from lektor._compat import text_type, PY2
from lektor.utils import AtomicFile
from lektor.exception import LektorException

if PY2:
    from scandir import scandir
else:
    from os import scandir


class VfsError(LektorException):

    def __init__(self, message, path=None):
        LektorException.__init__(self, message)
        self.path = path

    def to_json(self):
        rv = LektorException.to_json(self)
        rv['path'] = self.path
        return rv

    def __unicode__(self):
        return u'%s (path=%s)' % (
            LektorException.__unicode__(self),
            self.path,
        )


class PathNotFound(VfsError):
    pass


class PermissionDenied(VfsError):
    pass


class IncompatiblePathType(VfsError):
    pass


_error_mapping = {
    errno.ENOENT: (PathNotFound, u'Path does not exist.'),
    errno.EACCES: (PermissionDenied, u'Path could not be accessed.'),
    errno.EPERM: (PermissionDenied, u'Path could not be accessed.'),
    errno.EISDIR: (IncompatiblePathType, u'The path was a directory not a file.'),
    errno.ENOTDIR: (IncompatiblePathType, u'The path was not a directory.'),
}


class VfsPathEntry(object):

    def __init__(self, base, name, is_dir=False, is_file=False, size=0,
                 mtime=None):
        self.base = base
        self.name = name
        self.is_dir = is_dir
        self.is_file = is_file
        self.size = size
        self.mtime = mtime

    @property
    def path(self):
        return posixpath.join(self.base, self.name)

    @property
    def type(self):
        if self.is_dir:
            return 'directory'
        elif self.is_file:
            return 'file'
        return 'unknown'

    def __repr__(self):
        return '<VfsPathEntry name=%r type=%r>' % (
            self.name,
            self.type,
        )


class VfsSettings(object):

    def __init__(self, ignore_path_callback=None):
        self.ignore_path_callback = ignore_path_callback


class Vfs(object):

    def __init__(self, **settings):
        self.settings = VfsSettings(**settings)

    def join_path(self, a, *other):
        """Joins two virtual paths together."""
        return posixpath.join(text_type(a), *[
            text_type(x).lstrip('/') for x in other])

    def describe_path(self, path):
        """Describes a path."""
        return self._describe_path(*posixpath.split(u'/' + path.lstrip(u'/')))

    def is_file(self, path):
        """Checks if a path is a file."""
        try:
            return self.describe_path(path).is_file
        except VfsError:
            return False

    def is_dir(self, path):
        """Checks if a path is a directory."""
        try:
            return self.describe_path(path).is_dir
        except VfsError:
            return False

    def open(self, path, mode='rb'):
        """Opens a file in a specific mode.  This can either be rb/wb
        for reading or writing binary.  This operation needs to return a
        file object that overwrites atomically on write.
        """
        if mode not in ('rb', 'wb'):
            raise TypeError('Invalid open mode %r' % (mode,))
        return self._open_impl(path.lstrip('/'), mode)

    def iter_path(self, path):
        """Iterates over all items in a path and yields path entries."""
        return self._iter_path(u'/' + path.lstrip(u'/'))

    def list_dir(self, path):
        """Like :meth:`iter_path` but only returns a list of filenames."""
        return [x.name for x in self.iter_path(path)]

    def rename(self, src, dst):
        """Perform an atomic rename from src to dst."""
        raise NotImplementedError()

    def delete(self, path, recursive=False):
        """Deletes a file."""

    def _is_ignored_file(self, name):
        if self.settings.ignore_path_callback is not None:
            if self.settings.ignore_path_callback(name):
                return True
        return False


class FileSystem(Vfs):

    def __init__(self, base, fs_enc=None, **settings):
        Vfs.__init__(self, **settings)
        if fs_enc is None:
            fs_enc = sys.getfilesystemencoding()
            try:
                if codecs.lookup(fs_enc).name == 'ascii':
                    fs_enc = 'utf-8'
            except LookupError:
                pass
        self.fs_enc = fs_enc

        # If the base is ascii only or already unicode, we upgrade it into
        # an unicode path.  Otherwise we stick with the type we have.
        try:
            base = text_type(base)
        except UnicodeError:
            pass
        self.base = base
        self._bytes_base = not isinstance(self.base, text_type)

    def _make_native_path(self, path):
        path = path.lstrip(u'/')
        if u'\\' in path or u'\x00' in path:
            raise VfsError('Invalid character in path')
        if self._bytes_base:
            path = path.encode(self.fs_enc)
        return os.path.join(self.base, path)

    @contextmanager
    def _translate_io_error(self, path):
        try:
            yield
        except (OSError, IOError) as e:
            rv = _error_mapping.get(e.errno)
            if rv is not None:
                exc, msg = rv
                raise exc(msg, path)
            raise

    def _describe_path_impl(self, base, name, st=None, dirent=None):
        is_file = is_dir = False
        if dirent is not None:
            if st is None:
                st = dirent.stat()
            if dirent.is_file():
                is_file = True
            elif dirent.is_dir():
                is_dir = True
            else:
                return None
        else:
            is_dir = stat.S_ISDIR(st.st_mode)
            is_file = stat.S_ISREG(st.st_mode)
        try:
            mtime = st.st_mtime_ns / 1e9
        except AttributeError:
            mtime = float(st.st_mtime)
        return VfsPathEntry(
            base=base,
            name=name,
            is_file=is_file,
            is_dir=is_dir,
            size=st.st_size,
            mtime=mtime
        )

    def _describe_path(self, base, name):
        path = self.join_path(base, name)
        with self._translate_io_error(path):
            native_path = self._make_native_path(path)
            return self._describe_path_impl(base, name, os.stat(native_path))

    def _open_impl(self, path, mode):
        with self._translate_io_error(path):
            return AtomicFile(self._make_native_path(path), mode)

    def iter_path(self, path):
        with self._translate_io_error(path):
            for dirent in scandir(self._make_native_path(path)):
                name = dirent.name
                if isinstance(name, bytes):
                    try:
                        name = name.decode(self.fs_enc)
                    except UnicodeError:
                        # XXX: the virtual file system ignores things that
                        # cannot be decoded to unicode
                        continue
                if self._is_ignored_file(name):
                    continue
                entry = self._describe_path_impl(path, name, dirent=dirent)
                if entry is not None:
                    yield entry

    def rename(self, src, dst):
        with self._translate_io_error(src):
            return rename(self._make_native_path(src),
                          self._make_native_path(dst))

    def delete(self, path, recursive=False):
        with self._translate_io_error(path):
            native_path = self._make_native_path(path)
            if recursive and os.path.isdir(native_path):
                shutil.rmtree(native_path)
            try:
                os.remove(native_path)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    return False
                raise
            return True
