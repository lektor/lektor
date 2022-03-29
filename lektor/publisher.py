import errno
import hashlib
import io
import os
import posixpath
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from ftplib import Error as FTPError

from werkzeug import urls

from lektor.exception import LektorException
from lektor.utils import locate_executable
from lektor.utils import portable_popen


def _patch_git_env(env_overrides, ssh_command=None):
    env = dict(os.environ)
    env.update(env_overrides or ())

    keys = [
        ("GIT_COMMITTER_NAME", "GIT_AUTHOR_NAME", "Lektor Bot"),
        ("GIT_COMMITTER_EMAIL", "GIT_AUTHOR_EMAIL", "bot@getlektor.com"),
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

    if ssh_command is not None and not env.get("GIT_SSH_COMMAND"):
        env["GIT_SSH_COMMAND"] = ssh_command

    return env


def _write_ssh_key_file(temp_fn, credentials):
    if credentials:
        key_file = credentials.get("key_file")
        if key_file is not None:
            return key_file
        key = credentials.get("key")
        if key:
            parts = key.split(":", 1)
            if len(parts) == 1:
                kt = "RSA"
            else:
                kt, key = parts
            with open(temp_fn, "w", encoding="utf-8") as f:
                f.write("-----BEGIN %s PRIVATE KEY-----\n" % kt.upper())
                for x in range(0, len(key), 64):
                    f.write(key[x : x + 64] + "\n")
                f.write("-----END %s PRIVATE KEY-----\n" % kt.upper())
            os.chmod(temp_fn, 0o600)
            return temp_fn
    return None


def _get_ssh_cmd(port=None, keyfile=None):
    ssh_args = []
    if port:
        ssh_args.append("-p %s" % port)
    if keyfile:
        ssh_args.append('-i "%s"' % keyfile)
    return "ssh %s" % " ".join(ssh_args)


@contextmanager
def _temporary_folder(env):
    base = env.temp_path
    try:
        os.makedirs(base)
    except OSError:
        pass

    folder = tempfile.mkdtemp(prefix=".deploytemp", dir=base)
    scratch = os.path.join(folder, "scratch")
    os.mkdir(scratch)
    os.chmod(scratch, 0o755)
    try:
        yield scratch
    finally:
        try:
            shutil.rmtree(folder)
        except (IOError, OSError):
            pass


class PublishError(LektorException):
    """Raised by publishers if something goes wrong."""


class Command:
    def __init__(self, argline, cwd=None, env=None, capture=True, silent=False):
        environ = dict(os.environ)
        if env:
            environ.update(env)
        kwargs = {"cwd": cwd, "env": environ}
        if silent:
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL
            capture = False
        if capture:
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.STDOUT
            if sys.version_info >= (3, 7):
                # Python >= 3.7 has sane encoding defaults in the case that the system is
                # (likely mis-)configured to use ASCII as the default encoding (PEP538).
                # It also provides a way for the user to force the use of UTF-8 (PEP540).
                kwargs["text"] = True
            else:
                kwargs["encoding"] = "utf-8"
            kwargs["errors"] = "replace"
        self.capture = capture
        self._cmd = portable_popen(argline, **kwargs)

    def wait(self):
        returncode = self._cmd.wait()
        if self._cmd.stdout is not None:
            self._cmd.stdout.close()
        return returncode

    @property
    def returncode(self):
        return self._cmd.returncode

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.wait()

    def __iter__(self):
        if not self.capture:
            raise RuntimeError("Not capturing")

        for line in self._cmd.stdout:
            yield line.rstrip()

    def safe_iter(self):
        with self:
            for line in self:
                yield line

    @property
    def output(self):
        return self.safe_iter()


class Publisher:
    def __init__(self, env, output_path):
        self.env = env
        self.output_path = os.path.abspath(output_path)

    def fail(self, message):
        # pylint: disable=no-self-use
        raise PublishError(message)

    def publish(self, target_url, credentials=None, **extra):
        raise NotImplementedError()


class RsyncPublisher(Publisher):
    def get_command(self, target_url, tempdir, credentials):
        credentials = credentials or {}
        argline = ["rsync", "-rclzv", "--exclude=.lektor"]
        target = []
        env = {}

        options = target_url.decode_query()
        exclude = options.getlist("exclude")
        for file in exclude:
            argline.extend(("--exclude", file))

        delete = options.get("delete", False) in ("", "on", "yes", "true", "1", None)
        if delete:
            argline.append("--delete-after")

        keyfile = _write_ssh_key_file(
            os.path.join(tempdir, "ssh-auth-key"), credentials
        )

        if target_url.port is not None or keyfile is not None:
            argline.append("-e")
            argline.append(_get_ssh_cmd(target_url.port, keyfile))

        username = credentials.get("username") or target_url.username
        if username:
            target.append(username + "@")

        if target_url.ascii_host is not None:
            target.append(target_url.ascii_host)
            target.append(":")
        target.append(target_url.path.rstrip("/") + "/")

        argline.append(self.output_path.rstrip("/\\") + "/")
        argline.append("".join(target))
        return Command(argline, env=env)

    def publish(self, target_url, credentials=None, **extra):
        with _temporary_folder(self.env) as tempdir:
            client = self.get_command(target_url, tempdir, credentials)
            with client:
                for line in client:
                    yield line


class FtpConnection:
    def __init__(self, url, credentials=None):
        credentials = credentials or {}
        self.con = self.make_connection()
        self.url = url
        self.username = credentials.get("username") or url.username
        self.password = credentials.get("password") or url.password
        self.log_buffer = []
        self._known_folders = set()

    @staticmethod
    def make_connection():
        # pylint: disable=import-outside-toplevel
        from ftplib import FTP

        return FTP()

    def drain_log(self):
        log = self.log_buffer[:]
        del self.log_buffer[:]
        for chunk in log:
            for line in chunk.splitlines():
                if not isinstance(line, str):
                    line = line.decode("utf-8", "replace")
                yield line.rstrip()

    def connect(self):
        options = self.url.decode_query()

        log = self.log_buffer
        log.append("000 Connecting to server ...")
        try:
            log.append(self.con.connect(self.url.ascii_host, self.url.port or 21))
        except Exception as e:
            log.append("000 Could not connect.")
            log.append(str(e))
            return False

        try:
            credentials = {}
            if self.username:
                credentials["user"] = self.username
            if self.password:
                credentials["passwd"] = self.password
            log.append(self.con.login(**credentials))

        except Exception as e:
            log.append("000 Could not authenticate.")
            log.append(str(e))
            return False

        passive = options.get("passive") in ("on", "yes", "true", "1", None)
        log.append("000 Using passive mode: %s" % (passive and "yes" or "no"))
        self.con.set_pasv(passive)

        try:
            log.append(self.con.cwd(self.url.path))
        except Exception as e:
            log.append(str(e))
            return False

        log.append("000 Connected!")
        return True

    def mkdir(self, path, recursive=True):
        if not isinstance(path, str):
            path = path.decode("utf-8")
        if path in self._known_folders:
            return
        dirname, _ = posixpath.split(path)
        if dirname and recursive:
            self.mkdir(dirname)
        try:
            self.con.mkd(path)
        except FTPError as e:
            msg = str(e)
            if msg[:4] != "550 ":
                self.log_buffer.append(str(e))
                return
        self._known_folders.add(path)

    def append(self, filename, data):
        if not isinstance(filename, str):
            filename = filename.decode("utf-8")

        input = io.BytesIO(data.encode("utf-8"))

        try:
            self.con.storbinary("APPE " + filename, input)
        except FTPError as e:
            self.log_buffer.append(str(e))
            return False
        return True

    def get_file(self, filename, out=None):
        if not isinstance(filename, str):
            filename = filename.decode("utf-8")
        getvalue = False
        if out is None:
            out = io.BytesIO()
            getvalue = True
        try:
            self.con.retrbinary("RETR " + filename, out.write)
        except FTPError as e:
            msg = str(e)
            if msg[:4] != "550 ":
                self.log_buffer.append(e)
            return None
        if getvalue:
            return out.getvalue().decode("utf-8")
        return out

    def upload_file(self, filename, src, mkdir=False):
        if isinstance(src, str):
            src = io.BytesIO(src.encode("utf-8"))
        if mkdir:
            directory = posixpath.dirname(filename)
            if directory:
                self.mkdir(directory, recursive=True)
        if not isinstance(filename, str):
            filename = filename.decode("utf-8")
        try:
            self.con.storbinary("STOR " + filename, src, blocksize=32768)
        except FTPError as e:
            self.log_buffer.append(str(e))
            return False
        return True

    def rename_file(self, src, dst):
        try:
            self.con.rename(src, dst)
        except FTPError as e:
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
        if isinstance(filename, str):
            filename = filename.encode("utf-8")
        try:
            self.con.delete(filename)
        except Exception as e:
            self.log_buffer.append(str(e))

    def delete_folder(self, filename):
        if isinstance(filename, str):
            filename = filename.encode("utf-8")
        try:
            self.con.rmd(filename)
        except Exception as e:
            self.log_buffer.append(str(e))
        self._known_folders.discard(filename)


class FtpTlsConnection(FtpConnection):
    def make_connection(self):
        # pylint: disable=import-outside-toplevel
        from ftplib import FTP_TLS

        return FTP_TLS()

    def connect(self):
        connected = super().connect()
        if connected:
            # Upgrade data connection to TLS.
            self.con.prot_p()  # pylint: disable=no-member
        return connected


class FtpPublisher(Publisher):
    connection_class = FtpConnection

    @staticmethod
    def read_existing_artifacts(con):
        contents = con.get_file(".lektor/listing")
        if not contents:
            return {}, set()
        duplicates = set()
        rv = {}
        # Later records override earlier ones.  There can be duplicate
        # entries if the file was not compressed.
        for line in contents.splitlines():
            items = line.split("|")
            if len(items) == 2:
                if not isinstance(items[0], str):
                    artifact_name = items[0].decode("utf-8")
                else:
                    artifact_name = items[0]
                if artifact_name in rv:
                    duplicates.add(artifact_name)
                rv[artifact_name] = items[1]
        return rv, duplicates

    def iter_artifacts(self):
        """Iterates over all artifacts in the build folder and yields the
        artifacts.
        """
        for dirpath, dirnames, filenames in os.walk(self.output_path):
            dirnames[:] = [x for x in dirnames if not self.env.is_ignored_artifact(x)]
            for filename in filenames:
                if self.env.is_ignored_artifact(filename):
                    continue
                full_path = os.path.join(self.output_path, dirpath, filename)
                local_path = full_path[len(self.output_path) :].lstrip(os.path.sep)
                if os.path.altsep:
                    local_path = local_path.lstrip(os.path.altsep)
                h = hashlib.sha1()
                try:
                    with open(full_path, "rb") as f:
                        while 1:
                            item = f.read(4096)
                            if not item:
                                break
                            h.update(item)
                except IOError as e:
                    if e.errno != errno.ENOENT:
                        raise
                yield (
                    local_path.replace(os.path.sep, "/"),
                    full_path,
                    h.hexdigest(),
                )

    @staticmethod
    def get_temp_filename(filename):
        dirname, basename = posixpath.split(filename)
        return posixpath.join(dirname, "." + basename + ".tmp")

    def upload_artifact(self, con, artifact_name, source_file, checksum):
        with open(source_file, "rb") as source:
            tmp_dst = self.get_temp_filename(artifact_name)
            con.log_buffer.append("000 Updating %s" % artifact_name)
            con.upload_file(tmp_dst, source, mkdir=True)
            con.rename_file(tmp_dst, artifact_name)
            con.append(".lektor/listing", "%s|%s\n" % (artifact_name, checksum))

    def consolidate_listing(self, con, current_artifacts):
        server_artifacts, duplicates = self.read_existing_artifacts(con)
        known_folders = set()
        for artifact_name in current_artifacts.keys():
            known_folders.add(posixpath.dirname(artifact_name))

        for artifact_name, checksum in server_artifacts.items():
            if artifact_name not in current_artifacts:
                con.log_buffer.append("000 Deleting %s" % artifact_name)
                con.delete_file(artifact_name)
                folder = posixpath.dirname(artifact_name)
                if folder not in known_folders:
                    con.log_buffer.append("000 Deleting %s" % folder)
                    con.delete_folder(folder)

        if duplicates or server_artifacts != current_artifacts:
            listing = []
            for artifact_name, checksum in current_artifacts.items():
                listing.append("%s|%s\n" % (artifact_name, checksum))
            listing.sort()
            con.upload_file(".lektor/.listing.tmp", "".join(listing))
            con.rename_file(".lektor/.listing.tmp", ".lektor/listing")

    def publish(self, target_url, credentials=None, **extra):
        con = self.connection_class(target_url, credentials)
        connected = con.connect()
        for event in con.drain_log():
            yield event
        if not connected:
            return

        yield "000 Reading server state ..."
        con.mkdir(".lektor")
        committed_artifacts, _ = self.read_existing_artifacts(con)
        for event in con.drain_log():
            yield event

        yield "000 Begin sync ..."
        current_artifacts = {}
        for artifact_name, filename, checksum in self.iter_artifacts():
            current_artifacts[artifact_name] = checksum
            if checksum != committed_artifacts.get(artifact_name):
                self.upload_artifact(con, artifact_name, filename, checksum)
                for event in con.drain_log():
                    yield event
        yield "000 Sync done!"

        yield "000 Consolidating server state ..."
        self.consolidate_listing(con, current_artifacts)
        for event in con.drain_log():
            yield event

        yield "000 All done!"


class FtpTlsPublisher(FtpPublisher):
    connection_class = FtpTlsConnection


class GithubPagesPublisher(Publisher):
    @staticmethod
    def get_credentials(url, credentials=None):
        credentials = credentials or {}
        username = credentials.get("username") or url.username
        password = credentials.get("password") or url.password
        rv = username
        if username and password:
            rv += ":" + password
        return rv if rv else None

    def update_git_config(self, repo, url, branch, credentials=None):
        ssh_command = None
        path = url.host + "/" + url.path.strip("/")
        cred = None
        if url.scheme in ("ghpages", "ghpages+ssh"):
            push_url = "git@github.com:%s.git" % path
            keyfile = _write_ssh_key_file(
                os.path.join(repo, ".git", "ssh-auth-key"), credentials
            )
            if keyfile or url.port:
                ssh_command = _get_ssh_cmd(url.port, keyfile)
        else:
            push_url = "https://github.com/%s.git" % path
            cred = self.get_credentials(url, credentials)

        with open(os.path.join(repo, ".git", "config"), "a", encoding="utf-8") as f:
            f.write(
                '[remote "origin"]\nurl = %s\n'
                "fetch = +refs/heads/%s:refs/remotes/origin/%s\n"
                % (push_url, branch, branch)
            )
            if cred:
                cred_path = os.path.join(repo, ".git", "credentials")
                f.write('[credential]\nhelper = store --file "%s"\n' % cred_path)
                with open(cred_path, "w", encoding="utf-8") as cf:
                    cf.write("https://%s@github.com\n" % cred)

        return ssh_command

    def link_artifacts(self, path):
        try:
            link = os.link
        except AttributeError:
            link = shutil.copy

        # Clean old
        for filename in os.listdir(path):
            if filename == ".git":
                continue
            filename = os.path.join(path, filename)
            try:
                os.remove(filename)
            except OSError:
                shutil.rmtree(filename)

        # Add new
        for dirpath, dirnames, filenames in os.walk(self.output_path):
            dirnames[:] = [x for x in dirnames if x != ".lektor"]
            for filename in filenames:
                full_path = os.path.join(self.output_path, dirpath, filename)
                dst = os.path.join(
                    path,
                    full_path[len(self.output_path) :]
                    .lstrip(os.path.sep)
                    .lstrip(os.path.altsep or ""),
                )
                try:
                    os.makedirs(os.path.dirname(dst))
                except (OSError, IOError):
                    pass
                try:
                    link(full_path, dst)
                except OSError:  # Different Filesystems
                    shutil.copy(full_path, dst)

    @staticmethod
    def write_cname(path, target_url):
        params = target_url.decode_query()
        cname = params.get("cname")
        if cname is not None:
            with open(os.path.join(path, "CNAME"), "w", encoding="utf-8") as f:
                f.write("%s\n" % cname)

    @staticmethod
    def detect_target_branch(target_url):
        # When pushing to the username.github.io repo we need to push to
        # master, otherwise to gh-pages
        if target_url.host.lower() + ".github.io" == target_url.path.strip("/").lower():
            branch = "master"
        else:
            branch = "gh-pages"
        return branch

    def publish(self, target_url, credentials=None, **extra):
        if not locate_executable("git"):
            self.fail("git executable not found; cannot deploy.")

        branch = self.detect_target_branch(target_url)

        with _temporary_folder(self.env) as path:
            ssh_command = None

            def git(args, **kwargs):
                kwargs["env"] = _patch_git_env(kwargs.pop("env", None), ssh_command)
                return Command(["git"] + args, cwd=path, **kwargs)

            for line in git(["init"]).output:
                yield line
            ssh_command = self.update_git_config(path, target_url, branch, credentials)
            for line in git(["remote", "update"]).output:
                yield line

            if git(["checkout", "-q", branch], silent=True).wait() != 0:
                git(["checkout", "-qb", branch], silent=True).wait()

            self.link_artifacts(path)
            self.write_cname(path, target_url)
            for line in git(["add", "-f", "--all", "."]).output:
                yield line
            for line in git(["commit", "-qm", "Synchronized build"]).output:
                yield line
            for line in git(["push", "origin", branch]).output:
                yield line


builtin_publishers = {
    "rsync": RsyncPublisher,
    "ftp": FtpPublisher,
    "ftps": FtpTlsPublisher,
    "ghpages": GithubPagesPublisher,
    "ghpages+https": GithubPagesPublisher,
    "ghpages+ssh": GithubPagesPublisher,
}


def publish(env, target, output_path, credentials=None, **extra):
    url = urls.url_parse(str(target))
    publisher = env.publishers.get(url.scheme)
    if publisher is None:
        raise PublishError('"%s" is an unknown scheme.' % url.scheme)
    return publisher(env, output_path).publish(url, credentials, **extra)
