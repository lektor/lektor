import os
import shutil
import posixpath

from collections import OrderedDict

from lektor._compat import text_type, iteritems, string_types
from lektor.metaformat import serialize
from lektor.utils import atomic_open, is_valid_id, secure_filename, \
     increment_filename
from lektor.environment import PRIMARY_ALT


implied_keys = set(['_id', '_path', '_gid', '_alt', '_source_alt',
                    '_attachment_for'])
possibly_implied_keys = set(['_model', '_template', '_attachment_type'])


class BadEdit(Exception):
    pass


class BadDelete(BadEdit):
    pass


def make_editor_session(pad, path, is_attachment=None, alt=PRIMARY_ALT,
                        datamodel=None):
    """Creates an editor session for the given path object."""
    if alt != PRIMARY_ALT and not pad.db.config.is_valid_alternative(alt):
        raise BadEdit('Attempted to edit an invalid alternative (%s)' % alt)

    raw_data = pad.db.load_raw_data(path, cls=OrderedDict, alt=alt,
                                    fallback=False)
    raw_data_fallback = None
    if alt != PRIMARY_ALT:
        raw_data_fallback = pad.db.load_raw_data(path, cls=OrderedDict)
        all_data = OrderedDict()
        all_data.update(raw_data_fallback or ())
        all_data.update(raw_data or ())
    else:
        all_data = raw_data

    id = posixpath.basename(path)
    if not is_valid_id(id):
        raise BadEdit('Invalid ID')

    record = None
    exists = all_data is not None
    if raw_data is None:
        raw_data = OrderedDict()

    if is_attachment is None:
        if not exists:
            is_attachment = False
        else:
            is_attachment = bool(all_data.get('_attachment_for'))
    elif bool(all_data.get('_attachment_for')) != is_attachment:
        raise BadEdit('The attachment flag passed is conflicting with the '
                      'record\'s attachment flag.')

    if exists:
        # XXX: what about changing the datamodel after the fact?
        if datamodel is not None:
            raise BadEdit('When editing an existing record, a datamodel '
                          'must not be provided.')
        datamodel = pad.db.get_datamodel_for_raw_data(all_data, pad)
    else:
        if datamodel is None:
            datamodel = pad.db.get_implied_datamodel(path, is_attachment, pad)
        elif isinstance(datamodel, string_types):
            datamodel = pad.db.datamodels[datamodel]

    if exists:
        record = pad.instance_from_data(dict(all_data), datamodel)

    for key in implied_keys:
        raw_data.pop(key, None)
        if raw_data_fallback:
            raw_data_fallback.pop(key, None)

    return EditorSession(pad, id, text_type(path), raw_data, raw_data_fallback,
                         datamodel, record, exists, is_attachment, alt)


class EditorSession(object):

    def __init__(self, pad, id, path, original_data, fallback_data,
                 datamodel, record, exists=True, is_attachment=False,
                 alt=PRIMARY_ALT):
        self.id = id
        self.pad = pad
        self.path = path
        self.record = record
        self.exists = exists
        self.original_data = original_data
        self.fallback_data = fallback_data
        self.datamodel = datamodel
        self.is_root = path.strip('/') == ''
        self.alt = alt

        slug_format = None
        parent_name = posixpath.dirname(path)
        if parent_name != path:
            parent = pad.get(parent_name)
            if parent is not None:
                slug_format = parent.datamodel.child_config.slug_format
        if slug_format is None:
            slug_format = u'{{ this._id }}'
        self.slug_format = slug_format
        self.implied_attachment_type = None

        if is_attachment:
            self.implied_attachment_type = pad.db.get_attachment_type(path)

        self._data = {}
        self._changed = set()
        self._delete_this = False
        self._recursive_delete = False
        self._master_delete = False
        self.is_attachment = is_attachment
        self.closed = False

    def to_json(self):
        label = None
        label_i18n = None
        url_path = None
        if self.record is not None:
            label = self.record.record_label
            label_i18n = self.record.get_record_label_i18n()
            url_path = self.record.url_path
        else:
            label = self.id
        can_be_deleted = not self.datamodel.protected and not self.is_root
        return {
            'data': dict(self.iteritems()),
            'record_info': {
                'id': self.id,
                'path': self.path,
                'exists': self.exists,
                'label': label,
                'label_i18n': label_i18n,
                'url_path': url_path,
                'alt': self.alt,
                'is_attachment': self.is_attachment,
                'can_be_deleted': can_be_deleted,
                'slug_format': self.slug_format,
                'implied_attachment_type': self.implied_attachment_type,
                'default_template': self.datamodel.get_default_template_name(),
            },
            'datamodel': self.datamodel.to_json(self.pad, self.record, self.alt)
        }

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __getitem__(self, key):
        if key in self._data:
            rv = self._data[key]
            if rv is None:
                raise KeyError(key)
            return rv
        if key in self.original_data:
            return self.original_data[key]
        if self.fallback_data and key in self.fallback_data:
            return self.fallback_data[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key in self.original_data:
            old_value = self.original_data[key]
        elif self.fallback_data and key in self.fallback_data:
            old_value = self.fallback_data[key]
        else:
            old_value = None

        if old_value != value:
            self._changed.add(key)
        else:
            # If the key is in the possibly implied key set and set to
            # that value, we will set it to changed anyways.  This allows
            # overriding of such special keys.
            if key in possibly_implied_keys:
                self._changed.add(value)
            else:
                self._changed.discard(value)
        self._data[key] = value

    def __delitem__(self, key):
        self[key] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def update(self, *args, **kwargs):
        for key, value in iteritems(dict(*args, **kwargs)):
            self[key] = value

    def iteritems(self, fallback=True):
        done = set()

        for key, value in iteritems(self.original_data):
            done.add(key)
            if key in implied_keys:
                continue
            if key in self._changed:
                value = self._data[key]
            if value is not None:
                yield key, value

        if fallback and self.fallback_data:
            for key, value in iteritems(self.fallback_data):
                if key in implied_keys or key in done:
                    continue
                done.add(key)
                if key in self._changed:
                    value = self._data[key]
                if value is not None:
                    yield key, value

        for key in sorted(self._data):
            if key in done:
                continue
            value = self._data.get(key)
            if value is not None:
                yield key, value

    def iterkeys(self, fallback=True):
        for key, _ in self.iteritems(fallback=fallback):
            yield key

    def itervalues(self, fallback=True):
        for _, value in self.iteritems(fallback=fallback):
            yield value

    def items(self, fallback=True):
        return list(self.iteritems(fallback=fallback))

    def keys(self, fallback=True):
        return list(self.iterkeys(fallback=fallback))

    def values(self, fallback=True):
        return list(self.itervalues(fallback=fallback))

    __iter__ = iterkeys

    def __len__(self):
        return len(self.items())

    def get_fs_path(self, alt=PRIMARY_ALT):
        """The path to the record file on the file system."""
        base = self.pad.db.to_fs_path(self.path)
        suffix = '.lr'
        if alt != PRIMARY_ALT:
            suffix = '+%s%s' % (alt, suffix)
        if self.is_attachment:
            return base + suffix
        return os.path.join(base, 'contents' + suffix)

    @property
    def fs_path(self):
        """The file system path of the content file on disk."""
        return self.get_fs_path(self.alt)

    @property
    def attachment_fs_path(self):
        """The file system path of the actual attachment."""
        if self.is_attachment:
            return self.pad.db.to_fs_path(self.path)

    def revert_key(self, key):
        """Reverts a key to the implied value."""
        if key in self._data:
            self._changed.discard(key)
        self._data.pop(key, None)

    def rollback(self):
        """Ignores all changes and rejects them."""
        if self.closed:
            return
        self.closed = True

    def commit(self):
        """Saves changes back to the file system."""
        if not self.closed:
            if self._delete_this:
                self._delete_impl()
            else:
                self._save_impl()
        self.closed = True

    def delete(self, recursive=None, delete_master=False):
        """Deletes the record.  How the delete works depends on what is being
        deleted:

        *   delete attachment: recursive mode is silently ignored.  If
            `delete_master` is set then the attachment is deleted, otherwise
            only the metadata is deleted.
        *   delete page: in recursive mode everything is deleted in which
            case `delete_master` must be set to `True` or an error is
            generated.  In fact, the default is to perform a recursive
            delete in that case.  If `delete_master` is False, then only the
            contents file of the current alt is deleted.

        If a delete cannot be performed, an error is generated.
        """
        if self.closed:
            return
        if recursive is None:
            recursive = not self.is_attachment and delete_master
        self._delete_this = True
        self._recursive_delete = recursive
        self._master_delete = delete_master

    def add_attachment(self, filename, fp):
        """Stores a new attachment.  Returns `None` if the file already"""
        if not self.exists:
            raise BadEdit('Record does not exist.')
        if self.is_attachment:
            raise BadEdit('Cannot attach something to an attachment.')
        directory = self.pad.db.to_fs_path(self.path)

        safe_filename = secure_filename(filename)

        while 1:
            fn = os.path.join(directory, safe_filename)
            if not os.path.isfile(fn):
                break
            safe_filename = increment_filename(fn)

        with atomic_open(fn, 'wb') as f:
            shutil.copyfileobj(fp, f)
        return safe_filename

    def _attachment_delete_impl(self):
        files = [self.fs_path]
        if self._master_delete:
            files.append(self.attachment_fs_path)
            for alt in self.pad.db.config.list_alternatives():
                files.append(self.get_fs_path(alt))

        for fn in files:
            try:
                os.unlink(fn)
            except OSError:
                pass

    def _page_delete_impl(self):
        directory = os.path.dirname(self.fs_path)

        if self._recursive_delete:
            try:
                shutil.rmtree(directory)
            except (OSError, IOError):
                pass
            return
        elif self._master_delete:
            raise BadDelete('Master deletes of pages require that recursive '
                            'deleting is enabled.')

        for fn in self.fs_path, directory:
            try:
                os.unlink(fn)
            except OSError:
                pass

    def _delete_impl(self):
        if self.alt != PRIMARY_ALT:
            if self._master_delete:
                raise BadDelete('Master deletes need to be done from the primary '
                                'alt.  Tried to delete from "%s"' % self.alt)
            if self._recursive_delete:
                raise BadDelete('Cannot perform recursive delete from a non '
                                'primary alt.  Tried to delete from "%s"' %
                                self.alt)

        if self.is_attachment:
            self._attachment_delete_impl()
        else:
            self._page_delete_impl()

    def _save_impl(self):
        # When creating a new alt from a primary self.exists is True but
        # the file does not exist yet.  In this case we want to explicitly
        # create it anyways instead of bailing.
        if not self._changed and self.exists and os.path.exists(self.fs_path):
            return

        try:
            os.makedirs(os.path.dirname(self.fs_path))
        except OSError:
            pass

        with atomic_open(self.fs_path, 'wb') as f:
            for chunk in serialize(self.iteritems(fallback=False),
                                   encoding='utf-8'):
                f.write(chunk)

    def __repr__(self):
        return '<%s %r%s%s>' % (
            self.__class__.__name__,
            self.path,
            self.alt != PRIMARY_ALT and ' alt=%r' % self.alt or '',
            not self.exists and ' new' or '',
        )
