from __future__ import annotations

import dataclasses
import io
import posixpath
import re
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Any
from typing import BinaryIO
from typing import ClassVar
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import NamedTuple
from typing import Sequence
from typing import TYPE_CHECKING
from xml.etree import ElementTree as etree

import exifread
import PIL.Image
import PIL.ImageCms
import PIL.ImageOps

from lektor.utils import deprecated
from lektor.utils import get_dependent_url

if TYPE_CHECKING:
    from lektor.builder import Artifact

PILLOW_VERSION_INFO = tuple(map(int, PIL.__version__.split(".")))

if PILLOW_VERSION_INFO >= (8, 0):
    from PIL.ImageOps import exif_transpose
else:
    # Exif_transpose is broken in older versions of Pillow
    # (It has trouble updating EXIF tags in some cases.)
    #
    # Ref: https://github.com/python-pillow/Pillow/issues/4896
    #
    _TRANSPOSE_FOR_ORIENTATION: dict[int, Any] = {
        2: PIL.Image.FLIP_LEFT_RIGHT,
        3: PIL.Image.ROTATE_180,
        4: PIL.Image.FLIP_TOP_BOTTOM,
        5: PIL.Image.TRANSPOSE,
        6: PIL.Image.ROTATE_270,
        7: PIL.Image.TRANSVERSE,
        8: PIL.Image.ROTATE_90,
    }

    def exif_transpose(image: PIL.Image.Image) -> PIL.Image.Image:
        """If an image has an EXIF Orientation tag, return a new image that is
        transposed accordingly.

        If the image has no Orientation tag, a copy of the original is returned.

        NOTE: Contrary to what ``PIL.ImageOps.exif_transpose`` does, this version simply
        deletes all EXIF tags from the transposed image.

        """
        exif = image.getexif()
        orientation = exif.get(0x0112)
        if orientation not in _TRANSPOSE_FOR_ORIENTATION:
            return image.copy()
        transposed_image = image.transpose(_TRANSPOSE_FOR_ORIENTATION[orientation])
        del transposed_image.info["exif"]
        return transposed_image


SRGB_PROFILE = PIL.ImageCms.createProfile("sRGB")
SRGB_PROFILE_BYTES = PIL.ImageCms.ImageCmsProfile(SRGB_PROFILE).tobytes()


class ThumbnailMode(Enum):
    FIT = "fit"
    CROP = "crop"
    STRETCH = "stretch"

    DEFAULT = "fit"

    @property
    @deprecated("Use ThumbnailMode.value instead", version="3.3.0")
    def label(self):
        """The mode's label as used in templates."""
        return self.value

    @classmethod
    @deprecated(
        "Use the ThumbnailMode constructor, e.g. 'ThumbnailMode(label)', instead",
        version="3.3.0",
    )
    def from_label(cls, label):
        """Looks up the thumbnail mode by its textual representation."""
        return cls(label)


def _convert_gps(coords, hem):
    deg, min, sec = (float(x.num) / float(x.den) for x in coords)
    sign = -1 if hem in "SW" else 1
    return sign * (deg + min / 60.0 + sec / 3600.0)


def _combine_make(make, model):
    make = make or ""
    model = model or ""
    if make and model.startswith(make):
        return model
    return " ".join([make, model]).strip()


class EXIFInfo:
    def __init__(self, d):
        self._mapping = d

    def __bool__(self):
        return bool(self._mapping)

    __nonzero__ = __bool__

    def to_dict(self):
        rv = {}
        for key, value in self.__class__.__dict__.items():
            if key[:1] != "_" and isinstance(value, property):
                rv[key] = getattr(self, key)
        return rv

    def _get_string(self, key):
        try:
            value = self._mapping[key].values
        except KeyError:
            return None
        if isinstance(value, str):
            return value
        return value.decode("utf-8", "replace")

    def _get_int(self, key):
        try:
            return self._mapping[key].values[0]
        except LookupError:
            return None

    def _get_float(self, key, precision=4):
        try:
            val = self._mapping[key].values[0]
            if isinstance(val, int):
                return float(val)
            return round(float(val.num) / float(val.den), precision)
        except LookupError:
            return None

    def _get_frac_string(self, key):
        try:
            val = self._mapping[key].values[0]
            return f"{val.num}/{val.den}"
        except LookupError:
            return None

    @property
    def artist(self):
        return self._get_string("Image Artist")

    @property
    def copyright(self):
        return self._get_string("Image Copyright")

    @property
    def camera_make(self):
        return self._get_string("Image Make")

    @property
    def camera_model(self):
        return self._get_string("Image Model")

    @property
    def camera(self):
        return _combine_make(self.camera_make, self.camera_model)

    @property
    def lens_make(self):
        return self._get_string("EXIF LensMake")

    @property
    def lens_model(self):
        return self._get_string("EXIF LensModel")

    @property
    def lens(self):
        return _combine_make(self.lens_make, self.lens_model)

    @property
    def aperture(self):
        return self._get_float("EXIF ApertureValue")

    @property
    def f_num(self):
        return self._get_float("EXIF FNumber")

    @property
    def f(self):
        return "ƒ/%s" % self.f_num

    @property
    def exposure_time(self):
        return self._get_frac_string("EXIF ExposureTime")

    @property
    def shutter_speed(self):
        val = self._get_float("EXIF ShutterSpeedValue")
        if val is not None:
            return "1/%d" % round(
                1 / (2**-val)  # pylint: disable=invalid-unary-operand-type
            )
        return None

    @property
    def focal_length(self):
        val = self._get_float("EXIF FocalLength")
        if val is not None:
            return "%smm" % val
        return None

    @property
    def focal_length_35mm(self):
        val = self._get_float("EXIF FocalLengthIn35mmFilm")
        if val is not None:
            return "%dmm" % val
        return None

    @property
    def flash_info(self):
        try:
            value = self._mapping["EXIF Flash"].printable
        except KeyError:
            return None
        if isinstance(value, str):
            return value
        return value.decode("utf-8")

    @property
    def iso(self):
        val = self._get_int("EXIF ISOSpeedRatings")
        if val is not None:
            return val
        return None

    @property
    def created_at(self):
        date_tags = (
            "GPS GPSDate",
            "Image DateTimeOriginal",
            "EXIF DateTimeOriginal",
            "EXIF DateTimeDigitized",
            "Image DateTime",
        )
        for tag in date_tags:
            try:
                return datetime.strptime(
                    self._mapping[tag].printable, "%Y:%m:%d %H:%M:%S"
                )
            except (KeyError, ValueError):
                continue
        return None

    @property
    def longitude(self):
        try:
            return _convert_gps(
                self._mapping["GPS GPSLongitude"].values,
                self._mapping["GPS GPSLongitudeRef"].printable,
            )
        except KeyError:
            return None

    @property
    def latitude(self):
        try:
            return _convert_gps(
                self._mapping["GPS GPSLatitude"].values,
                self._mapping["GPS GPSLatitudeRef"].printable,
            )
        except KeyError:
            return None

    @property
    def altitude(self):
        val = self._get_float("GPS GPSAltitude")
        if val is not None:
            try:
                ref = self._mapping["GPS GPSAltitudeRef"].values[0]
            except LookupError:
                ref = 0
            if ref == 1:
                val *= -1
            return val
        return None

    @property
    def location(self):
        lat = self.latitude
        long = self.longitude
        if lat is not None and long is not None:
            return (lat, long)
        return None

    @property
    def documentname(self):
        return self._get_string("Image DocumentName")

    @property
    def description(self):
        return self._get_string("Image ImageDescription")

    @property
    def is_rotated(self):
        """Return if the image is rotated according to the Orientation header.

        The Orientation header in EXIF stores an integer value between
        1 and 8, where the values 5-8 represent "portrait" orientations
        (rotated 90deg left, right, and mirrored versions of those), i.e.,
        the image is rotated.
        """
        return self._get_int("Image Orientation") in {5, 6, 7, 8}


def _parse_svg_units_px(length):
    match = re.match(
        r"\d+(?: \.\d* )? (?= (?: \s*px )? \Z)", length.strip(), re.VERBOSE
    )
    if match:
        return float(match.group())
    return None


def get_svg_info(fp):
    try:
        _, svg = next(etree.iterparse(fp, events=["start"]))
    except (etree.ParseError, StopIteration):
        return None, None, None
    if svg.tag != "{http://www.w3.org/2000/svg}svg":
        return None, None, None
    width = _parse_svg_units_px(svg.attrib.get("width", ""))
    height = _parse_svg_units_px(svg.attrib.get("height", ""))
    return "svg", width, height


def _PIL_image_info(
    image: PIL.Image.Image,
) -> tuple[str, int, int] | tuple[None, None, None]:
    """Determine image format and dimensions for PIL Image"""

    FORMATS = {"PNG": "png", "GIF": "gif", "JPEG": "jpeg"}
    TRANSPOSED_ORIENTATIONS = {5, 6, 7, 8}

    if image.format not in FORMATS:
        return None, None, None

    fmt = FORMATS[image.format]
    width = image.width
    height = image.height

    exif = image.getexif()
    orientation = exif.get(0x0112)
    if orientation in TRANSPOSED_ORIENTATIONS:
        width, height = height, width

    return fmt, width, height


@contextmanager
def _save_position(fp):
    position = fp.tell()
    try:
        yield fp
    finally:
        fp.seek(position)


def get_image_info(fp):
    """Reads some image info from a file descriptor."""
    try:
        with _save_position(fp) as fp_:
            image = PIL.Image.open(fp_)
    except PIL.UnidentifiedImageError:
        return get_svg_info(fp)

    return _PIL_image_info(image)


def read_exif(fp):
    """Reads exif data from a file pointer of an image and returns it."""
    exif = exifread.process_file(fp)
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

    # save_image: _SaveImage = dataclasses.field(init=False)

    def __post_init__(self):
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


def _scale(x: int, num: int, denom: int) -> int:
    """Compute x * num / denom, rounded to integer.

    ``x``, ``num``, and ``denom`` should all be positive integers.

    Rounds 0.5 up to be consistent with imagemagick.
    """
    return (x * num + denom // 2) // denom


def compute_dimensions(
    width: int | None, height: int | None, source_width: int, source_height: int
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


def _convert_color_profile_to_srgb(im: PIL.Image.Image) -> None:
    """Convert image color profile to sRGB.

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
    if "icc_profile" in im.info:
        profile = PIL.ImageCms.getOpenProfile(io.BytesIO(im.info["icc_profile"]))
        profile_name = PIL.ImageCms.getProfileName(profile)
        # FIXME: is there a better way to tell if input already sRGB?
        # Is there even a well-defined single "sRGB" profile?
        # (See https://ninedegreesbelow.com/photography/srgb-profile-comparison.html)
        if profile_name.strip() not in ("sRGB", "sRGB IEC61966-2.1", "sRGB built-in"):
            PIL.ImageCms.profileToProfile(im, profile, SRGB_PROFILE, inPlace=True)
        im.info.pop("icc_profile")


def _create_thumbnail(
    image: PIL.Image.Image, params: ThumbnailParams
) -> PIL.Image.Image:
    # XXX: use Image.thumbnail sometimes? (Is it more efficient?)

    # transpose according to EXIF Orientation
    source = exif_transpose(image)

    resize_params: dict[str, Any] = {"reducing_gap": 3.0}
    if params.crop:
        resize_params["box"] = _compute_cropbox(
            params.size, source.width, source.height
        )

    if PILLOW_VERSION_INFO < (7, 0):
        del resize_params["reducing_gap"]  # not supported in older Pillow

    thumbnail = source.resize(params.size, **resize_params)

    _convert_color_profile_to_srgb(thumbnail)

    # Do not propate comment tag to thumbnail
    thumbnail.info.pop("comment", None)

    return thumbnail


def _create_artifact(
    source_image: str | Path | BinaryIO,
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
    return get_dependent_url(source_url_path, suffix, ext=ext)


def make_image_thumbnail(
    ctx,
    source_image,
    source_url_path,
    width=None,
    height=None,
    mode=ThumbnailMode.DEFAULT,
    upscale=None,
    quality=None,
):
    """Helper method that can create thumbnails from within the build process
    of an artifact.
    """
    if width is None and height is None:
        raise ValueError("Must specify at least one of width or height.")
    if mode != ThumbnailMode.FIT and (width is None or height is None):
        raise ValueError(
            f'"{mode.value}" mode requires both `width` and `height` to be specified.'
        )

    if upscale is None and mode in (ThumbnailMode.CROP, ThumbnailMode.STRETCH):
        upscale = True

    with open(source_image, "rb") as f:
        source_format, source_width, source_height = get_image_info(f)

    if source_format is None:
        raise RuntimeError("Cannot process unknown images")

    # If we are dealing with an actual svg image, we do not actually
    # resize anything, we just return it. This is not ideal but it's
    # better than outright failing.
    if source_format == "svg":
        # XXX: this is pretty broken.
        # (Deal with scaling mode properly?)
        return Thumbnail(source_url_path, width, height)

    if mode == ThumbnailMode.FIT:
        size = compute_dimensions(width, height, source_width, source_height)
    else:
        size = ImageSize(width, height)

    would_upscale = size.width > source_width or size.height > source_height
    if would_upscale and not upscale:
        return Thumbnail(source_url_path, source_width, source_height)

    thumbnail_params = ThumbnailParams(
        size=size,
        format=source_format.upper(),
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

    def __str__(self):
        return posixpath.basename(self.url_path)
