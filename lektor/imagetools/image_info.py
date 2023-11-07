"""Helper to probe basic image information: dimensions and format.
"""
from __future__ import annotations

import enum
import re
import sys
import warnings
from contextlib import contextmanager
from contextlib import ExitStack
from contextlib import suppress
from pathlib import Path
from typing import BinaryIO
from typing import Final
from typing import Generator
from typing import Mapping
from typing import NamedTuple
from typing import TYPE_CHECKING
from typing import Union
from xml.etree import ElementTree as etree

import PIL.Image

from ._compat import ExifTags
from ._compat import UnidentifiedImageError

if TYPE_CHECKING:
    from typing import Literal
    from _typeshed import SupportsRead


if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias


class SvgImageInfo(NamedTuple):
    format: Literal["svg"] = "svg"
    width: float | None = None
    height: float | None = None


class PILImageInfo(NamedTuple):
    format: str
    width: int
    height: int


class UnknownImageInfo(NamedTuple):
    format: None = None
    width: None = None
    height: None = None


ImageInfo: TypeAlias = Union[PILImageInfo, SvgImageInfo, UnknownImageInfo]


class TiffOrientation(enum.IntEnum):
    """The possible values of the "Exif Orientation" tag."""

    TOPLEFT = 1
    TOPRIGHT = 2
    BOTRIGHT = 3
    BOTLEFT = 4
    LEFTTOP = 5
    RIGHTTOP = 6
    RIGHTBOT = 7
    LEFTBOT = 8

    def __init__(self, value: int):
        # True if orientation implies width and height are transposed
        self.is_transposed = value in {5, 6, 7, 8}


def get_image_orientation(image: PIL.Image.Image) -> TiffOrientation:
    """Deduce the orientation of the image.

    Notes
    -----

    Note that browsers only seem to respect the "Exif" Orientation tag for JPEG images
    (and probably TIFF images). In particular, it is `typically ignored`__ by browsers
    when displaying PNG, WEBP and AVIF files (though AVIF files have their own way of
    indicating orientation — the "irot" and "imir" properties — which are respected.)

    __ https://zpl.fi/exif-orientation-in-different-formats/

    Exif information can be stored in PNG files, however the `spec for Exif in PNG`__
    does state that the Exif information should be considered "historical", under the
    assumption that it was probably copied directly from the source image (where it was
    written by, e.g., the camera). It implies that the "unsafe-to-copy" Exif information
    (e.g. orientation, size) should be ignored.

    __ https://ftp-osl.osuosl.org/pub/libpng/documents/proposals/eXIf/png-proposed-eXIf-chunk-2017-06-15.html

    Prior to Lektor 3.4, Lektor's ``get_image_info`` only checked the orientation for
    JPEG images (transposing width↔height when appropriate).  The ``-auto-orient``
    option to ImageMagick's ``convert`` appears to ignore Exif Orientation in PNG files,
    too.

    Finally, note that reading Exif information from PNG files using Pillow is a slow
    operation.  It seems to require loading and decoding the full image.  (Loading Exif
    information from JPEG files does not require decoding the image, so is much
    quicker.)

    For all of these reasons, we only check the Exif Orientation tag for JPEGs.

    """  # pylint: disable=line-too-long # noqa: E501
    if image.format != "JPEG":
        return TiffOrientation.TOPLEFT
    exif = image.getexif()
    try:
        orientation = exif[ExifTags.Base.Orientation]
        return TiffOrientation(orientation)
    except (ValueError, LookupError):
        return TiffOrientation.TOPLEFT


def _parse_svg_units_px(length: str) -> float | None:
    match = re.match(
        r"\d+(?: \.\d* )? (?= (?: \s*px )? \Z)", length.strip(), re.VERBOSE
    )
    if match:
        return float(match.group())
    return None


class BadSvgFile(Exception):
    """Exception raised when SVG file can not be parsed."""


def _get_svg_info(
    source: str | Path | SupportsRead[bytes],
) -> SvgImageInfo | UnknownImageInfo:
    try:
        _, svg = next(etree.iterparse(source, events=["start"]))
    except (etree.ParseError, StopIteration) as exc:
        raise BadSvgFile("can not parse SVG file") from exc
    if svg.tag != "{http://www.w3.org/2000/svg}svg":
        raise BadSvgFile("unknown tag in SVG file")
    width = _parse_svg_units_px(svg.attrib.get("width", ""))
    height = _parse_svg_units_px(svg.attrib.get("height", ""))
    return SvgImageInfo("svg", width, height)


# Mapping from PIL format to Lektor format
_LEKTOR_FORMATS: Final[Mapping[str, str]] = {
    "PNG": "png",
    "GIF": "gif",
    "JPEG": "jpeg",
}


def _PIL_image_info(
    image: PIL.Image.Image,
) -> PILImageInfo | UnknownImageInfo:
    """Determine image format and dimensions for PIL Image"""

    assert image.format is not None
    try:
        lektor_fmt = _LEKTOR_FORMATS[image.format]
    except LookupError:
        return UnknownImageInfo()

    width = image.width
    height = image.height

    orientation = get_image_orientation(image)
    if orientation.is_transposed:
        width, height = height, width

    return PILImageInfo(lektor_fmt, width, height)


@contextmanager
def _save_position(fp: BinaryIO) -> Generator[BinaryIO, None, None]:
    position = fp.tell()
    try:
        yield fp
    finally:
        fp.seek(position)


def get_image_info(source: str | Path | BinaryIO) -> ImageInfo:
    """Determine type and dimensions of an image file."""
    with suppress(UnidentifiedImageError), ExitStack() as stack:
        if not isinstance(source, (str, Path)):
            warnings.warn(
                "Passing a file object to 'get_image_info' is deprecated "
                "since version 3.4.0. Pass a file path instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            stack.enter_context(_save_position(source))

        image = stack.enter_context(PIL.Image.open(source))
        return _PIL_image_info(image)

    with suppress(BadSvgFile), ExitStack() as stack:
        if not isinstance(source, (str, Path)):
            stack.enter_context(_save_position(source))
        return _get_svg_info(source)

    return UnknownImageInfo()
