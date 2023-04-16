from __future__ import annotations

import dataclasses
import datetime
import html.parser
import io
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path
from unittest import mock
from xml.sax import saxutils

import PIL
import pytest
from pytest import approx

from lektor.imagetools import _combine_make
from lektor.imagetools import _compute_cropbox
from lektor.imagetools import _convert_color_profile_to_srgb
from lektor.imagetools import _create_artifact
from lektor.imagetools import _create_thumbnail
from lektor.imagetools import _get_thumbnail_url_path
from lektor.imagetools import _parse_svg_units_px
from lektor.imagetools import _save_position
from lektor.imagetools import _to_degrees
from lektor.imagetools import _to_flash_description
from lektor.imagetools import _to_float
from lektor.imagetools import _to_focal_length
from lektor.imagetools import _to_string
from lektor.imagetools import compute_dimensions
from lektor.imagetools import CropBox
from lektor.imagetools import EXIFInfo
from lektor.imagetools import get_image_info
from lektor.imagetools import ImageSize
from lektor.imagetools import make_image_thumbnail
from lektor.imagetools import read_exif
from lektor.imagetools import Thumbnail
from lektor.imagetools import ThumbnailMode
from lektor.imagetools import ThumbnailParams


HERE = Path(__file__).parent
DEMO_PROJECT = HERE / "demo-project/content"
COLORSPACE_TEST_JPG = DEMO_PROJECT / "colorspace-test/rgb-to-gbr-test.jpg"
NONIMAGE_FILE_PATH = Path(__file__)  # we are not an image

EXIF_ORIENTATION_TAG = 0x0112


@pytest.mark.parametrize(
    "make, model, expected",
    [
        ("Frobnotz", "Frobnicator v42", "Frobnotz Frobnicator v42"),
        ("Frobnotz", None, "Frobnotz"),
        (None, "Frobnicator v42", "Frobnicator v42"),
        ("Frobnotz", "Frobnotz Frobnicator v42", "Frobnotz Frobnicator v42"),
        (None, None, ""),
    ],
)
def test_combine_make(make, model, expected):
    assert _combine_make(make, model) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (0x41, "Flash fired, red-eye reduction mode"),
        (0x100, "Flash did not fire (256)"),
        (0x101, "Flash fired (257)"),
        (-1, "Flash fired (-1)"),
    ],
)
def test_to_flash_description(value, expected):
    assert _to_flash_description(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("a b", "a b"),
        ("a\xc2\xa0b", "a\xa0b"),
        ("a\xa0b", "a\xa0b"),
    ],
)
def test_to_string(value, expected):
    assert _to_string(value) == expected


def test_to_float():
    assert _to_float(Fraction("22/3")) == approx(7.3333, rel=1e-8)


def test_to_focal_length():
    assert _to_focal_length(Fraction("45/2")) == "22.5mm"


@pytest.mark.parametrize(
    "coords, hemisphere, expected",
    [
        (("45", "15", "30"), "N", approx(45.2583333)),
        (("45", "61/2", "0"), "S", approx(-45.5083333)),
        (("122", "0", "0"), "W", -122),
        (("45/2", "0", "0"), "E", 22.5),
    ],
)
def test_to_degrees(coords, hemisphere, expected):
    assert (
        _to_degrees(tuple(Fraction(coord) for coord in coords), hemisphere) == expected
    )


TEST_JPG_EXIF_INFO = {
    "altitude": approx(779.0293),
    "aperture": approx(2.275),
    "artist": None,
    "camera": "Apple iPhone 6",
    "camera_make": "Apple",
    "camera_model": "iPhone 6",
    "copyright": None,
    "created_at": datetime.datetime(2015, 12, 6, 11, 37, 38),
    "exposure_time": "1/33",
    "f": "ƒ/2.2",
    "f_num": approx(2.2),
    "flash_info": "Flash did not fire, compulsory flash mode",
    "focal_length": "4.2mm",
    "focal_length_35mm": "29mm",
    "iso": 160,
    "latitude": approx(46.633833),
    "lens": "Apple iPhone 6 back camera 4.15mm f/2.2",
    "lens_make": "Apple",
    "lens_model": "iPhone 6 back camera 4.15mm f/2.2",
    "longitude": approx(13.404833),
    "location": approx((46.633833, 13.404833)),
    "shutter_speed": "1/33",
    "documentname": "testName",
    "description": "testDescription",
    "is_rotated": True,
}

# This is the default ExifINFO for images without EXIF data
NULL_EXIF_INFO = {
    "altitude": None,
    "aperture": None,
    "artist": None,
    "camera": "",
    "camera_make": None,
    "camera_model": None,
    "copyright": None,
    "created_at": None,
    "description": None,
    "documentname": None,
    "exposure_time": None,
    "f": None,
    "f_num": None,
    "flash_info": None,
    "focal_length": None,
    "focal_length_35mm": None,
    "is_rotated": False,
    "iso": None,
    "latitude": None,
    "lens": "",
    "lens_make": None,
    "lens_model": None,
    "location": None,
    "longitude": None,
    "shutter_speed": None,
}

TEST_IMAGE_EXIF_INFO = {
    DEMO_PROJECT / "test.jpg": TEST_JPG_EXIF_INFO,
    DEMO_PROJECT / "test-sof-last.jpg": TEST_JPG_EXIF_INFO,
    DEMO_PROJECT / "test-progressive.jpg": NULL_EXIF_INFO,
    HERE / "exif-test-2.gif": NULL_EXIF_INFO,
    (HERE / "exif-test-1.jpg"): {
        "altitude": None,
        "aperture": None,
        "artist": "Geoffrey T. Dairiki",
        "camera": "NIKON CORPORATION NIKON D7100",
        "camera_make": "NIKON CORPORATION",
        "camera_model": "NIKON D7100",
        "copyright": "2015",
        "created_at": datetime.datetime(2022, 10, 22, 9, 20, 56),
        "description": None,
        "documentname": None,
        "exposure_time": "1/400",
        "f": "ƒ/4.5",
        "f_num": 4.5,
        "flash_info": "Flash did not fire, compulsory flash mode",
        "focal_length": "86mm",
        "focal_length_35mm": "129mm",
        "is_rotated": False,
        "iso": 1250,
        "latitude": None,
        "lens": "",
        "lens_make": None,
        "lens_model": None,
        "location": None,
        "longitude": None,
        "shutter_speed": None,
    },
}


@pytest.mark.parametrize(
    "path, attr, expected",
    [
        (path, attr, expected)
        for path, tags in TEST_IMAGE_EXIF_INFO.items()
        for attr, expected in tags.items()
    ],
)
def test_read_exif_attr(path, attr, expected):
    with path.open("rb") as fp:
        exif = read_exif(fp)
    assert getattr(exif, attr) == expected


def test_read_exif_unrecognized_image():
    exif_info = read_exif(io.BytesIO(b"unrecognized-image"))
    assert not exif_info


def make_exif(gps_data):
    """Construct a PIL.Image.Exif instance from GPS IFD data"""
    ifd0 = PIL.Image.Exif()
    ifd0[PIL.ExifTags.IFD.GPSInfo] = dict(gps_data)
    exif = PIL.Image.Exif()
    exif.load(ifd0.tobytes())
    return exif


@pytest.mark.parametrize(
    "gps_data, expected",
    [
        (
            {
                PIL.ExifTags.GPS.GPSAltitude: Fraction("1234/10"),
                PIL.ExifTags.GPS.GPSAltitudeRef: b"\x00",
            },
            approx(123.4),
        ),
        (
            {
                PIL.ExifTags.GPS.GPSAltitude: Fraction("123/10"),
                PIL.ExifTags.GPS.GPSAltitudeRef: b"\x01",
            },
            approx(-12.3),
        ),
        ({PIL.ExifTags.GPS.GPSAltitude: Fraction("1234/10")}, approx(123.4)),
    ],
)
def test_EXIFInfo_altitude(gps_data, expected):
    exif = make_exif(gps_data)
    exif_info = EXIFInfo(exif)
    assert exif_info.altitude == expected


@pytest.mark.parametrize(
    "dimension, pixels",
    [
        ("123", 123),
        ("50%", None),
        ("42px", 42),
        ("42.5 px", 42.5),
    ],
)
def test_parse_svg_units_px(dimension, pixels):
    assert _parse_svg_units_px(dimension) == pixels


@dataclasses.dataclass
class DummyImage:
    width: int
    height: int
    format: str = "PNG"
    orientation: int | None = None

    def open(self):
        fp = io.BytesIO()
        image = PIL.Image.new("RGB", (self.width, self.height), "#999")
        exif = image.getexif()
        if self.orientation is not None:
            exif[EXIF_ORIENTATION_TAG] = self.orientation
        image.save(fp, self.format, exif=exif)
        fp.seek(0)
        return fp


@dataclasses.dataclass
class DummySVGImage:
    width: int | str | None = None
    height: int | str | None = None
    xmlns: str | None = "http://www.w3.org/2000/svg"
    xml_decl: str | None = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'

    def open(self):
        values = dataclasses.asdict(self)
        svg_attrs = "".join(
            f" {key}={saxutils.quoteattr(values[key])}"
            for key in ("width", "height", "xmlns")
            if values[key] is not None
        )
        svg = (
            f'{self.xml_decl or ""}'
            f"<svg{svg_attrs}>"
            '<circle cx="50" cy="50" r="50" fill="lightgrey"/>'
            '<circle cx="30" cy="30" r="10" fill="black"/>'
            '<circle cx="60" cy="30" r="10" fill="black"/>'
            '<path stroke="black" d="M30 70 l30 0" stroke-width="5"/>'
            "</svg>"
        )
        return io.BytesIO(svg.encode("utf-8"))


@dataclasses.dataclass
class DummyFile:
    content: bytes = b""

    def open(self):
        return io.BytesIO(self.content)


@pytest.mark.parametrize(
    "image, expected",
    [
        (DummyFile(b"short"), (None, None, None)),
        (DummyFile(b"Not an image. " * 40), (None, None, None)),
        (DummyImage(10, 20, "JPEG"), ("jpeg", 10, 20)),
        (DummyImage(10, 20, "GIF"), ("gif", 10, 20)),
        (DummyImage(10, 20, "PNG"), ("png", 10, 20)),
        (DummyImage(10, 20, "JPEG", orientation=5), ("jpeg", 20, 10)),
        (DummyImage(10, 20, "PNG", orientation=7), ("png", 20, 10)),
        (DummyImage(10, 20, "PPM"), (None, None, None)),
        (DummySVGImage("10px", "20px"), ("svg", 10, 20)),
        (DummySVGImage("10", "20", xml_decl=None), ("svg", 10, 20)),
        (DummySVGImage(None, None), ("svg", None, None)),
        (DummySVGImage("invalid-width", "invalid-height"), ("svg", None, None)),
        (DummySVGImage("10px", "10px", xmlns=None), (None, None, None)),
    ],
)
def test_get_image_info(image, expected):
    assert get_image_info(image.open()) == expected


def test_save_position():
    fp = io.BytesIO(b"data")
    with _save_position(fp) as infp:
        assert infp.read() == b"data"
    assert fp.read() == b"data"


def test_ThumbnailParams_unrecognized_format():
    with pytest.raises(ValueError, match="unrecognized format"):
        ThumbnailParams(ImageSize(80, 60), "UNKNOWNFORMAT")


@pytest.mark.parametrize(
    "format, quality, expected",
    [
        ("GIF", None, {"format": "GIF"}),
        ("gif", 99, {"format": "GIF"}),
        ("JPEG", None, {"format": "JPEG", "quality": 85}),
        ("JPEG", 95, {"format": "JPEG", "quality": 95}),
        ("PNG", None, {"format": "PNG", "compress_level": 7}),
        ("PNG", 92, {"format": "PNG", "compress_level": 9}),
        ("PNG", 180, {"format": "PNG", "compress_level": 9}),
        ("PNG", 75, {"format": "PNG", "compress_level": 7}),
        ("PNG", -10, {"format": "PNG", "compress_level": 0}),
    ],
)
def test_ThumbnailParams_get_save_params(format, quality, expected):
    thumbnail_params = ThumbnailParams(ImageSize(10, 10), format, quality)
    assert thumbnail_params.get_save_params() == expected


@pytest.mark.parametrize(
    "width, height, source_width, source_height, expected",
    [
        (1, None, 100, 200, ImageSize(1, 2)),
        (1, None, 100, 249, ImageSize(1, 2)),
        (1, None, 100, 250, ImageSize(1, 3)),
        (None, 2, 100, 200, ImageSize(1, 2)),
        (10, 10, 100, 200, ImageSize(5, 10)),
        (10, 21, 100, 200, ImageSize(10, 20)),
        # tests from test_images.py::test_dimensions
        # landscape
        (50, 50, 100, 50, ImageSize(50, 25)),
        (100, 20, 100, 50, ImageSize(40, 20)),
        (200, 200, 100, 50, ImageSize(200, 100)),
        (500, 200, 100, 50, ImageSize(400, 200)),
        # test missing dimension
        (50, None, 100, 50, ImageSize(50, 25)),
        (None, 20, 100, 50, ImageSize(40, 20)),
        (200, None, 100, 50, ImageSize(200, 100)),
        (None, 200, 100, 50, ImageSize(400, 200)),
        # test that rounding is half-up
        (49, None, 100, 50, ImageSize(49, 25)),
        (51, None, 100, 50, ImageSize(51, 26)),
        #
        # portrait
        (50, 50, 50, 100, ImageSize(25, 50)),
        (20, 100, 50, 100, ImageSize(20, 40)),
        (200, 200, 50, 100, ImageSize(100, 200)),
        (200, 500, 50, 100, ImageSize(200, 400)),
        #
        (None, 50, 50, 100, ImageSize(25, 50)),
        (20, None, 50, 100, ImageSize(20, 40)),
        (None, 200, 50, 100, ImageSize(100, 200)),
        (200, None, 50, 100, ImageSize(200, 400)),
        #
        (None, 49, 50, 100, ImageSize(25, 49)),
        (None, 51, 50, 100, ImageSize(26, 51)),
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


def test_convert_color_profile_to_srgb():
    im = PIL.Image.open(COLORSPACE_TEST_JPG)
    # Top center of image is blue before color transform
    assert im.getpixel((im.width // 2, 0)) == approx((0, 0, 255), abs=10)

    _convert_color_profile_to_srgb(im)
    # Top center of image is red after color transform
    assert im.getpixel((im.width // 2, 0)) == approx((255, 0, 0), abs=10)
    assert "icc_profile" not in im.info


def test_convert_color_profile_to_srgb_no_profile():
    im = PIL.Image.new("RGB", (100, 100), "#999")
    _convert_color_profile_to_srgb(im)
    assert "icc_profile" not in im.info


def test_create_thumbnail(dummy_image):
    thumbnail_params = ThumbnailParams(ImageSize(80, 60), "PNG")
    thumb = _create_thumbnail(dummy_image, thumbnail_params)
    assert thumb.width == 80 and thumb.height == 60
    assert thumb.getpixel((40, 30)) == approx((153, 153, 153), abs=5)


class DummyArtifact:
    image = None

    @contextmanager
    def open(self, _mode):
        fp = io.BytesIO()
        yield fp
        fp.seek(0)
        self.image = PIL.Image.open(fp)


def test_create_artifact(dummy_jpg_path):
    thumbnail_params = ThumbnailParams(ImageSize(80, 60), "JPEG")
    artifact = DummyArtifact()
    _create_artifact(dummy_jpg_path, thumbnail_params, artifact)
    thumb = artifact.image
    assert thumb.width == 80 and thumb.height == 60
    assert thumb.getpixel((40, 30)) == approx((153, 153, 153), abs=5)


def test_create_artifact_strips_metadata():
    # this image has comment, dpi, exif, icc_profile, and photoshop data
    source_image = COLORSPACE_TEST_JPG
    jfif_info_keys = {"jfif", "jfif_density", "jfif_unit", "jfif_version"}
    thumbnail_params = ThumbnailParams(ImageSize(80, 60), "JPEG")
    artifact = DummyArtifact()
    _create_artifact(source_image, thumbnail_params, artifact)
    metadata_keys = set(artifact.image.info) - jfif_info_keys
    assert not metadata_keys


@pytest.mark.parametrize(
    "source_url_path, size, format, expected",
    [
        (
            "/urlpath/foo.bar.JPG",
            ImageSize(10, 20),
            "JPEG",
            "/urlpath/foo.bar@10x20.JPG",
        ),
        ("/urlpath/foo.bar", ImageSize(10, 20), "JPEG", "/urlpath/foo@10x20.jpeg"),
    ],
)
def test_get_thumbnail_url_path(source_url_path, size, format, expected):
    thumbnail_params = ThumbnailParams(size, format)
    assert _get_thumbnail_url_path(source_url_path, thumbnail_params) == expected


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
        # ThumbnailMode.FIT
        ("/test.jpg", {"width": 80, "height": 80}, (80, 60), "/test@80x60.jpg"),
        ("/test.jpg", {"width": 80}, (80, 60), "/test@80x60.jpg"),
        ("/test.jpg", {"height": 90, "quality": 85}, (120, 90), "/test@120x90_q85.jpg"),
        (
            "/test.jpg",
            {"width": 80, "mode": ThumbnailMode.FIT},
            (80, 60),
            "/test@80x60.jpg",
        ),
        # ThumbnailMode.CROP
        (
            "/test.jpg",
            {"width": 80, "height": 80, "mode": ThumbnailMode.CROP},
            (80, 80),
            "/test@80x80_crop.jpg",
        ),
        (
            "/test.jpg",
            {"width": 800, "height": 800, "mode": ThumbnailMode.CROP},
            (800, 800),
            "/test@800x800_crop.jpg",
        ),
        # ThumbnailMode.STRETCH
        (
            "/test.jpg",
            {"width": 80, "height": 80, "mode": ThumbnailMode.STRETCH},
            (80, 80),
            "/test@80x80.jpg",
        ),
        (
            "/test.jpg",
            {"width": 800, "height": 800, "mode": ThumbnailMode.STRETCH},
            (800, 800),
            "/test@800x800.jpg",
        ),
        # explicit upscale
        ("/test.jpg", {"width": 440, "upscale": True}, (440, 330), "/test@440x330.jpg"),
        # explicit upscale=False
        ("/test.jpg", {"width": 440, "upscale": False}, (400, 300), "/test.jpg"),
        # implicit upscale
        ("/test.jpg", {"width": 440}, (400, 300), "/test.jpg"),
    ],
)
def test_make_image_thumbnail(
    source_url_path, kwargs, expected_size, thumbnail_url_path, dummy_jpg_path
):
    ctx = mock.Mock(name="ctx")
    thumbnail = make_image_thumbnail(ctx, dummy_jpg_path, source_url_path, **kwargs)
    assert (thumbnail.width, thumbnail.height) == expected_size
    assert thumbnail.url_path == thumbnail_url_path
    if "@" in thumbnail_url_path:
        assert ctx.add_sub_artifact.call_count == 1
    else:
        assert len(ctx.mock_calls) == 0  # no implicit upscale


@pytest.mark.parametrize(
    "params, match",
    [
        ({}, "at least one of width or height"),
        ({"width": 8, "mode": ThumbnailMode.CROP}, "requires both"),
    ],
)
def test_make_image_thumbnail_invalid_params(params, match, dummy_jpg_path):
    ctx = mock.Mock(name="ctx")
    with pytest.raises(ValueError, match=match):
        make_image_thumbnail(ctx, dummy_jpg_path, "/test.jpg", **params)
    assert len(ctx.mock_calls) == 0


def test_make_image_thumbnail_unknown_image_format(tmp_path):
    ctx = mock.Mock(name="ctx")
    with pytest.raises(RuntimeError, match="unknown"):
        make_image_thumbnail(ctx, NONIMAGE_FILE_PATH, "/test.jpg", width=80)
    assert len(ctx.mock_calls) == 0


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


def test_Thumbnail_str():
    thumbnail = Thumbnail("/urlpath/image.jpg", 50, 80)
    assert str(thumbnail) == "image.jpg"


@dataclasses.dataclass
class DemoThumbnail:
    width: int
    height: int
    max_size: int | None = None


@dataclasses.dataclass
class ImgTag:
    src: str
    width: int | None
    height: int | None
    alt: str


class TestFunctional:
    """Remnants of the tests that were in test_images.py"""

    # pylint: disable=no-self-use

    @pytest.fixture
    def thumbnails(self):
        return {
            # original dimensions = 384 x 512
            "test@192x256.jpg": DemoThumbnail(192, 256),
            "test@300x100_crop.jpg": DemoThumbnail(300, 100),
            "test@300x100.jpg": DemoThumbnail(300, 100),
            "test@192x256_q20.jpg": DemoThumbnail(192, 256, 9200),
        }

    @pytest.fixture
    def built_demo_img_tags(self, built_demo):
        def int_val(value):
            if value is None:
                return None
            return int(value)

        imgs = []

        def handle_starttag(tag, attrs):
            if tag == "img":
                a = dict(attrs)
                imgs.append(
                    ImgTag(
                        src=a.get("src"),
                        alt=a.get("alt"),
                        width=int_val(a.get("width")),
                        height=int_val(a.get("height")),
                    )
                )

        parser = html.parser.HTMLParser()
        parser.handle_starttag = handle_starttag
        parser.feed(Path(built_demo, "index.html").read_text("utf-8"))
        parser.close()
        return imgs

    def test_img_tag_dimensions(self, built_demo_img_tags, thumbnails):
        seen = set()

        for img in built_demo_img_tags:
            seen.add(img.src)
            thumb = thumbnails.get(img.src)
            if thumb is not None:
                assert (img.width, img.height) == (thumb.width, thumb.height)
        assert seen >= set(thumbnails)

    def test_thumbnail_dimensions(self, built_demo, thumbnails):
        for name, thumb in thumbnails.items():
            with open(built_demo / name, "rb") as fp:
                _format, width, height = get_image_info(fp)
            assert (width, height) == (thumb.width, thumb.height)

    def test_thumbnails_distinct(self, built_demo, thumbnails):
        images = set()
        for name in thumbnails:
            images.add(Path(built_demo / name).read_bytes())
        assert len(images) == len(thumbnails)

    def test_max_size(self, built_demo, thumbnails):
        for name, thumb in thumbnails.items():
            if thumb.max_size is not None:
                assert Path(built_demo / name).stat().st_size < thumb.max_size

    def test_large_thumbnail_returns_original(self, built_demo_img_tags):
        large_thumb = ImgTag(alt="original", src="test.jpg", width=384, height=512)
        assert large_thumb in built_demo_img_tags


@pytest.fixture(
    params=[
        "test.jpg",  # base image, exif-rotated
        "test-sof-last.jpg",  # same image but with SOF marker last
        "test-progressive.jpg",  # with progressive encoding, rotated in place
    ]
)
def demo_test_jpg(request, pad):
    return pad.root.attachments.images.get(request.param)


def test_image_attributes(demo_test_jpg):
    assert demo_test_jpg.width == 384
    assert demo_test_jpg.height == 512
    assert demo_test_jpg.format == "jpeg"


def test_exif(demo_test_jpg):
    name = demo_test_jpg.path.lstrip("/")
    expected = TEST_IMAGE_EXIF_INFO[DEMO_PROJECT / name]

    assert demo_test_jpg.exif.to_dict() == expected
    if expected == NULL_EXIF_INFO:
        assert not demo_test_jpg.exif
    else:
        assert demo_test_jpg.exif
