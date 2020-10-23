# -*- coding: utf-8 -*-
"""
    lektor._compat
    ~~~~~~~~~~~~~~

    Some py2/py3 compatibility support based on a stripped down
    version of six so we don't have to depend on a specific version
    of it.

    Taken from jinja2/_compat.py
"""
# pylint: disable=unused-import
import queue  # noqa
from io import BytesIO  # noqa
from io import StringIO  # noqa


PY2 = False


range_type = range
text_type = str
string_types = (str,)
integer_types = (int,)

iterkeys = lambda d: iter(d.keys())
itervalues = lambda d: iter(d.values())
iteritems = lambda d: iter(d.items())


def reraise(tp, value, tb=None):
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value
