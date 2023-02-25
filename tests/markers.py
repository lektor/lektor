import pytest

try:
    import PIL
except ModuleNotFoundError:
    PIL = None


# FIXME: rename
imagemagick = pytest.mark.skipif(
    PIL is None,
    reason="Pillow required but not found",
)
