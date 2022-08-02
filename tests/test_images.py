import os
import warnings
from datetime import datetime
from hashlib import md5
from io import BytesIO

import pytest
from markers import imagemagick

from lektor.imagetools import compute_dimensions
from lektor.imagetools import get_image_info
from lektor.imagetools import is_rotated
from lektor.imagetools import make_image_thumbnail
from lektor.imagetools import ThumbnailMode


def almost_equal(a, b, e=0.00001):
    return abs(a - b) < e


@pytest.fixture(scope="function")
def make_svg():
    def _make_svg(size_unit=None, with_declaration=True, w=100, h=100):
        emotional_face = """<svg xmlns="http://www.w3.org/2000/svg" \
height="{h}{unit}" width="{w}{unit}">
    <circle cx="50" cy="50" r="50" fill="lightgrey"/>
    <circle cx="30" cy="30" r="10" fill="black"/>
    <circle cx="60" cy="30" r="10" fill="black"/>
    <path stroke="black" d="M30 70 l30 0" stroke-width="5"/>
 </svg>""".format(
            unit=size_unit or "", w=w, h=h
        ).encode(
            "utf-8"
        )

        if with_declaration:
            xml_declaration = b'<?xml version="1.0" standalone="yes"?>'
            svg = xml_declaration + emotional_face
        else:
            svg = emotional_face

        return BytesIO(svg)

    return _make_svg


def test_exif(pad):
    image = pad.root.attachments.images.get("test.jpg")
    assert image is not None

    assert image.exif

    assert almost_equal(image.exif.altitude, 779.0293)
    assert almost_equal(image.exif.aperture, 2.275)
    assert image.exif.artist is None
    assert image.exif.camera == "Apple iPhone 6"
    assert image.exif.camera_make == "Apple"
    assert image.exif.camera_model == "iPhone 6"
    assert image.exif.copyright is None
    assert image.exif.created_at == datetime(2015, 12, 6, 11, 37, 38)
    assert image.exif.exposure_time == "1/33"
    assert image.exif.f == "\u0192/2.2"
    assert almost_equal(image.exif.f_num, 2.2)
    assert image.exif.flash_info == "Flash did not fire, compulsory flash mode"
    assert image.exif.focal_length == "4.2mm"
    assert image.exif.focal_length_35mm == "29mm"
    assert image.exif.iso == 160
    assert almost_equal(image.exif.latitude, 46.6338333)
    assert image.exif.lens == "Apple iPhone 6 back camera 4.15mm f/2.2"
    assert image.exif.lens_make == "Apple"
    assert image.exif.lens_model == "iPhone 6 back camera 4.15mm f/2.2"
    assert almost_equal(image.exif.longitude, 13.4048333)
    assert image.exif.location == (image.exif.latitude, image.exif.longitude)
    assert image.exif.shutter_speed == "1/33"

    assert image.exif.documentname == "testName"
    assert image.exif.description == "testDescription"
    assert image.exif.is_rotated

    assert isinstance(image.exif.to_dict(), dict)

    for key, value in image.exif.to_dict().items():
        assert getattr(image.exif, key) == value


def test_image_attributes(pad):
    for img in (
        "test.jpg",  # base image, exif-rotated
        "test-sof-last.jpg",  # same image but with SOF marker last
        "test-progressive.jpg",  # with progressive encoding, rotated in place
    ):
        image = pad.root.attachments.images.get(img)
        assert image is not None

        assert image.width == 384
        assert image.height == 512
        assert image.format == "jpeg"


def test_is_rotated(pad):
    for img, rotated in (
        ("test.jpg", True),
        ("test-sof-last.jpg", True),
        ("test-progressive.jpg", False),
    ):
        image = pad.root.attachments.images.get(img)
        with open(image.attachment_filename, "rb") as f:
            assert is_rotated(f) == rotated


def test_image_info_svg_declaration(make_svg):
    w, h = 100, 100
    svg_with_xml_decl = make_svg(with_declaration=True, h=h, w=w)
    svg_no_xml_decl = make_svg(with_declaration=False, h=h, w=w)
    info_svg_no_xml_decl = get_image_info(svg_no_xml_decl)
    info_svg_with_xml_decl = get_image_info(svg_with_xml_decl)

    expected = "svg", w, h
    assert info_svg_with_xml_decl == expected
    assert info_svg_no_xml_decl == expected


def test_image_info_svg_length(make_svg):
    w, h = 100, 100
    svg_with_unit_px = make_svg(size_unit="px", w=w, h=h)
    svg_no_unit = make_svg(size_unit=None, w=w, h=h)
    info_with_unit_px = get_image_info(svg_with_unit_px)
    info_no_unit = get_image_info(svg_no_unit)

    expected = "svg", 100, 100
    assert info_with_unit_px == expected
    assert info_no_unit == expected


_SIMILAR_THUMBNAILS = {
    # original dimensions = 384 x 512
    "test@192.jpg": (192, 256),
    "test@x256.jpg": (192, 256),
    "test@256x256.jpg": (192, 256),
}
_DIFFERING_THUMBNAILS = {
    "test@300x100_crop.jpg": (300, 100),
    "test@300x100_stretch.jpg": (300, 100),
}
_THUMBNAILS = _SIMILAR_THUMBNAILS.copy()
_THUMBNAILS.update(_DIFFERING_THUMBNAILS)


def test_thumbnail_dimensions_reported(builder):
    builder.build_all()
    with open(
        os.path.join(builder.destination_path, "index.html"), encoding="utf-8"
    ) as f:
        html = f.read()

    for t, (w, h) in _THUMBNAILS.items():
        assert '<img src="%s" width="%s" height="%s">' % (t, w, h) in html


@imagemagick
def test_thumbnail_dimensions_real(builder):
    builder.build_all()
    for t, dimensions in _THUMBNAILS.items():
        image_file = os.path.join(builder.destination_path, t)
        with open(image_file, "rb") as f:
            _format, width, height = get_image_info(f)
            assert (width, height) == dimensions


@imagemagick
def test_thumbnails_similar(builder):
    builder.build_all()
    hashes = []
    for t in _SIMILAR_THUMBNAILS:
        image_file = os.path.join(builder.destination_path, t)
        with open(image_file, "rb") as f:
            hashes.append(md5(f.read()).hexdigest())
    for i in range(1, len(hashes)):
        assert hashes[i] == hashes[0]


@imagemagick
def test_thumbnails_differing(builder):
    builder.build_all()
    hashes = []
    for t in _DIFFERING_THUMBNAILS:
        image_file = os.path.join(builder.destination_path, t)
        with open(image_file, "rb") as f:
            hashes.append(md5(f.read()).hexdigest())
    for i in range(1, len(hashes)):
        assert hashes[i] != hashes[0]


@imagemagick
def test_thumbnail_quality(builder):
    builder.build_all()
    image_file = os.path.join(builder.destination_path, "test@192x256_q20.jpg")
    # See if the image file with said quality suffix exists
    assert os.path.isfile(image_file)

    image_size = os.path.getsize(image_file)
    # And the filesize is less than 9200 bytes
    assert image_size < 9200


# TODO: delete this when the thumbnails backwards-compatibility period ends
@pytest.mark.skip(reason="future behaviour")
def test_large_thumbnail_returns_original(builder):
    builder.build_all()
    with open(
        os.path.join(builder.destination_path, "index.html"), encoding="utf-8"
    ) as f:
        html = f.read()

    assert '<img alt="original" src="./test.jpg" width="384" height="512">' in html


def test_dimensions():
    # landscape
    w, h = 100, 50
    assert compute_dimensions(50, 50, w, h) == (50, 25)
    assert compute_dimensions(100, 20, w, h) == (40, 20)
    assert compute_dimensions(200, 200, w, h) == (200, 100)
    assert compute_dimensions(500, 200, w, h) == (400, 200)
    # test missing dimension
    assert compute_dimensions(50, None, w, h) == (50, 25)
    assert compute_dimensions(None, 20, w, h) == (40, 20)
    assert compute_dimensions(200, None, w, h) == (200, 100)
    assert compute_dimensions(None, 200, w, h) == (400, 200)
    # test that rounding is half-up
    assert compute_dimensions(49, None, w, h) == (49, 25)
    assert compute_dimensions(51, None, w, h) == (51, 26)

    # portrait
    w, h = 50, 100
    assert compute_dimensions(50, 50, w, h) == (25, 50)
    assert compute_dimensions(20, 100, w, h) == (20, 40)
    assert compute_dimensions(200, 200, w, h) == (100, 200)
    assert compute_dimensions(200, 500, w, h) == (200, 400)
    #
    assert compute_dimensions(None, 50, w, h) == (25, 50)
    assert compute_dimensions(20, None, w, h) == (20, 40)
    assert compute_dimensions(None, 200, w, h) == (100, 200)
    assert compute_dimensions(200, None, w, h) == (200, 400)
    #
    assert compute_dimensions(None, 49, w, h) == (25, 49)
    assert compute_dimensions(None, 51, w, h) == (26, 51)


class DummyContext:
    def __init__(self):
        self.sub_artifacts = []

    def sub_artifact(self, **kwargs):
        def decorate(f):
            self.add_sub_artifact(build_func=f, **kwargs)
            return f

        return decorate

    def add_sub_artifact(self, **kwargs):
        self.sub_artifacts.append(kwargs)


class Test_make_image_thumbnail:
    # pylint: disable=no-self-use

    @pytest.fixture
    def ctx(self):
        return DummyContext()

    @pytest.fixture
    def test_jpg(self, project):
        return os.path.join(project.tree, "content/test.jpg")

    @pytest.fixture
    def svg_image(self, make_svg, tmp_path):
        svg_path = tmp_path / "test.svg"
        svg_path.write_bytes(make_svg().getvalue())
        return str(svg_path)

    @pytest.fixture
    def source_url_path(self):
        return "test.jpg"

    def test_no_width_or_height(self, ctx, test_jpg, source_url_path):
        with pytest.raises(ValueError, match=r"Must specify at least one"):
            make_image_thumbnail(ctx, test_jpg, source_url_path)
        assert len(ctx.sub_artifacts) == 0

    def test_warn_fallback_to_fit(self, ctx, test_jpg, source_url_path):
        with pytest.warns(UserWarning, match=r"mode requires both"):
            make_image_thumbnail(
                ctx, test_jpg, source_url_path, width=80, mode=ThumbnailMode.CROP
            )
        assert len(ctx.sub_artifacts) == 1

    def test_unknown_image_format(self, ctx, project, source_url_path):
        bad_img = os.path.join(project.tree, "content/contents.lr")
        with pytest.raises(RuntimeError, match=r"unknown image"):
            make_image_thumbnail(ctx, bad_img, source_url_path, width=80)
        assert len(ctx.sub_artifacts) == 0

    def test_svg(self, ctx, svg_image, source_url_path):
        rv = make_image_thumbnail(ctx, svg_image, source_url_path, 40, 60)
        assert rv.width == 40
        assert rv.height == 60
        assert rv.url_path == source_url_path
        assert len(ctx.sub_artifacts) == 0

    @pytest.mark.parametrize(
        "w, h, mode, upscale, expect",
        [
            (50, None, ThumbnailMode.FIT, None, (50, 67)),
            (None, 128, ThumbnailMode.FIT, None, (96, 128)),
            (50, 50, ThumbnailMode.CROP, None, (50, 50)),
            (50, 50, ThumbnailMode.STRETCH, None, (50, 50)),
            (512, None, ThumbnailMode.FIT, True, (512, 683)),
            (512, 512, ThumbnailMode.CROP, None, (512, 512)),
            (512, 512, ThumbnailMode.STRETCH, None, (512, 512)),
        ],
    )
    def test_scale(
        self, ctx, test_jpg, source_url_path, w, h, mode, upscale, expect, recwarn
    ):
        warnings.simplefilter("error")  # no warnings should be emitted
        rv = make_image_thumbnail(ctx, test_jpg, source_url_path, w, h, mode, upscale)
        assert (rv.width, rv.height) == expect
        assert rv.url_path != source_url_path
        assert len(ctx.sub_artifacts) == 1

    def test_no_implicit_upscale(self, ctx, test_jpg, source_url_path):
        rv = make_image_thumbnail(ctx, test_jpg, source_url_path, 512)
        assert (rv.width, rv.height) == (384, 512)
        assert rv.url_path == "test.jpg"
        assert len(ctx.sub_artifacts) == 0

    @pytest.mark.parametrize("mode", iter(ThumbnailMode))
    def test_upscale_false(self, ctx, test_jpg, source_url_path, mode):
        rv = make_image_thumbnail(
            ctx, test_jpg, source_url_path, 4096, 4069, mode, upscale=False
        )
        assert (rv.width, rv.height) == (384, 512)
        assert rv.url_path == source_url_path
        assert len(ctx.sub_artifacts) == 0
