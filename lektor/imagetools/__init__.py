from __future__ import annotations

from pathlib import Path

from ..utils import deprecated
from .exif import read_exif
from .image_info import get_image_info
from .thumbnail import compute_dimensions
from .thumbnail import make_image_thumbnail
from .thumbnail import Thumbnail
from .thumbnail import ThumbnailMode

__all__ = [
    "compute_dimensions",
    "get_image_info",
    "get_quality",
    "make_image_thumbnail",
    "read_exif",
    "Thumbnail",
    "ThumbnailMode",
]


@deprecated(version="3.4.0")
def get_quality(source_filename: str | Path) -> int:
    """Get the effective default thumbnail _quality_.

    This is the ImageMagick "quality" that is used, by default, when generating
    thumbnails.

    """
    if get_image_info(source_filename).format == "png":
        return 75
    return 85
