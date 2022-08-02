import errno
import hashlib
import io
import os
import posixpath
from contextlib import contextmanager
from contextlib import ExitStack
from contextlib import suppress
from ftplib import Error as FTPError
from inspect import cleandoc
from pathlib import Path
from subprocess import CalledProcessError
from subprocess import CompletedProcess
from subprocess import DEVNULL
from subprocess import PIPE
from subprocess import STDOUT
from typing import Any
from typing import Callable
from typing import ContextManager
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import NoReturn
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING
from warnings import warn

from werkzeug import urls

from lektor.compat import TemporaryDirectory
from lektor.exception import LektorException
from lektor.utils import bool_from_string
from lektor.utils import locate_executable
from lektor.utils import portable_popen

if TYPE_CHECKING:  # pragma: no cover
    from _typeshed import StrOrBytesPath
    from _typeshed import StrPath
    from lektor.environment import Environment


@contextmanager
def _ssh_key_file(
    credentials: Optional[Mapping[str, str]]
) -> Iterator[Optional["StrPath"]]:
    with ExitStack() as stack:
        key_file: Optional["StrPath"]
        key_file = credentials.get("key_file") if credentials else None
        key = credentials.get("key") if credentials else None
        if not key_file and key:
            if ":" in key:
                key_type, _, key = key.partition(":")
                key_type = key_type.upper()
            else:
                key_type = "RSA"
            key_file = Path(stack.enter_context(TemporaryDirectory()), "keyfile")
            with key_file.open("w", encoding="utf-8") as f:
                f.write(f"-----BEGIN {key_type} PRIVATE KEY-----\n")
                f.writelines(key[x : x + 64] + "\n" for x in range(0, len(key), 64))
                f.write(f"-----END {key_type} PRIVATE KEY-----\n")
        yield key_file


@contextmanager
def _ssh_command(
    credentials: Optional[Mapping[str, str]], port: Optional[int] = None
) -> Iterator[Optional[str]]:
    with _ssh_key_file(credentials) as key_file:
        args = []
        if port:
            args.append(f" -p {port}")
        if key_file:
            args.append(f' -i "{key_file}" -o IdentitiesOnly=yes')
        if args:
            yield "ssh" + " ".join(args)
        else:
            yield None


class PublishError(LektorException):
    """Raised by publishers if something goes wrong."""


class Command(ContextManager["Command"]):
    """A wrapper around subprocess.Popen to facilitate streaming output via generator.

    :param argline: Command with arguments to execute.
    :param cwd: Optional. Directory in which to execute command.
    :param env: Optional. Environment with which to run command.
    :param capture: Default `True`. Whether to capture stdout and stderr.
    :param silent: Default `False`. Discard output altogether.
    :param check: Default `False`.
        If set, raise ``CalledProcessError`` on non-zero return code.
    :param input: Optional. A string to feed to the subprocess via stdin.
    :param capture_stdout: Default `False`. Capture stdout and
        return in ``CompletedProcess.stdout``.

    Basic Usage
    ===========

    To run a command, returning any output on stdout or stderr to the caller
    as an iterable (generator), while checking the return code from the command:

        def run_command(argline):
            # This passes the output
            rv = yield from Command(argline)
            if rv.returncode != 0:
                raise RuntimeError("Command failed!")

    This could be called as follows:

        for outline in run_command(('ls')):
            print(outline.rstrip())

    Supplying input via stdin, Capturing stdout
    ===========================================

    The following example shows how input may be fed to a subprocess via stdin,
    and how stdout may be captured for further processing.

        def run_wc(input):
            rv = yield from Command(('wc'), check=True, input=input, capture_stdout=True)
            lines, words, chars = rv.stdout.split()
            print(f"{words} words, {chars} chars")

        stderr_lines = list(run_wc("a few words"))
        # prints "3 words, 11 chars"

    Note that ``check=True`` will cause a ``CalledProcessError`` to be raised if the
    ``wc`` subprocess returns a non-zero return code.

    """

    def __init__(
        self,
        argline: Iterable[str],
        cwd: Optional["StrOrBytesPath"] = None,
        env: Optional[Mapping[str, str]] = None,
        capture: bool = True,
        silent: bool = False,
        check: bool = False,
        input: Optional[str] = None,
        capture_stdout: bool = False,
    ) -> None:
        kwargs: Dict[str, Any] = {"cwd": cwd}
        if env:
            kwargs["env"] = {**os.environ, **env}
        if silent:
            kwargs["stdout"] = DEVNULL
            kwargs["stderr"] = DEVNULL
            capture = False
        if input is not None:
            kwargs["stdin"] = PIPE
        if capture or capture_stdout:
            kwargs["stdout"] = PIPE
        if capture:
            kwargs["stderr"] = STDOUT if not capture_stdout else PIPE

        # Python >= 3.7 has sane encoding defaults in the case that the system is
        # (likely mis-)configured to use ASCII as the default encoding (PEP538).
        # It also provides a way for the user to force the use of UTF-8 (PEP540).
        kwargs["text"] = True
        kwargs["errors"] = "replace"

        self.capture = capture  # b/c - unused
        self.check = check
        self._stdout = None

        with ExitStack() as stack:
            self._cmd = stack.enter_context(portable_popen(list(argline), **kwargs))
            self._closer: Optional[Callable[[], None]] = stack.pop_all().close

        if input is not None or capture_stdout:
            self._output = self._communicate(input, capture_stdout, capture)
        elif capture:
            self._output = self._cmd.stdout
        else:
            self._output = None

    def _communicate(
        self, input: Optional[str], capture_stdout: bool, capture: bool
    ) -> Optional[Iterator[str]]:
        proc = self._cmd
        try:
            if capture_stdout:
                self._stdout, errout = proc.communicate(input)
            else:
                errout, _ = proc.communicate(input)
        except BaseException:
            proc.kill()
            with suppress(CalledProcessError):
                self.close()
            raise
        if capture:
            return iter(errout.splitlines())
        return None

    def close(self) -> None:
        """Wait for subprocess to complete.

        If check=True was passed to the constructor, raises ``CalledProcessError``
        if the subprocess returns a non-zero status code.
        """
        closer, self._closer = self._closer, None
        if closer:
            # This waits for process and closes standard file descriptors
            closer()
        if self.check:
            rc = self._cmd.poll()
            if rc != 0:
                raise CalledProcessError(rc, self._cmd.args, self._stdout)

    def wait(self) -> int:
        """Wait for subprocess to complete. Return status code."""
        self._cmd.wait()
        self.close()
        return self._cmd.returncode

    def result(self) -> "CompletedProcess[str]":
        """Wait for subprocess to complete.  Return ``CompletedProcess`` instance.

        If ``capture_stdout=True`` was passed to the constructor, the output
        captured from stdout will be available on the ``.stdout`` attribute
        of the return value.
        """
        return CompletedProcess(self._cmd.args, self.wait(), self._stdout)

    @property
    def returncode(self) -> Optional[int]:
        """Return exit status of the subprocess.

        Or ``None`` if the subprocess is still alive.
        """
        return self._cmd.returncode

    def __exit__(self, *__: Any) -> None:
        self.close()

    def __iter__(self) -> Generator[str, None, "CompletedProcess[str]"]:
        """A generator with yields any captured output and returns a ``CompletedProcess``.

        If ``capture`` is ``True`` (the default).  Both stdout and stderr are available
        in the iterator output.

        If ``capture_stdout`` is set, stdout is captured to a string which is made
        available via ``CompletedProcess.stdout`` attribute of the return value. Stderr
        output is available via the iterator output, as normal.
        """
        if self._output is None:
            raise RuntimeError("Not capturing")
        for line in self._output:
            yield line.rstrip()
        return self.result()

    safe_iter = __iter__  # b/c - deprecated

    @property
    def output(self) -> Iterator[str]:  # b/c - deprecated
        return self.safe_iter()


class Publisher:
    def __init__(self, env: "Environment", output_path: str) -> None:
        self.env = env
        self.output_path = os.path.abspath(output_path)

    def fail(self, message: str) -> NoReturn:
        # pylint: disable=no-self-use
        raise PublishError(message)

    def publish(
        self,
        target_url: urls.URL,
        credentials: Optional[Mapping[str, str]] = None,
        **extra: Any,
    ) -> Iterator[str]:
        raise NotImplementedError()


class RsyncPublisher(Publisher):
    @contextmanager
    def get_command(self, target_url, credentials):
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

        with _ssh_command(credentials, target_url.port) as ssh_command:
            if ssh_command:
                argline.extend(("-e", ssh_command))

            username = credentials.get("username") or target_url.username
            if username:
                target.append(username + "@")

            if target_url.ascii_host is not None:
                target.append(target_url.ascii_host)
                target.append(":")
            target.append(target_url.path.rstrip("/") + "/")

            argline.append(self.output_path.rstrip("/\\") + "/")
            argline.append("".join(target))
            yield Command(argline, env=env)

    def publish(self, target_url, credentials=None, **extra):
        with self.get_command(target_url, credentials) as client:
            yield from client


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
    @staticmethod
    def make_connection():
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


class GitRepo(ContextManager["GitRepo"]):
    """A temporary git repository.

    This class provides some lower-level utility methods which may be
    externally useful, but the main use case is:

        def publish(html_output):
            gitrepo = GitRepo(html_output)
            yield from gitrepo.publish_ghpages(
                push_url="git@github.com:owner/repo.git",
                branch="gh-pages"
            )

    :param work_tree: The work tree for the repository.
    """

    def __init__(self, work_tree: "StrPath") -> None:
        environ = {**os.environ, "GIT_WORK_TREE": str(work_tree)}

        for what, default in [("NAME", "Lektor Bot"), ("EMAIL", "bot@getlektor.com")]:
            value = (
                environ.get(f"GIT_AUTHOR_{what}")
                or environ.get(f"GIT_COMMITTER_{what}")
                or default
            )
            for key in f"GIT_AUTHOR_{what}", f"GIT_COMMITTER_{what}":
                environ[key] = environ.get(key) or value

        with ExitStack() as stack:
            environ["GIT_DIR"] = stack.enter_context(TemporaryDirectory(suffix=".git"))
            self.environ = environ
            self.run("init", "--quiet")

            self._exit_stack = stack.pop_all()

    def __exit__(self, *__: Any) -> None:
        self._exit_stack.close()

    def _popen(self, args: Sequence[str], **kwargs: Any) -> Command:
        cmd = ["git"]
        cmd.extend(args)
        return Command(cmd, env=self.environ, **kwargs)

    def popen(
        self,
        *args: str,
        check: bool = True,
        input: Optional[str] = None,
        capture_stdout: bool = False,
    ) -> Command:
        """Run a git subcommand."""
        return self._popen(
            args, check=check, input=input, capture_stdout=capture_stdout
        )

    def run(
        self,
        *args: str,
        check: bool = True,
        input: Optional[str] = None,
        capture_stdout: bool = False,
    ) -> "CompletedProcess[str]":
        """Run a git subcommand and wait for completion."""
        return self._popen(
            args, check=check, input=input, capture_stdout=capture_stdout, capture=False
        ).result()

    def set_ssh_credentials(self, credentials: Mapping[str, str]) -> None:
        """Set up git ssh credentials.

        This repository will be configured to used whatever SSH credentials
        can found in ``credentials`` (if any).
        """
        stack = self._exit_stack
        ssh_command = stack.enter_context(_ssh_command(credentials))
        if ssh_command:
            self.environ.setdefault("GIT_SSH_COMMAND", ssh_command)

    def set_https_credentials(self, credentials: Mapping[str, str]) -> None:
        """Set up git http(s) credentials.

        This repository will be configured to used whatever HTTP credentials
        can found in ``credentials`` (if any).
        """
        username = credentials.get("username", "")
        password = credentials.get("password")
        if username or password:
            userpass = f"{username}:{password}" if password else username
            git_dir = self.environ["GIT_DIR"]
            cred_file = Path(git_dir, "lektor_cred_file")
            # pylint: disable=unspecified-encoding
            cred_file.write_text(f"https://{userpass}@github.com\n")
            self.run("config", "credential.helper", f'store --file "{cred_file}"')

    def add_to_index(self, filename: str, content: str) -> None:
        """Create a file in the index.

        This creates file named ``filename`` with content ``content`` in the git
        index.
        """
        oid = self.run(
            "hash-object", "-w", "--stdin", input=content, capture_stdout=True
        ).stdout.strip()
        self.run("update-index", "--add", "--cacheinfo", "100644", oid, filename)

    def publish_ghpages(
        self,
        push_url: str,
        branch: str,
        cname: Optional[str] = None,
        preserve_history: bool = True,
    ) -> Iterator[str]:
        """Publish the contents of the work tree to GitHub pages.

        :param push_url: The URL to push to.
        :param branch: The branch to push to
        :param cname: Optional. Create a top-level ``CNAME`` with given contents.
        """
        refspec = f"refs/heads/{branch}"
        if preserve_history:
            yield "Fetching existing head"
            fetch_cmd = self.popen("fetch", "--depth=1", push_url, refspec, check=False)
            yield from _prefix_output(fetch_cmd)
            if fetch_cmd.returncode == 0:
                # If fetch was succesful, reset HEAD to remote head
                yield from _prefix_output(self.popen("reset", "--soft", "FETCH_HEAD"))
            else:
                # otherwise assume remote branch does not exist
                yield f"Creating new branch {branch}"

        # At this point, the index is still empty. Add all but .lektor dir to index
        yield from _prefix_output(
            self.popen("add", "--force", "--all", "--", ".", ":(exclude).lektor")
        )
        if cname is not None:
            self.add_to_index("CNAME", f"{cname}\n")

        # Check for changes
        diff_cmd = self.popen("diff", "--cached", "--exit-code", "--quiet", check=False)
        yield from _prefix_output(diff_cmd)
        if diff_cmd.returncode == 0:
            yield "No changes to publish☺"
        elif diff_cmd.returncode == 1:
            yield "Creating commit"
            yield from _prefix_output(
                self.popen("commit", "--quiet", "--message", "Synchronized build")
            )
            push_cmd = ["push", push_url, f"HEAD:{refspec}"]
            if not preserve_history:
                push_cmd.insert(1, "--force")
            yield "Pushing to github"
            yield from _prefix_output(self.popen(*push_cmd))
            yield "Success!"
        else:
            diff_cmd.result().check_returncode()  # raise error


def _prefix_output(lines: Iterable[str], prefix: str = "> ") -> Iterator[str]:
    """Add prefix to lines."""
    return (f"{prefix}{line}" for line in lines)


class GithubPagesPublisher(Publisher):
    """Publish to GitHub pages."""

    def publish(
        self,
        target_url: urls.URL,
        credentials: Optional[Mapping[str, str]] = None,
        **extra: Any,
    ) -> Iterator[str]:
        if not locate_executable("git"):
            self.fail("git executable not found; cannot deploy.")

        push_url, branch, cname, preserve_history, warnings = self._parse_url(
            target_url
        )
        creds = self._parse_credentials(credentials, target_url)

        yield from iter(warnings)

        with GitRepo(self.output_path) as repo:
            if push_url.startswith("https:"):
                repo.set_https_credentials(creds)
            else:
                repo.set_ssh_credentials(creds)
            yield from repo.publish_ghpages(push_url, branch, cname, preserve_history)

    def _parse_url(
        self, target_url: urls.URL
    ) -> Tuple[str, str, Optional[str], bool, Sequence[str]]:
        if not target_url.host:
            self.fail("github owner missing from target URL")
        gh_owner = target_url.host.lower()
        gh_project = target_url.path.strip("/").lower()
        if not gh_project:
            self.fail("github project missing from target URL")

        params = target_url.decode_query()
        cname = params.get("cname")
        branch = params.get("branch")
        preserve_history = bool_from_string(params.get("preserve_history"), True)

        warnings = []

        if not branch:
            if gh_project == f"{gh_owner}.github.io":
                warnings.extend(
                    cleandoc(self._EXPLICIT_BRANCH_SUGGESTED_MSG).splitlines()
                )
                warn(
                    " ".join(
                        cleandoc(self._DEFAULT_BRANCH_DEPRECATION_MSG).splitlines()
                    ),
                    category=DeprecationWarning,
                )
                branch = "master"
            else:
                branch = "gh-pages"

        if target_url.scheme in ("ghpages", "ghpages+ssh"):
            push_url = f"ssh://git@github.com/{gh_owner}/{gh_project}.git"
            default_port = 22
        else:
            push_url = f"https://github.com/{gh_owner}/{gh_project}.git"
            default_port = 443
        if target_url.port and target_url.port != default_port:
            self.fail("github does not support pushing to non-standard ports")

        return push_url, branch, cname, preserve_history, warnings

    _EXPLICIT_BRANCH_SUGGESTED_MSG = """
    ================================================================
    WARNING!!! You should explicitly set the name of the published
    branch of your GitHub pages repository.

    The default branch for new GitHub pages repositories has changed
    to 'main', but Lektor still defaults to the old value, 'master'.
    In a future version of Lektor, the default branch name will
    changed to match the new GitHub default.

    For details, see
    https://getlektor.com/docs/deployment/ghpages/#pushing-to-an-explicit-branch
    ================================================================
    """

    _DEFAULT_BRANCH_DEPRECATION_MSG = """
    Currently, by default, Lektor pushes to the 'master' branch when
    deploying to GitHub pages repositories.  In a future version of
    Lektor, the default branch will GitHub's new default, 'main'.
    It is suggest that you explicitly set which branch to push to.
    """

    @staticmethod
    def _parse_credentials(
        credentials: Optional[Mapping[str, str]], target_url: urls.URL
    ) -> Mapping[str, str]:
        creds = dict(credentials or {})
        # Fill in default username/password from target url
        for key, default in [
            ("username", target_url.username),
            ("password", target_url.password),
        ]:
            if not creds.get(key) and default:
                creds[key] = default
        return creds


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
