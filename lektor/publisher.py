import os
import select
import shutil
import tempfile
import subprocess
from contextlib import contextmanager

from werkzeug import urls

from lektor.utils import portable_popen, locate_executable
from lektor.exception import LektorException


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


@contextmanager
def _temporary_folder(env):
    base = env.temp_path
    try:
        os.makedirs(base)
    except OSError:
        pass

    folder = tempfile.mkdtemp(prefix='.deploytemp', dir=base)
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


class PublishError(LektorException):
    """Raised by publishers if something goes wrong."""
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

    def fail(self, message):
        raise PublishError(message)

    def publish(self, target_url, credentials=None, **extra):
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

    def publish(self, target_url, credentials=None, **extra):
        with _temporary_folder(self.env) as tempdir:
            client = self.get_command(target_url, tempdir, credentials)
            with client:
                for line in client:
                    yield line


class FtpPublisher(Publisher):

    def make_target(self, url, credentials=None):
        try:
            from ftpsync.targets import make_target
        except ImportError:
            self.fail("Please install pyftpsync for FTP support.")
        target = make_target(url.to_url())
        if credentials:
            username = credentials.get('username')
            if username:
                target.username = username
            password = credentials.get('password')
            if password:
                target.password = password
        return target

    def publish(self, target_url, credentials=None, **extra):
        try:
            from ftpsync.targets import FsTarget
            from ftpsync.synchronizers import UploadSynchronizer
        except ImportError:
            self.fail("Please install pyftpsync for FTP support.")
        local = FsTarget(self.output_path)
        remote = self.make_target(target_url, credentials)
        opts = {'dry_run': False, 'omit': '.lektor,.lektor/*'}
        opts.update(extra)
        sync = UploadSynchronizer(local, remote, opts)
        sync.run()
        return []  # ftpsync logs directly to stdout


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

    def publish(self, target_url, credentials=None, **extra):
        if not locate_executable('git'):
            self.fail('git executable not found; cannot deploy.')

        # When pushing to the username.github.io repo we need to push to
        # master, otherwise to gh-pages
        if target_url.host + '.github.io' == target_url.path.strip('/'):
            branch = 'master'
        else:
            branch = 'gh-pages'

        with _temporary_folder(self.env) as path:
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


builtin_publishers = {
    'rsync': RsyncPublisher,
    'ftp': FtpPublisher,
    'ftps': FtpPublisher,
    'ghpages': GithubPagesPublisher,
    'ghpages+https': GithubPagesPublisher,
    'ghpages+ssh': GithubPagesPublisher,
}


def publish(env, target, output_path, credentials=None, **extra):
    url = urls.url_parse(unicode(target))
    publisher = env.publishers.get(url.scheme)
    if publisher is None:
        raise PublishError('"%s" is an unknown scheme.' % url.scheme)
    return publisher(env, output_path).publish(url, credentials, **extra)
