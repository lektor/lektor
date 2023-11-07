from __future__ import annotations

import datetime
import io
from fractions import Fraction
from pathlib import Path

import pytest
from pytest import approx

from lektor.imagetools.exif import _combine_make
from lektor.imagetools.exif import _to_altitude
from lektor.imagetools.exif import _to_degrees
from lektor.imagetools.exif import _to_flash_description
from lektor.imagetools.exif import _to_float
from lektor.imagetools.exif import _to_focal_length
from lektor.imagetools.exif import _to_rational
from lektor.imagetools.exif import _to_string
from lektor.imagetools.exif import read_exif


HERE = Path(__file__).parent
DEMO_PROJECT = HERE / "../demo-project/content"


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
    "coerce, value, expected",
    [
        (_to_string, "a b", "a b"),
        (_to_string, "a\xc2\xa0b", "a\xa0b"),
        (_to_string, "a\xa0b", "a\xa0b"),
        #
        (_to_rational, 42, 42),
        (_to_rational, Fraction("22/7"), Fraction("22/7")),
        (_to_rational, (3, 2), Fraction("3/2")),
        #
        (_to_float, 42, 42),
        (_to_float, 1.5, 1.5),
        (_to_float, Fraction("22/7"), approx(3.142857)),
        (_to_float, (7, 4), 1.75),
        #
        (_to_flash_description, 0x41, "Flash fired, red-eye reduction mode"),
        (_to_flash_description, 0x100, "Flash did not fire (256)"),
        (_to_flash_description, 0x101, "Flash fired (257)"),
        (_to_flash_description, -1, "Flash fired (-1)"),
        #
        (_to_focal_length, Fraction("45/2"), "22.5mm"),
        (_to_focal_length, (521, 10), "52.1mm"),
    ],
)
def test_coersion(coerce, value, expected):
    assert coerce(value) == expected


@pytest.mark.parametrize(
    "coords, hemisphere, expected",
    [
        ((Fraction(45), Fraction(15), Fraction(30)), "N", approx(45.2583333)),
        ((Fraction(45), Fraction(61, 2), Fraction(0)), "S", approx(-45.5083333)),
        ((122, 0, 0), "W", -122),
        ((Fraction("45/2"), 0, 0), "E", 22.5),
        (((45, 2), (30, 1), (0, 1)), "N", approx(23)),
    ],
)
def test_to_degrees(coords, hemisphere, expected):
    assert _to_degrees(coords, hemisphere) == expected


@pytest.mark.parametrize(
    "altitude, altitude_ref, expected",
    [
        (Fraction("1234/10"), b"\x00", approx(123.4)),
        (Fraction("1234/10"), None, approx(123.4)),
        ((1234, 10), b"\x00", approx(123.4)),
        (Fraction("123/10"), b"\x01", approx(-12.3)),
    ],
)
def test_to_altitude(altitude, altitude_ref, expected):
    assert _to_altitude(altitude, altitude_ref) == expected


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
    HERE / "exif-test-3.jpg": {"altitude": approx(-85.9)},  # negative altitude
    HERE / "exif-test-4.jpg": {"altitude": approx(85.9)},  # This no GPSAltitudeRef tag:
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


@pytest.fixture(
    params=[
        "test.jpg",  # base image, exif-rotated
        "test-sof-last.jpg",  # same image but with SOF marker last
        "test-progressive.jpg",  # with progressive encoding, rotated in place
    ]
)
def demo_test_jpg(request, pad):
    return pad.root.attachments.images.get(request.param)


def test_image_exif_attr(demo_test_jpg):
    name = demo_test_jpg.path.lstrip("/")
    expected = TEST_IMAGE_EXIF_INFO[DEMO_PROJECT / name]

    assert demo_test_jpg.exif.to_dict() == expected
    if expected == NULL_EXIF_INFO:
        assert not demo_test_jpg.exif
    else:
        assert demo_test_jpg.exif
