# -*- coding: utf-8 -*-
import decimal
import json
import os
import subprocess
from collections import namedtuple
from datetime import timedelta

from lektor.imagetools import Thumbnail
from lektor.imagetools import ThumbnailMode
from lektor.reporter import reporter
from lektor.utils import get_dependent_url
from lektor.utils import locate_executable
from lektor.utils import portable_popen


THUMBNAIL_FORMATS = frozenset(["jpg", "jpeg", "png"])


def _imround(x):
    """Round float pixel values like imagemagick does it."""
    return decimal.Decimal(x).to_integral(decimal.ROUND_HALF_UP)


Rescaling = namedtuple("Rescaling", ["rescale", "crop"])


class Dimensions(namedtuple("Dimensions", ["width", "height"])):
    __slots__ = ()

    def __new__(cls, width, height):
        width = int(width)
        height = int(height)

        if width < 1 or height < 1:
            raise ValueError("Invalid dimensions")

        return super(Dimensions, cls).__new__(cls, width, height)

    @property
    def aspect_ratio(self):
        return float(self.width) / float(self.height)

    def _infer_dimensions(self, width, height):
        """Calculate dimensions based on aspect ratio if height, width or both
        are missing.
        """
        if width is None and height is None:
            return self

        if width is None:
            width = _imround(height * self.aspect_ratio)
        elif height is None:
            height = _imround(width / self.aspect_ratio)

        return Dimensions(width, height)

    def contains(self, other):
        """Return True if the given Dimensions can be completely enclosed by
        this Dimensions.
        """
        return self.width >= other.width and self.height >= other.height

    def fit_within(self, max_width=None, max_height=None, upscale=None):
        """Calculate resizing required to make these dimensions fit within the
        given dimensions.

        Note that resizing only occurs if upscale is enabled.

            >>> source = Dimensions(640, 480)
            >>> source.fit_within(max_width=320).rescale == Dimensions(320, 240)
            True

        :param max_width: Maximum width for the new rescaled dimensions.
        :param max_height: Maximum height for the new rescaled dimensions.
        :param upscale: Allow making the dimensions larger (default False).
        :return: Rescaling operations
        :rtype: Rescaling
        """
        if upscale is None:
            upscale = False

        max_dim = self._infer_dimensions(max_width, max_height)

        # Check if we should rescale at all
        if max_dim == self or (not upscale and max_dim.contains(self)):
            return Rescaling(self, self)

        ar = self.aspect_ratio
        rescale_dim = Dimensions(
            width=_imround(min(max_dim.width, max_dim.height * ar)),
            height=_imround(min(max_dim.height, max_dim.width / ar)),
        )

        return Rescaling(rescale=rescale_dim, crop=rescale_dim)

    def cover(self, min_width=None, min_height=None, upscale=None):
        """Calculate resizing required to make these dimensions cover the given
        dimensions.

        Note that resizing only occurs if upscale is enabled.

            >>> source = Dimensions(640, 480)
            >>> target = source.cover(240, 240)
            >>> target.rescale == Dimensions(320, 240)
            True
            >>> target.crop == Dimensions(240, 240)
            True

        :param min_width: Minimum width for the new rescaled dimensions.
        :param min_height: Minimum height for the new rescaled dimensions.
        :param upscale: Allow making the dimensions larger (default True).
        :return: Rescaling operations
        :rtype: Rescaling
        """
        if upscale is None:
            upscale = True

        min_dim = self._infer_dimensions(min_width, min_height)

        # Check if we should rescale at all
        if min_dim == self or (not upscale and min_dim.contains(self)):
            return Rescaling(self, self)

        ar = self.aspect_ratio
        rescale_dim = Dimensions(
            width=_imround(max(min_dim.width, min_dim.height * ar)),
            height=_imround(max(min_dim.height, min_dim.width / ar)),
        )

        return Rescaling(rescale=rescale_dim, crop=min_dim)

    def stretch(self, width=None, height=None, upscale=None):
        """Calculate resizing required to the given dimensions without
        considering aspect ratio.

        Note that resizing only occurs if upscale is enabled.

            >>> source = Dimensions(640, 480)
            >>> source.cover(240, 240).rescale == Dimensions(240, 240)
            True

        :param min_width: Minimum width for the new rescaled dimensions.
        :param min_height: Minimum height for the new rescaled dimensions.
        :param upscale: Allow making the dimensions larger (default True).
        :return: Rescaling operations
        :rtype: Rescaling
        """
        if upscale is None:
            upscale = True

        dim = self._infer_dimensions(width, height)

        # Check if we should rescale at all
        if dim == self or (not upscale and dim.contains(self)):
            return Rescaling(self, self)

        return Rescaling(rescale=dim, crop=dim)

    def resize(self, width=None, height=None, mode=ThumbnailMode.DEFAULT, upscale=None):
        if mode == ThumbnailMode.FIT:
            return self.fit_within(width, height, upscale)
        if mode == ThumbnailMode.CROP:
            return self.cover(width, height, upscale)
        if mode == ThumbnailMode.STRETCH:
            return self.stretch(width, height, upscale)

        raise ValueError('Unexpected mode "{!r}"'.format(mode))


def get_timecode(td):
    """Convert a timedelta to an ffmpeg compatible string timecode.

    A timecode has the format HH:MM:SS, with decimals if needed.
    """
    seconds = td.total_seconds()

    hours = int(seconds // 3600)
    seconds %= 3600

    minutes = int(seconds // 60)
    seconds %= 60

    str_seconds, str_decimals = str(float(seconds)).split(".")

    timecode = "{:02d}:{:02d}:{}".format(hours, minutes, str_seconds.zfill(2))
    if str_decimals != "0":
        timecode += ".{}".format(str_decimals)

    return timecode


def get_ffmpeg_quality(quality_percent):
    """Convert a value between 0-100 to an ffmpeg quality value (2-31).

    Note that this is only applicable to the mjpeg encoder (which is used for
    jpeg images). mjpeg values works in reverse, i.e. lower is better.
    """
    if not 0 <= quality_percent <= 100:
        raise ValueError("Video quality must be between 0 and 100")

    low, high = 2, 31
    span = high - low
    factor = float(quality_percent) / 100.0
    return int(low + round(span * (1 - factor)))


def get_suffix(seek, width, height, mode, quality):
    """Make suffix for a thumbnail that is unique to the given parameters."""
    timecode = get_timecode(seek).replace(":", "-").replace(".", "-")
    suffix = "t%s" % timecode

    if width is not None or height is not None:
        suffix += "_%s" % "x".join(str(x) for x in [width, height] if x is not None)

    if mode != ThumbnailMode.DEFAULT:
        suffix += "_%s" % mode.value

    if quality is not None:
        suffix += "_q%s" % quality

    return suffix


def get_video_info(filename):
    """Read video information using ffprobe if available.

    Returns a dict with: width, height and duration.
    """
    ffprobe = locate_executable("ffprobe")
    if ffprobe is None:
        raise RuntimeError("Failed to locate ffprobe")

    proc = portable_popen(
        [
            ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            filename,
        ],
        stdout=subprocess.PIPE,
    )
    stdout, _ = proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError("ffprobe exited with code %d" % proc.returncode)

    ffprobe_data = json.loads(stdout.decode("utf8"))
    info = {
        "width": None,
        "height": None,
        "duration": None,
    }

    # Try to extract total video duration
    try:
        info["duration"] = timedelta(seconds=float(ffprobe_data["format"]["duration"]))
    except (KeyError, TypeError, ValueError):
        pass

    # Try to extract width and height from the first found video stream
    for stream in ffprobe_data["streams"]:
        if stream["codec_type"] != "video":
            continue

        info["width"] = int(stream["width"])
        info["height"] = int(stream["height"])

        # We currently don't bother with multiple video streams
        break

    return info


def make_video_thumbnail(
    ctx,
    source_video,
    source_url_path,
    seek,
    width=None,
    height=None,
    mode=ThumbnailMode.DEFAULT,
    upscale=None,
    quality=None,
    format=None,
):
    if mode != ThumbnailMode.FIT and (width is None or height is None):
        msg = '"%s" mode requires both `width` and `height` to be defined.'
        raise ValueError(msg % mode.value)

    if upscale is None:
        upscale = {
            ThumbnailMode.FIT: False,
            ThumbnailMode.CROP: True,
            ThumbnailMode.STRETCH: True,
        }[mode]

    if format is None:
        format = "jpg"
    if format not in THUMBNAIL_FORMATS:
        raise ValueError('Invalid thumbnail format "%s"' % format)

    if quality is not None and format != "jpg":
        raise ValueError("The quality parameter is only supported for jpeg images")

    if seek < timedelta(0):
        raise ValueError("Seek must not be negative")

    ffmpeg = locate_executable("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Failed to locate ffmpeg")
    info = get_video_info(source_video)

    source_dim = Dimensions(info["width"], info["height"])
    resize_dim, crop_dim = source_dim.resize(width, height, mode, upscale)

    # Construct a filename suffix unique to the given parameters
    suffix = get_suffix(seek, width, height, mode=mode, quality=quality)
    dst_url_path = get_dependent_url(source_url_path, suffix, ext=".{}".format(format))

    if quality is None and format == "jpg":
        quality = 95

    def build_thumbnail_artifact(artifact):
        artifact.ensure_dir()

        vfilter = "thumbnail,scale={rw}:{rh},crop={tw}:{th}".format(
            rw=resize_dim.width,
            rh=resize_dim.height,
            tw=crop_dim.width,
            th=crop_dim.height,
        )

        cmdline = [
            ffmpeg,
            "-loglevel",
            "-8",
            "-ss",
            get_timecode(seek),  # Input seeking since it's faster
            "-i",
            source_video,
            "-vf",
            vfilter,
            "-frames:v",
            "1",
            "-qscale:v",
            str(get_ffmpeg_quality(quality)),
            artifact.dst_filename,
        ]

        reporter.report_debug_info("ffmpeg cmd line", cmdline)
        proc = portable_popen(cmdline)
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg exited with code {}".format(proc.returncode))

        if not os.path.exists(artifact.dst_filename):
            msg = (
                "Unable to create video thumbnail for {!r}. Maybe the seek "
                "is outside of the video duration?"
            )
            raise RuntimeError(msg.format(source_video))

    ctx.sub_artifact(artifact_name=dst_url_path, sources=[source_video])(
        build_thumbnail_artifact
    )

    return Thumbnail(dst_url_path, crop_dim.width, crop_dim.height)
