import sys

__all__ = ["importlib_metadata"]

if sys.version_info >= (3, 8):
    from importlib import metadata as importlib_metadata
else:
    import importlib_metadata
