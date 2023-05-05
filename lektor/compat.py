from __future__ import annotations

import os
import stat
import sys
import tempfile
import urllib.parse
from functools import partial
from itertools import chain
from typing import Any
from urllib.parse import urlsplit

from werkzeug import urls as werkzeug_urls
from werkzeug.datastructures import MultiDict

__all__ = ["TemporaryDirectory", "importlib_metadata", "werkzeug_urls_URL"]


def _ensure_tree_writeable(path: str) -> None:
    """Attempt to ensure that all files in the tree rooted at path are writeable."""
    dirscans = []

    def fix_mode(path, statfunc):
        try:
            # paranoia regarding symlink attacks
            current_mode = statfunc(follow_symlinks=False).st_mode
            if not stat.S_ISLNK(current_mode):
                isdir = stat.S_ISDIR(current_mode)
                fixed_mode = current_mode | (0o700 if isdir else 0o200)
                if current_mode != fixed_mode:
                    os.chmod(path, fixed_mode)
                if isdir:
                    dirscans.append(os.scandir(path))
        except FileNotFoundError:
            pass

    fix_mode(path, partial(os.stat, path))
    for entry in chain.from_iterable(dirscans):
        fix_mode(entry.path, entry.stat)


class FixedTemporaryDirectory(tempfile.TemporaryDirectory):
    """A version of tempfile.TemporaryDirectory that works if dir contains read-only files.

    On python < 3.8 under Windows, if any read-only files are created
    in a TemporaryDirectory, TemporaryDirectory will throw an
    exception when it tries to remove them on cleanup. See
    https://bugs.python.org/issue26660

    This can create issues, e.g., with temporary git repositories since
    git creates read-only files in its object store.

    """

    def cleanup(self) -> None:
        _ensure_tree_writeable(self.name)
        super().cleanup()


if sys.version_info >= (3, 8):
    TemporaryDirectory = tempfile.TemporaryDirectory
    from importlib import metadata as importlib_metadata
else:
    TemporaryDirectory = FixedTemporaryDirectory
    import importlib_metadata


class _CompatURL(urllib.parse.SplitResult):
    """This is a replacement for ``werkzeug.urls.URL``.

    Here we implement those attributes and methods of ``URL`` which are
    likely to be used by existing Lektor publishing plugins.

    Currently unreimplemented here are the ``encode_netloc``, ``decode_netloc``,
    ``get_file_location``, and ``encode`` methods of ``werkzeug.urls.URL``.

    NB: Use of this class is deprecated. DO NOT USE THIS IN NEW CODE!

    """

    def __str__(self) -> str:
        return self.geturl()

    def replace(self, **kwargs: Any) -> _CompatURL:
        return self._replace(**kwargs)

    @property
    def host(self) -> str | None:
        return self.hostname

    @property
    def ascii_host(self) -> str | None:
        host = self.hostname
        if host is None:
            return None
        try:
            return host.encode("idna").decode("ascii")
        except UnicodeError:
            return host

    @property
    def auth(self) -> str | None:
        auth, _, _ = self.netloc.rpartition("@")
        return auth if auth != "" else None

    @property
    def username(self) -> str | None:
        username = super().username
        if username is None:
            return None
        return _unquote_legacy(username)

    @property
    def raw_username(self) -> str | None:
        return super().username

    @property
    def password(self) -> str | None:
        password = super().password
        if password is None:
            return None
        return _unquote_legacy(password)

    @property
    def raw_password(self) -> str | None:
        return super().password

    def decode_query(
        self,
        charset: str = "utf-8",
        include_empty: bool = True,
        errors: str = "replace",
        # parse_qsl does not support the separator parameter in python < 3.7.10.
        # separator: str = "&",
    ) -> MultiDict:
        return MultiDict(
            urllib.parse.parse_qsl(
                self.query,
                keep_blank_values=include_empty,
                encoding=charset,
                errors=errors,
                # separator=separator,
            )
        )

    def join(
        self, url: str | tuple[str, str, str, str, str], allow_fragments: bool = True
    ) -> _CompatURL:
        if isinstance(url, tuple):
            url = urllib.parse.urlunsplit(url)
        joined = urllib.parse.urljoin(self.geturl(), url, allow_fragments)
        return _CompatURL._make(urlsplit(joined))

    def to_url(self) -> str:
        return self.geturl()

    def to_uri_tuple(self) -> _CompatURL:
        return _CompatURL._make(urlsplit(werkzeug_urls.iri_to_uri(self.geturl())))

    def to_iri_tuple(self) -> _CompatURL:
        return _CompatURL._make(urlsplit(werkzeug_urls.uri_to_iri(self.geturl())))


def _unquote_legacy(value: str) -> str:
    try:
        return urllib.parse.unquote(value, "utf-8", "strict")
    except UnicodeError:
        return urllib.parse.unquote(value, "latin1")


# Provide a replacement for the deprecated werkzeug.urls.URL class
#
# NB: Do not use this in new code!
#
# We only use this in lektor.publishers in order to provide some backward
# compatibility for custom publishers from existing Lektor plugins.
# At such point as we decide that backward-compatibility is no longer
# needed, will be deleted.
#
werkzeug_urls_URL = getattr(werkzeug_urls, "URL", _CompatURL)
