from __future__ import annotations

import dataclasses
import io
from pathlib import Path
from xml.sax import saxutils

import PIL
import pytest

from lektor.imagetools.image_info import _parse_svg_units_px
from lektor.imagetools.image_info import _save_position
from lektor.imagetools.image_info import get_image_info


EXIF_ORIENTATION_TAG = 0x0112


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


class DummyFileBase:
    def write(self, fp):
        raise NotImplementedError()

    def open(self):
        fp = io.BytesIO()
        self.write(fp)
        fp.seek(0)
        return fp

    def path(self, tmp_path: Path) -> Path:
        path = tmp_path / "dummy"
        with path.open("wb") as fp:
            self.write(fp)
        return path


@dataclasses.dataclass
class DummyImage(DummyFileBase):
    width: int
    height: int
    format: str = "PNG"
    orientation: int | None = None

    def write(self, fp):
        image = PIL.Image.new("RGB", (self.width, self.height), "#999")
        exif = image.getexif()
        if self.orientation is not None:
            exif[EXIF_ORIENTATION_TAG] = self.orientation
        image.save(fp, self.format, exif=exif)


@dataclasses.dataclass
class DummySVGImage(DummyFileBase):
    width: int | str | None = None
    height: int | str | None = None
    xmlns: str | None = "http://www.w3.org/2000/svg"
    xml_decl: str | None = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'

    def write(self, fp):
        values = dataclasses.asdict(self)
        svg_attrs = "".join(
            f" {key}={saxutils.quoteattr(str(values[key]))}"
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
        fp.write(svg.encode("utf-8"))


@dataclasses.dataclass
class DummyFile(DummyFileBase):
    content: bytes = b""

    def write(self, fp):
        fp.write(self.content)


@pytest.mark.parametrize(
    "image, expected",
    [
        (DummyFile(b"short"), (None, None, None)),
        (DummyFile(b"Not an image. " * 40), (None, None, None)),
        (DummyImage(10, 20, "JPEG"), ("jpeg", 10, 20)),
        (DummyImage(10, 20, "GIF"), ("gif", 10, 20)),
        (DummyImage(10, 20, "PNG"), ("png", 10, 20)),
        (DummyImage(10, 20, "JPEG", orientation=5), ("jpeg", 20, 10)),
        # check that Exif orientation is ignored for PNG images"
        (DummyImage(10, 20, "PNG", orientation=7), ("png", 10, 20)),
        (DummyImage(10, 20, "PPM"), (None, None, None)),
        (DummySVGImage("10px", "20px"), ("svg", 10, 20)),
        (DummySVGImage("10", "20", xml_decl=None), ("svg", 10, 20)),
        (DummySVGImage(None, None), ("svg", None, None)),
        (DummySVGImage("invalid-width", "invalid-height"), ("svg", None, None)),
        (DummySVGImage("10px", "10px", xmlns=None), (None, None, None)),
    ],
)
def test_get_image_info(image, expected, tmp_path):
    image_path = tmp_path / "test-image"
    with image_path.open("wb") as fp:
        image.write(fp)
    assert get_image_info(image_path) == expected


def test_get_image_info_fp_deprecated():
    image = DummyImage(10, 20, "JPEG")
    with pytest.deprecated_call() as w:
        assert get_image_info(image.open()) == ("jpeg", 10, 20)
    for warning in w:
        assert warning.filename == __file__


def test_save_position():
    fp = io.BytesIO(b"data")
    with _save_position(fp) as infp:
        assert infp.read() == b"data"
    assert fp.read() == b"data"


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
