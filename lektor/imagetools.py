# -*- coding: utf-8 -*-
import decimal
import os
import posixpath
import re
import struct
import warnings
from datetime import datetime
from enum import Enum
from xml.etree import ElementTree as etree

import exifread
import filetype

from lektor.reporter import reporter
from lektor.utils import get_dependent_url
from lektor.utils import locate_executable
from lektor.utils import portable_popen


# yay shitty library
datetime.strptime("", "")


class ThumbnailMode(Enum):
    FIT = "fit"
    CROP = "crop"
    STRETCH = "stretch"

    DEFAULT = "fit"

    @property
    def label(self):
        """The mode's label as used in templates."""
        warnings.warn(
            "ThumbnailMode.label is deprecated. (Use ThumbnailMode.value instead.)",
            DeprecationWarning,
        )
        return self.value

    @classmethod
    def from_label(cls, label):
        """Looks up the thumbnail mode by its textual representation."""
        warnings.warn(
            "ThumbnailMode.from_label is deprecated. "
            "Use the ThumbnailMode constructor, "
            'e.g. "ThumbnailMode(label)", instead.',
            DeprecationWarning,
        )
        return cls(label)


def _convert_gps(coords, hem):
    deg, min, sec = [float(x.num) / float(x.den) for x in coords]
    sign = -1 if hem in "SW" else 1
    return sign * (deg + min / 60.0 + sec / 3600.0)


def _combine_make(make, model):
    make = make or ""
    model = model or ""
    if make and model.startswith(make):
        return make
    return " ".join([make, model]).strip()


_parse_svg_units_re = re.compile(
    r"(?P<value>[+-]?(?:\d+)(?:\.\d+)?)\s*(?P<unit>\D+)?", flags=re.IGNORECASE
)


def _parse_svg_units_px(length):
    match = _parse_svg_units_re.match(length)
    if not match:
        return None
    match = match.groupdict()
    if match["unit"] and match["unit"] != "px":
        return None
    try:
        return float(match["value"])
    except ValueError:
        return None


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
            return "%s/%s" % (val.num, val.den)
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


def get_suffix(width, height, mode, quality=None):
    suffix = "" if width is None else str(width)
    if height is not None:
        suffix += "x%s" % height
    if mode != ThumbnailMode.DEFAULT:
        suffix += "_%s" % mode.value
    if quality is not None:
        suffix += "_q%s" % quality
    return suffix


def get_svg_info(fp):
    _, svg = next(etree.iterparse(fp, ["start"]), (None, None))
    fp.seek(0)
    width, height = None, None
    if svg is not None and svg.tag == "{http://www.w3.org/2000/svg}svg":
        width = _parse_svg_units_px(svg.attrib.get("width", ""))
        height = _parse_svg_units_px(svg.attrib.get("height", ""))
    return "svg", width, height


# see http://www.w3.org/Graphics/JPEG/itu-t81.pdf
# Table B.1 – Marker code assignments (page 32/36)
_JPEG_SOF_MARKERS = (
    # non-differential, Hufmann-coding
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    # differential, Hufmann-coding
    0xC5,
    0xC6,
    0xC7,
    # non-differential, arithmetic-coding
    0xC9,
    0xCA,
    0xCB,
    # differential, arithmetic-coding
    0xCD,
    0xCE,
    0xCF,
)


def get_image_info(fp):
    """Reads some image info from a file descriptor."""
    head = fp.read(32)
    fp.seek(0)
    if len(head) < 24:
        return "unknown", None, None

    magic_bytes = b"<?xml", b"<svg"
    if any(map(head.strip().startswith, magic_bytes)):
        return get_svg_info(fp)

    _type = filetype.image_match(bytearray(head))
    fmt = _type.mime.split("/")[1] if _type else None

    width = None
    height = None
    if fmt == "png":
        check = struct.unpack(">i", head[4:8])[0]
        if check == 0x0D0A1A0A:
            width, height = struct.unpack(">ii", head[16:24])
    elif fmt == "gif":
        width, height = struct.unpack("<HH", head[6:10])
    elif fmt == "jpeg":
        # specification available under
        # http://www.w3.org/Graphics/JPEG/itu-t81.pdf
        # Annex B (page 31/35)

        # we are looking for a SOF marker ("start of frame").
        # skip over the "start of image" marker
        # (filetype detection took care of that).
        fp.seek(2)

        while True:
            byte = fp.read(1)

            # "All markers are assigned two-byte codes: an X’FF’ byte
            # followed by a byte which is not equal to 0 or X’FF’."
            if not byte or ord(byte) != 0xFF:
                raise Exception("Malformed JPEG image.")

            # "Any marker may optionally be preceded by any number
            # of fill bytes, which are bytes assigned code X’FF’."
            while ord(byte) == 0xFF:
                byte = fp.read(1)

            if ord(byte) not in _JPEG_SOF_MARKERS:
                # header length parameter takes 2 bytes for all markers
                length = struct.unpack(">H", fp.read(2))[0]
                fp.seek(length - 2, 1)
                continue

            # else...
            # see Figure B.3 – Frame header syntax (page 35/39) and
            # Table B.2 – Frame header parameter sizes and values
            # (page 36/40)
            fp.seek(3, 1)  # skip header length and precision parameters
            height, width = struct.unpack(">HH", fp.read(4))

            if height == 0:
                # "Value 0 indicates that the number of lines shall be
                # defined by the DNL marker [...]"
                #
                # DNL is not supported by most applications,
                # so we won't support it either.
                raise Exception("JPEG with DNL not supported.")

            break

        # if the file is rotated, we want, for all intents and purposes,
        # to return the dimensions swapped. (all client apps will display
        # the image rotated, and any template computations are likely to want
        # to make decisions based on the "visual", not the "real" dimensions.
        # thumbnail code also depends on this behaviour.)
        fp.seek(0)
        if is_rotated(fp):
            width, height = height, width
    else:
        fmt = None

    return fmt, width, height


def read_exif(fp):
    """Reads exif data from a file pointer of an image and returns it."""
    exif = exifread.process_file(fp)
    return EXIFInfo(exif)


def is_rotated(fp):
    """Fast version of read_exif(fp).is_rotated, using an exif header subset."""
    exif = exifread.process_file(fp, stop_tag="Orientation", details=False)
    return EXIFInfo(exif).is_rotated


def find_imagemagick(im=None):
    """Finds imagemagick and returns the path to it."""
    # If it's provided explicitly and it's valid, we go with that one.
    if im is not None and os.path.isfile(im):
        return im

    # On windows, imagemagick was renamed to magick, because
    # convert is system utility for fs manipulation.
    imagemagick_exe = "convert" if os.name != "nt" else "magick"

    rv = locate_executable(imagemagick_exe)
    if rv is not None:
        return rv

    # Give up.
    raise RuntimeError("Could not locate imagemagick.")


def get_thumbnail_ext(source_filename):
    ext = source_filename.rsplit(".", 1)[-1].lower()
    # if the extension is already of a format that a browser understands
    # we will roll with it.
    if ext.lower() in ("png", "jpg", "jpeg", "gif"):
        return None
    # Otherwise we roll with JPEG as default.
    return ".jpeg"


def get_quality(source_filename):
    ext = source_filename.rsplit(".", 1)[-1].lower()
    if ext.lower() == "png":
        return 75
    return 85


def compute_dimensions(width, height, source_width, source_height):
    """computes the bounding dimensions"""
    computed_width, computed_height = width, height

    width, height, source_width, source_height = (
        None if v is None else float(v)
        for v in (width, height, source_width, source_height)
    )

    source_ratio = source_width / source_height

    def _round(x):
        # make sure things get top-rounded, to be consistent with imagemagick
        return int(decimal.Decimal(x).to_integral(decimal.ROUND_HALF_UP))

    if width is None or (height is not None and width / height > source_ratio):
        computed_width = _round(height * source_ratio)
    else:
        computed_height = _round(width / source_ratio)

    return computed_width, computed_height


def process_image(
    ctx,
    source_image,
    dst_filename,
    width=None,
    height=None,
    mode=ThumbnailMode.DEFAULT,
    quality=None,
):
    """Build image from source image, optionally compressing and resizing.

    "source_image" is the absolute path of the source in the content directory,
    "dst_filename" is the absolute path of the target in the output directory.
    """
    if width is None and height is None:
        raise ValueError("Must specify at least one of width or height.")

    im = find_imagemagick(ctx.build_state.config["IMAGEMAGICK_EXECUTABLE"])

    if quality is None:
        quality = get_quality(source_image)

    resize_key = ""
    if width is not None:
        resize_key += str(width)
    if height is not None:
        resize_key += "x" + str(height)

    if mode == ThumbnailMode.STRETCH:
        resize_key += "!"

    cmdline = [im, source_image, "-auto-orient"]
    if mode == ThumbnailMode.CROP:
        cmdline += [
            "-resize",
            resize_key + "^",
            "-gravity",
            "Center",
            "-extent",
            resize_key,
        ]
    else:
        cmdline += ["-resize", resize_key]

    cmdline += ["-strip", "-colorspace", "sRGB"]
    cmdline += ["-quality", str(quality), dst_filename]

    reporter.report_debug_info("imagemagick cmd line", cmdline)
    portable_popen(cmdline).wait()


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

    # temporarily fallback to "fit" in case of erroneous arguments
    # to preserve backward-compatibility.
    # this needs to change to an exception in the future.
    if mode != ThumbnailMode.FIT and (width is None or height is None):
        warnings.warn(
            f'"{mode.value}" mode requires both `width` and `height` '
            'to be specified. Falling back to "fit" mode.'
        )
        mode = ThumbnailMode.FIT

    if upscale is None and mode in (ThumbnailMode.CROP, ThumbnailMode.STRETCH):
        upscale = True

    with open(source_image, "rb") as f:
        format, source_width, source_height = get_image_info(f)

    if format is None:
        raise RuntimeError("Cannot process unknown images")

    # If we are dealing with an actual svg image, we do not actually
    # resize anything, we just return it. This is not ideal but it's
    # better than outright failing.
    if format == "svg":
        return Thumbnail(source_url_path, width, height)

    if mode == ThumbnailMode.FIT:
        computed_width, computed_height = compute_dimensions(
            width, height, source_width, source_height
        )
    else:
        computed_width, computed_height = width, height

    would_upscale = computed_width > source_width or computed_height > source_height

    # this part needs to be removed once backward-compatibility period passes
    if would_upscale and upscale is None:
        warnings.warn(
            "Your image is being scaled up since the requested thumbnail "
            "size is larger than the source. This default will change "
            "in the future. If you want to preserve the current behaviour, "
            "use `upscale=True`."
        )
        upscale = True

    if would_upscale and not upscale:
        return Thumbnail(source_url_path, source_width, source_height)

    suffix = get_suffix(width, height, mode, quality=quality)
    dst_url_path = get_dependent_url(
        source_url_path, suffix, ext=get_thumbnail_ext(source_image)
    )

    def build_thumbnail_artifact(artifact):
        artifact.ensure_dir()
        process_image(
            ctx,
            source_image,
            artifact.dst_filename,
            width,
            height,
            mode,
            quality=quality,
        )

    ctx.sub_artifact(artifact_name=dst_url_path, sources=[source_image])(
        build_thumbnail_artifact
    )

    return Thumbnail(dst_url_path, computed_width, computed_height)


class Thumbnail:
    """Holds information about a thumbnail."""

    def __init__(self, url_path, width, height=None):
        #: the `width` of the thumbnail in pixels.
        self.width = width
        #: the `height` of the thumbnail in pixels.
        self.height = height
        #: the URL path of the image.
        self.url_path = url_path

    def __str__(self):
        return posixpath.basename(self.url_path)
