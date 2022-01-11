from typing import NewType
from typing import Union

# Any valid db path.  (This may include a @virtual_path.)
DbPath = NewType("DbPath", str)

# A path to a record.  This does not include a virtual path.
RecordPath = NewType("RecordPath", DbPath)

# A normalized path to a record.
NormalizedPath = NewType("NormalizedPath", RecordPath)

# When a Path contains an '@', the trailing part is the ExtraPath.
# This can be a VirtualPath (path to a VirtualSourceObject)
VirtualPath = NewType("VirtualPath", str)
# Or it can be the page number
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
