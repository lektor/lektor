import os
import base64
import codecs
import hashlib
import mimetypes


class FileContents(object):

    def __init__(self, filename):
        self.filename = filename
        self._md5 = None
        self._sha1 = None
        self._integrity = None
        self._mimetype = mimetypes.guess_type(filename)[0] \
            or 'application/octet-stream'

    @property
    def sha1(self):
        self._ensure_hashes()
        return self._sha1

    @property
    def md5(self):
        self._ensure_hashes()
        return self._md5

    @property
    def integrity(self):
        self._ensure_hashes()
        return self._integrity

    @property
    def mimetype(self):
        return self._mimetype

    @property
    def bytes(self):
        try:
            return os.stat(self.filename).st_size
        except (OSError, IOError):
            return 0

    def as_data_url(self, mediatype=None):
        if mediatype is None:
            mediatype = self.mimetype
        return 'data:%s;base64,%s' % (
            mediatype,
            self.as_base64(),
        )

    def as_text(self):
        with self.open() as f:
            return f.read()

    def as_bytes(self):
        with self.open('rb') as f:
            return f.read()

    def as_base64(self):
        return base64.b64encode(self.as_bytes())

    def open(self, mode='r', encoding=None):
        if mode == 'rb':
            return open(self.filename, 'rb')
        elif mode != 'r':
            raise TypeError('Can only open files for reading')
        return codecs.open(self.filename, encoding=encoding or 'utf-8')

    def _ensure_hashes(self):
        if self._md5 is not None:
            return
        with self.open('rb') as f:
            md5 = hashlib.md5()
            sha1 = hashlib.sha1()
            sha384 = hashlib.sha384()
            while 1:
                chunk = f.read(16384)
                if not chunk:
                    break
                md5.update(chunk)
                sha1.update(chunk)
                sha384.update(chunk)
            self._md5 = md5.hexdigest()
            self._sha1 = sha1.hexdigest()
            self._integrity = 'sha384-' + base64.b64encode(sha384.digest())

    def __repr__(self):
        return '<FileContents %r md5=%r>' % (
            self.filename,
            self.md5,
        )
