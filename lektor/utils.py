# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import zip
from builtins import str
from builtins import range
from past.builtins import basestring
from builtins import object
import os
import sys
import re
import json
import uuid
import codecs
import subprocess
import tempfile
import posixpath
import traceback
import unicodedata
import multiprocessing
import hashlib
from queue import Queue
from threading import Thread
from datetime import datetime
from contextlib import contextmanager

import click

from werkzeug.http import http_date
from werkzeug.urls import url_parse
from werkzeug import urls
from werkzeug.posixemulation import rename
from jinja2 import is_undefined
from markupsafe import Markup

from lektor.uilink import BUNDLE_BIN_PATH, EXTRA_PATHS


is_windows = (os.name == 'nt')

_slash_escape = '\\/' not in json.dumps('/')

_slashes_re = re.compile(r'/+')
_last_num_re = re.compile(r'^(.*)(\d+)(.*?)$')
_list_marker = object()
_value_marker = object()
_slug_re = re.compile(r'([a-zA-Z0-9.-_]+)')

# Figure out our fs encoding, if it's ascii we upgrade to utf-8
fs_enc = sys.getfilesystemencoding()
try:
    if codecs.lookup(fs_enc).name == 'ascii':
        fs_enc = 'utf-8'
except LookupError:
    pass


def cleanup_path(path):
    return '/' + _slashes_re.sub('/', path.strip('/'))


def to_os_path(path):
    return path.strip('/').replace('/', os.path.sep)


def is_path(path):
    return os.path.sep in path or (os.path.altsep and os.path.altsep in path)


def magic_split_ext(filename, ext_check=True):
    """Splits a filename into base and extension.  If ext check is enabled
    (which is the default) then it verifies the extension is at least
    reasonable.
    """
    def bad_ext(ext):
        if not ext_check:
            return False
        if not ext or ext.split() != [ext] or ext.strip():
            return True
        return False

    parts = filename.rsplit('.', 2)
    if len(parts) == 2 and not parts[0]:
        return parts[0], ''
    if len(parts) == 3 and len(parts[1]) < 5:
        ext = '.'.join(parts[1:])
        if not bad_ext(ext):
            return parts[0], ext
    ext = parts[-1]
    if bad_ext(ext):
        return filename, ''
    basename = '.'.join(parts[:-1])
    return basename, ext


def iter_dotted_path_prefixes(dotted_path):
    pieces = dotted_path.split('.')
    if len(pieces) == 1:
        yield dotted_path, None
    else:
        for x in range(1, len(pieces)):
            yield '.'.join(pieces[:x]), '.'.join(pieces[x:])


def resolve_dotted_value(obj, dotted_path):
    node = obj
    for key in dotted_path.split('.'):
        if isinstance(node, dict):
            new_node = node.get(key)
            if new_node is None and key.isdigit():
                new_node = node.get(int(key))
        elif isinstance(node, list):
            try:
                new_node = node[int(key)]
            except (ValueError, TypeError, IndexError):
                new_node = None
        else:
            new_node = None
        node = new_node
        if node is None:
            break
    return node


def decode_flat_data(itemiter, dict_cls=dict):
    def _split_key(name):
        result = name.split('.')
        for idx, part in enumerate(result):
            if part.isdigit():
                result[idx] = int(part)
        return result

    def _enter_container(container, key):
        if key not in container:
            return container.setdefault(key, dict_cls())
        return container[key]

    def _convert(container):
        if _value_marker in container:
            force_list = False
            values = container.pop(_value_marker)
            if container.pop(_list_marker, False):
                force_list = True
                values.extend(_convert(x[1]) for x in
                              sorted(container.items()))
            if not force_list and len(values) == 1:
                values = values[0]

            if not container:
                return values
            return _convert(container)
        elif container.pop(_list_marker, False):
            return [_convert(x[1]) for x in sorted(container.items())]
        return dict_cls((k, _convert(v)) for k, v in container.items())

    result = dict_cls()

    for key, value in itemiter:
        parts = _split_key(key)
        if not parts:
            continue
        container = result
        for part in parts:
            last_container = container
            container = _enter_container(container, part)
            last_container[_list_marker] = isinstance(part, int)
        container[_value_marker] = [value]

    return _convert(result)


def merge(a, b):
    """Merges two values together."""
    if b is None and a is not None:
        return a
    if a is None:
        return b
    if isinstance(a, list) and isinstance(b, list):
        for idx, (item_1, item_2) in enumerate(zip(a, b)):
            a[idx] = merge(item_1, item_2)
    if isinstance(a, dict) and isinstance(b, dict):
        for key, value in b.items():
            a[key] = merge(a.get(key), value)
        return a
    return a


def secure_filename(filename, fallback_name='file'):
    base = filename.replace('/', ' ').replace('\\', ' ')
    basename, ext = magic_split_ext(base)
    rv = slugify(basename).lstrip('.')
    if not rv:
        rv = fallback_name
    if ext:
        return rv + '.' + ext
    return rv


def increment_filename(filename):
    directory, filename = os.path.split(filename)
    basename, ext = magic_split_ext(filename, ext_check=False)

    match = _last_num_re.match(basename)
    if match is not None:
        rv = match.group(1) + str(int(match.group(2)) + 1) + match.group(3)
    else:
        rv = basename + '2'

    if ext:
        rv += '.' + ext
    if directory:
        return os.path.join(directory, rv)
    return rv


def locate_executable(exe_file, cwd=None, include_bundle_path=True):
    """Locates an executable in the search path."""
    choices = [exe_file]
    resolve = True

    # If it's already a path, we don't resolve.
    if os.path.sep in exe_file or \
       (os.path.altsep and os.path.altsep in exe_file):
        resolve = False

    extensions = os.environ.get('PATHEXT', '').split(';')
    _, ext = os.path.splitext(exe_file)
    if os.name != 'nt' and '' not in extensions or \
       any(ext.lower() == extension.lower() for extension in extensions):
        extensions.insert(0, '')

    if resolve:
        paths = os.environ.get('PATH', '').split(os.pathsep)
        if BUNDLE_BIN_PATH and include_bundle_path:
            paths.insert(0, BUNDLE_BIN_PATH)
        for extra_path in EXTRA_PATHS:
            if extra_path not in paths:
                paths.append(extra_path)
        choices = [os.path.join(path, exe_file) for path in paths]

    if os.name == 'nt':
        choices.append(os.path.join((cwd or os.getcwd()), exe_file))

    try:
        for path in choices:
            for ext in extensions:
                if os.access(path + ext, os.X_OK):
                    return path + ext
    except OSError:
        pass


class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        if is_undefined(o):
            return None
        if isinstance(o, datetime):
            return http_date(o)
        if isinstance(o, uuid.UUID):
            return str(o)
        if hasattr(o, '__html__'):
            return str(o.__html__())
        return json.JSONEncoder.default(self, o)


def htmlsafe_json_dump(obj, **kwargs):
    kwargs.setdefault('cls', JSONEncoder)
    rv = json.dumps(obj, **kwargs) \
        .replace('<', '\\u003c') \
        .replace('>', '\\u003e') \
        .replace('&', '\\u0026') \
        .replace(u"'", '\\u0027')
    if not _slash_escape:
        rv = rv.replace('\\/', '/')
    return rv


def tojson_filter(obj, **kwargs):
    return Markup(htmlsafe_json_dump(obj, **kwargs))


def safe_call(func, args=None, kwargs=None):
    try:
        return func(*(args or ()), **(kwargs or {}))
    except Exception:
        # XXX: logging
        traceback.print_exc()


class Worker(Thread):

    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while 1:
            func, args, kwargs = self.tasks.get()
            safe_call(func, args, kwargs)
            self.tasks.task_done()


class WorkerPool(object):

    def __init__(self, num_threads=None):
        if num_threads is None:
            num_threads = multiprocessing.cpu_count()
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        self.tasks.put((func, args, kargs))

    def wait_for_completion(self):
        self.tasks.join()


def slugify(value):
    # XXX: not good enough
    rv = ' '.join(value.strip().split()).lower()
    words = _slug_re.findall(rv)
    return '-'.join(words)


class Url(object):

    def __init__(self, value):
        self.url = value
        u = url_parse(value)
        i = u.to_iri_tuple()
        self.ascii_url = str(u)
        self.host = i.host
        self.ascii_host = u.ascii_host
        self.port = u.port
        self.path = i.path
        self.query = u.query
        self.anchor = i.fragment
        self.scheme = u.scheme

    def __unicode__(self):
        return self.url

    def __str__(self):
        return self.ascii_url


def is_unsafe_to_delete(path, base):
    a = os.path.abspath(path)
    b = os.path.abspath(base)
    diff = os.path.relpath(a, b)
    first = diff.split(os.path.sep)[0]
    return first in (os.path.curdir, os.path.pardir)


def prune_file_and_folder(name, base):
    if is_unsafe_to_delete(name, base):
        return False
    try:
        os.remove(name)
    except OSError:
        try:
            os.rmdir(name)
        except OSError:
            return False
    head, tail = os.path.split(name)
    if not tail:
        head, tail = os.path.split(head)
    while head and tail:
        try:
            if is_unsafe_to_delete(head, base):
                return False
            os.rmdir(head)
        except OSError:
            break
        head, tail = os.path.split(head)
    return True


def sort_normalize_string(s):
    return unicodedata.normalize('NFD', str(s).lower().strip())


def get_dependent_url(url_path, suffix, ext=None):
    url_directory, url_filename = posixpath.split(url_path)
    url_base, url_ext = posixpath.splitext(url_filename)
    if ext is None:
        ext = url_ext
    return posixpath.join(url_directory, url_base + '@' + suffix + ext)


@contextmanager
def atomic_open(filename, mode='r'):
    if 'r' not in mode:
        fd, tmp_filename = tempfile.mkstemp(
            dir=os.path.dirname(filename), prefix='.__atomic-write')
        os.chmod(tmp_filename, 0o644)
        f = os.fdopen(fd, mode)
    else:
        f = open(filename, mode)
        tmp_filename = None
    try:
        yield f
    except:
        f.close()
        exc_info = sys.exc_info()
        if tmp_filename is not None:
            try:
                os.remove(tmp_filename)
            except OSError:
                pass
        if sys.version_info[0] >= 3:
            raise exc_info[0].with_traceback(exc_info[1], exc_info[2])
        else:
            eval("raise exc_info[0], exc_info[1], exc_info[2]; 1", None, { 'exc_info': exc_info })

    else:
        f.close()
        if tmp_filename is not None:
            rename(tmp_filename, filename)


def portable_popen(cmd, *args, **kwargs):
    """A portable version of subprocess.Popen that automatically locates
    executables before invoking them.  This also looks for executables
    in the bundle bin.
    """
    exe = locate_executable(cmd[0], kwargs.get('cwd'))
    if exe is None:
        raise RuntimeError('Could not locate executable "%s"' % cmd[0])

    if isinstance(exe, str):
        exe = exe.encode(sys.getfilesystemencoding())
    cmd[0] = exe
    return subprocess.Popen(cmd, *args, **kwargs)


def is_valid_id(value):
    if value == '':
        return True
    return (
        '/' not in value and
        value.strip() == value and
        value.split() == [value] and
        not value.startswith('.')
    )


def secure_url(url):
    url = urls.url_parse(url)
    if url.password is not None:
        url = url.replace(netloc='%s@%s' % (
            url.username,
            url.netloc.split('@')[-1],
        ))
    return url.to_url()


def bool_from_string(val, default=None):
    if val in (True, False, 1, 0):
        return bool(val)
    if isinstance(val, basestring):
        val = val.lower()
        if val in ('true', 'yes', '1'):
            return True
        elif val in ('false', 'no', '0'):
            return False
    return default


def make_relative_url(base, target):
    """Returns a relative URL from base to target."""
    if base == '/':
        depth = 0
        prefix = './'
    else:
        depth = ('/' + base.strip('/')).count('/')
        prefix = ''

    ends_in_slash = target[-1:] == '/'
    target = posixpath.normpath(posixpath.join(base, target))
    if ends_in_slash and target[-1:] != '/':
        target += '/'

    return (prefix + '../' * depth).rstrip('/') + target


def get_structure_hash(params):
    """Given a Python structure this generates a hash.  This is useful for
    storing artifact config hashes.  Not all Python types are supported, but
    quite a few are.
    """
    h = hashlib.md5()
    def _hash(obj):
        if obj is None:
            h.update('N;')
        elif obj is True:
            h.update('T;')
        elif obj is False:
            h.update('F;')
        elif isinstance(obj, dict):
            h.update('D%d;' % len(obj))
            for key, value in sorted(obj.items()):
                _hash(key)
                _hash(value)
        elif isinstance(obj, tuple):
            h.update('T%d;' % len(obj))
            for item in obj:
                _hash(item)
        elif isinstance(obj, list):
            h.update('L%d;' % len(obj))
            for item in obj:
                _hash(item)
        elif isinstance(obj, int):
            h.update('T%d;' % obj)
        elif isinstance(obj, bytes):
            h.update('B%d;%s;' % (len(obj), obj))
        elif isinstance(obj, str):
            h.update('S%d;%s;' % (len(obj), obj.encode('utf-8')))
        elif hasattr(obj, '__get_lektor_param_hash__'):
            obj.__get_lektor_param_hash__(h)
    _hash(params)
    return h.hexdigest()


def profile_func(func):
    from cProfile import Profile
    from pstats import Stats

    p = Profile()
    rv = []
    p.runcall(lambda: rv.append(func()))
    p.dump_stats('/tmp/lektor-%s.prof' % func.__name__)

    stats = Stats(p, stream=sys.stderr)
    stats.sort_stats('time', 'calls')
    stats.print_stats()

    return rv[0]


def deg_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return (d, m, sd)


def format_lat_long(lat=None, long=None, secs=True):
    def _format(value, sign):
        d, m, sd = deg_to_dms(value)
        return '%d° %d′ %s%s' % (
            abs(d),
            abs(m),
            secs and ('%d″ ' % abs(sd)) or '',
            sign[d < 0],
        )
    rv = []
    if lat is not None:
        rv.append(_format(lat, 'NS'))
    if int is not None:
        rv.append(_format(int, 'EW'))
    return ', '.join(rv)


def get_app_dir():
    return click.get_app_dir('Lektor')


def get_cache_dir():
    if is_windows:
        folder = os.environ.get('APPDATA')
        if folder is None:
            folder = os.path.expanduser('~')
        return os.path.join(folder, 'Lektor', 'Cache')
    if sys.platform == 'darwin':
        return os.path.join(os.path.expanduser('~/Library/Caches/Lektor'))
    return os.path.join(
        os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')),
        'lektor')
