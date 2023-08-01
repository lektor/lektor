from __future__ import annotations

import dataclasses
import html.parser
import io
import os
import shutil
from contextlib import contextmanager
from pathlib import Path

import PIL
import pytest
from pytest import approx

from lektor.context import Context
from lektor.db import Image
from lektor.imagetools.thumbnail import _compute_cropbox
from lektor.imagetools.thumbnail import _convert_icc_profile_to_srgb
from lektor.imagetools.thumbnail import _create_artifact
from lektor.imagetools.thumbnail import _create_thumbnail
from lektor.imagetools.thumbnail import _get_thumbnail_url_path
from lektor.imagetools.thumbnail import compute_dimensions
from lektor.imagetools.thumbnail import CropBox
from lektor.imagetools.thumbnail import get_image_info
from lektor.imagetools.thumbnail import ImageSize
from lektor.imagetools.thumbnail import make_image_thumbnail
from lektor.imagetools.thumbnail import Thumbnail
from lektor.imagetools.thumbnail import ThumbnailMode
from lektor.imagetools.thumbnail import ThumbnailParams


HERE = Path(__file__).parent
DEMO_PROJECT = HERE / "../demo-project/content"
ICC_PROFILE_TEST_JPG = DEMO_PROJECT / "icc-profile-test/rgb-to-gbr-test.jpg"
CMYK_ICC_PROFILE_TEST = DEMO_PROJECT / "icc-profile-test/CGATS001Compat-v2-micro.icc"
NONIMAGE_FILE_PATH = Path(__file__)  # we are not an image


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
    "format, proposed_ext, expected",
    [
        ("GIF", ".gif", ".gif"),
        ("GIF", ".gIf", ".gIf"),
        ("GIF", ".bad", ".gif"),
        ("GIF", "GIF", ".gif"),
        ("JPEG", ".jpg", ".jpg"),
        ("JPEG", ".JPEG", ".JPEG"),
        ("JPEG", ".j", ".jpeg"),
        ("PNG", ".x", ".png"),
        ("PNG", ".PNG", ".PNG"),
    ],
)
def test_ThumbnailParams_get_ext(format, proposed_ext, expected):
    thumbnail_params = ThumbnailParams(ImageSize(10, 20), format)
    assert thumbnail_params.get_ext(proposed_ext) == expected


@pytest.mark.parametrize(
    "format, width, height, quality, crop, expected",
    [
        ("GIF", 10, 20, None, False, "10x20"),
        ("gif", 10, 20, 92, False, "10x20"),
        ("GIF", 10, 20, None, True, "10x20_crop"),
        ("JPEG", 200, 300, 92, False, "200x300_q92"),
        ("JPEG", 200, 300, None, True, "200x300_crop"),
        ("PNG", 1, 2, 92, True, "1x2_crop_q9"),
        ("PNG", 4, 5, None, False, "4x5"),
    ],
)
def test_ThumbnailParams_get_tag(format, width, height, quality, crop, expected):
    thumbnail_params = ThumbnailParams(ImageSize(width, height), format, quality, crop)
    assert thumbnail_params.get_tag() == expected


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


def test_convert_icc_profile_to_srgb():
    im = PIL.Image.open(ICC_PROFILE_TEST_JPG)
    # Top center of image is blue before color transform
    assert im.getpixel((im.width // 2, 0)) == approx((0, 0, 255), abs=10)

    _convert_icc_profile_to_srgb(im)
    # Top center of image is red after color transform
    assert im.getpixel((im.width // 2, 0)) == approx((255, 0, 0), abs=10)
    assert "icc_profile" not in im.info


def test_convert_icc_profile_to_srgb_no_profile():
    im = PIL.Image.new("RGB", (100, 100), "#999")
    _convert_icc_profile_to_srgb(im)
    assert "icc_profile" not in im.info


def test_create_thumbnail(dummy_image):
    thumbnail_params = ThumbnailParams(ImageSize(80, 60), "PNG")
    thumb = _create_thumbnail(dummy_image, thumbnail_params)
    assert thumb.width == 80 and thumb.height == 60
    assert thumb.getpixel((40, 30)) == approx((153, 153, 153), abs=5)


def test_create_thumbnail_converts_hsv_to_rgb():
    hsv_image = PIL.Image.new("HSV", (100, 100), (0, 0, 153))
    thumb = _create_thumbnail(hsv_image, ThumbnailParams(ImageSize(80, 60), "JPEG"))
    assert thumb.mode == "RGB"
    assert thumb.getpixel((40, 30)) == approx((153, 153, 153), abs=2)


def test_create_thumbnail_converts_indexed_to_rgb():
    image = PIL.Image.new("P", (100, 100), 0)
    image.putpalette(b"\x10\x20\x30", "RGB")
    thumb = _create_thumbnail(image, ThumbnailParams(ImageSize(80, 60), "JPEG"))
    assert thumb.mode == "RGB"
    assert thumb.getpixel((40, 30)) == approx((16, 32, 48), abs=2)


def test_create_thumbnail_converts_cmyk_to_rgb(dummy_image):
    cmyk_image = dummy_image.convert("CMYK")
    thumb = _create_thumbnail(cmyk_image, ThumbnailParams(ImageSize(80, 60), "JPEG"))
    assert thumb.mode == "RGB"
    assert thumb.getpixel((40, 30)) == approx((153, 153, 153), abs=5)


def test_create_thumbnail_converts_cmyk_to_rgb_via_icc_profile(dummy_image):
    cmyk_image = dummy_image.convert("CMYK")
    cmyk_image.info["icc_profile"] = CMYK_ICC_PROFILE_TEST.read_bytes()
    thumb = _create_thumbnail(cmyk_image, ThumbnailParams(ImageSize(80, 60), "PNG"))
    assert thumb.mode == "RGB"
    assert thumb.getpixel((40, 30)) == approx((162, 148, 145), abs=5)


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
    source_image = ICC_PROFILE_TEST_JPG
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


@pytest.fixture
def ctx(builder):
    build_state = builder.new_build_state()
    with Context(build_state.new_artifact("dummy-artifact")) as ctx:
        yield ctx


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
    ctx, source_url_path, kwargs, expected_size, thumbnail_url_path, dummy_jpg_path
):
    thumbnail = make_image_thumbnail(ctx, dummy_jpg_path, source_url_path, **kwargs)
    assert (thumbnail.width, thumbnail.height) == expected_size
    assert thumbnail.url_path == thumbnail_url_path
    if "@" in thumbnail_url_path:
        assert len(ctx.sub_artifacts) == 1
    else:
        assert len(ctx.sub_artifacts) == 0  # no implicit upscale


@pytest.mark.parametrize(
    "params, match",
    [
        ({}, "at least one of width or height"),
        ({"width": 8, "mode": ThumbnailMode.CROP}, "requires both"),
    ],
)
def test_make_image_thumbnail_invalid_params(ctx, params, match, dummy_jpg_path):
    with pytest.raises(ValueError, match=match):
        make_image_thumbnail(ctx, dummy_jpg_path, "/test.jpg", **params)
    assert len(ctx.sub_artifacts) == 0


def test_make_image_thumbnail_unknown_image_format(ctx, tmp_path):
    with pytest.raises(RuntimeError, match="unknown"):
        make_image_thumbnail(ctx, NONIMAGE_FILE_PATH, "/test.jpg", width=80)
    assert len(ctx.sub_artifacts) == 0


@pytest.fixture
def dummy_svg_file(tmp_path):
    dummy_svg = tmp_path / "dummy.svg"

    def svg_file(**kwargs):
        attrs = " ".join(f'{key}="{value}"' for key, value in kwargs.items())
        dummy_svg.write_text(f'<svg {attrs} xmlns="http://www.w3.org/2000/svg"></svg>')
        return dummy_svg

    return svg_file


def test_make_image_thumbnail_svg(ctx, dummy_svg_file):
    svg_file = dummy_svg_file(width="400px", height="300px")
    thumbnail = make_image_thumbnail(
        ctx, svg_file, "/urlpath/dummy.svg", width=80, height=60
    )
    assert (thumbnail.width, thumbnail.height) == (80, 60)
    assert thumbnail.url_path == "/urlpath/dummy.svg"
    assert len(ctx.sub_artifacts) == 0


def test_make_image_thumbnail_svg_fit_mode_fails_if_missing_dim(ctx, dummy_svg_file):
    svg_file = dummy_svg_file(width="400px")  # missing height
    with pytest.raises(ValueError, match="Cannot determine aspect ratio"):
        make_image_thumbnail(ctx, svg_file, "/urlpath/dummy.svg", width=80, height=60)


def test_Thumbnail_str():
    thumbnail = Thumbnail("/urlpath/image.jpg", 50, 80)
    assert str(thumbnail) == "image.jpg"


class TestArtifactDependencyTracking:
    @staticmethod
    @pytest.fixture
    def scratch_project_data(scratch_project_data):
        # add two identical thumbnails to the page template
        page_html = scratch_project_data / "templates/page.html"
        with page_html.open("a") as fp:
            fp.write(
                """
                {% set im = this.attachments.get('test.jpg') %}
                <img src="{{ im.thumbnail(20) }}">
                <img src="{{ im.thumbnail(20) }}">
                """
            )
        shutil.copy(ICC_PROFILE_TEST_JPG, scratch_project_data / "content/test.jpg")
        return scratch_project_data

    @staticmethod
    def build_page(builder) -> list[str]:
        _, build_state = builder.build(builder.pad.root)
        assert len(build_state.failed_artifacts) == 0
        return [
            os.path.basename(artifact.dst_filename)
            for artifact in build_state.updated_artifacts
        ]

    def test(self, scratch_builder):
        built = self.build_page(scratch_builder)
        assert built == ["index.html", "test@20x20.jpg"]

        # rebuild doesn't rebuild any more artifacts
        Path(scratch_builder.destination_path, "index.html").unlink()
        built = self.build_page(scratch_builder)
        assert built == ["index.html"]

    @pytest.mark.xfail(reason="This will (or should, at least) be fixed by PR #1148")
    def test_racy_source_changes(self, scratch_builder, monkeypatch):
        # Modify source image immediately after the first call to Image.thumbnail().
        # Note that this occurs *before* the thumbnail artifact is built.
        #
        # We are doing this to ensure there are no race conditions in
        # the dependency tracking. Since the source was changed after the thumbnail
        # parameters were computed, the artifact should be updated at the next build.

        def thumbnail_advice(self, *args, **kwargs):
            monkeypatch.undo()
            try:
                return Image.thumbnail(self, *args, **kwargs)
            finally:
                with open(self.attachment_filename, "ab") as fp:
                    fp.write(b"\0")

        monkeypatch.setattr(Image, "thumbnail", thumbnail_advice)

        built = self.build_page(scratch_builder)
        assert built == ["index.html", "test@20x20.jpg"]

        Path(scratch_builder.destination_path, "index.html").unlink()
        built = self.build_page(scratch_builder)
        assert built == ["index.html", "test@20x20.jpg"]


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
            _format, width, height = get_image_info(built_demo / name)
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
