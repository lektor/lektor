import errno
import math
import os

from inifile import IniFile

from lektor import types
from lektor._compat import iteritems, itervalues
from lektor.environment import Expression, FormatExpression, PRIMARY_ALT
from lektor.i18n import get_i18n_block, load_i18n_block, generate_i18n_kvs
from lektor.pagination import Pagination
from lektor.utils import bool_from_string, slugify


class ChildConfig(object):

    def __init__(self, enabled=None, slug_format=None, model=None,
                 order_by=None, replaced_with=None, hidden=None):
        if enabled is None:
            enabled = True
        self.enabled = enabled
        self.slug_format = slug_format
        self.model = model
        self.order_by = order_by
        self.replaced_with = replaced_with
        self.hidden = hidden

    def to_json(self):
        return {
            'enabled': self.enabled,
            'slug_format': self.slug_format,
            'model': self.model,
            'order_by': self.order_by,
            'replaced_with': self.replaced_with,
            'hidden': self.hidden,
        }


class PaginationConfig(object):

    def __init__(self, env, enabled=None, per_page=None, url_suffix=None,
                 items=None):
        self.env = env
        if enabled is None:
            enabled = False
        self.enabled = enabled
        if per_page is None:
            per_page = 20
        self.per_page = per_page
        if url_suffix is None:
            url_suffix = 'page'
        self.url_suffix = url_suffix
        self.items = items
        self._items_tmpl = None

    def count_total_items(self, record):
        """Counts the number of items over all pages."""
        return self.get_pagination_query(record).count()

    def count_pages(self, record):
        """Returns the total number of pages for the children of a record."""
        total = self.count_total_items(record)
        return int(math.ceil(total / float(self.per_page)))

    def slice_query_for_page(self, record, page):
        """Slices the query so it returns the children for a given page."""
        query = self.get_pagination_query(record)
        if not self.enabled or page is None:
            return query
        return query.limit(self.per_page).offset((page - 1) * self.per_page)

    def get_record_for_page(self, record, page_num):
        """Given a normal record this one returns the version specific
        for a page.
        """
        # If we already have the right version, return it.
        if record.page_num == page_num:
            return record

        # Check if we have a cached version
        pad = record.pad
        rv = pad.cache.get(record.path, record.alt, str(page_num))
        if rv is not Ellipsis:
            return rv

        # Make what we need out of what we have and put it into the cache.
        cls = record.__class__
        rv = cls(record.pad, record._data, page_num=page_num)
        pad.cache.remember(rv)
        return rv

    def match_pagination(self, record, url_path):
        """Matches the pagination from the URL path."""
        if not self.enabled:
            return
        suffixes = self.url_suffix.strip('/').split('/')
        if url_path[:len(suffixes)] != suffixes:
            return

        try:
            page_num = int(url_path[len(suffixes)])
        except (ValueError, IndexError):
            return

        # It's important we do not allow "1" here as the first page is always
        # on the root.  Changing this would mean the URLs are incorrectly
        # generated if someone manually went to /page/1/.
        if page_num == 1 or len(url_path) != len(suffixes) + 1:
            return

        # Page needs to have at least a single child.
        rv = self.get_record_for_page(record, page_num)
        if rv.pagination.items.first() is not None:
            return rv

    def get_pagination_controller(self, record):
        if not self.enabled:
            raise RuntimeError('Pagination is disabled')
        return Pagination(record, self)

    def get_pagination_query(self, record):
        items_expr = self.items
        if items_expr is None:
            return record.children
        if self._items_tmpl is None or \
           self._items_tmpl[0] != items_expr:
            self._items_tmpl = (
                items_expr,
                Expression(self.env, items_expr)
            )

        return self._items_tmpl[1].evaluate(
            record.pad, this=record)

    def to_json(self):
        return {
            'enabled': self.enabled,
            'per_page': self.per_page,
            'url_suffix': self.url_suffix,
            'items': self.items,
        }


class AttachmentConfig(object):

    def __init__(self, enabled=None, model=None, order_by=None,
                 hidden=None):
        if enabled is None:
            enabled = True
        if hidden is None:
            hidden = False
        self.enabled = enabled
        self.model = model
        self.order_by = order_by
        self.hidden = hidden

    def to_json(self):
        return {
            'enabled': self.enabled,
            'model': self.model,
            'order_by': self.order_by,
            'hidden': self.hidden,
        }


class Field(object):

    def __init__(self, env, name, type=None, options=None):
        if type is None:
            type = env.types['string']
        if options is None:
            options = {}
        self.options = options
        self.name = name
        label_i18n = get_i18n_block(options, 'label')
        if not label_i18n:
            label_i18n = {'en': name.replace('_', ' ').strip().capitalize()}
        self.label_i18n = label_i18n
        self.description_i18n = get_i18n_block(options, 'description') or None
        self.default = options.get('default')
        self.type = type(env, options)

    @property
    def label(self):
        return self.label_i18n.get('en')

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        return {
            'name': self.name,
            'label': self.label,
            'label_i18n': self.label_i18n,
            'hide_label': bool_from_string(self.options.get('hide_label'),
                                           default=False),
            'description_i18n': self.description_i18n,
            'type': self.type.to_json(pad, record, alt),
            'default': self.default,
        }

    def deserialize_value(self, value, pad=None):
        raw_value = types.RawValue(self.name, value, field=self, pad=pad)
        return self.type.value_from_raw_with_default(raw_value)

    def serialize_value(self, value):
        return self.type.value_to_raw(value)

    def __repr__(self):
        return '<%s %r type=%r>' % (
            self.__class__.__name__,
            self.name,
            self.type,
        )


def _iter_all_fields(obj):
    for name in sorted(x for x in obj.field_map if x[:1] == '_'):
        yield obj.field_map[name]
    for field in obj.fields:
        yield field


class DataModel(object):

    def __init__(self, env, id, name_i18n, label_i18n=None,
                 filename=None, hidden=None, protected=None,
                 child_config=None, attachment_config=None,
                 pagination_config=None, fields=None,
                 primary_field=None, parent=None):
        self.env = env
        self.filename = filename
        self.id = id
        self.name_i18n = name_i18n
        self.label_i18n = label_i18n
        if hidden is None:
            hidden = False
        self.hidden = hidden
        if protected is None:
            protected = False
        self.protected = protected
        if child_config is None:
            child_config = ChildConfig()
        self.child_config = child_config
        if attachment_config is None:
            attachment_config = AttachmentConfig()
        self.attachment_config = attachment_config
        if pagination_config is None:
            pagination_config = PaginationConfig(env)
        self.pagination_config = pagination_config
        if fields is None:
            fields = []
        self.fields = fields
        if primary_field is None and fields:
            primary_field = fields[0].name
        self.primary_field = primary_field
        self.parent = parent

        # This is a mapping of the key names to the actual field which
        # also includes the system fields.  This is primarily used for
        # fast internal operations but also the admin.
        self.field_map = dict((x.name, x) for x in fields)
        for key, (ty, opts) in iteritems(system_fields):
            self.field_map[key] = Field(env, name=key, type=ty, options=opts)

        self._child_slug_tmpl = None
        self._child_replacements = None
        self._label_tmpls = {}

    @property
    def name(self):
        name = (self.name_i18n or {}).get('en')
        return name or self.id.title().replace('_', ' ')

    @property
    def label(self):
        return (self.label_i18n or {}).get('en')

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        """Describes the datamodel as JSON data."""
        return {
            'filename': self.filename,
            'alt': alt,
            'id': self.id,
            'name': self.name,
            'name_i18n': self.name_i18n,
            'primary_field': self.primary_field,
            'label': self.label,
            'label_i18n': self.label_i18n,
            'hidden': self.hidden,
            'protected': self.protected,
            'child_config': self.child_config.to_json(),
            'attachment_config': self.attachment_config.to_json(),
            'pagination_config': self.pagination_config.to_json(),
            'fields': [x.to_json(pad, record, alt) for x in
                       _iter_all_fields(self)],
        }

    def format_record_label(self, record, lang='en'):
        """Returns the label for a given record."""
        label = self.label_i18n.get(lang)
        if label is None:
            return None

        tmpl = self._label_tmpls.get(lang)
        if tmpl is None:
            tmpl = (
                label,
                FormatExpression(self.env, label)
            )
            self._label_tmpls[lang] = tmpl

        try:
            return tmpl[1].evaluate(record.pad, this=record)
        except Exception:
            # XXX: log
            return None

    def get_default_child_slug(self, pad, data):
        """Formats out the child slug."""
        slug_format = self.child_config.slug_format
        if slug_format is None:
            return data['_id']

        if self._child_slug_tmpl is None or \
           self._child_slug_tmpl[0] != slug_format:
            self._child_slug_tmpl = (
                slug_format,
                FormatExpression(self.env, slug_format)
            )

        try:
            return '_'.join(self._child_slug_tmpl[1].evaluate(
                pad, this=data).strip().split()).strip('/')
        except Exception:
            # XXX: log
            return 'temp-' + slugify(data['_id'])

    def get_default_template_name(self):
        return self.id + '.html'

    @property
    def has_own_children(self):
        return self.child_config.replaced_with is None and \
               self.child_config.enabled

    @property
    def has_own_attachments(self):
        return self.attachment_config.enabled

    def get_child_replacements(self, record):
        """Returns the query that should be used as replacement for the
        actual children.
        """
        replaced_with = self.child_config.replaced_with
        if replaced_with is None:
            return None

        if self._child_replacements is None or \
           self._child_replacements[0] != replaced_with:
            self._child_replacements = (
                replaced_with,
                Expression(self.env, replaced_with)
            )

        return self._child_replacements[1].evaluate(record.pad, this=record)

    def process_raw_data(self, raw_data, pad=None):
        rv = {}
        for field in itervalues(self.field_map):
            value = raw_data.get(field.name)
            rv[field.name] = field.deserialize_value(value, pad=pad)
        rv['_model'] = self.id
        return rv

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.id,
        )


class FlowBlockModel(object):

    def __init__(self, env, id, name_i18n, filename=None, fields=None,
                 order=None, button_label=None):
        self.env = env
        self.id = id
        self.name_i18n = name_i18n
        self.filename = filename
        if fields is None:
            fields = []
        self.fields = fields
        if order is None:
            order = 100
        self.order = order
        self.button_label = button_label

        self.field_map = dict((x.name, x) for x in fields)
        self.field_map['_flowblock'] = Field(
            env, name='_flowblock', type=env.types['string'])

    @property
    def name(self):
        return self.name_i18n.get('en') or self.id.title().replace('_', ' ')

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        return {
            'id': self.id,
            'name': self.name,
            'name_i18n': self.name_i18n,
            'filename': self.filename,
            'fields': [x.to_json(pad, record, alt) for x in _iter_all_fields(self)
                       if x.name != '_flowblock'],
            'order': self.order,
            'button_label': self.button_label,
        }

    def process_raw_data(self, raw_data, pad=None):
        rv = {}
        for field in itervalues(self.field_map):
            value = raw_data.get(field.name)
            rv[field.name] = field.deserialize_value(value, pad=pad)
        rv['_flowblock'] = self.id
        return rv

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.id,
        )


def fielddata_from_ini(inifile):
    return [(
        sect.split('.', 1)[1],
        inifile.section_as_dict(sect),
    ) for sect in inifile.sections() if sect.startswith('fields.')]


def datamodel_data_from_ini(id, inifile):
    def _parse_order(value):
        value = (value or '').strip()
        if not value:
            return None
        return [x for x in [x.strip() for x in value.strip().split(',')] if x]

    return dict(
        filename=inifile.filename,
        id=id,
        parent=inifile.get('model.inherits'),
        name_i18n=get_i18n_block(inifile, 'model.name'),
        label_i18n=get_i18n_block(inifile, 'model.label'),
        primary_field=inifile.get('model.primary_field'),
        hidden=inifile.get_bool('model.hidden', default=None),
        protected=inifile.get_bool('model.protected', default=None),
        child_config=dict(
            enabled=inifile.get_bool('children.enabled', default=None),
            slug_format=inifile.get('children.slug_format'),
            model=inifile.get('children.model'),
            order_by=_parse_order(inifile.get('children.order_by')),
            replaced_with=inifile.get('children.replaced_with'),
            hidden=inifile.get_bool('children.hidden', default=None),
        ),
        attachment_config=dict(
            enabled=inifile.get_bool('attachments.enabled', default=None),
            model=inifile.get('attachments.model'),
            order_by=_parse_order(inifile.get('attachments.order_by')),
            hidden=inifile.get_bool('attachments.hidden', default=None),
        ),
        pagination_config=dict(
            enabled=inifile.get_bool('pagination.enabled', default=None),
            per_page=inifile.get_int('pagination.per_page'),
            url_suffix=inifile.get('pagination.url_suffix'),
            items=inifile.get('pagination.items'),
        ),
        fields=fielddata_from_ini(inifile),
    )


def flowblock_data_from_ini(id, inifile):
    return dict(
        filename=inifile.filename,
        id=id,
        name_i18n=get_i18n_block(inifile, 'block.name'),
        fields=fielddata_from_ini(inifile),
        order=inifile.get_int('block.order'),
        button_label=inifile.get('block.button_label'),
    )


def fields_from_data(env, data, parent_fields=None):
    fields = []
    known_fields = set()

    for name, options in data:
        ty = env.types[options.get('type', 'string')]
        fields.append(Field(env=env, name=name, type=ty, options=options))
        known_fields.add(name)

    if parent_fields is not None:
        prepended_fields = []
        for field in parent_fields:
            if field.name not in known_fields:
                prepended_fields.append(field)
        fields = prepended_fields + fields

    return fields


def datamodel_from_data(env, model_data, parent=None):
    def get_value(key):
        path = key.split('.')
        node = model_data
        for item in path:
            node = node.get(item)
        if node is not None:
            return node
        if parent is not None:
            node = parent
            for item in path:
                node = getattr(node, item)
            return node

    fields = fields_from_data(env, model_data['fields'],
                              parent and parent.fields or None)

    return DataModel(
        env,

        # data that never inherits
        filename=model_data['filename'],
        id=model_data['id'],
        parent=parent,
        name_i18n=model_data['name_i18n'],
        primary_field=model_data['primary_field'],

        # direct data that can inherit
        label_i18n=get_value('label_i18n'),
        hidden=get_value('hidden'),
        protected=get_value('protected'),
        child_config=ChildConfig(
            enabled=get_value('child_config.enabled'),
            slug_format=get_value('child_config.slug_format'),
            model=get_value('child_config.model'),
            order_by=get_value('child_config.order_by'),
            replaced_with=get_value('child_config.replaced_with'),
            hidden=get_value('child_config.hidden'),
        ),
        attachment_config=AttachmentConfig(
            enabled=get_value('attachment_config.enabled'),
            model=get_value('attachment_config.model'),
            order_by=get_value('attachment_config.order_by'),
            hidden=get_value('attachment_config.hidden'),
        ),
        pagination_config=PaginationConfig(env,
            enabled=get_value('pagination_config.enabled'),
            per_page=get_value('pagination_config.per_page'),
            url_suffix=get_value('pagination_config.url_suffix'),
            items=get_value('pagination_config.items'),
        ),
        fields=fields,
    )


def flowblock_from_data(env, block_data):
    return FlowBlockModel(
        env,
        filename=block_data['filename'],
        id=block_data['id'],
        name_i18n=block_data['name_i18n'],
        fields=fields_from_data(env, block_data['fields']),
        order=block_data['order'],
        button_label=block_data['button_label'],
    )


def iter_inis(path):
    try:
        for filename in os.listdir(path):
            if not filename.endswith('.ini') or filename[:1] in '_.':
                continue
            fn = os.path.join(path, filename)
            if os.path.isfile(fn):
                base = filename[:-4]
                base = base.encode('utf-8').decode('ascii', 'replace')
                inifile = IniFile(fn)
                yield base, inifile
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def load_datamodels(env):
    """Loads the datamodels for a specific environment."""
    path = os.path.join(env.root_path, 'models')
    data = {}

    for model_id, inifile in iter_inis(path):
        data[model_id] = datamodel_data_from_ini(model_id, inifile)

    rv = {}

    def get_model(model_id):
        model = rv.get(model_id)
        if model is not None:
            return model
        if model_id in data:
            return create_model(model_id)

    def create_model(model_id):
        model_data = data.get(model_id)
        if model_data is None:
            raise RuntimeError('Model %r not found' % model_id)

        if model_data['parent'] is not None:
            parent = get_model(model_data['parent'])
        else:
            parent = None

        rv[model_id] = mod = datamodel_from_data(env, model_data, parent)
        return mod

    for model_id in data.keys():
        get_model(model_id)

    rv['none'] = DataModel(env, 'none', {'en': 'None'}, hidden=True)

    return rv


def load_flowblocks(env):
    """Loads all the flow blocks for a specific environment."""
    path = os.path.join(env.root_path, 'flowblocks')
    rv = {}

    for flowblock_id, inifile in iter_inis(path):
        rv[flowblock_id] = flowblock_from_data(env,
            flowblock_data_from_ini(flowblock_id, inifile))

    return rv


system_fields = {}


def add_system_field(name, **opts):
    opts = dict(generate_i18n_kvs(**opts))
    ty = types.builtin_types[opts.pop('type')]
    system_fields[name] = (ty, opts)


# The full path of the record
add_system_field('_path', type='string')

# The local ID (within a folder) of the record
add_system_field('_id', type='string')

# The global ID (within a folder) of the record
add_system_field('_gid', type='string')

# The alt key that identifies this record
add_system_field('_alt', type='string')

# The alt key for the file that was actually referenced.
add_system_field('_source_alt', type='string')

# the model that defines the data of the record
add_system_field('_model', type='string')

# the template that should be used for rendering if not hidden
add_system_field('_template', type='string',
                 label_i18n='TEMPLATE', width='1/2',
                 addon_label='[[code]]')

# the slug that should be used for this record.  This is added below the
# slug of the parent.
add_system_field('_slug', type='slug', label_i18n='URL_SLUG',
                 width='1/2')

# This can be used to hide an individual record.
add_system_field('_hidden', type='boolean', label_i18n='HIDE_PAGE',
                 checkbox_label_i18n='HIDE_PAGE_EXPLANATION')

# This marks a page as undiscoverable.
add_system_field('_discoverable', type='boolean', default='yes',
                 label_i18n='PAGE_IS_DISCOVERABLE',
                 checkbox_label_i18n='PAGE_IS_DISCOVERABLE_EXPLANATION')

# Useful fields for attachments.
add_system_field('_attachment_for', type='string')
add_system_field('_attachment_type', type='string',
                 label_i18n='ATTACHMENT_TYPE', addon_label='[[paperclip]]')
