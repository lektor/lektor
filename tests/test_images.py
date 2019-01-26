import io
import os
from datetime import datetime

import pytest

from lektor._compat import iteritems
from lektor.imagetools import get_image_info


def almost_equal(a, b, e=0.00001):
    return abs(a - b) < e


@pytest.fixture(scope='function')
def make_svg():

    def _make_svg(size_unit=None, with_declaration=True, w=100, h=100):
        emotional_face = """<svg xmlns="http://www.w3.org/2000/svg" \
height="{h}{unit}" width="{w}{unit}">
    <circle cx="50" cy="50" r="50" fill="lightgrey"/>
    <circle cx="30" cy="30" r="10" fill="black"/>
    <circle cx="60" cy="30" r="10" fill="black"/>
    <path stroke="black" d="M30 70 l30 0" stroke-width="5"/>
 </svg>""" \
        .format(unit=size_unit or '', w=w, h=h) \
        .encode('utf-8')

        if with_declaration:
            xml_declaration = b'<?xml version="1.0" standalone="yes"?>'
            svg = xml_declaration + emotional_face
        else:
            svg = emotional_face

        return io.BytesIO(svg)

    return _make_svg


def test_exif(pad):
    image = pad.root.attachments.images.get('test.jpg')
    assert image is not None

    assert image.exif

    assert almost_equal(image.exif.altitude, 779.0293)
    assert almost_equal(image.exif.aperture, 2.275)
    assert image.exif.artist is None
    assert image.exif.camera == 'Apple iPhone 6'
    assert image.exif.camera_make == 'Apple'
    assert image.exif.camera_model == 'iPhone 6'
    assert image.exif.copyright is None
    assert image.exif.created_at == datetime(2015, 12, 6, 11, 37, 38)
    assert image.exif.exposure_time == '1/33'
    assert image.exif.f == u'\u0192/2.2'
    assert almost_equal(image.exif.f_num, 2.2)
    assert image.exif.flash_info == 'Flash did not fire, compulsory flash mode'
    assert image.exif.focal_length == '4.2mm'
    assert image.exif.focal_length_35mm == '29mm'
    assert image.exif.iso == 160
    assert almost_equal(image.exif.latitude, 46.6338333)
    assert image.exif.lens == 'Apple iPhone 6 back camera 4.15mm f/2.2'
    assert image.exif.lens_make == 'Apple'
    assert image.exif.lens_model == 'iPhone 6 back camera 4.15mm f/2.2'
    assert almost_equal(image.exif.longitude, 13.4048333)
    assert image.exif.location == (image.exif.latitude, image.exif.longitude)
    assert image.exif.shutter_speed == '1/33'

    assert image.exif.documentname == 'testName'
    assert image.exif.description == 'testDescription'
    assert image.exif.is_rotated

    assert isinstance(image.exif.to_dict(), dict)

    for key, value in iteritems(image.exif.to_dict()):
        assert getattr(image.exif, key) == value


def test_image_attributes(pad):
    for img in (
        'test.jpg',
        'test-sof-last.jpg', # same image but with SOF marker last
        'test-progressive.jpg', # same image, but with progressive encoding
    ):
        image = pad.root.attachments.images.get(img)
        assert image is not None

        assert image.width == 512
        assert image.height == 384
        assert image.format == 'jpeg'


def test_image_info_svg_declaration(make_svg):
    w, h = 100, 100
    svg_with_xml_decl = make_svg(with_declaration=True, h=h, w=w)
    svg_no_xml_decl = make_svg(with_declaration=False, h=h, w=w)
    info_svg_no_xml_decl = get_image_info(svg_no_xml_decl)
    info_svg_with_xml_decl = get_image_info(svg_with_xml_decl)

    expected = 'svg', w, h
    assert info_svg_with_xml_decl == expected
    assert info_svg_no_xml_decl == expected


def test_image_info_svg_length(make_svg):
    w, h = 100, 100
    svg_with_unit_px = make_svg(size_unit='px', w=w, h=h)
    svg_no_unit = make_svg(size_unit=None, w=w, h=h)
    info_with_unit_px = get_image_info(svg_with_unit_px)
    info_no_unit = get_image_info(svg_no_unit)

    expected = 'svg', 100, 100
    assert info_with_unit_px == expected
    assert info_no_unit == expected


def test_thumbnail_height(builder):
    builder.build_all()
    with open(os.path.join(builder.destination_path, 'index.html')) as f:
        html = f.read()

    # Thumbnail is half the original width, so its computed height is half.
    assert '<img src="./test@192.jpg" width="192" height="256">' in html

def test_thumbnail_quality(builder):
    builder.build_all()
    image_file = os.path.join(builder.destination_path, 'test@192x256_q20.jpg')
    image_size = os.path.getsize(image_file)

    # See if the image file with said quality suffix exists
    assert os.path.isfile(image_file)
    # And the filesize is less than 9200 bytes
    assert image_size < 9200
