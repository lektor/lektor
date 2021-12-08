# -*- coding: utf-8 -*-
"""
    lektor._compat
    ~~~~~~~~~~~~~~

    Some py2/py3 compatibility support based on a stripped down
    version of six so we don't have to depend on a specific version
    of it.

    Taken from jinja2/_compat.py
"""
# pylint: disable=invalid-name, import-error, unused-import, undefined-variable, reimported
import sys


PY2 = sys.version_info[0] == 2
_identity = lambda x: x


if PY2:
    unichr = unichr  # pylint: disable=self-assigning-variable  # noqa
    text_type = unicode  # noqa
    range_type = xrange  # noqa
    string_types = (str, unicode)  # noqa
    integer_types = (int, long)  # noqa

    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()

    from cStringIO import StringIO as BytesIO, StringIO
    import Queue as queue  # noqa

    NativeStringIO = BytesIO

    exec(  # pylint: disable=exec-used
        "def reraise(tp, value, tb=None):\n raise tp, value, tb"
    )

    from werkzeug.posixemulation import rename as os_replace  # noqa


else:
    unichr = chr
    range_type = range
    text_type = str
    string_types = (str,)
    integer_types = (int,)

    iterkeys = lambda d: iter(d.keys())
    itervalues = lambda d: iter(d.values())
    iteritems = lambda d: iter(d.items())

    from io import BytesIO, StringIO
    import queue  # noqa

    NativeStringIO = StringIO

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    from os import replace as os_replace  # noqa


def python_2_unicode_compatible(klass):
    """
    A decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.
    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.
    """
    if PY2:
        if "__str__" not in klass.__dict__:
            raise ValueError(
                "@python_2_unicode_compatible cannot be applied "
                "to %s because it doesn't define __str__()." % klass.__name__
            )
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode("utf-8")
    return klass
