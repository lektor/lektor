import os
import posixpath

from lektor.sourceobj import SourceObject
from lektor.vfs import PathNotFound


def get_asset(pad, filename, parent):
    vfs = pad.db.vfs
    path = vfs.join_path(parent.source_filename, filename)

    try:
        record = vfs.describe_path(path)
    except PathNotFound:
        return None

    # Check if the asset is ignored.  We chop off the leading assets/
    # in the path here as the db API assumes a path below that folder.
    if pad.db.is_ignored_asset(path.split('/', 1)[-1]):
        print 'NO ASSET', path
        return None

    if record.is_dir:
        return Directory(pad, filename, parent=parent)
    ext = os.path.splitext(filename)[1]
    cls = pad.db.env.special_file_assets.get(ext, File)
    return cls(pad, filename, parent=parent)


class Asset(SourceObject):
    # source specific overrides.  the source_filename to none removes
    # the inherited descriptor.
    source_classification = 'asset'
    source_filename = None

    artifact_extension = ''

    def __init__(self, pad, name, path=None, parent=None):
        SourceObject.__init__(self, pad)
        if parent is not None:
            if path is None:
                path = name
            path = os.path.join(parent.source_filename, path)
        self.source_filename = path

        self.name = name
        self.parent = parent

    @property
    def vfs(self):
        return self.pad.db.vfs

    @property
    def url_name(self):
        name = self.name
        base, ext = posixpath.splitext(name)

        # If this is a known extension from an attachment then convert it
        # to lowercase
        if ext.lower() in self.pad.db.config['ATTACHMENT_TYPES']:
            ext = ext.lower()

        return base + ext + self.artifact_extension

    @property
    def url_path(self):
        if self.parent is None:
            return '/' + self.name
        return self.pad.db.vfs.join_path(self.parent.url_path, self.url_name)

    @property
    def artifact_name(self):
        if self.parent is not None:
            return self.parent.artifact_name.rstrip('/') + '/' + self.url_name
        return self.url_path

    def build_asset(self, f):
        pass

    @property
    def children(self):
        return iter(())

    def get_child(self, name, from_url=False):
        return None

    def resolve_url_path(self, url_path):
        if not url_path:
            return self
        child = self.get_child(url_path[0], from_url=True)
        if child is not None:
            return child.resolve_url_path(url_path[1:])

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.artifact_name,
        )


class Directory(Asset):
    """Represents an asset directory."""

    @property
    def children(self):
        # TODO: optimize. this stats twice with get_child
        try:
            files = self.vfs.list_dir(self.source_filename)
        except PathNotFound:
            return

        for filename in files:
            asset = self.get_child(filename)
            if asset is not None:
                yield asset

    def get_child(self, name, from_url=False):
        rv = get_asset(self.pad, name, parent=self)
        if rv is not None or not from_url:
            return rv

        # This this point it means we did not find a child yet, but we
        # came from an URL.  We can try to chop of product suffixes to
        # find the original source asset.  For instance a file called
        # foo.less.css will be reduced to foo.less.
        prod_suffix = '.' + '.'.join(name.rsplit('.', 2)[1:])
        ext = self.pad.db.env.special_file_suffixes.get(prod_suffix)
        if ext is not None:
            return get_asset(self.pad, name[:-len(prod_suffix)] + ext, parent=self)

    def resolve_url_path(self, url_path):
        # Resolve "/path/" to "/path/index.html", as production servers do.
        if not url_path:
            index = self.get_child('index.html') or self.get_child('index.htm')
            if index is not None:
                return index

        return Asset.resolve_url_path(self, url_path)


class File(Asset):
    """Represents a static asset file."""
