import os
from datetime import datetime

from lektor._compat import iteritems


def almost_equal(a, b, e=0.00001):
    return abs(a - b) < e


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
    assert image.exif.created_at == datetime(2015, 12, 6, 11, 37, 34)
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

    assert isinstance(image.exif.to_dict(), dict)

    for key, value in iteritems(image.exif.to_dict()):
        assert getattr(image.exif, key) == value


def test_image_attributes(pad):
    image = pad.root.attachments.images.get('test.jpg')
    assert image is not None

    assert image.width == 384
    assert image.height == 512
    assert image.format == 'jpeg'


def test_thumbnail_height(builder):
    builder.build_all()
    with open(os.path.join(builder.destination_path, 'index.html')) as f:
        html = f.read()

    # Thumbnail is half the original width, so its computed height is half.
    assert '<img src="./test@192.jpg" width="192" height="256">' in html
