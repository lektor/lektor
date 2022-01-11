import sys
from collections import defaultdict
from typing import Any
from typing import TYPE_CHECKING

__all__ = ["Literal"]

if TYPE_CHECKING or sys.version_info >= (3, 8):
    from typing import Literal
else:
    # We are running under a python which is old enough to not have
    # typing.Literal.  Since we are not type-checking, we only need a
    # version good enough to not cause run-time errors.
    Literal = defaultdict(lambda: Any)
