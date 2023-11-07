"""Helper to access Exif info in images.
"""
from __future__ import annotations

import numbers
import sys
from datetime import datetime
from fractions import Fraction
from functools import wraps
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Tuple
from typing import TYPE_CHECKING
from typing import TypeVar
from typing import Union

import PIL.Image

from ._compat import ExifTags
from ._compat import UnidentifiedImageError
from .image_info import TiffOrientation

if TYPE_CHECKING:
    from typing import Literal
    from _typeshed import SupportsRead

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias


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


def read_exif(source: str | Path | SupportsRead[bytes]) -> EXIFInfo:
    """Reads exif data from an image file."""
    try:
        with PIL.Image.open(source) as image:
            exif = image.getexif()
    except UnidentifiedImageError:
        exif = PIL.Image.Exif()
    return EXIFInfo(exif)
