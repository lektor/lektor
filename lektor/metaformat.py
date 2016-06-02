def _line_is_dashes(line):
    line = line.strip()
    return line == u'-' * len(line) and len(line) >= 3


def _process_buf(buf):
    for idx, line in enumerate(buf):
        if _line_is_dashes(line):
            line = line[1:]
        buf[idx] = line

    if buf and buf[-1][-1:] == '\n':
        buf[-1] = buf[-1][:-1]

    return buf[:]


def tokenize(iterable, interesting_keys=None, encoding=None):
    """This tokenizes an iterable of newlines as bytes into key value
    pairs out of the lektor bulk format.  By default it will process all
    fields, but optionally it can skip values of uninteresting keys and
    will instead yield `None`.  The values are left as list of decoded
    lines with their endings preserved.

    This will not perform any other processing on the data other than
    decoding and basic tokenizing.
    """
    key = []
    buf = []
    want_newline = False
    is_interesting = True

    def _flush_item():
        the_key = key[0]
        if not is_interesting:
            value = None
        else:
            value = _process_buf(buf)
        del key[:], buf[:]
        return the_key, value

    if encoding is not None:
        iterable = (x.decode(encoding, 'replace') for x in iterable)

    for line in iterable:
        line = line.rstrip(u'\r\n') + u'\n'

        if line.rstrip() == u'---':
            want_newline = False
            if key:
                yield _flush_item()
        elif key:
            if want_newline:
                want_newline = False
                if not line.strip():
                    continue
            if is_interesting:
                buf.append(line)
        else:
            bits = line.split(u':', 1)
            if len(bits) == 2:
                key = [bits[0].strip()]
                if interesting_keys is None:
                    is_interesting = True
                else:
                    is_interesting = key[0] in interesting_keys
                if is_interesting:
                    first_bit = bits[1].strip(u'\t ')
                    if first_bit.strip():
                        buf = [first_bit]
                    else:
                        buf = []
                        want_newline = True

    if key:
        yield _flush_item()


def serialize(iterable, encoding=None):
    """Serializes an iterable of key value pairs into a stream of
    string chunks.  If an encoding is provided, it will be encoded into that.

    This is primarily used by the editor to write back data to a source file.
    """
    def _produce(item, escape=False):
        if escape:
            if _line_is_dashes(item):
                item = u'-' + item
        if encoding is not None:
            item = item.encode(encoding)
        return item

    for idx, (key, value) in enumerate(iterable):
        value = value.replace('\r\n', '\n').replace('\r', '\n')
        if idx > 0:
            yield _produce('---\n')
        if '\n' in value or value.strip('\t ') != value:
            yield _produce(key + ':\n')
            yield _produce('\n')
            for line in value.splitlines(True):
                yield _produce(line, escape=True)
            yield _produce('\n')
        else:
            yield _produce('%s: %s\n' % (key, value))
