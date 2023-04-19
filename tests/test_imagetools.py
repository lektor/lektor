from __future__ import annotations

import dataclasses
import datetime
import html.parser
import io
from contextlib import contextmanager
from pathlib import Path
from unittest import mock
from xml.sax import saxutils

import PIL
import pytest
from exifread.utils import Ratio
from pytest import approx

from lektor.imagetools import _combine_make
from lektor.imagetools import _compute_cropbox
from lektor.imagetools import _convert_color_profile_to_srgb
from lektor.imagetools import _convert_gps
from lektor.imagetools import _create_artifact
from lektor.imagetools import _create_thumbnail
from lektor.imagetools import _get_thumbnail_url_path
from lektor.imagetools import _parse_svg_units_px
from lektor.imagetools import compute_dimensions
from lektor.imagetools import CropBox
from lektor.imagetools import EXIFInfo
from lektor.imagetools import get_image_info
from lektor.imagetools import ImageSize
from lektor.imagetools import is_rotated
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
    "coords, hemisphere, expected",
    [
        (("45", "15", "30"), "N", approx(45.2583333)),
        (("45", "61/2", "0"), "S", approx(-45.5083333)),
        (("122", "0", "0"), "W", -122),
        (("45/2", "0", "0"), "E", 22.5),
    ],
)
def test_convert_gps(coords, hemisphere, expected):
    assert _convert_gps(tuple(Ratio(coord) for coord in coords), hemisphere) == expected


def test_exif(pad):
    expected = {
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

    image = pad.root.attachments.images.get("test.jpg")
    assert image.exif
    for key, value in expected.items():
        assert getattr(image.exif, key) == value
    assert image.exif.to_dict() == expected


def test_read_exif_unrecognized_image():
    exif_info = read_exif(io.BytesIO(b"unrecognized-image"))
    assert not exif_info


@pytest.mark.parametrize(
    "attr, expected",
    [
        ("altitude", None),
        ("aperture", None),
        ("artist", None),
        ("camera", ""),
        ("camera_make", None),
        ("camera_model", None),
        ("copyright", None),
        ("created_at", None),
        ("description", None),
        ("documentname", None),
        ("exposure_time", None),
        pytest.param("f", None, marks=pytest.mark.xfail(reason="FIXME")),
        ("f_num", None),
        ("flash_info", None),
        ("focal_length", None),
        ("focal_length_35mm", None),
        ("is_rotated", False),
        ("iso", None),
        ("latitude", None),
        ("lens", ""),
        ("lens_make", None),
        ("lens_model", None),
        ("location", None),
        ("longitude", None),
        ("shutter_speed", None),
    ],
)
def test_null_EXIFInfo(attr, expected):
    exif_info = EXIFInfo({})
    assert not exif_info
    assert getattr(exif_info, attr) == expected


@pytest.mark.parametrize(
    "exif_data, expected",
    [
        (
            {
                "GPS GPSAltitude": mock.Mock(values=[Ratio("1234/10")]),
                "GPS GPSAltitudeRef": mock.Mock(values=[0]),
            },
            approx(123.4),
        ),
        (
            {
                "GPS GPSAltitude": mock.Mock(values=[Ratio("123/10")]),
                "GPS GPSAltitudeRef": mock.Mock(values=[1]),
            },
            approx(-12.3),
        ),
        ({"GPS GPSAltitude": mock.Mock(values=[Ratio("1234/10")])}, approx(123.4)),
    ],
)
def test_EXIFInfo_altitude(exif_data, expected):
    exif_info = EXIFInfo(exif_data)
    assert exif_info.altitude == expected


@pytest.mark.parametrize(
    "image_name, expected",
    [
        ("test.jpg", True),
        ("test-sof-last.jpg", True),
        ("test-progressive.jpg", False),
    ],
)
def test_is_rotated(image_name, expected):
    image_path = DEMO_PROJECT / image_name
    with image_path.open("rb") as fp:
        assert is_rotated(fp) == expected


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
        pytest.param(
            DummyImage(10, 20, "PNG", orientation=7),
            ("png", 20, 10),
            id="rotated PNG",
            marks=pytest.mark.xfail(reason="FIXME"),
        ),
        (DummyImage(10, 20, "PPM"), (None, None, None)),
        (DummySVGImage("10px", "20px"), ("svg", 10, 20)),
        (DummySVGImage("10", "20", xml_decl=None), ("svg", 10, 20)),
        (DummySVGImage(None, None), ("svg", None, None)),
        (DummySVGImage("invalid-width", "invalid-height"), ("svg", None, None)),
        pytest.param(
            DummySVGImage("10px", "10px", xmlns=None),
            (None, None, None),
            id="SVG without namespaced <svg>",
            marks=pytest.mark.xfail(reason="FIXME"),
        ),
    ],
)
def test_get_image_info(image, expected):
    assert get_image_info(image.open()) == expected


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


@pytest.mark.parametrize(
    "image_name",
    [
        "test.jpg",  # base image, exif-rotated
        "test-sof-last.jpg",  # same image but with SOF marker last
        "test-progressive.jpg",  # with progressive encoding, rotated in place
    ],
)
def test_image_attributes(pad, image_name):
    image = pad.root.attachments.images.get(image_name)
    assert image.width == 384
    assert image.height == 512
    assert image.format == "jpeg"
