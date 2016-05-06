import os
import errno
import hashlib
import operator
import posixpath

from itertools import islice, chain

from jinja2 import Undefined, is_undefined
from jinja2.utils import LRUCache
from jinja2.exceptions import UndefinedError

from werkzeug.urls import url_join
from werkzeug.utils import cached_property

from lektor._compat import string_types, text_type, integer_types, \
     iteritems, range_type
from lektor import metaformat
from lektor.utils import sort_normalize_string, cleanup_path, \
     untrusted_to_os_path, fs_enc
from lektor.sourceobj import SourceObject, VirtualSourceObject
from lektor.context import get_ctx, Context
from lektor.datamodel import load_datamodels, load_flowblocks
from lektor.imagetools import make_thumbnail, read_exif, get_image_info
from lektor.assets import Directory
from lektor.editor import make_editor_session
from lektor.environment import PRIMARY_ALT
from lektor.databags import Databags
from lektor.filecontents import FileContents
from lektor.utils import make_relative_url, split_virtual_path


def get_alts(source=None, fallback=False):
    """Given a source this returns the list of all alts that the source
    exists as.  It does not include fallbacks unless `fallback` is passed.
    If no source is provided all configured alts are returned.  If alts are
    not configured at all, the return value is an empty list.
    """
    if source is None:
        ctx = get_ctx()
        if ctx is None:
            raise RuntimeError('This function requires the context to be supplied.')
        pad = ctx.pad
    else:
        pad = source.pad
    alts = list(pad.config.iter_alternatives())
    if alts == [PRIMARY_ALT]:
        return []

    rv = alts

    # If a source is provided and it's not virtual, we look up all alts
    # of the path on the pad to figure out which records exist.
    if source is not None and '@' not in source.path:
        rv = []
        for alt in alts:
            if pad.alt_exists(source.path, alt=alt,
                              fallback=fallback):
                rv.append(alt)

    return rv


def _process_slug(slug, last_segment=False):
    if last_segment:
        return slug
    segments = slug.split('/')
    if '.' not in segments[-1]:
        return slug
    if len(segments) == 1:
        return '_' + segments[0]
    return segments[0] + '/_' + segments[1]


def _require_ctx(record):
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError('This operation requires a context but none was '
                           'on the stack.')
    if ctx.pad is not record.pad:
        raise RuntimeError('The context on the stack does not match the '
                           'pad of the record.')
    return ctx


def _is_content_file(filename, alt=PRIMARY_ALT):
    if filename == 'contents.lr':
        return True
    if alt != PRIMARY_ALT and filename == 'contents+%s.lr' % alt:
        return True
    return False


class _CmpHelper(object):

    def __init__(self, value, reverse):
        self.value = value
        self.reverse = reverse

    @staticmethod
    def coerce(a, b):
        if isinstance(a, string_types) and isinstance(b, string_types):
            return sort_normalize_string(a), sort_normalize_string(b)
        if type(a) is type(b):
            return a, b
        if isinstance(a, Undefined) or isinstance(b, Undefined):
            if isinstance(a, Undefined):
                a = None
            if isinstance(b, Undefined):
                b = None
            return a, b
        if isinstance(a, integer_types) or isinstance(a, float):
            try:
                return a, type(a)(b)
            except (ValueError, TypeError, OverflowError):
                pass
        if isinstance(b, integer_types) or isinstance(b, float):
            try:
                return type(b)(a), b
            except (ValueError, TypeError, OverflowError):
                pass
        return a, b

    def __eq__(self, other):
        a, b = self.coerce(self.value, other.value)
        return a == b

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        a, b = self.coerce(self.value, other.value)
        try:
            if self.reverse:
                return b < a
            return a < b
        except TypeError:
            # Put None at the beginning if reversed, else at the end.
            if self.reverse:
                return a is not None
            return a is None

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return not self.__lt__(other)


def _auto_wrap_expr(value):
    if isinstance(value, Expression):
        return value
    return _Literal(value)


def save_eval(filter, record):
    try:
        return filter.__eval__(record)
    except UndefinedError as e:
        return Undefined(e.message)


class Expression(object):

    def __eval__(self, record):
        return record

    def __eq__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.eq)

    def __ne__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.ne)

    def __and__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.and_)

    def __or__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.or_)

    def __gt__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.gt)

    def __ge__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.ge)

    def __lt__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.lt)

    def __le__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.le)

    def contains(self, item):
        return _ContainmentExpr(self, _auto_wrap_expr(item))

    def startswith(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
            lambda a, b: text_type(a).lower().startswith(text_type(b).lower()))

    def endswith(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
            lambda a, b: text_type(a).lower().endswith(text_type(b).lower()))

    def startswith_cs(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
                        lambda a, b: text_type(a).startswith(text_type(b)))

    def endswith_cs(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
                        lambda a, b: text_type(a).endswith(text_type(b)))

    def false(self):
        return _IsBoolExpr(self, False)

    def true(self):
        return _IsBoolExpr(self, True)


# Query helpers for the template engine
setattr(Expression, 'and', lambda x, o: x & o)
setattr(Expression, 'or', lambda x, o: x | o)


class _CallbackExpr(Expression):

    def __init__(self, func):
        self.func = func

    def __eval__(self, record):
        return self.func(record)


class _IsBoolExpr(Expression):

    def __init__(self, expr, true):
        self.__expr = expr
        self.__true = true

    def __eval__(self, record):
        val = self.__expr.__eval__(record)
        return (not is_undefined(val) and
                val not in (None, 0, False, '')) == self.__true


class _Literal(Expression):

    def __init__(self, value):
        self.__value = value

    def __eval__(self, record):
        return self.__value


class _BinExpr(Expression):

    def __init__(self, left, right, op):
        self.__left = left
        self.__right = right
        self.__op = op

    def __eval__(self, record):
        return self.__op(
            self.__left.__eval__(record),
            self.__right.__eval__(record)
        )


class _ContainmentExpr(Expression):

    def __init__(self, seq, item):
        self.__seq = seq
        self.__item = item

    def __eval__(self, record):
        seq = self.__seq.__eval__(record)
        item = self.__item.__eval__(record)
        if isinstance(item, Record):
            item = item['_id']
        return item in seq


class _RecordQueryField(Expression):

    def __init__(self, field):
        self.__field = field

    def __eval__(self, record):
        try:
            return record[self.__field]
        except KeyError:
            return Undefined(obj=record, name=self.__field)


class _RecordQueryProxy(object):

    def __getattr__(self, name):
        if name[:2] != '__':
            return _RecordQueryField(name)
        raise AttributeError(name)

    def __getitem__(self, name):
        try:
            return self.__getattr__(name)
        except AttributeError:
            raise KeyError(name)


F = _RecordQueryProxy()


class Record(SourceObject):
    source_classification = 'record'
    supports_pagination = False

    def __init__(self, pad, data, page_num=None):
        SourceObject.__init__(self, pad)
        self._data = data
        self._bound_data = {}
        if page_num is not None and not self.supports_pagination:
            raise RuntimeError('%s does not support pagination' %
                               self.__class__.__name__)
        self.page_num = page_num

    @property
    def record(self):
        return self

    @property
    def datamodel(self):
        """Returns the data model for this record."""
        try:
            return self.pad.db.datamodels[self._data['_model']]
        except LookupError:
            # If we cannot find the model we fall back to the default one.
            return self.pad.db.default_model

    @property
    def alt(self):
        """Returns the alt of this source object."""
        return self['_alt']

    @property
    def is_hidden(self):
        """Indicates if a record is hidden.  A record is considered hidden
        if the record itself is hidden or the parent is.
        """
        if not is_undefined(self._data['_hidden']):
            return self._data['_hidden']
        return self._is_considered_hidden()

    def _is_considered_hidden(self):
        parent = self.parent
        if parent is None:
            return False

        hidden_children = parent.datamodel.child_config.hidden
        if hidden_children is not None:
            return hidden_children
        return parent.is_hidden

    @property
    def is_discoverable(self):
        """Indicates if the page is discoverable without knowing the URL."""
        return self._data['_discoverable'] and not self.is_hidden

    @cached_property
    def pagination(self):
        """Returns the pagination controller for the record."""
        if not self.supports_pagination:
            raise AttributeError()
        return self.datamodel.pagination_config.get_pagination_controller(self)

    @cached_property
    def contents(self):
        return FileContents(self.source_filename)

    def get_fallback_record_label(self, lang):
        if not self['_id']:
            return '(Index)'
        return self['_id'].replace('-', ' ').replace('_', ' ').title()

    def get_record_label_i18n(self):
        rv = {}
        for lang, _ in iteritems((self.datamodel.label_i18n or {})):
            label = self.datamodel.format_record_label(self, lang)
            if not label:
                label = self.get_fallback_record_label(lang)
            rv[lang] = label
        # Fill in english if missing
        if not rv:
            rv['en'] = self.get_fallback_record_label('en')
        return rv

    @property
    def record_label(self):
        return (self.get_record_label_i18n() or {}).get('en')

    @property
    def url_path(self):
        """The target path where the record should end up."""
        prefix, suffix = self.pad.db.config.get_alternative_url_span(
            self.alt)
        bits = []
        node = self
        while node is not None:
            bits.append(_process_slug(node['_slug'], node is self))
            node = node.parent
        bits.reverse()

        clean_path = '/'.join(bits).strip('/')
        if prefix:
            clean_path = prefix + clean_path
        if suffix:
            # XXX: 404.html with suffix -de becomes 404.html-de but should
            # actually become 404-de.html
            clean_path += suffix
        return '/' + clean_path.strip('/')

    @property
    def path(self):
        return self['_path']

    def get_sort_key(self, fields):
        """Returns a sort key for the given field specifications specific
        for the data in the record.
        """
        rv = [None] * len(fields)
        for idx, field in enumerate(fields):
            if field[:1] == '-':
                field = field[1:]
                reverse = True
            else:
                field = field.lstrip('+')
                reverse = False
            rv[idx] = _CmpHelper(self._data.get(field), reverse)
        return rv

    def __contains__(self, name):
        return name in self._data and not is_undefined(self._data[name])

    def __getitem__(self, name):
        rv = self._bound_data.get(name, Ellipsis)
        if rv is not Ellipsis:
            return rv
        rv = self._data[name]
        if hasattr(rv, '__get__'):
            rv = rv.__get__(self)
        self._bound_data[name] = rv
        return rv

    def __eq__(self, other):
        if self is other:
            return True
        if self.__class__ != other.__class__:
            return False
        return self['_path'] == other['_path']

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        return '<%s model=%r path=%r%s%s>' % (
            self.__class__.__name__,
            self['_model'],
            self['_path'],
            self.alt != PRIMARY_ALT and ' alt=%r' % self.alt or '',
            self.page_num is not None and ' page_num=%r' % self.page_num or '',
        )


class Siblings(VirtualSourceObject):
    def __init__(self, record, prev_page, next_page):
        """Virtual source representing previous and next sibling of 'record'."""
        VirtualSourceObject.__init__(self, record)
        self._path = record.path + '@siblings'
        self._prev_page = prev_page
        self._next_page = next_page

    @property
    def path(self):
        # Used as a key in Context.referenced_virtual_dependencies.
        return self._path

    @property
    def prev_page(self):
        return self._prev_page

    @property
    def next_page(self):
        return self._next_page

    def iter_source_filenames(self):
        for page in self._prev_page, self._next_page:
            if page:
                yield page.source_filename

    def _file_infos(self, path_cache):
        for page in self._prev_page, self._next_page:
            if page:
                yield path_cache.get_file_info(page.source_filename)

    def get_mtime(self, path_cache):
        mtimes = [i.mtime for i in self._file_infos(path_cache)]
        return max(mtimes) if mtimes else None

    def get_checksum(self, path_cache):
        sums = '|'.join(i.filename_and_checksum
                        for i in self._file_infos(path_cache))

        return sums or None


def siblings_resolver(node, url_path):
    return node.get_siblings()


class Page(Record):
    """This represents a loaded record."""
    is_attachment = False
    supports_pagination = True

    @cached_property
    def path(self):
        rv = self['_path']
        if self.page_num is not None:
            rv = '%s@%s' % (rv, self.page_num)
        return rv

    @cached_property
    def record(self):
        if self.page_num is None:
            return self
        return self.pad.get(self['_path'],
                            persist=self.pad.cache.is_persistent(self),
                            alt=self.alt)

    @property
    def source_filename(self):
        if self.alt != PRIMARY_ALT:
            return os.path.join(self.pad.db.to_fs_path(self['_path']),
                                'contents+%s.lr' % self.alt)
        return os.path.join(self.pad.db.to_fs_path(self['_path']),
                            'contents.lr')

    def iter_source_filenames(self):
        yield self.source_filename
        if self.alt != PRIMARY_ALT:
            yield os.path.join(self.pad.db.to_fs_path(self['_path']),
                               'contents.lr')

    @property
    def url_path(self):
        rv = Record.url_path.__get__(self).rstrip('/')
        last_part = rv.rsplit('/')[-1]
        if '.' not in last_part:
            rv += '/'
        if self.page_num in (1, None):
            return rv
        if '.' in last_part:
            raise RuntimeError('When file extensions is provided pagination '
                               'cannot be used.')
        return '%s%s/%d/' % (
            rv,
            self.datamodel.pagination_config.url_suffix.strip('/'),
            self.page_num,
        )

    def resolve_url_path(self, url_path):
        pg = self.datamodel.pagination_config

        # If we hit the end of the url path, then we found our target.
        # However if pagination is enabled we want to resolve the first
        # page instead of the unpaginated version.
        if not url_path:
            if pg.enabled and self.page_num is None:
                return pg.get_record_for_page(self, 1)
            return self

        # Try to resolve the correctly paginated version here.
        elif pg.enabled:
            rv = pg.match_pagination(self, url_path)
            if rv is not None:
                return rv

        # When we resolve URLs we also want to be able to explicitly
        # target undiscoverable pages.  Those who know the URL are
        # rewarded.
        q = self.children.include_undiscoverable(True)

        for idx in range_type(len(url_path)):
            piece = '/'.join(url_path[:idx + 1])
            child = q.filter(F._slug == piece).first()
            if child is None:
                attachment = self.attachments.filter(F._slug == piece).first()
                if attachment is None:
                    obj = self.pad.db.env.resolve_custom_url_path(
                        self, url_path)
                    if obj is None:
                        continue
                    node = obj
                else:
                    node = attachment
            else:
                node = child

            rv = node.resolve_url_path(url_path[idx + 1:])
            if rv is not None:
                return rv

    @cached_property
    def parent(self):
        """The parent of the record."""
        this_path = self._data['_path']
        parent_path = posixpath.dirname(this_path)
        if parent_path != this_path:
            return self.pad.get(parent_path,
                                persist=self.pad.cache.is_persistent(self),
                                alt=self.alt)

    @property
    def children(self):
        """A query over all children that are not hidden or undiscoverable.
        want undiscoverable then use ``children.include_undiscoverable(True)``.
        """
        repl_query = self.datamodel.get_child_replacements(self)
        if repl_query is not None:
            return repl_query.include_undiscoverable(False)
        return Query(path=self['_path'], pad=self.pad, alt=self.alt)

    @property
    def attachments(self):
        """Returns a query for the attachments of this record."""
        return AttachmentsQuery(path=self['_path'], pad=self.pad,
                                alt=self.alt)

    def has_prev(self):
        return self.get_siblings().prev_page is not None

    def has_next(self):
        return self.get_siblings().next_page is not None

    def get_siblings(self):
        """The next and previous children of this page's parent.

        Uses parent's pagination query, if any, else parent's "children" config.
        """
        siblings = Siblings(self, *self._siblings)
        ctx = get_ctx()
        if ctx:
            ctx.pad.db.track_record_dependency(siblings)
        return siblings

    @cached_property
    def _siblings(self):
        parent = self.parent
        pagination_enabled = parent.datamodel.pagination_config.enabled

        # Don't track dependencies for this part.
        with Context(pad=self.pad):
            if pagination_enabled:
                pagination = parent.pagination
                siblings = list(pagination.config.get_pagination_query(parent))
            else:
                siblings = list(parent.children)

            prev_item, next_item = None, None
            try:
                me = siblings.index(self)
            except ValueError:
                # Self not in parents.children or not in parents.pagination.
                pass
            else:
                if me > 0:
                    prev_item = siblings[me - 1]

                if me + 1 < len(siblings):
                    next_item = siblings[me + 1]

        return prev_item, next_item


class Attachment(Record):
    """This represents a loaded attachment."""
    is_attachment = True

    @property
    def source_filename(self):
        if self.alt != PRIMARY_ALT:
            suffix = '+%s.lr' % self.alt
        else:
            suffix = '.lr'
        return self.pad.db.to_fs_path(self['_path']) + suffix

    def _is_considered_hidden(self):
        # Attachments are only considered hidden if they have been
        # configured as such.  This means that even if a record itself is
        # hidden, the attachments by default will not.
        parent = self.parent
        if parent is None:
            return False
        return parent.datamodel.attachment_config.hidden

    @property
    def record(self):
        return self

    @property
    def attachment_filename(self):
        return self.pad.db.to_fs_path(self['_path'])

    @property
    def parent(self):
        """The associated record for this attachment."""
        return self.pad.get(self._data['_attachment_for'],
                            persist=self.pad.cache.is_persistent(self))

    @cached_property
    def contents(self):
        return FileContents(self.attachment_filename)

    def get_fallback_record_label(self, lang):
        return self['_id']

    def iter_source_filenames(self):
        yield self.source_filename
        yield self.attachment_filename


class Image(Attachment):
    """Specific class for image attachments."""

    def _get_image_info(self):
        rv = getattr(self, '_image_info', None)
        if rv is None:
            with open(self.attachment_filename, 'rb') as f:
                self._image_info = rv = get_image_info(f)
        return rv

    @property
    def exif(self):
        """Provides access to the exif data."""
        rv = getattr(self, '_exif_cache', None)
        if rv is None:
            with open(self.attachment_filename, 'rb') as f:
                rv = self._exif_cache = read_exif(f)
        return rv

    @property
    def width(self):
        """The width of the image if possible to determine."""
        rv = self._get_image_info()[1]
        if rv is not None:
            return rv
        return Undefined('Width of image could not be determined.')

    @property
    def height(self):
        """The height of the image if possible to determine."""
        rv = self._get_image_info()[2]
        if rv is not None:
            return rv
        return Undefined('Height of image could not be determined.')

    @property
    def format(self):
        """Returns the format of the image."""
        rv = self._get_image_info()[0]
        if rv is not None:
            return rv
        return Undefined('The format of the image could not be determined.')

    def thumbnail(self, width, height=None, crop=False):
        """Utility to create thumbnails."""
        width = int(width)
        if height is not None:
            height = int(height)
        return make_thumbnail(_require_ctx(self),
            self.attachment_filename, self.url_path,
            width=width, height=height, crop=crop)


attachment_classes = {
    'image': Image,
}


class Query(object):
    """Object that helps finding records.  The default configuration
    only finds pages.
    """

    def __init__(self, path, pad, alt=PRIMARY_ALT):
        self.path = path
        self.pad = pad
        self.alt = alt
        self._include_pages = True
        self._include_attachments = False
        self._order_by = None
        self._filters = None
        self._pristine = True
        self._limit = None
        self._offset = None
        self._include_hidden = None
        self._include_undiscoverable = False
        self._page_num = None
        self._filter_func = None

    def __get_lektor_param_hash__(self, h):
        h.update(str(self.alt))
        h.update(str(self._include_pages))
        h.update(str(self._include_attachments))
        h.update('(%s)' % u'|'.join(self._order_by or ()).encode('utf-8'))
        h.update(str(self._limit))
        h.update(str(self._offset))
        h.update(str(self._include_hidden))
        h.update(str(self._include_undiscoverable))
        h.update(str(self._page_num))

    @property
    def self(self):
        """Returns the object this query starts out from."""
        return self.pad.get(self.path, alt=self.alt)

    def _clone(self, mark_dirty=False):
        """Makes a flat copy but keeps the other data on it shared."""
        rv = object.__new__(self.__class__)
        rv.__dict__.update(self.__dict__)
        if mark_dirty:
            rv._pristine = False
        return rv

    def _get(self, id, persist=True, page_num=Ellipsis):
        """Low level record access."""
        if page_num is Ellipsis:
            page_num = self._page_num
        return self.pad.get('%s/%s' % (self.path, id), persist=persist,
                            alt=self.alt, page_num=page_num)

    def _matches(self, record):
        include_hidden = self._include_hidden
        if include_hidden is not None:
            if not self._include_hidden and record.is_hidden:
                return False
        if not self._include_undiscoverable and record.is_undiscoverable:
            return False
        for filter in self._filters or ():
            if not save_eval(filter, record):
                return False
        return True

    def _iterate(self):
        """Low level record iteration."""
        # If we iterate over children we also need to track those
        # dependencies.  There are two ways in which we track them.  The
        # first is through the start record of the query.  If that does
        # not work for whatever reason (because it does not exist for
        # instance).
        self_record = self.pad.get(self.path, alt=self.alt)
        if self_record is not None:
            self.pad.db.track_record_dependency(self_record)

        # We also always want to record the path itself as dependency.
        ctx = get_ctx()
        if ctx is not None:
            ctx.record_dependency(self.pad.db.to_fs_path(self.path))

        for name, _, is_attachment in self.pad.db.iter_items(
                self.path, alt=self.alt):
            if not ((is_attachment == self._include_attachments) or
                    (not is_attachment == self._include_pages)):
                continue

            record = self._get(name, persist=False)
            if self._matches(record):
                yield record

    def filter(self, expr):
        """Filters records by an expression."""
        rv = self._clone(mark_dirty=True)
        rv._filters = list(self._filters or ())
        if callable(expr):
            expr = _CallbackExpr(expr)
        rv._filters.append(expr)
        return rv

    def get_order_by(self):
        """Returns the order that should be used."""
        if self._order_by is not None:
            return self._order_by
        base_record = self.pad.get(self.path)
        if base_record is not None:
            if self._include_attachments and not self._include_pages:
                return base_record.datamodel.attachment_config.order_by
            elif self._include_pages and not self._include_attachments:
                return base_record.datamodel.child_config.order_by
            # Otherwise the query includes either both or neither
            # attachments and/nor children.  I have no idea which
            # value of order_by to use.  We could punt and return
            # child_config.order_by, but for now, just return None.

    def include_hidden(self, value):
        """Controls if hidden records should be included which will not
        happen by default for queries to children.
        """
        rv = self._clone(mark_dirty=True)
        rv._include_hidden = value
        return rv

    def include_undiscoverable(self, value):
        """Controls if undiscoverable records should be included as well."""
        rv = self._clone(mark_dirty=True)
        rv._include_undiscoverable = value

        # If we flip from not including undiscoverables to discoverables
        # but we did not yet decide on the value of _include_hidden it
        # becomes False to not include it.
        if rv._include_hidden is None and value:
            rv._include_hidden = False

        return rv

    def request_page(self, page_num):
        """Requests a specific page number instead of the first."""
        rv = self._clone(mark_dirty=True)
        rv._page_num = page_num
        return rv

    def first(self):
        """Loads all matching records as list."""
        return next(iter(self), None)

    def all(self):
        """Loads all matching records as list."""
        return list(self)

    def order_by(self, *fields):
        """Sets the ordering of the query."""
        rv = self._clone()
        rv._order_by = fields or None
        return rv

    def offset(self, offset):
        """Sets the ordering of the query."""
        rv = self._clone(mark_dirty=True)
        rv._offset = offset
        return rv

    def limit(self, limit):
        """Sets the ordering of the query."""
        rv = self._clone(mark_dirty=True)
        rv._limit = limit
        return rv

    def count(self):
        """Counts all matched objects."""
        rv = 0
        for item in self:
            rv += 1
        return rv

    def distinct(self, fieldname):
        """Set of unique values for the given field."""
        rv = set()

        for item in self:
            if fieldname in item._data:
                value = item._data[fieldname]
                if isinstance(value, (list, tuple)):
                    rv |= set(value)
                elif not isinstance(value, Undefined):
                    rv.add(value)

        return rv

    def get(self, id, page_num=Ellipsis):
        """Gets something by the local path."""
        # If we're not pristine, we need to query here
        if not self._pristine:
            q = self.filter(F._id == id)
            if page_num is not Ellipsis:
                q = q.request_page(page_num)
            return q.first()
        # otherwise we can load it directly.
        return self._get(id, page_num=page_num)

    def __bool__(self):
        return self.first() is not None
    __nonzero__ = __bool__

    def __iter__(self):
        """Iterates over all records matched."""
        iterable = self._iterate()

        order_by = self.get_order_by()
        if order_by:
            iterable = sorted(
                iterable, key=lambda x: x.get_sort_key(order_by))

        if self._offset is not None or self._limit is not None:
            iterable = islice(iterable, self._offset or 0,
                              (self._offset or 0) + self._limit)

        for item in iterable:
            yield item

    def __repr__(self):
        return '<%s %r%s>' % (
            self.__class__.__name__,
            self.path,
            self.alt and ' alt=%r' % self.alt or '',
        )


class EmptyQuery(Query):

    def _get(self, id, persist=True, page_num=Ellipsis):
        pass

    def _iterate(self):
        """Low level record iteration."""
        return iter(())


class AttachmentsQuery(Query):
    """Specialized query class that only finds attachments."""

    def __init__(self, path, pad, alt=PRIMARY_ALT):
        Query.__init__(self, path, pad, alt=PRIMARY_ALT)
        self._include_pages = False
        self._include_attachments = True

    @property
    def images(self):
        """Filters to images."""
        return self.filter(F._attachment_type == 'image')

    @property
    def videos(self):
        """Filters to videos."""
        return self.filter(F._attachment_type == 'video')

    @property
    def audio(self):
        """Filters to audio."""
        return self.filter(F._attachment_type == 'audio')

    @property
    def documents(self):
        """Filters to documents."""
        return self.filter(F._attachment_type == 'document')

    @property
    def text(self):
        """Filters to plain text data."""
        return self.filter(F._attachment_type == 'text')


def _iter_filename_choices(fn_base, alts, config, fallback=True):
    """Returns an iterator over all possible filename choices to .lr files
    below a base filename that matches any of the given alts.
    """
    # the order here is important as attachments can exist without a .lr
    # file and as such need to come second or the loading of raw data will
    # implicitly say the record exists.
    for alt in alts:
        if alt != PRIMARY_ALT and config.is_valid_alternative(alt):
            yield os.path.join(fn_base, 'contents+%s.lr' % alt), alt, False

    if fallback or PRIMARY_ALT in alts:
        yield os.path.join(fn_base, 'contents.lr'), PRIMARY_ALT, False

    for alt in alts:
        if alt != PRIMARY_ALT and config.is_valid_alternative(alt):
            yield fn_base + '+%s.lr' % alt, alt, True

    if fallback or PRIMARY_ALT in alts:
        yield fn_base + '.lr', PRIMARY_ALT, True


def _iter_content_files(dir_path, alts):
    """Returns an iterator over all existing content files below the given
    directory.  This yields specific files for alts before it falls back
    to the primary alt.
    """
    for alt in alts:
        if alt == PRIMARY_ALT:
            continue
        if os.path.isfile(os.path.join(dir_path, 'contents+%s.lr' % alt)):
            yield alt
    if os.path.isfile(os.path.join(dir_path, 'contents.lr')):
        yield PRIMARY_ALT


def _iter_datamodel_choices(datamodel_name, path, is_attachment=False):
    yield datamodel_name
    if not is_attachment:
        yield posixpath.basename(path).split('.')[0].replace('-', '_').lower()
        yield 'page'
    yield 'none'


class Database(object):

    def __init__(self, env, config=None):
        self.env = env
        if config is None:
            config = env.load_config()
        self.config = config
        self.datamodels = load_datamodels(env)
        self.flowblocks = load_flowblocks(env)

    def to_fs_path(self, path):
        """Convenience function to convert a path into an file system path."""
        return os.path.join(self.env.root_path, 'content',
                            untrusted_to_os_path(path))

    def load_raw_data(self, path, alt=PRIMARY_ALT, cls=None,
                      fallback=True):
        """Internal helper that loads the raw record data.  This performs
        very little data processing on the data.
        """
        path = cleanup_path(path)
        if cls is None:
            cls = dict

        fn_base = self.to_fs_path(path)

        rv = cls()
        rv_type = None

        choiceiter = _iter_filename_choices(fn_base, [alt], self.config,
                                            fallback=fallback)
        for fs_path, source_alt, is_attachment in choiceiter:
            # If we already determined what our return value is but the
            # type mismatches what we try now, we have to abort.  Eg:
            # a page can not become an attachment or the other way round.
            if rv_type is not None and rv_type != is_attachment:
                break

            try:
                with open(fs_path, 'rb') as f:
                    if rv_type is None:
                        rv_type = is_attachment
                    for key, lines in metaformat.tokenize(f, encoding='utf-8'):
                        if key not in rv:
                            rv[key] = u''.join(lines)
            except IOError as e:
                if e.errno not in (errno.ENOTDIR, errno.ENOENT):
                    raise
                if not is_attachment or not os.path.isfile(fs_path[:-3]):
                    continue
                # Special case: we are loading an attachment but the meta
                # data file does not exist.  In that case we still want to
                # record that we're loading an attachment.
                elif is_attachment:
                    rv_type = True

            if '_source_alt' not in rv:
                rv['_source_alt'] = source_alt

        if rv_type is None:
            return

        rv['_path'] = path
        rv['_id'] = posixpath.basename(path)
        rv['_gid'] = hashlib.md5(path.encode('utf-8')).hexdigest()
        rv['_alt'] = alt
        if rv_type:
            rv['_attachment_for'] = posixpath.dirname(path)

        return rv

    def iter_items(self, path, alt=PRIMARY_ALT):
        """Iterates over all items below a path and yields them as
        tuples in the form ``(id, alt, is_attachment)``.
        """
        fn_base = self.to_fs_path(path)

        if alt is None:
            alts = self.config.list_alternatives()
            single_alt = False
        else:
            alts = [alt]
            single_alt = True

        choiceiter = _iter_filename_choices(fn_base, alts, self.config)

        for fs_path, actual_alt, is_attachment in choiceiter:
            if not os.path.isfile(fs_path):
                continue

            # This path is actually for an attachment, which means that we
            # cannot have any items below it and will just abort with an
            # empty iterator.
            if is_attachment:
                break

            try:
                dir_path = os.path.dirname(fs_path)
                for filename in os.listdir(dir_path):
                    if not isinstance(filename, text_type):
                        try:
                            filename = filename.decode(fs_enc)
                        except UnicodeError:
                            continue

                    if filename.endswith('.lr') or \
                       self.env.is_uninteresting_source_name(filename):
                        continue

                    # We found an attachment.  Attachments always live
                    # below the primary alt, so we report it as such.
                    if os.path.isfile(os.path.join(dir_path, filename)):
                        yield filename, PRIMARY_ALT, True

                    # We found a directory, let's make sure it contains a
                    # contents.lr file (or a contents+alt.lr file).
                    else:
                        for content_alt in _iter_content_files(
                                os.path.join(dir_path, filename), alts):
                            yield filename, content_alt, False
                            # If we want a single alt, we break here so
                            # that we only produce a single result.
                            # Otherwise this would also return the primary
                            # fallback here.
                            if single_alt:
                                break
            except IOError as e:
                if e.errno != errno.ENOENT:
                    raise
                continue

            # If we reach this point, we found our parent, so we can stop
            # searching for more at this point.
            break

    def get_datamodel_for_raw_data(self, raw_data, pad=None):
        """Returns the datamodel that should be used for a specific raw
        data.  This might require the discovery of a parent object through
        the pad.
        """
        path = raw_data['_path']
        is_attachment = bool(raw_data.get('_attachment_for'))
        datamodel = (raw_data.get('_model') or '').strip() or None
        return self.get_implied_datamodel(path, is_attachment, pad,
                                          datamodel=datamodel)

    def iter_dependent_models(self, datamodel):
        seen = set()
        def deep_find(datamodel):
            seen.add(datamodel)

            if datamodel.parent is not None and datamodel.parent not in seen:
                deep_find(datamodel.parent)

            for related_dm_name in (datamodel.child_config.model,
                                    datamodel.attachment_config.model):
                dm = self.datamodels.get(related_dm_name)
                if dm is not None and dm not in seen:
                    deep_find(dm)

        deep_find(datamodel)
        seen.discard(datamodel)
        return iter(seen)

    def get_implied_datamodel(self, path, is_attachment=False, pad=None,
                              datamodel=None):
        """Looks up a datamodel based on the information about the parent
        of a model.
        """
        dm_name = datamodel

        # Only look for a datamodel if there was not defined.
        if dm_name is None:
            parent = posixpath.dirname(path)
            dm_name = None

            # If we hit the root, and there is no model defined we need
            # to make sure we do not recurse onto ourselves.
            if parent != path:
                if pad is None:
                    pad = self.new_pad()
                parent_obj = pad.get(parent)
                if parent_obj is not None:
                    if is_attachment:
                        dm_name = parent_obj.datamodel.attachment_config.model
                    else:
                        dm_name = parent_obj.datamodel.child_config.model

        for dm_name in _iter_datamodel_choices(dm_name, path, is_attachment):
            # If that datamodel exists, let's roll with it.
            datamodel = self.datamodels.get(dm_name)
            if datamodel is not None:
                return datamodel

        raise AssertionError("Did not find an appropriate datamodel.  "
                             "That should never happen.")

    def get_attachment_type(self, path):
        """Gets the attachment type for a path."""
        return self.config['ATTACHMENT_TYPES'].get(
            posixpath.splitext(path)[1].lower())

    def track_record_dependency(self, record):
        ctx = get_ctx()
        if ctx is not None:
            for filename in record.iter_source_filenames():
                ctx.record_dependency(filename)
            for virtual_source in record.iter_virtual_sources():
                ctx.record_virtual_dependency(virtual_source)
            if getattr(record, 'datamodel', None) and record.datamodel.filename:
                ctx.record_dependency(record.datamodel.filename)
                for dep_model in self.iter_dependent_models(record.datamodel):
                    if dep_model.filename:
                        ctx.record_dependency(dep_model.filename)
        return record

    def get_default_slug(self, data, pad):
        parent_path = posixpath.dirname(data['_path'])
        parent = None
        if parent_path != data['_path']:
            parent = pad.get(parent_path)
        if parent:
            slug = parent.datamodel.get_default_child_slug(pad, data)
        else:
            slug = ''
        return slug

    def process_data(self, data, datamodel, pad):
        # Automatically fill in slugs
        if not data['_slug']:
            data['_slug'] = self.get_default_slug(data, pad)
        else:
            data['_slug'] = data['_slug'].strip('/')

        # For attachments figure out the default attachment type if it's
        # not yet provided.
        if is_undefined(data['_attachment_type']) and \
           data['_attachment_for']:
            data['_attachment_type'] = self.get_attachment_type(data['_path'])

        # Automatically fill in templates
        if is_undefined(data['_template']):
            data['_template'] = datamodel.get_default_template_name()

    def get_record_class(self, datamodel, raw_data):
        """Returns the appropriate record class for a datamodel and raw data."""
        is_attachment = bool(raw_data.get('_attachment_for'))
        if not is_attachment:
            return Page
        attachment_type = raw_data['_attachment_type']
        return attachment_classes.get(attachment_type, Attachment)

    def new_pad(self):
        """Creates a new pad object for this database."""
        return Pad(self)


def _split_alt_from_url(config, clean_path):
    primary = config.primary_alternative

    # The alternative system is not configured, just return
    if primary is None:
        return None, clean_path

    # First try to find alternatives that are identified by a prefix.
    for prefix, alt in config.get_alternative_url_prefixes():
        if clean_path.startswith(prefix):
            return alt, clean_path[len(prefix):].strip('/')
        # Special case which is the URL root.
        elif prefix.strip('/') == clean_path:
            return alt, ''

    # Now find alternatives that are identified by a suffix.
    for suffix, alt in config.get_alternative_url_suffixes():
        if clean_path.endswith(suffix):
            return alt, clean_path[:-len(suffix)].strip('/')

    # If we have a primary alternative without a prefix and suffix, we can
    # return that one.
    if config.primary_alternative_is_rooted:
        return None, clean_path

    return None, None


class Pad(object):

    def __init__(self, db):
        self.db = db
        self.cache = RecordCache(db.config['EPHEMERAL_RECORD_CACHE_SIZE'])
        self.databags = Databags(db.env)

    @property
    def config(self):
        """The config for this pad."""
        return self.db.config

    @property
    def env(self):
        """The env for this pad."""
        return self.db.env

    def make_absolute_url(self, url):
        """Given a URL this makes it absolute if this is possible."""
        base_url = self.db.config['PROJECT'].get('url')
        if base_url is None:
            raise RuntimeError('To use absolute URLs you need to configure '
                               'the URL in the project config.')
        return url_join(base_url.rstrip('/') + '/', url.lstrip('/'))

    def make_url(self, url, base_url=None, absolute=None, external=None):
        """Helper method that creates a finalized URL based on the parameters
        provided and the config.
        """
        url_style = self.db.config.url_style
        if absolute is None:
            absolute = url_style == 'absolute'
        if external is None:
            external = url_style == 'external'
        if external:
            external_base_url = self.db.config.base_url
            if external_base_url is None:
                raise RuntimeError('To use absolute URLs you need to '
                                   'configure the URL in the project config.')
            return url_join(external_base_url, url.lstrip('/'))
        if absolute:
            return url_join(self.db.config.base_path, url.lstrip('/'))
        if base_url is None:
            raise RuntimeError('Cannot calculate a relative URL if no base '
                               'URL has been provided.')
        return make_relative_url(base_url, url)

    def resolve_url_path(self, url_path, include_invisible=False,
                         include_assets=True, alt_fallback=True):
        """Given a URL path this will find the correct record which also
        might be an attachment.  If a record cannot be found or is unexposed
        the return value will be `None`.
        """
        pieces = clean_path = cleanup_path(url_path).strip('/')

        # Split off the alt and if no alt was found, point it to the
        # primary alternative.  If the clean path comes back as `None`
        # then the config does not include a rooted alternative and we
        # have to skip handling of regular records.
        alt, clean_path = _split_alt_from_url(self.db.config, clean_path)
        if clean_path is not None:
            if not alt:
                if alt_fallback:
                    alt = self.db.config.primary_alternative or PRIMARY_ALT
                else:
                    alt = PRIMARY_ALT
            node = self.get_root(alt=alt)
            if node is None:
                raise RuntimeError('Tree root could not be found.')

            pieces = clean_path.split('/')
            if pieces == ['']:
                pieces = []

            rv = node.resolve_url_path(pieces)
            if rv is not None and (include_invisible or rv.is_visible):
                return rv

        if include_assets:
            return self.asset_root.resolve_url_path(pieces)

    def get_root(self, alt=PRIMARY_ALT):
        """The root page of the database."""
        return self.get('/', alt=alt, persist=True)

    root = property(get_root)

    @property
    def asset_root(self):
        """The root of the asset tree."""
        return Directory(self, name='',
                         path=os.path.join(self.db.env.root_path, 'assets'))

    def get_all_roots(self):
        """Returns all the roots for building."""
        rv = []
        for alt in self.db.config.list_alternatives():
            rv.append(self.get_root(alt=alt))

        # If we don't have any alternatives, then we go with the implied
        # root.
        if not rv and self.root:
            rv = [self.root]

        rv.append(self.asset_root)
        return rv

    def get_virtual(self, record, virtual_path):
        """Resolves a virtual path below a record."""
        pieces = virtual_path.strip('/').split('/')
        if not pieces or pieces == ['']:
            return record

        if pieces[0].isdigit():
            if len(pieces) == 1:
                return self.get(record['_path'], page_num=int(pieces[0]))
            return None

        resolver = self.env.virtual_sources.get(pieces[0])
        if resolver is None:
            return None

        return resolver(record, pieces[1:])

    def get(self, path, alt=PRIMARY_ALT, page_num=None, persist=True,
            allow_virtual=True):
        """Loads a record by path."""
        virt_markers = path.count('@')

        # If the virtual marker is included, we also want to look up the
        # virtual path below an item.  Special case: if virtual paths are
        # not allowed but one was passed, we just return `None`.
        if virt_markers == 1:
            if page_num is not None:
                raise RuntimeError('Cannot use both virtual paths and '
                                   'explicit page number lookups.  You '
                                   'need to one or the other.')
            if not allow_virtual:
                return None
            path, virtual_path = path.split('@', 1)
            rv = self.get(path, alt=alt, page_num=page_num,
                          persist=persist)
            if rv is None:
                return None
            return self.get_virtual(rv, virtual_path)

        # Sanity check: there must only be one or things will get weird.
        elif virt_markers > 1:
            return None

        path = cleanup_path(path)
        virtual_path = None
        if page_num is not None:
            virtual_path = str(page_num)

        rv = self.cache.get(path, alt, virtual_path)
        if rv is not Ellipsis:
            if rv is not None:
                self.db.track_record_dependency(rv)
            return rv

        raw_data = self.db.load_raw_data(path, alt=alt)
        if raw_data is None:
            self.cache.remember_as_missing(path, alt, virtual_path)
            return

        rv = self.instance_from_data(raw_data, page_num=page_num)

        if persist:
            self.cache.persist(rv)
        else:
            self.cache.remember(rv)

        return self.db.track_record_dependency(rv)

    def alt_exists(self, path, alt=PRIMARY_ALT, fallback=False):
        """Checks if an alt exists."""
        path = cleanup_path(path)
        if '@' in path:
            return False

        # If we find the path in the cache, check if it was loaded from
        # the right source alt.
        rv = self.get(path, alt)
        if rv is not None:
            if rv['_source_alt'] == alt:
                return True
            elif (fallback or
                  (rv['_source_alt'] == PRIMARY_ALT and
                   alt == self.config.primary_alternative)):
                return True
            return False

        return False

    def get_asset(self, path):
        """Loads an asset by path."""
        clean_path = cleanup_path(path).strip('/')
        node = self.asset_root
        for piece in clean_path.split('/'):
            node = node.get_child(piece)
            if node is None:
                break
        return node

    def instance_from_data(self, raw_data, datamodel=None, page_num=None):
        """This creates an instance from the given raw data."""
        if datamodel is None:
            datamodel = self.db.get_datamodel_for_raw_data(raw_data, self)
        data = datamodel.process_raw_data(raw_data, self)
        self.db.process_data(data, datamodel, self)
        cls = self.db.get_record_class(datamodel, data)
        return cls(self, data, page_num=page_num)

    def query(self, path=None, alt=PRIMARY_ALT):
        """Queries the database either at root level or below a certain
        path.  This is the recommended way to interact with toplevel data.
        The alternative is to work with the :attr:`root` document.
        """
        # Don't accidentally pass `None` down to the query as this might
        # do some unexpected things.
        if alt is None:
            alt = PRIMARY_ALT
        return Query(path='/' + (path or '').strip('/'), pad=self, alt=alt) \
            .include_hidden(True)


class TreeItem(object):
    """Represents a single tree item and all the alts within it."""

    def __init__(self, tree, path, alts, exists=True,
                 is_attachment=False, attachment_type=None,
                 can_have_children=False, can_have_attachments=False,
                 can_be_deleted=False, is_visible=True,
                 label_i18n=None):
        self.tree = tree
        self.path = path
        self.alts = alts
        self.exists = exists
        self.is_attachment = is_attachment
        self.attachment_type = attachment_type
        self.can_have_children = can_have_children
        self.can_have_attachments = can_have_attachments
        self.can_be_deleted = can_be_deleted
        self.is_visible = is_visible
        self.label_i18n = label_i18n

    @property
    def id(self):
        """The local ID of the item."""
        return posixpath.basename(self.path)

    def get_parent(self):
        """Returns the parent item."""
        if self.path == '/':
            return None
        return self.tree.get(posixpath.dirname(self.path))

    def get(self, path):
        """Returns a child within this item."""
        if self.exists:
            return self.tree.get(posixpath.join(self.path, path))

    def iter_children(self, include_attachments=True, include_pages=True):
        """Iterates over all children."""
        if not self.exists:
            return iter(())
        return self.tree.iter_children(self.path, include_attachments,
                                       include_pages)

    def get_children(self, offset=0, limit=None, include_attachments=True,
                     include_pages=True):
        """Returns a list of all children."""
        if not self.exists:
            return []
        return self.tree.get_children(self.path, offset, limit,
                                      include_attachments, include_pages)

    def __repr__(self):
        return '<TreeItem %r%s>' % (
            self.path,
            self.is_attachment and ' attachment' or '',
        )


class Alt(object):

    def __init__(self, id, record):
        self.id = id
        self.record = record
        self.exists = record is not None and \
            os.path.isfile(record.source_filename)

    def __repr__(self):
        return '<Alt %r%s>' % (self.id, self.exists and '*' or '')


class Tree(object):
    """Special object that can be used to get a broader insight into the
    database in a way that is not bound to the alt system directly.

    This wraps a pad and provides additional ways to interact with the data
    of the database in a way that is similar to how the data is actually laid
    out on the file system and not as the data is represented.  Primarily the
    difference is how alts are handled.  Where the pad resolves the alts
    automatically to make the handling automatic, the tree will give access
    to the underlying alts automatically.
    """

    def __init__(self, pad):
        self.pad = pad

    def get(self, path=None, persist=True):
        """Returns a path item at the given node."""
        path = '/' + (path or '').strip('/')
        alts = {}
        exists = False
        first_record = None
        label_i18n = None

        for alt in chain([PRIMARY_ALT], self.pad.db.config.list_alternatives()):
            record = self.pad.get(path, alt=alt, persist=persist,
                                  allow_virtual=False)
            if first_record is None:
                first_record = record
            if record is not None:
                exists = True
            alts[alt] = Alt(alt, record)

        # These flags only really make sense if we found an existing
        # record, otherwise we fall back to some sort of sane default.
        # Note that in theory different alts can disagree on what
        # datamodel they use but this is something that is really not
        # supported.  This cannot happen if you edit based on the admin
        # panel and if you edit it manually and screw up the part, we
        # cannot really do anything about it.
        #
        # More importantly we genreally assume that first_record is the
        # primary alt.  There are some situations in which case this is
        # not true, for instance if no primary alt exists.  In this case
        # we just go with any record.
        is_visible = True
        is_attachment = False
        attachment_type = None
        can_have_children = False
        can_have_attachments = False
        can_be_deleted = exists and path != '/'

        if first_record is not None:
            is_attachment = first_record.is_attachment
            is_visible = first_record.is_visible
            dm = first_record.datamodel
            if not is_attachment:
                can_have_children = dm.has_own_children
                can_have_attachments = dm.has_own_attachments
                if dm.protected:
                    can_be_deleted = False
            else:
                attachment_type = first_record['_attachment_type'] or None
            label_i18n = first_record.get_record_label_i18n()

        return TreeItem(self, path, alts, exists, is_attachment=is_attachment,
                        attachment_type=attachment_type,
                        can_have_children=can_have_children,
                        can_have_attachments=can_have_attachments,
                        can_be_deleted=can_be_deleted,
                        is_visible=is_visible, label_i18n=label_i18n)

    def _get_child_ids(self, path=None, include_attachments=True,
                       include_pages=True):
        """Returns a sorted list of just the IDs of children below a path."""
        path = '/' + (path or '').strip('/')
        names = set()
        for name, _, is_attachment in self.pad.db.iter_items(
                path, alt=None):
            if (is_attachment and include_attachments) or \
               (not is_attachment and include_pages):
                names.add(name)
        return sorted(names, key=lambda x: x.lower())

    def iter_children(self, path=None, include_attachments=True,
                      include_pages=True):
        """Iterates over all children below a path."""
        path = '/' + (path or '').strip('/')
        for name in self._get_child_ids(path, include_attachments,
                                        include_pages):
            yield self.get(posixpath.join(path, name), persist=False)

    def get_children(self, path=None, offset=0, limit=None,
                     include_attachments=True, include_pages=True):
        """Returns a slice of children."""
        path = '/' + (path or '').strip('/')
        end = None
        if limit is not None:
            end = offset + limit
        return [self.get(posixpath.join(path, name), persist=False)
                for name in self._get_child_ids(
                    path, include_attachments, include_pages)[offset:end]]

    def edit(self, path, is_attachment=None, alt=PRIMARY_ALT, datamodel=None):
        """Edits a record by path."""
        return make_editor_session(self.pad, cleanup_path(path), alt=alt,
                                   is_attachment=is_attachment,
                                   datamodel=datamodel)


class RecordCache(object):
    """The record cache holds records eitehr in an persistent or ephemeral
    section which helps the pad not load records it already saw.
    """

    def __init__(self, ephemeral_cache_size=1000):
        self.persistent = {}
        self.ephemeral = LRUCache(ephemeral_cache_size)

    def _get_cache_key(self, record_or_path, alt=PRIMARY_ALT,
                       virtual_path=None):
        if isinstance(record_or_path, string_types):
            path = record_or_path.strip('/')
        else:
            path, virtual_path = split_virtual_path(record_or_path.path)
            path = path.strip('/')
            virtual_path = virtual_path or None
            alt = record_or_path.alt
        return (path, alt, virtual_path)

    def flush(self):
        """Flushes the cache"""
        self.persistent.clear()
        self.ephemeral.clear()

    def is_persistent(self, record):
        """Indicates if a record is in the persistent record cache."""
        cache_key = self._get_cache_key(record)
        return cache_key in self.persistent

    def remember(self, record):
        """Remembers the record in the record cache."""
        cache_key = self._get_cache_key(record)
        if cache_key not in self.persistent and cache_key not in self.ephemeral:
            self.ephemeral[cache_key] = record

    def persist(self, record):
        """Persists a record.  This will put it into the persistent cache."""
        cache_key = self._get_cache_key(record)
        self.persistent[cache_key] = record
        try:
            del self.ephemeral[cache_key]
        except KeyError:
            pass

    def persist_if_cached(self, record):
        """If the record is already ephemerally cached, this promotes it to
        the persistent cache section.
        """
        cache_key = self._get_cache_key(record)
        if cache_key in self.ephemeral:
            self.persist(record)

    def get(self, path, alt=PRIMARY_ALT, virtual_path=None):
        """Looks up a record from the cache."""
        cache_key = self._get_cache_key(path, alt, virtual_path)
        rv = self.persistent.get(cache_key, Ellipsis)
        if rv is not Ellipsis:
            return rv
        rv = self.ephemeral.get(cache_key, Ellipsis)
        if rv is not Ellipsis:
            return rv
        return Ellipsis

    def remember_as_missing(self, path, alt=PRIMARY_ALT, virtual_path=None):
        cache_key = self._get_cache_key(path, alt, virtual_path)
        self.persistent.pop(cache_key, None)
        self.ephemeral[cache_key] = None
