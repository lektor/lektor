from __future__ import annotations

import dataclasses
import io
import math
import numbers
import posixpath
import re
import sys
import warnings
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from enum import IntEnum
from fractions import Fraction
from functools import partial
from functools import wraps
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
from typing import Any
from typing import BinaryIO
from typing import Callable
from typing import ClassVar
from typing import Generator
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import NamedTuple
from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING
from typing import TypeVar
from typing import Union
from xml.etree import ElementTree as etree

import PIL.ExifTags
import PIL.Image
import PIL.ImageCms
import PIL.ImageOps

from lektor.utils import deprecated
from lektor.utils import get_dependent_url

if TYPE_CHECKING:
    from typing import Literal
    from _typeshed import SupportsRead
    from lektor.builder import Artifact
    from lektor.context import Context

if sys.version_info >= (3, 8):
    from typing import Final
else:
    from typing_extensions import Final

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias


PILLOW_VERSION_INFO = tuple(map(int, PIL.__version__.split(".")))

if PILLOW_VERSION_INFO >= (9, 4):
    ExifTags: ModuleType | SimpleNamespace = PIL.ExifTags
else:

    def _reverse_map(mapping: Mapping[int, str]) -> dict[str, int]:
        return dict(map(reversed, mapping.items()))  # type: ignore[arg-type]

    ExifTags = SimpleNamespace(
        Base=IntEnum("Base", _reverse_map(PIL.ExifTags.TAGS)),
        GPS=IntEnum("GPS", _reverse_map(PIL.ExifTags.GPSTAGS)),
        IFD=IntEnum("IFD", [("Exif", 34665), ("GPSInfo", 34853)]),
        TAGS=PIL.ExifTags.TAGS,
        GPSTAGS=PIL.ExifTags.GPSTAGS,
    )


UnidentifiedImageError = getattr(PIL, "UnidentifiedImageError", OSError)


class TiffOrientation(IntEnum):
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


class ThumbnailMode(Enum):
    FIT = "fit"
    CROP = "crop"
    STRETCH = "stretch"

    DEFAULT = "fit"

    @property
    @deprecated("Use ThumbnailMode.value instead", version="3.3.0")
    def label(self) -> str:
        """The mode's label as used in templates."""
        assert isinstance(self.value, str)
        return self.value

    @classmethod
    @deprecated(
        "Use the ThumbnailMode constructor, e.g. 'ThumbnailMode(label)', instead",
        version="3.3.0",
    )
    def from_label(cls, label: str) -> ThumbnailMode:
        """Looks up the thumbnail mode by its textual representation."""
        return cls(label)


def _combine_make(make: str | None, model: str | None) -> str:
    make = make or ""
    model = model or ""
    if make and model.startswith(make):
        return model
    return " ".join([make, model]).strip()


# Interpretation of the Exif Flash tag value
#
# See: https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif/flash.html
#
# Code copied from
# https://github.com/ianare/exif-py/blob/51d5c5adf638219632dd755c6b7a4ce2535ada62/exifread/tags/exif.py#L318-L341
#
_EXIF_FLASH_VALUES = {
    0: "Flash did not fire",
    1: "Flash fired",
    5: "Strobe return light not detected",
    7: "Strobe return light detected",
    9: "Flash fired, compulsory flash mode",
    13: "Flash fired, compulsory flash mode, return light not detected",
    15: "Flash fired, compulsory flash mode, return light detected",
    16: "Flash did not fire, compulsory flash mode",
    24: "Flash did not fire, auto mode",
    25: "Flash fired, auto mode",
    29: "Flash fired, auto mode, return light not detected",
    31: "Flash fired, auto mode, return light detected",
    32: "No flash function",
    65: "Flash fired, red-eye reduction mode",
    69: "Flash fired, red-eye reduction mode, return light not detected",
    71: "Flash fired, red-eye reduction mode, return light detected",
    73: "Flash fired, compulsory flash mode, red-eye reduction mode",
    77: (
        "Flash fired, compulsory flash mode, red-eye reduction mode, "
        "return light not detected"
    ),
    79: (
        "Flash fired, compulsory flash mode, red-eye reduction mode, "
        "return light detected"
    ),
    89: "Flash fired, auto mode, red-eye reduction mode",
    93: "Flash fired, auto mode, return light not detected, red-eye reduction mode",
    95: "Flash fired, auto mode, return light detected, red-eye reduction mode",
}


def _to_flash_description(value: int) -> str:
    desc = _EXIF_FLASH_VALUES.get(value)
    if desc is None:
        desc = f"{_EXIF_FLASH_VALUES[int(value) & 1]} ({value})"
    return desc


def _to_string(value: str) -> str:
    # XXX: By spec, strings in EXIF tags are in ASCII, however some tools
    # that handle EXIF tags support UTF-8.
    # PIL seems to return strings decoded as iso-8859-1, which is rarely, if ever,
    # right.  Attempt re-decoding as UTF-8.
    if not isinstance(value, str):
        raise ValueError(f"Value {value!r} is not a string")
    try:
        return value.encode("iso-8859-1").decode("utf-8")
    except UnicodeDecodeError:
        return value


# NB: Older versions of Pillow return (numerator, denominator) tuples
# for EXIF rational numbers.  New versions return a Fraction instance.
ExifRational: TypeAlias = Union[numbers.Rational, Tuple[int, int]]
ExifReal: TypeAlias = Union[numbers.Real, Tuple[int, int]]


def _to_rational(value: ExifRational) -> numbers.Rational:
    # NB: Older versions of Pillow return (numerator, denominator) tuples
    # for EXIF rational numbers.  New versions return a Fraction instance.
    if isinstance(value, numbers.Rational):
        return value
    if isinstance(value, tuple) and len(value) == 2:
        return Fraction(*value)
    raise ValueError(f"Can not convert {value!r} to Rational")


def _to_float(value: ExifReal) -> float:
    if not isinstance(value, numbers.Real):
        value = _to_rational(value)
    return float(value)


def _to_focal_length(value: ExifReal) -> str:
    return f"{_to_float(value):g}mm"


def _to_degrees(
    coords: tuple[ExifReal, ExifReal, ExifReal], hemisphere: Literal["E", "W", "N", "S"]
) -> float:
    degrees, minutes, seconds = map(_to_float, coords)
    degrees = degrees + minutes / 60 + seconds / 3600
    if hemisphere in {"S", "W"}:
        degrees = -degrees
    return degrees


def _to_altitude(altitude: ExifReal, altitude_ref: Literal[b"\x00", b"\x01"]) -> float:
    value = _to_float(altitude)
    if altitude_ref == b"\x01":
        value = -value
    return value


_T = TypeVar("_T")


def _default_none(wrapped: Callable[[EXIFInfo], _T]) -> Callable[[EXIFInfo], _T | None]:
    """Return ``None`` if wrapped getter raises a ``LookupError``.

    This is a decorator intended for use on property getters for the EXIFInfo class.

    If the wrapped getter raises a ``LookupError`` (as might happen if it tries to
    access a non-existent value in one of the EXIF tables, the wrapper will return
    ``None`` rather than propagating the exception.

    """

    @wraps(wrapped)
    def wrapper(self: EXIFInfo) -> _T | None:
        try:
            return wrapped(self)
        except LookupError:
            return None

    return wrapper


class EXIFInfo:
    """Adapt Exif tags to more user-friendly values.

    This is an adapter that wraps a ``PIL.Image.Exif`` instance to make access to certain
    Exif tags more user-friendly.

    """

    def __init__(self, exif: PIL.Image.Exif):
        self._exif = exif

    def __bool__(self) -> bool:
        """True if any Exif data exists."""
        return bool(self._exif)

    def to_dict(self) -> dict[str, str | float | tuple[float, float] | None]:
        """Return a dict containing the values of all known Exif tags."""
        rv = {}
        for key, value in self.__class__.__dict__.items():
            if key[:1] != "_" and isinstance(value, property):
                rv[key] = getattr(self, key)
        return rv

    @property
    def _ifd0(self) -> Mapping[int, Any]:
        """The main "Image File Directory" (IFD0).

        This mapping contains the basic Exif tags applying to the main image.  Keys are
        the Exif tag number, values are typing strings, ints, floats, or rationals.

        References
        ----------

        - https://www.media.mit.edu/pia/Research/deepview/exif.html#ExifTags
        - https://www.awaresystems.be/imaging/tiff/tifftags/baseline.html

        """
        return self._exif

    @property
    def _exif_ifd(self) -> Mapping[int, Any]:
        """The Exif SubIFD.

        - https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif.html
        """
        return self._exif.get_ifd(ExifTags.IFD.Exif)  # type: ignore[no-any-return]

    @property
    def _gpsinfo_ifd(self) -> Mapping[int, Any]:
        """The GPS IFD

        - https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/gps.html
        """
        # On older Pillow versions, get_ifd(GPSinfo) returns None.
        # Prior to somewhere around Pillow 8.2.0, the GPS IFD was accessible at
        # the top level. Try that first.
        #
        # https://pillow.readthedocs.io/en/stable/releasenotes/8.2.0.html#image-getexif-exif-and-gps-ifd
        gps_ifd = self._exif.get(ExifTags.IFD.GPSInfo)
        if isinstance(gps_ifd, dict):
            return gps_ifd
        return self._exif.get_ifd(ExifTags.IFD.GPSInfo)  # type: ignore[no-any-return]

    @property
    @_default_none
    def artist(self) -> str:
        return _to_string(self._ifd0[ExifTags.Base.Artist])

    @property
    @_default_none
    def copyright(self) -> str:
        return _to_string(self._ifd0[ExifTags.Base.Copyright])

    @property
    @_default_none
    def camera_make(self) -> str:
        return _to_string(self._ifd0[ExifTags.Base.Make])

    @property
    @_default_none
    def camera_model(self) -> str:
        return _to_string(self._ifd0[ExifTags.Base.Model])

    @property
    def camera(self) -> str:
        return _combine_make(self.camera_make, self.camera_model)

    @property
    @_default_none
    def lens_make(self) -> str:
        return _to_string(self._exif_ifd[ExifTags.Base.LensMake])

    @property
    @_default_none
    def lens_model(self) -> str:
        return _to_string(self._exif_ifd[ExifTags.Base.LensModel])

    @property
    def lens(self) -> str:
        return _combine_make(self.lens_make, self.lens_model)

    @property
    @_default_none
    def aperture(self) -> float:
        return round(_to_float(self._exif_ifd[ExifTags.Base.ApertureValue]), 4)

    @property
    @_default_none
    def f_num(self) -> float:
        return round(_to_float(self._exif_ifd[ExifTags.Base.FNumber]), 4)

    @property
    @_default_none
    def f(self) -> str:
        value = _to_float(self._exif_ifd[ExifTags.Base.FNumber])
        return f"ƒ/{value:g}"

    @property
    @_default_none
    def exposure_time(self) -> str:
        value = _to_rational(self._exif_ifd[ExifTags.Base.ExposureTime])
        return f"{value.numerator}/{value.denominator}"

    @property
    @_default_none
    def shutter_speed(self) -> str:
        value = _to_float(self._exif_ifd[ExifTags.Base.ShutterSpeedValue])
        return f"1/{2 ** value:.0f}"

    @property
    @_default_none
    def focal_length(self) -> str:
        return _to_focal_length(self._exif_ifd[ExifTags.Base.FocalLength])

    @property
    @_default_none
    def focal_length_35mm(self) -> str:
        return _to_focal_length(self._exif_ifd[ExifTags.Base.FocalLengthIn35mmFilm])

    @property
    @_default_none
    def flash_info(self) -> str:
        return _to_flash_description(self._exif_ifd[ExifTags.Base.Flash])

    @property
    @_default_none
    def iso(self) -> float:
        return _to_float(self._exif_ifd[ExifTags.Base.ISOSpeedRatings])

    @property
    def created_at(self) -> datetime | None:
        date_tags = (
            # XXX: GPSDateStamp includes just the date
            # https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/gps/gpsdatestamp.html
            (self._gpsinfo_ifd, ExifTags.GPS.GPSDateStamp),
            # XXX: DateTimeOriginal is an EXIF tag, not and IFD0 tag
            (self._ifd0, ExifTags.Base.DateTimeOriginal),
            (self._exif_ifd, ExifTags.Base.DateTimeOriginal),
            (self._exif_ifd, ExifTags.Base.DateTimeDigitized),
            (self._ifd0, ExifTags.Base.DateTime),
        )
        for ifd, tag in date_tags:
            try:
                return datetime.strptime(ifd[tag], "%Y:%m:%d %H:%M:%S")
            except (LookupError, ValueError):
                continue
        return None

    @property
    @_default_none
    def longitude(self) -> float:
        gpsinfo_ifd = self._gpsinfo_ifd
        return _to_degrees(
            gpsinfo_ifd[ExifTags.GPS.GPSLongitude],
            gpsinfo_ifd[ExifTags.GPS.GPSLongitudeRef],
        )

    @property
    @_default_none
    def latitude(self) -> float:
        gpsinfo_ifd = self._gpsinfo_ifd
        return _to_degrees(
            gpsinfo_ifd[ExifTags.GPS.GPSLatitude],
            gpsinfo_ifd[ExifTags.GPS.GPSLatitudeRef],
        )

    @property
    @_default_none
    def altitude(self) -> float:
        gpsinfo_ifd = self._gpsinfo_ifd
        value = _to_float(gpsinfo_ifd[ExifTags.GPS.GPSAltitude])
        ref = gpsinfo_ifd.get(ExifTags.GPS.GPSAltitudeRef)
        if ref == b"\x01":
            value = -value
        return value

    @property
    def location(self) -> tuple[float, float] | None:
        lat = self.latitude
        long = self.longitude
        if lat is not None and long is not None:
            return (lat, long)
        return None

    @property
    @_default_none
    def documentname(self) -> str:
        return _to_string(self._ifd0[ExifTags.Base.DocumentName])

    @property
    @_default_none
    def description(self) -> str:
        return _to_string(self._ifd0[ExifTags.Base.ImageDescription])

    @property
    def is_rotated(self) -> bool:
        """Return if the image is rotated according to the Orientation header.

        The Orientation header in EXIF stores an integer value between
        1 and 8, where the values 5-8 represent "portrait" orientations
        (rotated 90deg left, right, and mirrored versions of those), i.e.,
        the image is rotated.
        """
        try:
            orientation = TiffOrientation(self._ifd0[ExifTags.Base.Orientation])
        except (LookupError, ValueError):
            return False
        return orientation.is_transposed


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


def _parse_svg_units_px(length: str) -> float | None:
    match = re.match(
        r"\d+(?: \.\d* )? (?= (?: \s*px )? \Z)", length.strip(), re.VERBOSE
    )
    if match:
        return float(match.group())
    return None


def get_svg_info(
    source: str | Path | SupportsRead[bytes],
) -> SvgImageInfo | UnknownImageInfo:
    try:
        _, svg = next(etree.iterparse(source, events=["start"]))
    except (etree.ParseError, StopIteration):
        return UnknownImageInfo()
    if svg.tag != "{http://www.w3.org/2000/svg}svg":
        return UnknownImageInfo()
    width = _parse_svg_units_px(svg.attrib.get("width", ""))
    height = _parse_svg_units_px(svg.attrib.get("height", ""))
    return SvgImageInfo("svg", width, height)


def _get_image_orientation(image: PIL.Image.Image) -> TiffOrientation:
    """Deduce the orientation of the image.

    Notes
    -----

    Note that browsers only seem to respect the "Exif" Orientation tag for JPEG images
    (and probably TIFF images). In particular, it is `typically ignored`__ by
    browsers when displaying PNG, WEBP and AVIF files (though AVIF files have their own way
    of indicating orientation — the "irot" and "imir" properties — which are respected.)

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

    orientation = _get_image_orientation(image)
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
    try:
        if isinstance(source, (str, Path)):
            with PIL.Image.open(source) as image:
                return _PIL_image_info(image)
        else:
            warnings.warn(
                "Passing a file object to 'get_image_info' is deprecated "
                "since version 3.4.0. Pass a file path instead.",
                DeprecationWarning,
            )
            with _save_position(source) as fp_:
                with PIL.Image.open(fp_) as image:
                    return _PIL_image_info(image)

    except UnidentifiedImageError:
        return get_svg_info(source)


def read_exif(source: str | Path | SupportsRead[bytes]) -> EXIFInfo:
    """Reads exif data from an image file."""
    try:
        with PIL.Image.open(source) as image:
            exif = image.getexif()
    except UnidentifiedImageError:
        exif = PIL.Image.Exif()
    return EXIFInfo(exif)


class ImageSize(NamedTuple):
    width: int
    height: int


class CropBox(NamedTuple):
    # field names taken from
    # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.crop
    left: int
    upper: int
    right: int
    lower: int


class _FormatInfo:
    format: ClassVar[str]
    default_save_params: ClassVar[dict[str, Any]] = {}
    extensions: ClassVar[Sequence[str]]

    @classmethod
    def get_save_params(cls, thumbnail_params: ThumbnailParams) -> dict[str, Any]:
        """Compute kwargs to be passed to Image.save() when writing the thumbnail."""
        params = dict(cls.default_save_params)
        params.update(cls._extra_save_params(thumbnail_params))
        params["format"] = cls.format
        return params

    @classmethod
    def get_thumbnail_tag(cls, thumbnail_params: ThumbnailParams) -> str:
        """Get a string which serializes the thumbnail_params.

        This is value is used as a suffix when generating the file name for the
        thumbnail.
        """
        width, height = thumbnail_params.size
        bits = [f"{width}x{height}"]
        if thumbnail_params.crop:
            bits.append("crop")
        bits.extend(cls._extra_tag_bits(thumbnail_params))
        return "_".join(bits)

    @classmethod
    def get_ext(cls, proposed_ext: str | None = None) -> str:
        """Get file extension suitable for image format.

        If proposed_ext is an acceptable extension for the format, return that.
        Otherwise return the default extension for the format.
        """
        if proposed_ext is not None and proposed_ext.lower() in cls.extensions:
            return proposed_ext
        return cls.extensions[0]

    @staticmethod
    def _extra_save_params(
        thumbnail_params: ThumbnailParams,
    ) -> Mapping[str, Any] | Iterable[tuple[str, Any]]:
        return {}

    @staticmethod
    def _extra_tag_bits(thumbnail_params: ThumbnailParams) -> Iterable[str]:
        return ()


class _GifFormatInfo(_FormatInfo):
    format = "GIF"
    extensions = (".gif",)


class _PngFormatInfo(_FormatInfo):
    format = "PNG"
    default_save_params = {"compress_level": 7}
    extensions = (".png",)

    @staticmethod
    def _extra_save_params(
        thumbnail_params: ThumbnailParams,
    ) -> Iterator[tuple[str, Any]]:
        quality = thumbnail_params.quality
        if quality is not None:
            yield "compress_level", min(9, max(0, quality // 10))

    @classmethod
    def _extra_tag_bits(cls, thumbnail_params: ThumbnailParams) -> Iterable[str]:
        for key, value in cls._extra_save_params(thumbnail_params):
            assert key == "compress_level"
            yield f"q{value}"


class _JpegFormatInfo(_FormatInfo):
    format = "JPEG"
    default_save_params = {"quality": 85}
    extensions = (".jpeg", ".jpg")

    @staticmethod
    def _extra_save_params(
        thumbnail_params: ThumbnailParams,
    ) -> Iterator[tuple[str, Any]]:
        quality = thumbnail_params.quality
        if quality is not None:
            yield "quality", quality

    @classmethod
    def _extra_tag_bits(cls, thumbnail_params: ThumbnailParams) -> Iterable[str]:
        for key, value in cls._extra_save_params(thumbnail_params):
            assert key == "quality"
            yield f"q{value}"


@dataclasses.dataclass
class ThumbnailParams:
    """Encapsulates the parameters necessary to generate a thumbnail."""

    size: ImageSize
    format: str
    quality: int | None = None
    crop: bool = False

    def __post_init__(self) -> None:
        format = self.format.upper()
        for format_info_cls in _FormatInfo.__subclasses__():
            if format_info_cls.format == format:
                break
        else:
            raise ValueError(f"unrecognized format ({self.format!r})")
        self.format_info = format_info_cls

    def get_save_params(self) -> Mapping[str, Any]:
        """Get kwargs to pass to Image.save() when writing the thumbnail."""
        return self.format_info.get_save_params(self)

    def get_ext(self, proposed_ext: str | None = None) -> str:
        """Get file extension for thumbnail.

        If proposed_ext is an acceptable extension for the thumbnail, return that.
        Otherwise return the default extension for the thumbnail format.
        """
        return self.format_info.get_ext(proposed_ext)

    def get_tag(self) -> str:
        """Get a string which serializes the thumbnail_params.

        This is value is used as a suffix when generating the file name for the
        thumbnail.
        """
        return self.format_info.get_thumbnail_tag(self)


def _scale(x: int, num: float, denom: float) -> int:
    """Compute x * num / denom, rounded to integer.

    ``x``, ``num``, and ``denom`` should all be positive.

    Rounds 0.5 up to be consistent with imagemagick.

    """
    if isinstance(num, int) and isinstance(denom, int):
        # If all arguments are integers, carry out the computation using integer math to
        # ensure that 0.5 rounds up.
        return (x * num + denom // 2) // denom
    # If floats are involved, we do our best to round 0.5 up, but loss of precision
    # involved in floating point math makes the idea of "exactly" 0.5 a little fuzzy.
    return math.trunc((x * num + denom / 2) // denom)


def compute_dimensions(
    width: int | None, height: int | None, source_width: float, source_height: float
) -> ImageSize:
    """Compute "fit"-mode dimensions of thumbnail.

    Returns the maximum size of a thumbnail with that has (nearly) the same aspect ratio
    as the source and whose maximum size is set by ``width`` and ``height``.

    One, but not both, of ``width`` or ``height`` can be ``None``.
    """
    if width is None and height is None:
        raise ValueError("width and height may not both be None")
    if width is not None:
        size = ImageSize(width, _scale(width, source_height, source_width))
    if height is not None and (width is None or height < size.height):
        size = ImageSize(_scale(height, source_width, source_height), height)
    return size


def _compute_cropbox(size: ImageSize, source_width: int, source_height: int) -> CropBox:
    """Compute "crop"-mode crop-box to be applied to the source image before
    it is scaled to the final thumbnail dimensions.

    """
    use_width = min(source_width, _scale(source_height, size.width, size.height))
    use_height = min(source_height, _scale(source_width, size.height, size.width))
    crop_l = (source_width - use_width) // 2
    crop_t = (source_height - use_height) // 2
    return CropBox(crop_l, crop_t, crop_l + use_width, crop_t + use_height)


SRGB_PROFILE: Final = PIL.ImageCms.createProfile("sRGB")
SRGB_PROFILE_BYTES: Final = PIL.ImageCms.ImageCmsProfile(SRGB_PROFILE).tobytes()


def _get_icc_transform(
    icc_profile: bytes, inMode: str, outMode: str
) -> PIL.ImageCms.ImageCmsTransform:
    """Construct ICC transform mapping icc_profile to sRGB."""
    profile = PIL.ImageCms.getOpenProfile(io.BytesIO(icc_profile))
    transform = PIL.ImageCms.buildTransform(profile, SRGB_PROFILE, inMode, outMode)
    assert isinstance(transform, PIL.ImageCms.ImageCmsTransform)
    return transform


def _convert_to_rgb(image: PIL.Image.Image) -> PIL.Image.Image:
    # Ensure image is RGB before scaling
    targetMode = "RGBA" if image.mode.upper().endswith("A") else "RGB"
    if image.mode != targetMode:
        icc_profile = image.info.get("icc_profile")
        if icc_profile is not None:
            icc_transform = _get_icc_transform(icc_profile, image.mode, targetMode)
            image = PIL.ImageCms.applyTransform(image, icc_transform)
            del image.info["icc_profile"]
        else:
            image = image.convert(targetMode)
    return image


def _convert_icc_profile_to_srgb(image: PIL.Image.Image) -> None:
    """Convert image from embedded ICC profile to sRGB.

    The image is modified **in place**.

    After conversion, any embedded color profile is removed. (The default color
    space for the web is "sRGB", so we don't need to embed it.)
    """
    # XXX: The old imagemagick code (which ran `convert` with `-strip -colorspace sRGB`)
    # did not attempt any colorspace conversion.  It simply stripped and ignored any
    # color profile in the input image (causing the resulting thumbnail to be
    # interpreted as if it were in sRGB even though its not.)
    #
    # Here we attempt to convert from any embedded colorspace in the source image
    # to sRGB.
    #
    # Note: _convert_to_rgb may have already done this if the original image was
    # not in RGB(A) mode.  In that case it should have removed the icc_profile from
    # the images .info dict.
    #
    # XXX: There seems to be no real way to compare to color profiles to see whether
    # they are the same.  It's not even clear that all "sRGB" profiles are really the
    # same.  (See
    # https://ninedegreesbelow.com/photography/srgb-profile-comparison.html.) So we
    # always convert if the image has a color profile.
    #
    icc_profile = image.info.get("icc_profile")
    if icc_profile is not None and icc_profile != SRGB_PROFILE_BYTES:
        icc_transform = _get_icc_transform(icc_profile, image.mode, image.mode)
        PIL.ImageCms.applyTransform(image, icc_transform, inPlace=True)
        del image.info["icc_profile"]


_TRANSPOSE_FOR_ORIENTATION: Final[Mapping[TiffOrientation, int]] = {
    TiffOrientation.TOPRIGHT: PIL.Image.FLIP_LEFT_RIGHT,
    TiffOrientation.BOTRIGHT: PIL.Image.ROTATE_180,
    TiffOrientation.BOTLEFT: PIL.Image.FLIP_TOP_BOTTOM,
    TiffOrientation.LEFTTOP: PIL.Image.TRANSPOSE,
    TiffOrientation.RIGHTTOP: PIL.Image.ROTATE_270,
    TiffOrientation.RIGHTBOT: PIL.Image.TRANSVERSE,
    TiffOrientation.LEFTBOT: PIL.Image.ROTATE_90,
}


def _auto_orient_image(image: PIL.Image.Image) -> PIL.Image.Image:
    """Transpose image as indicated by the Exif Orientation tag.

    We only do this for JPEG images.  See _get_image_orientation for notes on why.

    """
    orientation = _get_image_orientation(image)
    if orientation in _TRANSPOSE_FOR_ORIENTATION:
        image = image.transpose(
            _TRANSPOSE_FOR_ORIENTATION[orientation]  # type: ignore[arg-type]
        )
    return image


def _create_thumbnail(
    image: PIL.Image.Image, params: ThumbnailParams
) -> PIL.Image.Image:
    # XXX: use Image.thumbnail sometimes? (Is it more efficient?)

    # Ensure image is RGB before scaling
    image = _convert_to_rgb(image)

    # transpose according to EXIF Orientation
    image = _auto_orient_image(image)

    # resize
    resize_params: dict[str, Any] = {"reducing_gap": 3.0}
    if params.crop:
        resize_params["box"] = _compute_cropbox(params.size, image.width, image.height)
    if PILLOW_VERSION_INFO < (7, 0):
        del resize_params["reducing_gap"]  # not supported in older Pillow
    thumbnail = image.resize(params.size, **resize_params)

    _convert_icc_profile_to_srgb(thumbnail)

    # Do not propate comment tag to thumbnail
    thumbnail.info.pop("comment", None)

    return thumbnail


def _create_artifact(
    source_image: str | Path | SupportsRead[bytes],
    thumbnail_params: ThumbnailParams,
    artifact: Artifact,
) -> None:
    """Create artifact by computing thumbnail for source image."""
    # XXX: would passing explicit `formats` to Image.open make it any faster?
    with PIL.Image.open(source_image) as image:
        thumbnail = _create_thumbnail(image, thumbnail_params)
        save_params = thumbnail_params.get_save_params()
    with artifact.open("wb") as fp:
        thumbnail.save(fp, **save_params)


def _get_thumbnail_url_path(
    source_url_path: str, thumbnail_params: ThumbnailParams
) -> str:
    source_ext = posixpath.splitext(source_url_path)[1]
    # leave ext unchanged from source if valid for the thumbnail format
    ext = thumbnail_params.get_ext(source_ext)
    suffix = thumbnail_params.get_tag()
    return get_dependent_url(  # type: ignore[no-any-return]
        source_url_path, suffix, ext=ext
    )


def make_image_thumbnail(
    ctx: Context,
    source_image: str | Path,
    source_url_path: str,
    width: int | None = None,
    height: int | None = None,
    mode: ThumbnailMode = ThumbnailMode.DEFAULT,
    upscale: bool | None = None,
    quality: int | None = None,
) -> Thumbnail:
    """Helper method that can create thumbnails from within the build process
    of an artifact.
    """
    image_info = get_image_info(source_image)
    if isinstance(image_info, UnknownImageInfo):
        raise RuntimeError("Cannot process unknown images")

    if mode == ThumbnailMode.FIT:
        if width is None and height is None:
            raise ValueError("Must specify at least one of width or height.")
        if image_info.width is None or image_info.height is None:
            assert isinstance(image_info, SvgImageInfo)
            raise ValueError("Cannot determine aspect ratio of SVG image.")
        if upscale is None:
            upscale = False
        size = compute_dimensions(width, height, image_info.width, image_info.height)
    else:
        if width is None or height is None:
            raise ValueError(
                f'"{mode.value}" mode requires both `width` and `height` to be specified.'
            )
        if upscale is None:
            upscale = True
        size = ImageSize(width, height)

    # If we are dealing with an actual svg image, we do not actually
    # resize anything, we just return it. This is not ideal but it's
    # better than outright failing.
    if isinstance(image_info, SvgImageInfo):
        # XXX: Since we don't always know the original dimensions,
        # we currently omit the upscaling check for SVG images.
        return Thumbnail(source_url_path, size.width, size.height)

    would_upscale = size.width > image_info.width or size.height > image_info.height
    if would_upscale and not upscale:
        return Thumbnail(source_url_path, image_info.width, image_info.height)

    thumbnail_params = ThumbnailParams(
        size=size,
        format=image_info.format.upper(),
        quality=quality,
        crop=mode == ThumbnailMode.CROP,
    )
    dst_url_path = _get_thumbnail_url_path(source_url_path, thumbnail_params)

    ctx.add_sub_artifact(
        artifact_name=dst_url_path,
        sources=[source_image],
        build_func=partial(_create_artifact, source_image, thumbnail_params),
    )

    return Thumbnail(dst_url_path, size.width, size.height)


@dataclasses.dataclass(frozen=True)
class Thumbnail:
    """Holds information about a thumbnail."""

    url_path: str
    width: int
    height: int

    def __str__(self) -> str:
        return posixpath.basename(self.url_path)
