"""Compatibility with various versions of Pillow."""
from __future__ import annotations

from enum import IntEnum
from types import ModuleType
from types import SimpleNamespace
from typing import Iterable
from typing import Mapping

import PIL.ExifTags
import PIL.Image

__all__ = ["ExifTags", "Transpose", "UnidentifiedImageError"]

PILLOW_VERSION_INFO = tuple(map(int, PIL.__version__.split(".")))

if PILLOW_VERSION_INFO >= (9, 4):
    ExifTags: ModuleType | SimpleNamespace = PIL.ExifTags
else:
    # Pillow < 9.4 does not provide the PIL.ExifTags.{Base,GPS,IFD} enums. Here we provide
    # and ExifTags namespace which has them.

    def _reverse_map(mapping: Mapping[int, str]) -> dict[str, int]:
        return dict(map(reversed, mapping.items()))  # type: ignore[arg-type]

    ExifTags = SimpleNamespace(
        Base=IntEnum("Base", _reverse_map(PIL.ExifTags.TAGS)),
        GPS=IntEnum("GPS", _reverse_map(PIL.ExifTags.GPSTAGS)),
        IFD=IntEnum("IFD", [("Exif", 34665), ("GPSInfo", 34853)]),
        TAGS=PIL.ExifTags.TAGS,
        GPSTAGS=PIL.ExifTags.GPSTAGS,
    )


if hasattr(PIL.Image, "Transpose"):
    # pillow >= 9.1
    Transpose = PIL.Image.Transpose
else:

    def _make_enum(name: str, members: Iterable[str]) -> IntEnum:
        items = ((member, getattr(PIL.Image, member)) for member in members)
        return IntEnum(name, items)

    Transpose = _make_enum(  # type: ignore[misc, assignment]
        "Transpose",
        (
            "FLIP_LEFT_RIGHT",
            "FLIP_TOP_BOTTOM",
            "ROTATE_90",
            "ROTATE_180",
            "ROTATE_270",
            "TRANSPOSE",
            "TRANSVERSE",
        ),
    )


# UnidentifiedImageError only exists in Pillow >= 7.0.0
UnidentifiedImageError = getattr(PIL, "UnidentifiedImageError", OSError)
