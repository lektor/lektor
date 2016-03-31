import re

from jinja2 import TemplateNotFound, is_undefined
from markupsafe import Markup

from lektor._compat import iteritems
from lektor.context import get_ctx
from lektor.environment import PRIMARY_ALT
from lektor.metaformat import tokenize
from lektor.types import Type


_block_re = re.compile(r'^####\s*([^#]*?)\s*####\s*$')
_line_unescape_re = re.compile(r'^#####(.*?)#####(\s*)$')


def discover_relevant_flowblock_models(flow, pad, record, alt):
    """Returns a dictionary of all relevant flow blocks.  If no list of
    flow block names is provided all flow blocks are returned.  Otherwise
    only flow blocks that are in the list or are children of flowblocks
    in the list are returned.
    """
    flow_blocks = flow.flow_blocks

    all_blocks = pad.db.flowblocks
    if flow_blocks is None:
        return dict((k, v.to_json(pad, record, alt))
                    for k, v in iteritems(all_blocks))

    wanted_blocks = set()
    to_process = flow_blocks[:]

    while to_process:
        block_name = to_process.pop()
        flowblock = all_blocks.get(block_name)
        if block_name in wanted_blocks or flowblock is None:
            continue
        wanted_blocks.add(block_name)
        for field in flowblock.fields:
            if isinstance(field.type, FlowType):
                if field.type.flow_blocks is None:
                    raise RuntimeError('Nested flow-blocks require explicit '
                                       'list of involved blocks.')
                to_process.extend(field.type.flow_blocks)

    rv = {}
    for block_name in wanted_blocks:
        rv[block_name] = all_blocks[block_name].to_json(pad, record, alt)

    return rv


class BadFlowBlock(Exception):

    def __init__(self, message):
        self.message = message


class FlowBlock(object):
    """Represents a flowblock for the template."""

    def __init__(self, data, pad, record):
        self._data = data
        self._bound_data = {}
        self.pad = pad
        self.record = record

    @property
    def flowblockmodel(self):
        """The flowblock model that created this flow block."""
        return self.pad.db.flowblocks[self._data['_flowblock']]

    def __contains__(self, name):
        return name in self._data and not is_undefined(self._data[name])

    def __getitem__(self, name):
        # If any data of a flowblock is accessed, we record that we need
        # this dependency.
        ctx = get_ctx()
        if ctx is not None:
            ctx.record_dependency(self.flowblockmodel.filename)

        rv = self._bound_data.get(name, Ellipsis)
        if rv is not Ellipsis:
            return rv
        rv = self._data[name]
        if hasattr(rv, '__get__'):
            rv = rv.__get__(self.record)
            self._bound_data[name] = rv
        return rv

    def __html__(self):
        ctx = get_ctx()

        # If we're in a nested render, we disable the rendering here or we
        # risk a recursion error.
        if ctx is None or self in ctx.flow_block_render_stack:
            return Markup.escape(repr(self))

        ctx.flow_block_render_stack.append(self)
        try:
            try:
                return self.pad.db.env.render_template(
                    ['blocks/%s.html' % self._data['_flowblock'],
                     'blocks/default.html'],
                    pad=self.pad,
                    this=self,
                    alt=self.record.alt,
                    values={'record': self.record}
                )
            except TemplateNotFound:
                return Markup('[could not find snippet template]')
        finally:
            ctx.flow_block_render_stack.pop()

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self['_flowblock'],
        )


class Flow(object):

    def __init__(self, blocks, record):
        self.blocks = blocks
        self.record = record

    def __html__(self):
        return Markup(u'\n\n'.join(x.__html__() for x in self.blocks))

    def __bool__(self):
        return bool(self.blocks)
    __nonzero__ = __bool__

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.blocks,
        )


class FlowDescriptor(object):

    def __init__(self, blocks, pad):
        self._blocks = blocks
        self._pad = pad

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return Flow([FlowBlock(data, self._pad, obj)
                     for data in self._blocks], obj)


def process_flowblock_data(raw_value):
    lineiter = iter(raw_value.splitlines(True))
    block = None
    buf = []
    blocks = []

    for line in lineiter:
        # Until we found the first block, we ignore leading whitespace.
        if block is None and not line.strip():
            continue

        # Find a new block start
        block_start = _block_re.match(line)
        if block_start is None:
            if block is None:
                raise BadFlowBlock('Did not find beginning of flow block')
        else:
            if block is not None:
                blocks.append((block, buf))
                buf = []
            block = block_start.group(1)
            continue
        buf.append(_line_unescape_re.sub('####\\1####\\2', line))

    if block is not None:
        blocks.append((block, buf))

    return blocks


class FlowType(Type):
    widget = 'flow'

    def __init__(self, env, options):
        Type.__init__(self, env, options)
        self.flow_blocks = [
            x.strip() for x in options.get('flow_blocks', '').split(',')
            if x.strip()] or None

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing flow')
        if raw.pad is None:
            return raw.missing_value('Flow value was technically present '
                                     'but used in a place where it cannot '
                                     'be used.')

        db = raw.pad.db
        rv = []

        try:
            for block, block_lines in process_flowblock_data(raw.value):
                # Unknown flow blocks are skipped for the moment
                if self.flow_blocks is not None and \
                   block not in self.flow_blocks:
                    continue
                flowblock = db.flowblocks.get(block)
                if flowblock is None:
                    continue

                d = {}
                for key, lines in tokenize(block_lines):
                    d[key] = u''.join(lines)
                rv.append(flowblock.process_raw_data(d, pad=raw.pad))
        except BadFlowBlock as e:
            return raw.bad_value(e.message)

        return FlowDescriptor(rv, raw.pad)

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        rv = Type.to_json(self, pad, record, alt)

        rv['flowblocks'] = discover_relevant_flowblock_models(
            self, pad, record, alt)

        block_order = self.flow_blocks
        if block_order is None:
            block_order = [k for k, v in sorted(iteritems(pad.db.flowblocks),
                                                key=lambda x: x[1].order)]
        rv['flowblock_order'] = block_order

        return rv
