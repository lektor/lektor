import sys

__all__ = ["importlib_metadata"]

if sys.version_info >= (3, 10):
    from importlib import metadata as importlib_metadata
else:
    # we use importlib.metadata.packages_distributions() which is new in python 3.10
    import importlib_metadata
