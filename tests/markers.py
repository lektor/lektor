import pytest
from lektor.imagetools import find_imagemagick


try:
    im_path = find_imagemagick()
except RuntimeError:
    im_path = None


imagemagick = pytest.mark.skipif(
    not im_path,
    reason="imagemagick required but not found",
)
