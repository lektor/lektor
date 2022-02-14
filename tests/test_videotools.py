import os
from datetime import timedelta

import pytest

from lektor.utils import locate_executable
from lektor.videotools import Dimensions
from lektor.videotools import get_ffmpeg_quality
from lektor.videotools import get_timecode


has_ffmpeg = locate_executable("ffmpeg")
has_ffprobe = locate_executable("ffprobe")
require_ffmpeg = pytest.mark.skipif(
    not has_ffmpeg or not has_ffprobe, reason="requires ffmpeg and ffprobe in path"
)


@pytest.mark.parametrize(
    "td, tc",
    [
        (timedelta(), "00:00:00"),
        (timedelta(seconds=1), "00:00:01"),
        (timedelta(seconds=1.5), "00:00:01.5"),
        (timedelta(hours=8, minutes=15), "08:15:00"),
        (timedelta(hours=36, minutes=35, seconds=34.25), "36:35:34.25"),
    ],
)
def test_get_timecode(td, tc):
    assert get_timecode(td) == tc


@pytest.mark.parametrize(
    "in_quality, out_quality",
    [
        (0, 31),
        (100, 2),
    ],
)
def test_get_ffmpeg_quality(in_quality, out_quality):
    assert get_ffmpeg_quality(in_quality) == out_quality


@pytest.mark.parametrize(
    "in_quality",
    [
        -1,
        101,
    ],
)
def test_get_ffmpeg_quality_bad_range(in_quality):
    with pytest.raises(ValueError):
        get_ffmpeg_quality(in_quality)


@pytest.mark.parametrize(
    "dim, ar",
    [
        (Dimensions(100, 100), 1),
        (Dimensions(320, 160), 2),
        (Dimensions(160, 320), 0.5),
    ],
)
def test_dimensions_aspect_ratio(dim, ar):
    assert dim.aspect_ratio == ar


@pytest.mark.parametrize(
    "source, target, upscale, rescale",
    [
        ((100, 100), (50, None), None, (50, 50)),
        ((100, 50), (50, None), None, (50, 25)),
        ((100, 50), (None, 25), None, (50, 25)),
    ],
)
def test_dimensions_fit_within(source, target, upscale, rescale):
    # We don't take a crop parameter here since it will always be the same as
    # rescale
    source = Dimensions(*source)
    target_width, target_height = target
    rescale = Dimensions(*rescale)

    new_dims = source.fit_within(target_width, target_height, upscale)
    assert rescale == new_dims.rescale
    assert rescale == new_dims.crop


@pytest.mark.parametrize(
    "source, target, upscale, rescale, crop",
    [
        ((100, 50), (25, 25), None, (50, 25), (25, 25)),
        ((100, 50), (100, 100), None, (200, 100), (100, 100)),
        ((100, 50), (100, 100), False, (100, 50), (100, 50)),
    ],
)
def test_dimensions_cover(source, target, upscale, rescale, crop):
    source = Dimensions(*source)
    target_width, target_height = target
    rescale = Dimensions(*rescale)
    crop = Dimensions(*crop)

    new_dims = source.cover(target_width, target_height, upscale)
    assert rescale == new_dims.rescale
    assert crop == new_dims.crop


@pytest.mark.parametrize(
    "source, target, upscale, rescale",
    [
        ((100, 50), (25, 25), None, (25, 25)),
        ((100, 50), (100, 100), None, (100, 100)),
        ((100, 50), (100, 100), False, (100, 50)),
    ],
)
def test_dimensions_stretch(source, target, upscale, rescale):
    # We don't take a crop parameter here since it will always be the same as
    # rescale
    source = Dimensions(*source)
    target_width, target_height = target
    rescale = Dimensions(*rescale)

    new_dims = source.stretch(target_width, target_height, upscale)
    assert rescale == new_dims.rescale
    assert rescale == new_dims.crop


def test_dimensions_invalid_resize():
    dim = Dimensions(640, 480)
    with pytest.raises(ValueError):
        dim.resize(mode="invalid")


@require_ffmpeg
def test_metadata(pad):
    video = pad.root.attachments.videos.get("test.mp4")
    assert video is not None

    assert video.width == 320
    assert video.height == 180
    assert video.duration == timedelta(seconds=3)


@require_ffmpeg
def test_thumbnail_height(builder):
    builder.build_all()
    with open(
        os.path.join(builder.destination_path, "index.html"), encoding="utf-8"
    ) as f:
        html = f.read()

    # The first thumbnail has the same dimensions as the source video,
    # seeked to 1.5 seconds in
    assert '<img src="test@t00-00-01-5.jpg" width="320" height="180">' in html

    # Thumbnail is half the original width, so its computed height is half.
    assert '<img src="test@t00-00-00_160.jpg" width="160" height="90">' in html

    # There should also be a square thumbnail
    assert (
        '<img src="test@t00-00-02_160x160_crop.jpg" width="160" height="160">' in html
    )
