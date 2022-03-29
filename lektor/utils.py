# -*- coding: utf-8 -*-
import codecs
import hashlib
import json
import multiprocessing
import os
import posixpath
import re
import subprocess
import sys
import tempfile
import traceback
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from pathlib import PurePosixPath
from queue import Queue
from threading import Thread

import click
from jinja2 import is_undefined
from markupsafe import Markup
from slugify import slugify as _slugify
from werkzeug import urls
from werkzeug.http import http_date
from werkzeug.urls import url_parse


is_windows = os.name == "nt"

_slash_escape = "\\/" not in json.dumps("/")

_slashes_re = re.compile(r"(/\.{1,2}(/|$))|/")
_last_num_re = re.compile(r"^(.*)(\d+)(.*?)$")
_list_marker = object()
_value_marker = object()

# Figure out our fs encoding, if it's ascii we upgrade to utf-8
fs_enc = sys.getfilesystemencoding()
try:
    if codecs.lookup(fs_enc).name == "ascii":
        fs_enc = "utf-8"
except LookupError:
    pass


def split_virtual_path(path):
    if "@" in path:
        return path.split("@", 1)
    return path, None


def _norm_join(a, b):
    return posixpath.normpath(posixpath.join(a, b))


def join_path(a, b):
    a_p, a_v = split_virtual_path(a)
    b_p, b_v = split_virtual_path(b)

    # Special case: paginations are considered special virtual paths
    # where the parent is the actual parent of the page.  This however
    # is explicitly not done if the path we join with refers to the
    # current path (empty string or dot).
    if b_p not in ("", ".") and a_v and a_v.isdigit():
        a_v = None

    # New path has a virtual path, add that to it.
    if b_v:
        rv = _norm_join(a_p, b_p) + "@" + b_v
    elif a_v:
        rv = a_p + "@" + _norm_join(a_v, b_p)
    else:
        rv = _norm_join(a_p, b_p)
    if rv[-2:] == "@.":
        rv = rv[:-2]
    return rv


def cleanup_path(path):
    return "/" + _slashes_re.sub("/", path).strip("/")


def parse_path(path):
    x = cleanup_path(path).strip("/").split("/")
    if x == [""]:
        return []
    return x


def is_path_child_of(a, b, strict=True):
    a_p, a_v = split_virtual_path(a)
    b_p, b_v = split_virtual_path(b)
    a_p = parse_path(a_p)
    b_p = parse_path(b_p)
    a_v = parse_path(a_v or "")
    b_v = parse_path(b_v or "")

    if not strict and a_p == b_p and a_v == b_v:
        return True
    if not a_v and b_v:
        return False
    if a_p == b_p and a_v[: len(b_v)] == b_v and len(a_v) > len(b_v):
        return True
    return a_p[: len(b_p)] == b_p and len(a_p) > len(b_p)


def untrusted_to_os_path(path):
    path = path.strip("/").replace("/", os.path.sep)
    if not isinstance(path, str):
        path = path.decode(fs_enc, "replace")
    return path


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
        if not ext or ext.split() != [ext] or ext.strip() != ext:
            return True
        return False

    parts = filename.rsplit(".", 2)
    if len(parts) == 1:
        return parts[0], ""
    if len(parts) == 2 and not parts[0]:
        return "." + parts[1], ""
    if len(parts) == 3 and len(parts[1]) < 5:
        ext = ".".join(parts[1:])
        if not bad_ext(ext):
            return parts[0], ext
    ext = parts[-1]
    if bad_ext(ext):
        return filename, ""
    basename = ".".join(parts[:-1])
    return basename, ext


def iter_dotted_path_prefixes(dotted_path):
    pieces = dotted_path.split(".")
    if len(pieces) == 1:
        yield dotted_path, None
    else:
        for x in range(1, len(pieces)):
            yield ".".join(pieces[:x]), ".".join(pieces[x:])


def resolve_dotted_value(obj, dotted_path):
    node = obj
    for key in dotted_path.split("."):
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
        result = name.split(".")
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
                values.extend(_convert(x[1]) for x in sorted(container.items()))
            if not force_list and len(values) == 1:
                values = values[0]

            if not container:
                return values
            return _convert(container)
        if container.pop(_list_marker, False):
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


def slugify(text):
    """
    A wrapper around python-slugify which preserves file extensions
    and forward slashes.
    """

    parts = text.split("/")
    parts[-1], ext = magic_split_ext(parts[-1])

    out = "/".join(_slugify(part) for part in parts)

    if ext:
        return out + "." + ext
    return out


def secure_filename(filename, fallback_name="file"):
    base = filename.replace("/", " ").replace("\\", " ")
    basename, ext = magic_split_ext(base)
    rv = slugify(basename).lstrip(".")
    if not rv:
        rv = fallback_name
    if ext:
        return rv + "." + ext
    return rv


def increment_filename(filename):
    directory, filename = os.path.split(filename)
    basename, ext = magic_split_ext(filename, ext_check=False)

    match = _last_num_re.match(basename)
    if match is not None:
        rv = match.group(1) + str(int(match.group(2)) + 1) + match.group(3)
    else:
        rv = basename + "2"

    if ext:
        rv += "." + ext
    if directory:
        return os.path.join(directory, rv)
    return rv


@lru_cache(maxsize=None)
def locate_executable(exe_file, cwd=None, include_bundle_path=True):
    """Locates an executable in the search path."""
    choices = [exe_file]
    resolve = True

    # If it's already a path, we don't resolve.
    if os.path.sep in exe_file or (os.path.altsep and os.path.altsep in exe_file):
        resolve = False

    extensions = os.environ.get("PATHEXT", "").split(";")
    _, ext = os.path.splitext(exe_file)
    if (
        os.name != "nt"
        and "" not in extensions
        or any(ext.lower() == extension.lower() for extension in extensions)
    ):
        extensions.insert(0, "")

    if resolve:
        paths = os.environ.get("PATH", "").split(os.pathsep)
        choices = [os.path.join(path, exe_file) for path in paths]

    if os.name == "nt":
        choices.append(os.path.join((cwd or os.getcwd()), exe_file))

    try:
        for path in choices:
            for ext in extensions:
                if os.access(path + ext, os.X_OK):
                    return path + ext
        return None
    except OSError:
        return None


class JSONEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if is_undefined(o):
            return None
        if isinstance(o, datetime):
            return http_date(o)
        if isinstance(o, uuid.UUID):
            return str(o)
        if hasattr(o, "__html__"):
            return str(o.__html__())
        return json.JSONEncoder.default(self, o)


def htmlsafe_json_dump(obj, **kwargs):
    kwargs.setdefault("cls", JSONEncoder)
    rv = (
        json.dumps(obj, **kwargs)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("'", "\\u0027")
    )
    if not _slash_escape:
        rv = rv.replace("\\/", "/")
    return rv


def tojson_filter(obj, **kwargs):
    return Markup(htmlsafe_json_dump(obj, **kwargs))


def safe_call(func, args=None, kwargs=None):
    try:
        return func(*(args or ()), **(kwargs or {}))
    except Exception:
        # XXX: logging
        traceback.print_exc()
        return None


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


class WorkerPool:
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


class Url:
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
    return unicodedata.normalize("NFD", str(s).lower().strip())


def get_dependent_url(url_path, suffix, ext=None):
    url_directory, url_filename = posixpath.split(url_path)
    url_base, url_ext = posixpath.splitext(url_filename)
    if ext is None:
        ext = url_ext
    return posixpath.join(url_directory, url_base + "@" + suffix + ext)


@contextmanager
def atomic_open(filename, mode="r", encoding=None):
    if "r" not in mode:
        fd, tmp_filename = tempfile.mkstemp(
            dir=os.path.dirname(filename), prefix=".__atomic-write"
        )
        os.chmod(tmp_filename, 0o644)
        f = os.fdopen(fd, mode)
    else:
        f = open(filename, mode=mode, encoding=encoding)
        tmp_filename = None
    try:
        yield f
    except Exception as e:
        f.close()
        _exc_type, exc_value, tb = sys.exc_info()
        if tmp_filename is not None:
            try:
                os.remove(tmp_filename)
            except OSError:
                pass

        if exc_value.__traceback__ is not tb:
            raise exc_value.with_traceback(tb) from e
        raise exc_value from e
    else:
        f.close()
        if tmp_filename is not None:
            os.replace(tmp_filename, filename)


def portable_popen(cmd, *args, **kwargs):
    """A portable version of subprocess.Popen that automatically locates
    executables before invoking them.  This also looks for executables
    in the bundle bin.
    """
    if cmd[0] is None:
        raise RuntimeError("No executable specified")
    exe = locate_executable(cmd[0], kwargs.get("cwd"))
    if exe is None:
        raise RuntimeError('Could not locate executable "%s"' % cmd[0])

    if isinstance(exe, str) and sys.platform != "win32":
        exe = exe.encode(sys.getfilesystemencoding())
    cmd[0] = exe
    return subprocess.Popen(cmd, *args, **kwargs)


def is_valid_id(value):
    if value == "":
        return True
    return (
        "/" not in value
        and value.strip() == value
        and value.split() == [value]
        and not value.startswith(".")
    )


def secure_url(url):
    url = urls.url_parse(url)
    if url.password is not None:
        url = url.replace(
            netloc="%s@%s"
            % (
                url.username,
                url.netloc.split("@")[-1],
            )
        )
    return url.to_url()


def bool_from_string(val, default=None):
    if val in (True, False, 1, 0):
        return bool(val)
    if isinstance(val, str):
        val = val.lower()
        if val in ("true", "yes", "1"):
            return True
        if val in ("false", "no", "0"):
            return False
    return default


def make_relative_url(source, target):
    """
    Returns the relative path (url) needed to navigate
    from `source` to `target`.
    """

    # WARNING: this logic makes some unwarranted assumptions about
    # what is a directory and what isn't. Ideally, this function
    # would be aware of the actual filesystem.
    s_is_dir = source.endswith("/")
    t_is_dir = target.endswith("/")

    source = PurePosixPath(posixpath.normpath(source))
    target = PurePosixPath(posixpath.normpath(target))

    if not s_is_dir:
        source = source.parent

    relpath = str(get_relative_path(source, target))
    if t_is_dir:
        relpath += "/"

    return relpath


def get_relative_path(source, target):
    """
    Returns the relative path needed to navigate from `source` to `target`.

    get_relative_path(source: PurePosixPath,
                      target: PurePosixPath) -> PurePosixPath
    """

    if not source.is_absolute() and target.is_absolute():
        raise ValueError("Cannot navigate from a relative path" " to an absolute one")

    if source.is_absolute() and not target.is_absolute():
        # nothing to do
        return target

    if source.is_absolute() and target.is_absolute():
        # convert them to relative paths to simplify the logic
        source = source.relative_to("/")
        target = target.relative_to("/")

    # is the source an ancestor of the target?
    try:
        return target.relative_to(source)
    except ValueError:
        pass

    # even if it isn't, one of the source's ancestors might be
    # (and if not, the root will be the common ancestor)
    distance = PurePosixPath(".")
    for ancestor in source.parents:
        distance /= ".."

        try:
            relpath = target.relative_to(ancestor)
        except ValueError:
            continue
        else:
            # prepend the distance to the common ancestor
            return distance / relpath
    # We should never get here.  (The last ancestor in source.parents will
    # be '.' — target.relative_to('.') will always succeed.)
    raise AssertionError("This should not happen")


def get_structure_hash(params):
    """Given a Python structure this generates a hash.  This is useful for
    storing artifact config hashes.  Not all Python types are supported, but
    quite a few are.
    """
    h = hashlib.md5()

    def _hash(obj):
        if obj is None:
            h.update("N;")
        elif obj is True:
            h.update("T;")
        elif obj is False:
            h.update("F;")
        elif isinstance(obj, dict):
            h.update("D%d;" % len(obj))
            for key, value in sorted(obj.items()):
                _hash(key)
                _hash(value)
        elif isinstance(obj, tuple):
            h.update("T%d;" % len(obj))
            for item in obj:
                _hash(item)
        elif isinstance(obj, list):
            h.update("L%d;" % len(obj))
            for item in obj:
                _hash(item)
        elif isinstance(obj, int):
            h.update("T%d;" % obj)
        elif isinstance(obj, bytes):
            h.update("B%d;%s;" % (len(obj), obj))
        elif isinstance(obj, str):
            h.update("S%d;%s;" % (len(obj), obj.encode("utf-8")))
        elif hasattr(obj, "__get_lektor_param_hash__"):
            obj.__get_lektor_param_hash__(h)

    _hash(params)
    return h.hexdigest()


def profile_func(func):
    # pylint: disable=import-outside-toplevel

    from cProfile import Profile
    from pstats import Stats

    p = Profile()
    rv = []
    p.runcall(lambda: rv.append(func()))
    p.dump_stats("/tmp/lektor-%s.prof" % func.__name__)

    stats = Stats(p, stream=sys.stderr)
    stats.sort_stats("time", "calls")
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
        return "%d° %d′ %s%s" % (
            abs(d),
            abs(m),
            secs and ("%d″ " % abs(sd)) or "",
            sign[d < 0],
        )

    rv = []
    if lat is not None:
        rv.append(_format(lat, "NS"))
    if long is not None:
        rv.append(_format(long, "EW"))
    return ", ".join(rv)


def get_app_dir():
    return click.get_app_dir("Lektor")


def get_cache_dir():
    if is_windows:
        folder = os.environ.get("LOCALAPPDATA")
        if folder is None:
            folder = os.environ.get("APPDATA")
            if folder is None:
                folder = os.path.expanduser("~")
        return os.path.join(folder, "Lektor", "Cache")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~/Library/Caches/Lektor"))
    return os.path.join(
        os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "lektor"
    )


class URLBuilder:
    def __init__(self):
        self.items = []

    def append(self, item):
        if item is None:
            return
        item = str(item).strip("/")
        if item:
            self.items.append(item)

    def get_url(self, trailing_slash=None):
        url = "/" + "/".join(self.items)
        if trailing_slash is not None and not trailing_slash:
            return url
        if url == "/":
            return url
        if trailing_slash is None:
            _, last = url.split("/", 1)
            if "." in last:
                return url
        return url + "/"


def build_url(iterable, trailing_slash=None):
    builder = URLBuilder()
    for item in iterable:
        builder.append(item)
    return builder.get_url(trailing_slash=trailing_slash)


def comma_delimited(s):
    """Split a comma-delimited string."""
    for part in s.split(","):
        stripped = part.strip()
        if stripped:
            yield stripped


def process_extra_flags(flags):
    if isinstance(flags, dict):
        return flags
    rv = {}
    for flag in flags or ():
        if ":" in flag:
            k, v = flag.split(":", 1)
            rv[k] = v
        else:
            rv[flag] = flag
    return rv
