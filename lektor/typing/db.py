"""
****************************************
The various kinds of DB paths and pieces
****************************************

DbPathComp
==========

An allowed component of a NormalizedPath to a db record.


VirtualPathComp
===============

An allowed component of a NormalizedPath to a db record.


DbPath
======

This is a valid first argument to Pad.get().

This is interpreted as an absolute path.  Nominally, it should start with
a leading "/", but one will be assumed if it is omitted.

Roughly the valid forms are:

    RecordPath
    RecordPath "@" NonNormalizedVirtualPath

Note that page numbers are never included in a DbPath.


RecordPath
==========

This is a DbPath that does not include an "@".  That means there is no virtual path.

Note that this may include "." and ".." in its path segments.
E.g. "/path/../whoops" is an allowed value and is equivalenet to
"/whoops".

NormalizedPath
==============

This is the normalized version of a RecordPath.  It always starts with
a "/" and does not contain any "." or ".." path segments.

This is the type of Attachment.path (since attachments do not have page numbers.)

    "/" [ DbPathComp [ "/" DbPathComp ]* ]

VirtualPath
===========

The normalized virtual path.

    VPathComp [ "/" VPathComp ]*

DbSourcePath
============

Very much like a DbPath, expect, fully normalized.

    NormalizedPath [ "@" VirtualPath ]

Never includes a page number

PaginatedPath
=============

Encodes the page number (if non-None) after an "@", e.g. "/blog@2" for
the second page of the blog.  Note that the page number is not a
VirtualPath, and a PaginatedPath, therefore, is not a
DbPath. (Pad.get("/blog@2") does not work.  Rather, you must use
Pad.get("/blog", page_num=2) for that.)

    NormalizedPath "@" <page_num>

RelativeDbPath
==============

A relative version of DbPath.  The rules for joining a RelativeDbPath
to an (absolute) DbPath are a bit strange, owing to the possibility of
virtual paths, etc.  See lektor.utils.join_path.


"""
from typing import NewType
from typing import Sequence
from typing import Union

from lektor.typing.compat import TypeAlias

DbPathComp = NewType("DbPathComp", str)
VPathComp = NewType("VPathComp", str)

VPathParts: TypeAlias = Sequence[VPathComp]

DbPath = NewType("DbPath", str)

# A path to a record.  This does not include a virtual path.
RecordPath = NewType("RecordPath", DbPath)

DbSourcePath = NewType("DbSourcePath", DbPath)

# A normalized path to a record.
# FIXME: a NormalizedPath is also a RecordPath
NormalizedPath = NewType("NormalizedPath", DbSourcePath)

PaginatedPath = NewType("PaginatedPath", str)

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
