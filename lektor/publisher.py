import os
import errno
import select
import shutil
import hashlib
import tempfile
import posixpath
import subprocess
import mimetypes
from contextlib import contextmanager
from cStringIO import StringIO
from hashlib import md5

import boto3
from boto3.session import Session
import botocore.exceptions
from werkzeug import urls

from lektor.utils import portable_popen, locate_executable


devnull = open(os.devnull, 'rb+')


def _patch_git_env(env_overrides, ssh_command=None):
    env = dict(os.environ)
    env.update(env_overrides or ())

    keys = [
        ('GIT_COMMITTER_NAME', 'GIT_AUTHOR_NAME', 'Lektor Bot'),
        ('GIT_COMMITTER_EMAIL', 'GIT_AUTHOR_EMAIL',
         'bot@getlektor.com'),
    ]

    for key_a, key_b, default in keys:
        value_a = env.get(key_a)
        value_b = env.get(key_b)
        if value_a:
            if not value_b:
                env[key_b] = value_a
        elif value_b:
            if not value_a:
                env[key_a] = value_b
        else:
            env[key_a] = default
            env[key_b] = default

    if ssh_command is not None and not env.get('GIT_SSH_COMMAND'):
        env['GIT_SSH_COMMAND'] = ssh_command

    return env


def _write_ssh_key_file(temp_fn, credentials):
    if credentials:
        key_file = credentials.get('key_file')
        if key_file is not None:
            return key_file
        key = credentials.get('key')
        if key:
            parts = key.split(':', 1)
            if len(parts) == 1:
                kt = 'RSA'
            else:
                kt, key = parts
            with open(temp_fn, 'wb') as f:
                f.write(b'-----BEGIN %s PRIVATE KEY-----\n' % kt.upper())
                for x in xrange(0, len(key), 64):
                    f.write(key[x:x + 64].encode('utf-8') + b'\n')
                f.write(b'-----END %s PRIVATE KEY-----\n' % kt.upper())
            os.chmod(temp_fn, 0600)
            return temp_fn


def _get_ssh_cmd(port=None, keyfile=None):
    ssh_args = []
    if port:
        ssh_args.append('-p %s' % port)
    if keyfile:
        ssh_args.append('-i "%s"' % keyfile)
    return 'ssh %s' % ' '.join(ssh_args)


class PublishError(Exception):
    pass


class Command(object):

    def __init__(self, argline, cwd=None, env=None, capture=True,
                 silent=False):
        environ = dict(os.environ)
        if env:
            environ.update(env)
        kwargs = {'cwd': cwd, 'env': env}
        if silent:
            kwargs['stdout'] = devnull
            kwargs['stderr'] = devnull
            capture = False
        if capture:
            kwargs['stdout'] = subprocess.PIPE
            kwargs['stderr'] = subprocess.PIPE
        self.capture = capture
        self._cmd = portable_popen(argline, **kwargs)

    def wait(self):
        return self._cmd.wait()

    @property
    def status(self):
        return self._cmd.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._cmd.wait()

    def __iter__(self):
        if not self.capture:
            raise RuntimeError('Not capturing')
        streams = [self._cmd.stdout, self._cmd.stderr]
        while streams:
            for l in select.select(streams, [], streams):
                for stream in l:
                    line = stream.readline()
                    if not line:
                        if stream in streams:
                            streams.remove(stream)
                        break
                    yield line.rstrip().decode('utf-8', 'replace')

    def safe_iter(self):
        with self:
            for line in self:
                yield line

    def proc(self):
        if self.capture:
            return self.safe_iter()
        return self


class Publisher(object):

    def __init__(self, env, output_path):
        self.env = env
        self.output_path = os.path.abspath(output_path)

    @contextmanager
    def temporary_folder(self):
        folder = tempfile.mkdtemp()
        scratch = os.path.join(folder, 'scratch')
        os.mkdir(scratch)
        os.chmod(scratch, 0755)
        try:
            yield scratch
        finally:
            try:
                shutil.rmtree(folder)
            except (IOError, OSError):
                pass

    def publish(self, target_url, credentials=None):
        raise NotImplementedError()


class RsyncPublisher(Publisher):

    def get_command(self, target_url, tempdir, credentials):
        credentials = credentials or {}
        argline = ['rsync', '-rclzv', '--exclude=.lektor']
        target = []
        env = {}

        keyfile = _write_ssh_key_file(os.path.join(
            tempdir, 'ssh-auth-key'), credentials)

        if target_url.port is not None or keyfile is not None:
            argline.append('-e')
            argline.append(_get_ssh_cmd(target_url.port, keyfile))

        username = credentials.get('username') or target_url.username
        if username:
            target.append(username.encode('utf-8') + '@')

        target.append(target_url.ascii_host)
        target.append(':' + target_url.path.encode('utf-8').rstrip('/') + '/')

        argline.append(self.output_path.rstrip('/\\') + '/')
        argline.append(''.join(target))
        return Command(argline, env=env)

    def publish(self, target_url, credentials=None):
        with self.temporary_folder() as tempdir:
            client = self.get_command(target_url, tempdir, credentials)
            with client:
                for line in client:
                    yield line


class FtpConnection(object):

    def __init__(self, url, credentials=None):
        credentials = credentials or {}
        self.con = self.make_connection()
        self.url = url
        self.username = credentials.get('username') or url.username
        self.password = credentials.get('password') or url.password
        self.log_buffer = []
        self._known_folders = set()

    def make_connection(self):
        from ftplib import FTP
        return FTP()

    def drain_log(self):
        log = self.log_buffer[:]
        del self.log_buffer[:]
        for chunk in log:
            for line in chunk.splitlines():
                if isinstance(line, str):
                    line = line.decode('utf-8', 'replace')
                yield line.rstrip()

    def connect(self):
        options = self.url.decode_query()

        log = self.log_buffer
        log.append('000 Connecting to server ...')
        try:
            log.append(self.con.connect(self.url.ascii_host,
                                        self.url.port or 21))
        except Exception as e:
            log.append('000 Could not connect.')
            log.append(str(e))
            return False

        try:
            log.append(self.con.login(self.username.encode('utf-8'),
                                      self.password.encode('utf-8')))
        except Exception as e:
            log.append('000 Could not authenticate.')
            log.append(str(e))
            return False

        passive = options.get('passive') in ('on', 'yes', 'true', '1', None)
        log.append('000 Using passive mode: %s' % (passive and 'yes' or 'no'))
        self.con.set_pasv(passive)

        try:
            log.append(self.con.cwd(self.url.path.encode('utf-8')))
        except Exception as e:
            log.append(str(e))
            return False

        log.append('000 Connected!')
        return True

    def mkdir(self, path, recursive=True):
        if isinstance(path, unicode):
            path = path.encode('utf-8')
        if path in self._known_folders:
            return
        dirname, basename = posixpath.split(path)
        if dirname and recursive:
            self.mkdir(dirname)
        try:
            self.con.mkd(path)
        except Exception as e:
            msg = str(e)
            if msg[:4] != '550 ':
                self.log_buffer.append(e)
                return
        self._known_folders.add(path)

    def append(self, filename, data):
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        input = StringIO(data)
        try:
            self.con.storbinary('APPE ' + filename, input)
        except Exception as e:
            self.log_buffer.append(str(e))
            return False
        return True

    def get_file(self, filename, out=None):
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        getvalue = False
        if out is None:
            out = StringIO()
            getvalue = True
        try:
            self.con.retrbinary('RETR ' + filename, out.write)
        except Exception as e:
            msg = str(e)
            if msg[:4] != '550 ':
                self.log_buffer.append(e)
            return None
        if getvalue:
            return out.getvalue()
        return out

    def upload_file(self, filename, src, mkdir=False):
        if isinstance(src, basestring):
            src = StringIO(src)
        if mkdir:
            directory = posixpath.dirname(filename)
            if directory:
                self.mkdir(directory, recursive=True)
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        try:
            self.con.storbinary('STOR ' + filename, src,
                                blocksize=32768)
        except Exception as e:
            self.log_buffer.append(str(e))
            return False
        return True

    def rename_file(self, src, dst):
        try:
            self.con.rename(src, dst)
        except Exception as e:
            self.log_buffer.append(str(e))
            try:
                self.con.delete(dst)
            except Exception as e:
                self.log_buffer.append(str(e))
            try:
                self.con.rename(src, dst)
            except Exception as e:
                self.log_buffer.append(str(e))

    def delete_file(self, filename):
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        try:
            self.con.delete(filename)
        except Exception as e:
            self.log_buffer.append(str(e))

    def delete_folder(self, filename):
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        try:
            self.con.rmd(filename)
        except Exception as e:
            self.log_buffer.append(str(e))
        self._known_folders.discard(filename)


class FtpTlsConnection(FtpConnection):

    def make_connection(self):
        from ftplib import FTP_TLS
        return FTP_TLS()


class FtpPublisher(Publisher):
    connection_class = FtpConnection

    def read_existing_artifacts(self, con):
        contents = con.get_file('.lektor/listing')
        if not contents:
            return {}, set()
        duplicates = set()
        rv = {}
        # Later records override earlier ones.  There can be duplicate
        # entries if the file was not compressed.
        for line in contents.splitlines():
            items = line.split('|')
            if len(items) == 2:
                artifact_name = items[0].decode('utf-8')
                if artifact_name in rv:
                    duplicates.add(artifact_name)
                rv[artifact_name] = items[1]
        return rv, duplicates

    def iter_artifacts(self):
        """Iterates over all artifacts in the build folder and yields the
        artifacts.
        """
        for dirpath, dirnames, filenames in os.walk(self.output_path):
            dirnames[:] = [x for x in dirnames
                           if not self.env.is_ignored_artifact(x)]
            for filename in filenames:
                if self.env.is_ignored_artifact(filename):
                    continue
                full_path = os.path.join(self.output_path, dirpath, filename)
                local_path = full_path[len(self.output_path):] \
                    .lstrip(os.path.sep)
                if os.path.altsep:
                    local_path = local_path.lstrip(os.path.altsep)
                h = hashlib.sha1()
                try:
                    with open(full_path, 'rb') as f:
                        item = f.read(4096)
                        if not item:
                            break
                        h.update(item)
                except IOError as e:
                    if e.errno != errno.ENOENT:
                        raise
                yield (
                    local_path.replace(os.path.sep, '/'),
                    full_path,
                    h.hexdigest(),
                )

    def get_temp_filename(self, filename):
        dirname, basename = posixpath.split(filename)
        return posixpath.join(dirname, '.' + basename + '.tmp')

    def upload_artifact(self, con, artifact_name, source_file, checksum):
        with open(source_file, 'rb') as source:
            tmp_dst = self.get_temp_filename(artifact_name)
            con.log_buffer.append('000 Updating %s' % artifact_name)
            con.upload_file(tmp_dst, source, mkdir=True)
            con.rename_file(tmp_dst, artifact_name)
            con.append('.lektor/listing', '%s|%s\n' % (
                artifact_name.encode('utf-8'), checksum
            ))

    def consolidate_listing(self, con, current_artifacts):
        server_artifacts, duplicates = self.read_existing_artifacts(con)
        known_folders = set()
        for artifact_name in current_artifacts.iterkeys():
            known_folders.add(posixpath.dirname(artifact_name))

        for artifact_name, checksum in server_artifacts.iteritems():
            if artifact_name not in current_artifacts:
                con.log_buffer.append('000 Deleting %s' % artifact_name)
                con.delete_file(artifact_name)
                folder = posixpath.dirname(artifact_name)
                if folder not in known_folders:
                    con.log_buffer.append('000 Deleting %s' % folder)
                    con.delete_folder(folder)

        if duplicates or server_artifacts != current_artifacts:
            listing = []
            for artifact_name, checksum in current_artifacts.iteritems():
                listing.append('%s|%s\n' % (artifact_name, checksum))
            listing.sort()
            con.upload_file('.lektor/.listing.tmp', ''.join(listing))
            con.rename_file('.lektor/.listing.tmp', '.lektor/listing')

    def publish(self, target_url, credentials=None):
        con = self.connection_class(target_url, credentials)
        connected = con.connect()
        for event in con.drain_log():
            yield event
        if not connected:
            return

        yield '000 Reading server state ...'
        con.mkdir('.lektor')
        committed_artifacts, _ = self.read_existing_artifacts(con)
        for event in con.drain_log():
            yield event

        yield '000 Begin sync ...'
        current_artifacts = {}
        for artifact_name, filename, checksum in self.iter_artifacts():
            current_artifacts[artifact_name] = checksum
            if checksum != committed_artifacts.get(artifact_name):
                self.upload_artifact(con, artifact_name, filename, checksum)
                for event in con.drain_log():
                    yield event
        yield '000 Sync done!'

        yield '000 Consolidating server state ...'
        self.consolidate_listing(con, current_artifacts)
        for event in con.drain_log():
            yield event

        yield '000 All done!'


class FtpTlsPublisher(FtpPublisher):
    connection_class = FtpTlsConnection


class GithubPagesPublisher(Publisher):

    def get_credentials(self, url, credentials=None):
        credentials = credentials or {}
        username = credentials.get('username') or url.username
        password = credentials.get('password') or url.password
        rv = username
        if username and password:
            rv += ':' + password
        return rv and rv.encode('utf-8') or None

    def update_git_config(self, repo, url, branch, credentials=None):
        ssh_command = None
        path = (url.host + u'/' + url.path.strip(u'/')).encode('utf-8')
        cred = None
        if url.scheme in ('ghpages', 'ghpages+ssh'):
            push_url = 'git@github.com:%s.git' % path
            keyfile = _write_ssh_key_file(os.path.join(
                repo, '.git', 'ssh-auth-key'), credentials)
            if keyfile or url.port:
                ssh_command = _get_ssh_cmd(url.port, keyfile)
        else:
            push_url = 'https://github.com/%s' % path
            cred = self.get_credentials(url, credentials)

        with open(os.path.join(repo, '.git', 'config'), 'a') as f:
            f.write('[remote "origin"]\nurl = %s\n'
                    'fetch = +refs/heads/%s:refs/remotes/origin/%s\n' %
                    (push_url, branch, branch))
            if cred:
                cred_path = os.path.join(repo, '.git', 'credentials')
                f.write('[credential]\nhelper = store --file "%s"\n' %
                        cred_path)
                with open(cred_path, 'w') as cf:
                    cf.write('https://%s@github.com\n' % cred)

        return ssh_command

    def link_artifacts(self, path):
        try:
            link = os.link
        except AttributeError:
            link = shutil.copy

        # Clean old
        for filename in os.listdir(path):
            if filename == '.git':
                continue
            filename = os.path.join(path, filename)
            try:
                os.remove(filename)
            except OSError:
                shutil.rmtree(filename)

        # Add new
        for dirpath, dirnames, filenames in os.walk(self.output_path):
            dirnames[:] = [x for x in dirnames if x != '.lektor']
            for filename in filenames:
                full_path = os.path.join(self.output_path, dirpath, filename)
                dst = os.path.join(path, full_path[len(self.output_path):]
                                   .lstrip(os.path.sep)
                                   .lstrip(os.path.altsep or ''))
                try:
                    os.makedirs(os.path.dirname(dst))
                except (OSError, IOError):
                    pass
                link(full_path, dst)

    def write_cname(self, path, target_url):
        params = target_url.decode_query()
        cname = params.get('cname')
        if cname is not None:
            with open(os.path.join(path, 'CNAME'), 'w') as f:
                f.write('%s\n' % cname.encode('utf-8'))

    def publish(self, target_url, credentials=None):
        if not locate_executable('git'):
            raise PublishError('git executable not found; cannot deploy.')

        # When pushing to the username.github.io repo we need to push to
        # master, otherwise to gh-pages
        if target_url.host + '.github.io' == target_url.path.strip('/'):
            branch = 'master'
        else:
            branch = 'gh-pages'

        with self.temporary_folder() as path:
            ssh_command = None
            def git(args, **kwargs):
                kwargs['env'] = _patch_git_env(kwargs.pop('env', None),
                                               ssh_command)
                return Command(['git'] + args, cwd=path, **kwargs).proc()

            for line in git(['init']):
                yield line
            ssh_command = self.update_git_config(path, target_url, branch,
                                                 credentials)
            for line in git(['remote', 'update']):
                yield line

            if git(['checkout', '-q', branch], silent=True).wait() != 0:
                git(['checkout', '-qb', branch], silent=True).wait()

            self.link_artifacts(path)
            self.write_cname(path, target_url)
            for line in git(['add', '-f', '--all', '.']):
                yield line
            for line in git(['commit', '-qm', 'Synchronized build']):
                yield line
            for line in git(['push', 'origin', branch]):
                yield line


class S3Publisher(Publisher):

    def __init__(self, env, output_path):
        super(S3Publisher, self).__init__(env, output_path)
        self.s3 = None
        self.bucket = None
        self.key_prefix = ''

    def split_bucket_uri(self, target_url):
        bucket = target_url.netloc
        key = target_url.path
        if key != '':
            if key.startswith('/'):
                key = key[1:]
            if not key.endswith('/'):
                key = key + '/'
        return bucket, key

    def verify_bucket_exists(self):
        exists = True
        try:
            self.s3.meta.client.head_bucket(Bucket=self.bucket.name)
        except botocore.exceptions.ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                exists = False
        return exists

    def list_remote(self):
        return self.bucket.objects.filter(Prefix=self.key_prefix)

    def list_local(self):
        all_files = []
        for path, _, files in os.walk(self.output_path):
            for f in files:
                fullpath = os.path.join(path, f)
                relpath = os.path.relpath(fullpath, self.output_path)
                if os.path.dirname(relpath) != ".lektor":
                    all_files.append(os.path.relpath(fullpath, self.output_path))

        return all_files

    def file_md5(self, filename):
        '''Compute the md5 checksum for a file.'''
        md5sum = md5()
        with open(filename, 'rb') as f:
            data = f.read(8192)
            while len(data) > 0:
                md5sum.update(data)
                data = f.read(8192)
        return md5sum.hexdigest()

    def obj_md5(self, obj):
        """Compute the md5 checksum for an S3 object.

        MD5s can be stored in the 'ETag' field of S3 objects. The
        field doesn't store the MD5 in two cases: objects uploaded
        with Multipart Upload and objects encrypted with SSE-C or
        SSE-KMS. In those cases, we'll just return an empty string.

        """

        # Multipart-uploaded messages have etags that look like 'xxx-nnn'
        if '-' in obj.e_tag:
            return ''

        # SSE-C and SSE-KMS-encrypted objects have a few values set
        # when you call HeadObject on them
        obj_meta = self.s3.meta.client.head_object(
            Bucket=obj.bucket_name,
            Key=obj.key,
        )
        if obj_meta.get('SSECustomerAlgorithm') is not None:
            return ''
        if obj_meta.get('ServerSideEncryption') == 'aws:kms':
            return ''

        # Else, the etag stores an md5 checksum enclosed in double quotes
        return obj.e_tag.strip('"')

    def different(self, local_filename, remote_obj):
        """Return true if the local file is different than the remote object."""
        abs_filename = os.path.join(self.output_path, local_filename)
        # Check size first.
        if remote_obj.size != os.path.getsize(abs_filename):
            return True

        # check md5
        if self.file_md5(abs_filename) != self.obj_md5(remote_obj):
            return True

        # they're the same
        return False

    def compute_diff(self, local, remote):
        """Compute the changeset for updating remote to match local"""
        diff = {
            'add': [],
            'update': [],
            'delete': [],
        }
        remote_keys = {o.key: o for o in remote}
        for f in local:
            key = self.key_prefix + f
            if key in remote_keys:
                if self.different(f, remote_keys[key]):
                    diff['update'].append(f)
            else:
                diff['add'].append(f)
        for k in remote_keys:
            if k not in local:
                diff['delete'].append(k)
        return diff

    def add(self, filename):
        abs_filename = os.path.join(self.output_path, filename)
        key = self.key_prefix + filename

        mime, _ = mimetypes.guess_type(filename)
        if mime is None:
            mime = "text/plain"
        self.bucket.upload_file(abs_filename, key, ExtraArgs={'ContentType': mime})

    def update(self, filename):
        # Updates are just overwrites in S3
        self.add(filename)

    def delete_batch(self, filenames):
        if len(filenames) == 0:
            return
        self.bucket.delete_objects(
            Delete={'Objects': [{'Key': self.key_prefix + f} for f in filenames]}
        )

    def connect(self, credentials):
        self.s3 = boto3.resource(service_name='s3')

    def publish(self, target_url, credentials=None):
        if credentials is None:
            credentials = {}
        self.connect(credentials)

        bucket_uri, self.key_prefix = self.split_bucket_uri(target_url)
        self.bucket = self.s3.Bucket(bucket_uri)
        if not self.verify_bucket_exists():
            raise PublishError(
                's3 bucket "%s" does not exist, please create it first'
                % bucket_uri
            )

        local = self.list_local()
        remote = self.list_remote()
        diff = self.compute_diff(local, remote)

        for f in diff['add']:
            yield 'adding %s' % f
            self.add(f)

        for f in diff['update']:
            yield 'updating %s' % f
            self.update(f)

        for f in diff['delete']:
            yield 'deleting %s' % f
        self.delete_batch(diff['delete'])


publishers = {
    'rsync': RsyncPublisher,
    'ftp': FtpPublisher,
    'ftps': FtpTlsPublisher,
    'ghpages': GithubPagesPublisher,
    'ghpages+https': GithubPagesPublisher,
    'ghpages+ssh': GithubPagesPublisher,
    's3': S3Publisher,
}


def publish(env, target, output_path, credentials=None):
    url = urls.url_parse(unicode(target))
    publisher = publishers.get(url.scheme)
    if publisher is not None:
        return publisher(env, output_path).publish(url, credentials)
