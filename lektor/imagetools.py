# -*- coding: utf-8 -*-
import os
import imghdr
import struct
import posixpath
from datetime import datetime
from xml.etree import ElementTree as etree
import exifread

from lektor.utils import get_dependent_url, portable_popen, locate_executable
from lektor.reporter import reporter
from lektor.uilink import BUNDLE_BIN_PATH
from lektor._compat import iteritems, text_type, PY2


# yay shitty library
datetime.strptime('', '')


def _convert_gps(coords, hem):
    deg, min, sec = [float(x.num) / float(x.den) for x in coords]
    sign = -1 if hem in 'SW' else 1
    return sign * (deg + min / 60.0 + sec / 3600.0)


def _combine_make(make, model):
    make = make or ''
    model = model or ''
    if make and model.startswith(make):
        return make
    return u' '.join([make, model]).strip()


class EXIFInfo(object):

    def __init__(self, d):
        self._mapping = d

    def __bool__(self):
        return bool(self._mapping)
    __nonzero__ = __bool__

    def to_dict(self):
        rv = {}
        for key, value in iteritems(self.__class__.__dict__):
            if key[:1] != '_' and isinstance(value, property):
                rv[key] = getattr(self, key)
        return rv

    def _get_string(self, key):
        try:
            value = self._mapping[key].values
        except KeyError:
            return None
        if isinstance(value, text_type):
            return value
        return value.decode('utf-8', 'replace')

    def _get_int(self, key):
        try:
            return self._mapping[key].values[0]
        except LookupError:
            return None

    def _get_float(self, key, precision=4):
        try:
            val = self._mapping[key].values[0]
            if isinstance(val, int):
                return float(val)
            return round(float(val.num) / float(val.den), precision)
        except LookupError:
            return None

    def _get_frac_string(self, key):
        try:
            val = self._mapping[key].values[0]
            return '%s/%s' % (val.num, val.den)
        except LookupError:
            return None

    @property
    def artist(self):
        return self._get_string('Image Artist')

    @property
    def copyright(self):
        return self._get_string('Image Copyright')

    @property
    def camera_make(self):
        return self._get_string('Image Make')

    @property
    def camera_model(self):
        return self._get_string('Image Model')

    @property
    def camera(self):
        return _combine_make(self.camera_make, self.camera_model)

    @property
    def lens_make(self):
        return self._get_string('EXIF LensMake')

    @property
    def lens_model(self):
        return self._get_string('EXIF LensModel')

    @property
    def lens(self):
        return _combine_make(self.lens_make, self.lens_model)

    @property
    def aperture(self):
        return self._get_float('EXIF ApertureValue')

    @property
    def f_num(self):
        return self._get_float('EXIF FNumber')

    @property
    def f(self):
        return u'ƒ/%s' % self.f_num

    @property
    def exposure_time(self):
        return self._get_frac_string('EXIF ExposureTime')

    @property
    def shutter_speed(self):
        val = self._get_float('EXIF ShutterSpeedValue')
        if val is not None:
            return '1/%d' % round(1 / (2 ** -val))  # pylint: disable=invalid-unary-operand-type
        return None

    @property
    def focal_length(self):
        val = self._get_float('EXIF FocalLength')
        if val is not None:
            return u'%smm' % val
        return None

    @property
    def focal_length_35mm(self):
        val = self._get_float('EXIF FocalLengthIn35mmFilm')
        if val is not None:
            return u'%dmm' % val
        return None

    @property
    def flash_info(self):
        try:
            value = self._mapping['EXIF Flash'].printable
        except KeyError:
            return None
        if isinstance(value, text_type):
            return value
        return value.decode('utf-8')

    @property
    def iso(self):
        val = self._get_int('EXIF ISOSpeedRatings')
        if val is not None:
            return val
        return None

    @property
    def created_at(self):
        date_tags = (
            'GPS GPSDate',
            'Image DateTimeOriginal',
            'EXIF DateTimeOriginal',
            'EXIF DateTimeDigitized',
            'Image DateTime',
        )
        for tag in date_tags:
            try:
                return datetime.strptime(self._mapping[tag].printable,
                                         '%Y:%m:%d %H:%M:%S')
            except (KeyError, ValueError):
                continue
        return None

    @property
    def longitude(self):
        try:
            return _convert_gps(self._mapping['GPS GPSLongitude'].values,
                                self._mapping['GPS GPSLongitudeRef'].printable)
        except KeyError:
            return None

    @property
    def latitude(self):
        try:
            return _convert_gps(self._mapping['GPS GPSLatitude'].values,
                                self._mapping['GPS GPSLatitudeRef'].printable)
        except KeyError:
            return None

    @property
    def altitude(self):
        val = self._get_float('GPS GPSAltitude')
        if val is not None:
            try:
                ref = self._mapping['GPS GPSAltitudeRef'].values[0]
            except LookupError:
                ref = 0
            if ref == 1:
                val *= -1
            return val
        return None

    @property
    def location(self):
        lat = self.latitude
        long = self.longitude
        if lat is not None and long is not None:
            return (lat, long)
        return None

    @property
    def documentname(self):
        return self._get_string('Image DocumentName')

    @property
    def description(self):
        return self._get_string('Image ImageDescription')

    @property
    def is_rotated(self):
        """Return if the image is rotated according to the Orientation header.

        The Orientation header in EXIF stores an integer value between
        1 and 8, where the values 5-8 represent "portrait" orientations
        (rotated 90deg left, right, and mirrored versions of those), i.e.,
        the image is rotated.
        """
        return self._get_int('Image Orientation') in {5, 6, 7, 8}

def get_suffix(width, height, crop=False, quality=None):
    suffix = str(width)
    if height is not None:
        suffix += 'x%s' % height
    if crop:
        suffix += '_crop'
    if quality is not None:
        suffix += '_q%s' % quality
    return suffix


def get_svg_info(fp):
    _, svg = next(etree.iterparse(fp, ['start']), (None, None))
    fp.seek(0)
    if svg is not None and svg.tag == '{http://www.w3.org/2000/svg}svg':
        try:
            width = int(svg.attrib['width'])
            height = int(svg.attrib['height'])
            return 'svg', width, height
        except (ValueError, KeyError):
            pass
    return 'unknown', None, None


def get_image_info(fp):
    """Reads some image info from a file descriptor."""
    head = fp.read(32)
    fp.seek(0)
    if len(head) < 24:
        return 'unknown', None, None

    if head.strip().startswith(b'<?xml '):
        return get_svg_info(fp)

    fmt = imghdr.what(None, head)

    width = None
    height = None
    if fmt == 'png':
        check = struct.unpack('>i', head[4:8])[0]
        if check == 0x0d0a1a0a:
            width, height = struct.unpack('>ii', head[16:24])
    elif fmt == 'gif':
        width, height = struct.unpack('<HH', head[6:10])
    elif fmt == 'jpeg':
        try:
            fp.seek(0)
            size = 2
            ftype = 0
            while not 0xc0 <= ftype <= 0xcf:
                fp.seek(size, 1)
                byte = fp.read(1)
                while ord(byte) == 0xff:
                    byte = fp.read(1)
                ftype = ord(byte)
                size = struct.unpack('>H', fp.read(2))[0] - 2
            # We are at a SOFn block
            fp.seek(1, 1)  # Skip `precision' byte.
            height, width = struct.unpack('>HH', fp.read(4))
        except Exception:
            return 'jpeg', None, None

    return fmt, width, height


def read_exif(fp):
    """Reads exif data from a file pointer of an image and returns it."""
    exif = exifread.process_file(fp)
    return EXIFInfo(exif)


def find_imagemagick(im=None):
    """Finds imagemagick and returns the path to it."""
    # If it's provided explicitly and it's valid, we go with that one.
    if im is not None and os.path.isfile(im):
        return im

    # On windows, imagemagick was renamed to magick, because
    # convert is system utility for fs manipulation.
    imagemagick_exe = 'convert' if os.name != 'nt' else 'magick'

    # If we have a shipped imagemagick, then we used this one.
    if BUNDLE_BIN_PATH is not None:
        executable = os.path.join(BUNDLE_BIN_PATH, imagemagick_exe)
        if os.name == 'nt':
            executable += '.exe'
        if os.path.isfile(executable):
            return executable

    rv = locate_executable(imagemagick_exe)
    if rv is not None:
        return rv

    # Give up.
    raise RuntimeError('Could not locate imagemagick.')


def get_thumbnail_ext(source_filename):
    ext = source_filename.rsplit('.', 1)[-1].lower()
    # if the extension is already of a format that a browser understands
    # we will roll with it.
    if ext.lower() in ('png', 'jpg', 'jpeg', 'gif'):
        return None
    # Otherwise we roll with JPEG as default.
    return '.jpeg'


def get_quality(source_filename):
    ext = source_filename.rsplit('.', 1)[-1].lower()
    if ext.lower() == 'png':
        return 75
    return 85


def computed_height(source_image, format, width, actual_width, actual_height):
    # If the file is a JPEG file and the EXIF header shows that the image
    # is rotated, imagemagick will auto-orient the file. That is, a 400x200
    # file where the target width is 100px will *not* be converted to a
    # 100x50 image, but to 100x200.
    if format == 'jpeg':
        with open(source_image, 'rb') as image_file:
            exif = read_exif(image_file)
        if exif.is_rotated:
            actual_width, actual_height = actual_height, actual_width
    return int(float(actual_height) * (float(width) / float(actual_width)))


def process_image(ctx, source_image, dst_filename, width, height=None,
                  crop=False, quality=None):
    """Build image from source image, optionally compressing and resizing.

    "source_image" is the absolute path of the source in the content directory,
    "dst_filename" is the absolute path of the target in the output directory.
    """
    im = find_imagemagick(
        ctx.build_state.config['IMAGEMAGICK_EXECUTABLE'])

    if quality is None:
        quality = get_quality(source_image)

    resize_key = str(width)
    if height is not None:
        resize_key += 'x' + str(height)

    cmdline = [im, source_image, '-auto-orient']
    if crop:
        cmdline += ['-resize', resize_key + '^',
                    '-gravity', 'Center',
                    '-extent', resize_key]
    else:
        cmdline += ['-resize', resize_key]

    cmdline += ['-quality', str(quality), dst_filename]

    reporter.report_debug_info('imagemagick cmd line', cmdline)
    portable_popen(cmdline).wait()


def make_thumbnail(ctx, source_image, source_url_path, width, height=None,
                   crop=False, quality=None):
    """Helper method that can create thumbnails from within the build process
    of an artifact.
    """
    with open(source_image, 'rb') as f:
        format, source_width, source_height = get_image_info(f)
        if format == 'unknown':
            raise RuntimeError('Cannot process unknown images')

    suffix = get_suffix(width, height, crop=crop, quality=quality)
    dst_url_path = get_dependent_url(source_url_path, suffix,
                                     ext=get_thumbnail_ext(source_image))
    report_height = height

    if height is None:
        # we can only crop if a height is specified
        crop = False
        report_height = computed_height(source_image, format, width,
                                        source_width, source_height)

    # If we are dealing with an actual svg image, we do not actually
    # resize anything, we just return it.  This is not ideal but it's
    # better than outright failing.
    if format == 'svg':
        return Thumbnail(source_url_path, width, height)

    @ctx.sub_artifact(artifact_name=dst_url_path, sources=[source_image])
    def build_thumbnail_artifact(artifact):
        artifact.ensure_dir()
        process_image(ctx, source_image, artifact.dst_filename,
                      width, height, crop=crop, quality=quality)

    return Thumbnail(dst_url_path, width, report_height)


class Thumbnail(object):
    """Holds information about a thumbnail."""

    def __init__(self, url_path, width, height=None):
        #: the `width` of the thumbnail in pixels.
        self.width = width
        #: the `height` of the thumbnail in pixels.
        self.height = height
        #: the URL path of the image.
        self.url_path = url_path

    def __unicode__(self):
        return posixpath.basename(self.url_path)

    if not PY2:
        __str__ = __unicode__
