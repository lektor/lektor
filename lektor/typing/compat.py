import sys

__all__ = ["Literal", "Protocol", "TypeAlias", "TypedDict"]

if sys.version_info >= (3, 8):
    from typing import Literal
    from typing import Protocol
    from typing import TypedDict
else:
    from typing_extensions import Literal
    from typing_extensions import Protocol
    from typing_extensions import TypedDict

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias
