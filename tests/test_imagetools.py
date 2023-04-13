import io
import os
import re
from pathlib import Path
from unittest import mock

import pytest
from pytest import approx

from lektor.imagetools import _compute_cropbox
from lektor.imagetools import _compute_thumbnail
from lektor.imagetools import _convert_color_profile_to_srgb
from lektor.imagetools import _get_thumbnail_url_path
from lektor.imagetools import _SaveImage
from lektor.imagetools import compute_dimensions
from lektor.imagetools import CropBox
from lektor.imagetools import ImageSize
from lektor.imagetools import make_image_thumbnail
from lektor.imagetools import Thumbnail
from lektor.imagetools import ThumbnailBuildFunc
from lektor.imagetools import ThumbnailMode

try:
    import PIL
except ModuleNotFoundError:
    PIL = None


@pytest.mark.parametrize(
    "width, height, source_width, source_height, expected",
    [
        (1, None, 100, 200, ImageSize(1, 2)),
        (1, None, 100, 249, ImageSize(1, 2)),
        (1, None, 100, 250, ImageSize(1, 3)),
        (None, 2, 100, 200, ImageSize(1, 2)),
        (10, 10, 100, 200, ImageSize(5, 10)),
        (10, 21, 100, 200, ImageSize(10, 20)),
    ],
)
def test_compute_dimensions(width, height, source_width, source_height, expected):
    size = compute_dimensions(width, height, source_width, source_height)
    assert size == expected


def test_compute_dimensions_raises_value_error():
    with pytest.raises(ValueError, match="may not both be None"):
        compute_dimensions(None, None, 10, 20)


@pytest.mark.parametrize(
    "size, source_width, source_height, expected",
    [
        (ImageSize(1, 1), 10, 20, CropBox(0, 5, 10, 15)),
        (ImageSize(1, 1), 10, 11, CropBox(0, 0, 10, 10)),
        (ImageSize(1, 1), 20, 10, CropBox(5, 0, 15, 10)),
    ],
)
def test_compute_cropbox(size, source_width, source_height, expected):
    assert _compute_cropbox(size, source_width, source_height) == expected


@pytest.fixture(scope="session")
def dummy_image():
    return PIL.Image.new("RGB", (100, 100), "#999")


@pytest.mark.parametrize("format", ["PNG", "GIF", "JPEG"])
@pytest.mark.requirespillow
def test_SaveImage_call(format, dummy_image, tmp_path):
    outpath = tmp_path / "image"
    save_image = _SaveImage.get_subclass(format)()
    with outpath.open("wb") as fp:
        save_image(dummy_image, fp)
    image = PIL.Image.open(outpath)
    assert image.width == dummy_image.width
    assert image.height == dummy_image.height
    assert image.format == format


def test_SaveImage_get_subclass_unknown():
    assert _SaveImage.get_subclass("UNKNOWN") is None


@pytest.mark.parametrize(
    "quality, compress_level",
    [
        (None, 7),
        (92, 9),
        (150, 9),
        (75, 7),
        (-10, 0),
    ],
)
def test_SavePNG_compress_level(quality, compress_level):
    save_image = _SaveImage.get_subclass("PNG")(quality=quality)
    assert save_image.params["compress_level"] == compress_level


@pytest.mark.requirespillow
def test_convert_color_profile_to_srgb():
    demo_project = Path(__file__).parent / "demo-project"
    im = PIL.Image.open(demo_project / "content/colorspace-test/rgb-to-gbr-test.jpg")
    # Top center of image is blue before color transform
    assert im.getpixel((im.width // 2, 0)) == approx((0, 0, 255), abs=10)

    _convert_color_profile_to_srgb(im)
    # Top center of image is red after color transform
    assert im.getpixel((im.width // 2, 0)) == approx((255, 0, 0), abs=10)


@pytest.mark.requirespillow
def test_convert_color_profile_to_srgb_add_profile():
    im = PIL.Image.new("RGB", (100, 100), "#999")
    _convert_color_profile_to_srgb(im)
    profile = PIL.ImageCms.getOpenProfile(io.BytesIO(im.info["icc_profile"]))
    profile_name = PIL.ImageCms.getProfileName(profile)
    assert re.match(r"sRGB\b", profile_name)


@pytest.mark.requirespillow
def test_compute_thumbnail(dummy_image):
    infp = io.BytesIO()
    dummy_image.save(infp, "PNG")
    infp.seek(0)
    outfp = io.BytesIO()
    _compute_thumbnail(infp, outfp, ImageSize(10, 15), "JPEG", crop=True)
    outfp.seek(0)
    thumb = PIL.Image.open(outfp)
    assert thumb.width == 10 and thumb.height == 15
    assert thumb.getpixel((5, 7)) == approx((153, 153, 153), abs=5)


@pytest.mark.requirespillow
def test_compute_thumbnail_unrecognized_format():
    with pytest.raises(ValueError, match="unrecognized format"):
        _compute_thumbnail(io.BytesIO(), io.BytesIO(), ImageSize(10, 10), "UNKNOWN")


def test_compute_thumbnail_no_pillow(monkeypatch):
    monkeypatch.setattr("lektor.imagetools.HAVE_PILLOW", False)
    with pytest.raises(RuntimeError, match="(?i)requires Pillow"):
        _compute_thumbnail(io.BytesIO(), io.BytesIO(), ImageSize(10, 10), "PNG")


@pytest.mark.parametrize(
    "source_url_path, format, thumbnail_url_path",
    [
        ("/urlpath/foo.bar.JPG", "JPEG", "/urlpath/foo.bar@suffix.JPG"),
        ("/urlpath/foo.bar", "JPEG", "/urlpath/foo@suffix.jpeg"),
    ],
)
def test_get_thumbnail_url_path(source_url_path, format, thumbnail_url_path):
    source_filename = os.fspath(Path("/fspath") / Path(source_url_path).name)
    assert (
        _get_thumbnail_url_path(source_url_path, source_filename, format, "suffix")
        == thumbnail_url_path
    )


@pytest.fixture(scope="session")
def dummy_jpg_path(tmp_path_factory):
    dummy_jpg = tmp_path_factory.mktemp("images") / "dummy.jpg"
    im = PIL.Image.new("RGB", (400, 300), "#999")
    with dummy_jpg.open("wb") as fp:
        im.save(fp, "JPEG")
    return dummy_jpg


@pytest.mark.parametrize(
    "source_url_path, kwargs, expected_size, thumbnail_url_path",
    [
        ("/test.jpg", {"width": 80, "height": 80}, (80, 60), "/test@80x80.jpg"),
        ("/test.jpg", {"width": 80}, (80, 60), "/test@80.jpg"),
        ("/test.jpg", {"height": 90, "quality": 85}, (120, 90), "/test@x90_q85.jpg"),
        ("/test.jpg", {"width": 500}, (400, 300), "/test.jpg"),
        (
            "/test.jpg",
            {"width": 80, "height": 80, "mode": ThumbnailMode.CROP},
            (80, 80),
            "/test@80x80_crop.jpg",
        ),
        (
            "/test.jpg",
            {"width": 80, "height": 80, "mode": ThumbnailMode.STRETCH},
            (80, 80),
            "/test@80x80_stretch.jpg",
        ),
    ],
)
@pytest.mark.requirespillow
def test_make_image_thumbnail(
    source_url_path, kwargs, expected_size, thumbnail_url_path, dummy_jpg_path
):
    ctx = mock.Mock(name="ctx")
    thumbnail = make_image_thumbnail(ctx, dummy_jpg_path, source_url_path, **kwargs)
    assert (thumbnail.width, thumbnail.height) == expected_size
    assert thumbnail.url_path == thumbnail_url_path


@pytest.mark.requirespillow
def test_make_image_thumbnail_fallback_to_fit_mode(dummy_jpg_path):
    ctx = mock.Mock(name="ctx")
    with pytest.warns(UserWarning, match=r"(?i)falling back to .*\bfit\b.* mode"):
        thumbnail = make_image_thumbnail(
            ctx, dummy_jpg_path, "/test.jpg", width=80, mode=ThumbnailMode.CROP
        )
    assert (thumbnail.width, thumbnail.height) == (80, 60)
    assert thumbnail.url_path == "/test@80.jpg"


@pytest.mark.requirespillow
def test_make_image_thumbnail_no_dims(dummy_jpg_path):
    ctx = mock.Mock(name="ctx")
    with pytest.raises(ValueError, match="at least one of width or height"):
        make_image_thumbnail(ctx, dummy_jpg_path, "/test.jpg")


def test_make_image_thumbnail_unknown_image_format(tmp_path):
    ctx = mock.Mock(name="ctx")
    image_path = tmp_path / "test.jpg"
    image_path.write_bytes(b"junk")
    with pytest.raises(RuntimeError, match="unknown"):
        make_image_thumbnail(ctx, image_path, "/test.jpg", width=80)


def test_make_image_thumbnail_svg(tmp_path):
    dummy_svg = tmp_path / "dummy.svg"
    dummy_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400px" height="300px"></svg>'
    )
    ctx = mock.Mock(name="ctx")
    thumbnail = make_image_thumbnail(
        ctx, dummy_svg, "/urlpath/dummy.svg", width=80, height=60
    )
    assert (thumbnail.width, thumbnail.height) == (80, 60)
    assert thumbnail.url_path == "/urlpath/dummy.svg"


@pytest.mark.requirespillow
def test_ThumbnailBuildFunc(dummy_jpg_path, tmp_path):
    artifact = tmp_path / "thumb.png"
    build_func = ThumbnailBuildFunc(
        source_image=dummy_jpg_path,
        size=ImageSize(80, 60),
        format="PNG",
    )
    build_func(artifact)
    im = PIL.Image.open(artifact)
    assert im.width == 80 and im.height == 60
    assert im.format == "PNG"


def test_Thumbnail_str():
    thumbnail = Thumbnail("/urlpath/image.jpg", 50, 80)
    assert str(thumbnail) == "image.jpg"
