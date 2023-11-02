"""Thumbnail generation."""
from __future__ import annotations

import dataclasses
import io
import math
import posixpath
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Any
from typing import ClassVar
from typing import Final
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import NamedTuple
from typing import Sequence
from typing import TYPE_CHECKING

import PIL.Image
import PIL.ImageCms

from ..utils import get_dependent_url
from ._compat import PILLOW_VERSION_INFO
from ._compat import Transpose  # PIL.Image.Transpose
from .image_info import get_image_info
from .image_info import get_image_orientation
from .image_info import SvgImageInfo
from .image_info import TiffOrientation
from .image_info import UnknownImageInfo

if TYPE_CHECKING:
    from _typeshed import SupportsRead
    from lektor.builder import Artifact
    from lektor.context import Context


class ThumbnailMode(Enum):
    FIT = "fit"
    CROP = "crop"
    STRETCH = "stretch"

    DEFAULT = "fit"


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


class ImageSize(NamedTuple):
    width: int
    height: int


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


class CropBox(NamedTuple):
    # field names taken from
    # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.crop
    left: int
    upper: int
    right: int
    lower: int


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
    # Note: _convert_to_rgb may have already done this if the original image was not in
    # RGB(A) mode.  In that case it will have removed the icc_profile from the images
    # .info dict.
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
    TiffOrientation.TOPRIGHT: Transpose.FLIP_LEFT_RIGHT,
    TiffOrientation.BOTRIGHT: Transpose.ROTATE_180,
    TiffOrientation.BOTLEFT: Transpose.FLIP_TOP_BOTTOM,
    TiffOrientation.LEFTTOP: Transpose.TRANSPOSE,
    TiffOrientation.RIGHTTOP: Transpose.ROTATE_270,
    TiffOrientation.RIGHTBOT: Transpose.TRANSVERSE,
    TiffOrientation.LEFTBOT: Transpose.ROTATE_90,
}


def _auto_orient_image(image: PIL.Image.Image) -> PIL.Image.Image:
    """Transpose image as indicated by the Exif Orientation tag.

    We only do this for JPEG images.  See _get_image_orientation for notes on why.

    """
    orientation = get_image_orientation(image)
    if orientation in _TRANSPOSE_FOR_ORIENTATION:
        image = image.transpose(
            _TRANSPOSE_FOR_ORIENTATION[orientation]  # type: ignore[arg-type]
        )
    return image


def _create_thumbnail(
    image: PIL.Image.Image, params: ThumbnailParams
) -> PIL.Image.Image:
    # XXX: There is an Image.thumbnail() method that can be significantly faster at
    # down-scaling than Image.resize() in some particular cases. Perhaps we want to use
    # that. (Image.thumbnail() never upscales, so we can only use it when down-scaling.)
    #
    # Image.thumbnail *only* has a possible advantage when down-scaling JPEG images,
    # where it configures the image loader to help with the down-scaling.  (With other
    # image types, .thumbnail just loads the image normally then uses .resize.)
    #
    # Some tests, downscaling a 5MB 4032x3024 JPEG, using:
    #
    #     python -m timeit -s "from PIL import Image" \
    #       "im = Image.open('in.jpg'); im.thumbnail((W,H)); im.save('out.jpg')"
    # or
    #     python -m timeit -s "from PIL import Image" \
    #       "im = Image.open('in.jpg'); im.resize((W,H)[,reducing_gap=3]).save('out.jpg')"
    #
    #         WxH    |  .resize()  |  .thumbnail()  |  .resize(reducing_gap=3)
    #     ===========|=============|================|===========================
    #      1024x768  |  117 msec   |   115 msec     |  130 msec
    #       512x384  |  105 msec   |    51 msec     |   82 msec
    #       256x192  |  103 msec   |    33 msec     |   63 msec
    #       120x90   |  100 msec   |    22 msec     |   60 msec
    #         4x3    |   88 msec   |    22 msec     |   58 msec
    #
    # Thumbnail() by default uses reducing_gap=2.
    #
    # The big wins for .thumbnail() appear to come when downscaling by a factor of ~8 or
    # more.

    # Ensure image is in RGB (or RGBA) mode before scaling
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

    # Convert from any embedded ICC color profile to sRGB.
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
