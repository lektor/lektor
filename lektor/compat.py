from __future__ import annotations

import importlib.metadata
import tempfile
import urllib.parse
from typing import Any
from urllib.parse import urlsplit
from warnings import warn

from werkzeug import urls as werkzeug_urls
from werkzeug.datastructures import MultiDict

from lektor.utils import DeprecatedWarning

__all__ = ["werkzeug_urls_URL"]


_DEPRECATED_ATTRS = {
    "TemporaryDirectory": tempfile.TemporaryDirectory,
    "importlib_metadata": importlib.metadata,
}


def __getattr__(name):
    try:
        value = _DEPRECATED_ATTRS.get(name)
    except KeyError:
        # pylint: disable=raise-missing-from
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    if hasattr(value, "__module__"):
        replacement = f"{value.__module__}.{value.__name__}"
    else:
        replacement = f"{value.__name__}"
    warn(
        DeprecatedWarning(
            name=f"lektor.compat.{name}",
            reason=f"use {replacement} instead",
            version="3.4.0",
        ),
        stacklevel=2,
    )
    return value


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
