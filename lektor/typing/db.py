"""****************************************
The various kinds of DB paths and pieces
****************************************

RecordPathPart
==============

An allowed component of a RecordPath to a db record.


VirtualPathPart
===============

An allowed component of a RecordPath to a db record.


UnsafeDbPath
============

FIXME: UnsafeDbPath and UnsafeRecordPath should probably be gotten rid
of.  Just use str for unparsed values.

This is a valid first argument to Pad.get().

This is interpreted as an absolute path.  Nominally, it should start with
a leading "/", but one will be assumed if it is omitted.

Roughly the valid forms are:

    UnsafeRecordPath
    UnsafeRecordPath "@" NonNormalizedVirtualPath

Note that page numbers are never included in a UnsafeDbPath.


UnsafeRecordPath
================


This is a UnsafeDbPath that does not include an "@".  That means there is no virtual path.

Note that this may include "." and ".." in its path segments.
E.g. "/path/../whoops" is an allowed value and is equivalenet to
"/whoops".

RecordPath
==========

This is the normalized version of a UnsafeRecordPath.  It always starts with
a "/" and does not contain any "." or ".." path segments.

This is the type of Attachment.path (since attachments do not have page numbers.)

    "/" [ RecordPathPart [ "/" RecordPathPart ]* ]

VirtualPath
===========

The normalized virtual path.

    VirtualPathPart [ "/" VirtualPathPart ]*

DbPath
======

Very much like a UnsafeDbPath, expect, fully normalized.

    RecordPath [ "@" VirtualPath ]

Never includes a page number

PaginatedPath
=============

Encodes the page number (if non-None) after an "@", e.g. "/blog@2" for
the second page of the blog.  Note that the page number is not a
VirtualPath, and a PaginatedPath, therefore, is not a
UnsafeDbPath. (Pad.get("/blog@2") does not work.  Rather, you must use
Pad.get("/blog", page_num=2) for that.)

    RecordPath "@" <page_num>

UnsafeRelativeDbPath
====================

FIXME: just use str

A relative version of UnsafeDbPath.  The rules for joining an UnsafeRelativeDbPath
to an (absolute) UnsafeDbPath are a bit strange, owing to the possibility of
virtual paths, etc.  See lektor.utils.join_path.

"""
from typing import NewType
from typing import Sequence
from typing import Union

from lektor.typing.compat import TypeAlias

RecordPathPart = NewType("RecordPathPart", str)
VirtualPathPart = NewType("VirtualPathPart", str)

VPathParts: TypeAlias = Sequence[VirtualPathPart]

UnsafeDbPath = NewType("UnsafeDbPath", str)

# A path to a record.  This does not include a virtual path.
UnsafeRecordPath = NewType("UnsafeRecordPath", UnsafeDbPath)

DbPath = NewType("DbPath", UnsafeDbPath)

# A normalized path to a record.
# FIXME: a RecordPath is also a UnsafeRecordPath
RecordPath = NewType("RecordPath", DbPath)

PaginatedPath = NewType("PaginatedPath", str)

# FIXME: this needs refactored. Do away with ExtraPath
# When a Path contains an '@', the trailing part is the ExtraPath.
# This can be a VirtualPath (path to a VirtualSourceObject)
VirtualPath = NewType("VirtualPath", str)
# Or it can be the page number # FIXME: get rid of these?
PageNumberPath = NewType("PageNumberPath", str)
ExtraPath = Union[VirtualPath, PageNumberPath]

# A ConcreteAlt is one of the alts configured for the site.
#
# If alternatives are not configured, this is Literal[PRIMARY_ALT].
#
# If alternatives are in use, this is something like: Literal["en",
# "de"].  Note that "_primary" (PRIMARY_ALT) is not included. When
# alternatives are configured, no artifact is generated for
# alt="_primary" — rather, that record is used as fallback data to
# fill in missing bits for each concrete alt.
Alt = NewType("Alt", str)
ConcreteAlt = NewType("ConcreteAlt", Alt)


# URLs
"""
UrlPath: str
============

URL relative to the project base_path.  This is the type of SourceObject.url_path.

It should always start with a "/".


UrlParts: Sequence[str]
=======================

A sequence of URL path segments.  Should be normalized. E.g. no ".", "..".

"""
UrlPath = NewType("UrlPath", str)
UrlParts: TypeAlias = Sequence[str]


# Source Filenames
"""
SourceFilename
==============

Absolute path to a source file.  (Starts with a "/")

ArtifactName
============

Name of artifact file, relative to the output directory.  Starts with a "/".
"""
SourceFilename = NewType("SourceFilename", str)
ArtifactName = NewType("ArtifactName", str)
