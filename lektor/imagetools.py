# -*- coding: utf-8 -*-
import os
import imghdr
import struct
import exifread
import posixpath

from datetime import datetime

from lektor.utils import get_dependent_url, portable_popen, locate_executable
from lektor.reporter import reporter
from lektor.uilink import BUNDLE_BIN_PATH


# yay shitty library
datetime.strptime('', '')


def _convert_gps(coords, hem):
    deg, min, sec = [float(x.num) / float(x.den) for x in coords]
    sign = hem in 'SW' and -1 or 1
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

    def __nonzero__(self):
        return bool(self._mapping)

    def to_dict(self):
        rv = {}
        for key, value in self.__class__.__dict__.iteritems():
            if key[:1] != '_' and isinstance(value, property):
                rv[key] = getattr(self, key)
        return rv

    def _get_string(self, key):
        try:
            return self._mapping[key].values.decode('utf-8', 'replace')
        except KeyError:
            return None

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
            return '1/%d' % round(1 / (2 ** -val))

    @property
    def focal_length(self):
        val = self._get_float('EXIF FocalLength')
        if val is not None:
            return u'%smm' % val

    @property
    def focal_length_35mm(self):
        val = self._get_float('EXIF FocalLengthIn35mmFilm')
        if val is not None:
            return u'%dmm' % val

    @property
    def flash_info(self):
        try:
            return self._mapping['EXIF Flash'].printable.decode('utf-8')
        except KeyError:
            return None

    @property
    def iso(self):
        val = self._get_int('EXIF ISOSpeedRatings')
        if val is not None:
            return val

    @property
    def created_at(self):
        try:
            return datetime.strptime(self._mapping['Image DateTime'].printable,
                                     '%Y:%m:%d %H:%M:%S')
        except (KeyError, ValueError):
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

    @property
    def location(self):
        lat = self.latitude
        long = self.longitude
        if lat is not None and long is not None:
            return (lat, long)


def get_image_info(fp):
    """Reads some image info from a file descriptor."""
    head = fp.read(32)
    fp.seek(0)
    if len(head) < 24:
        return 'unknown', None, None

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


def make_thumbnail(ctx, source_image, source_url_path, size, **options):
    """Helper method that can create thumbnails from within the build process
    of an artifact. `size` is either a one-tuple (width,) or (width, height).
    """
    options['size'] = size
    options['imagemagick'] = ctx.build_state.config['IMAGEMAGICK_EXECUTABLE']
    thumbnailer = Thumbnailer(source_image, options)

    dst_url_path = get_dependent_url(source_url_path, thumbnailer.get_suffix(),
                                     ext=thumbnailer.get_thumbnail_ext())

    @ctx.sub_artifact(artifact_name=dst_url_path, sources=[source_image])
    def build_thumbnail_artifact(artifact):
        artifact.ensure_dir()
        thumbnailer.generate(artifact.dst_filename)

    return Thumbnail(dst_url_path, *options['size'])


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


class ThumbnailError(Exception):
    pass


class Thumbnailer(object):
    """Creates thumbnails from images with more control of generation options"""

    def __init__(self, source_image, options):
        self.source_image = source_image
        im = self.find_imagemagick(options.pop('imagemagick', None))
        self.options = options
        self.cmdline = self.generate_cmdline(im, options)

    def generate_cmdline(self, im, options):
        cmdline = [im, self.source_image,
                   # parse EXIF data to show image in correct orientation
                   # (portrait or landscape)
                   '-auto-orient',
                   '-quality', str(self.get_quality())]
        for k, v in options.items():
            if hasattr(self, 'parse_%s' % k):
                result = getattr(self, 'parse_%s' % k)(v)
                if result:
                    cmdline += result
            else:
                raise ThumbnailError('Unknown thumbnail option: %s' % k)

        if '-resize' not in cmdline:
            # if no other parameter tried to resize, do it now
            cmdline += ['-resize', self.size_str]
        return cmdline

    def find_imagemagick(self, im):
        """Finds imagemagick and returns the path to it."""
        # If it's provided explicitly and it's valid, we go with that one.
        if im is not None and os.path.isfile(im):
            return im

        # If we have a shipped imagemagick, then we used this one.
        if BUNDLE_BIN_PATH is not None:
            executable = os.path.join(BUNDLE_BIN_PATH, 'convert')
            if os.name == 'nt':
                executable += '.exe'
            if os.path.isfile(executable):
                return executable

        # If we're not on windows, we locate the executable like we would
        # do normally.
        if os.name != 'nt':
            rv = locate_executable('convert')
            if rv is not None:
                return rv

        # On windows, we only scan the program files for an image magick
        # installation, because this is where this usually goes.  We do
        # this because the convert executable is otherwise the system
        # one which can convert file systems and stuff like this.
        else:
            for key in 'ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)':
                value = os.environ.get(key)
                if not value:
                    continue
                try:
                    for filename in os.listdir(value):
                        if filename.lower().startswith('imagemagick-'):
                            exe = os.path.join(value, filename, 'convert.exe')
                            if os.path.isfile(exe):
                                return exe
                except OSError:
                    continue

        # Give up.
        raise RuntimeError('Could not locate imagemagick.')

    def get_suffix(self):
        parts = [self.size_str]
        for key, value in sorted(self.options.iteritems()):
            if not value or key == 'size':
                continue
            if value is True:
                parts.append(key)
                continue
            if not isinstance(value, basestring):
                try:
                    value = ','.join([unicode(item) for item in value])
                except TypeError:
                    value = unicode(value)
            parts.append(u'%s-%s' % (key, value))
        return u'_'.join(parts)

    def get_thumbnail_ext(self):
        ext = self.source_image.rsplit('.', 1)[-1].lower()
        # if the extension is already of a format that a browser understands
        # we will roll with it.
        if ext.lower() in ('png', 'jpg', 'jpeg', 'gif'):
            return None
        # Otherwise we roll with JPEG as default.
        return '.jpeg'

    def get_quality(self):
        ext = self.source_image.rsplit('.', 1)[-1].lower()
        if ext.lower() == 'png':
            return 75
        return 85

    @property
    def size_str(self):
        return 'x'.join(map(str, self.options['size']))

    def parse_size(self, __):
        # size does not need to be parsed explicitly
        pass

    def parse_crop(self, crop):
        if crop and len(self.options['size']) > 1:
            # we can crop only if there's a height
            return ['-resize', self.size_str + '^',
                    '-gravity', 'Center',
                    '-extent', self.size_str]

    def generate(self, dst_filename):
        self.cmdline.append(dst_filename)
        reporter.report_debug_info('imagemagick cmd line', self.cmdline)
        portable_popen(self.cmdline).wait()
