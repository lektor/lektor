import gc
import os
import re
import signal
import sys
import warnings
import weakref
from contextlib import ExitStack
from itertools import chain
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError
from subprocess import DEVNULL
from subprocess import PIPE
from subprocess import run

import pytest
from werkzeug.urls import url_parse

from lektor.publisher import _ssh_command
from lektor.publisher import _ssh_key_file
from lektor.publisher import Command
from lektor.publisher import GithubPagesPublisher
from lektor.publisher import GitRepo
from lektor.publisher import publish
from lektor.publisher import PublishError
from lektor.utils import locate_executable


def test_ssh_key_file():
    credentials = {"key_file": "/some/id", "key": "rsa:ignored"}
    with _ssh_key_file(credentials) as key_file:
        assert key_file == "/some/id"


def test_ssh_key_file_returns_none():
    with _ssh_key_file({}) as key_file:
        assert key_file is None


@pytest.mark.parametrize("prefix, key_type", [("test:", "TEST"), ("", "RSA")])
def test_ssh_key_file_creates_key(prefix, key_type):
    credentials = {"key": prefix + "".join(["1234567890abcdef"] * 7)}
    with _ssh_key_file(credentials) as key_file:
        assert Path(key_file).read_text() == (  # pylint: disable=unspecified-encoding
            f"-----BEGIN {key_type} PRIVATE KEY-----\n"
            "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef\n"
            "1234567890abcdef1234567890abcdef1234567890abcdef\n"
            f"-----END {key_type} PRIVATE KEY-----\n"
        )
    assert not Path(key_file).exists()


@pytest.mark.parametrize(
    "credentials, port, expected",
    [
        ({}, None, None),
        ({}, 42, "ssh -p 42"),
        ({"key_file": "/keyfile"}, None, 'ssh -i "/keyfile" -o IdentitiesOnly=yes'),
    ],
)
def test_ssh_command(credentials, port, expected):
    with _ssh_command(credentials, port) as key_file:
        assert key_file == expected


def _pyscript(script):
    return (sys.executable, "-c", script)


@pytest.mark.parametrize(
    "cmd, input, expect_rc, expected",
    [
        ("print('xxx')", None, 0, ["xxx"]),
        ("print('yyy', file=sys.stderr)", None, 0, ["yyy"]),
        ("exit(42)", None, 42, []),
        (
            "for _ in sorted(sys.stdin): print(_.strip())",
            "foo\nbar\n",
            0,
            ["bar", "foo"],
        ),
    ],
)
def test_Command_capture(cmd, input, expect_rc, expected):
    command = Command(_pyscript("import sys\n" + cmd), input=input)

    def iter_output():
        proc = yield from command
        assert proc.returncode == expect_rc
        assert proc.stdout is None

    assert list(iter_output()) == expected


def test_Command_env():
    command = Command(
        _pyscript("import os; print(os.environ['TESTVAR'])"),
        env={"TESTVAR": "boo"},
    )
    assert list(command) == ["boo"]


def test_Command_raises_CalledProcessError():
    command = Command(_pyscript("print('x'); exit(42)"), check=True)

    def iter_output():
        with pytest.raises(CalledProcessError) as exc_info:
            yield from command
        assert exc_info.value.returncode == 42

    assert list(iter_output()) == ["x"]


@pytest.mark.parametrize(
    "capture_stdout, silent, stdout, out_err",
    [
        (False, False, None, ("foo\n", "bar\n")),
        (True, False, "foo\n", ("", "bar\n")),
        (False, True, None, ("", "")),
        (True, True, "foo\n", ("", "")),
    ],
)
def test_Command_no_capture(capture_stdout, silent, stdout, out_err, capfd):
    command = Command(
        _pyscript("import sys; print('foo'); print('bar', file=sys.stderr)"),
        capture=False,
        silent=silent,
        capture_stdout=capture_stdout,
    )
    assert command.wait() == 0
    assert command.result().stdout == stdout
    captured = tuple(_.replace(os.linesep, "\n") for _ in capfd.readouterr())
    assert captured == out_err


def test_Command_iter_raises_if_not_capturing():
    command = Command(_pyscript("exit(0)"), capture=False)
    with pytest.raises(RuntimeError) as exc_info:
        next(iter(command))
    assert "Not capturing" in str(exc_info.value)
    assert command.wait() == 0


@pytest.mark.skipif(os.name == "nt", reason="Windows")
# XXX: Can not figure out how to reliably test KeyboardInterrupt handling under Windows.
# Response to signal.SIGINT and/or signal.CTRL_C_EVENT varies depending on what shell
# the test is run under.
def test_Command_handles_keyboard_interrupt():
    pid = os.getpid()
    sig = signal.SIGINT
    with pytest.raises(KeyboardInterrupt):
        command = Command(
            (sys.executable, "-c", f"import os; os.kill({pid}, {sig})"),
            capture_stdout=True,
        )
        list(command)


def test_Command_returncode():
    command = Command((sys.executable, "-c", "exit(42)"))
    assert command.returncode is None
    list(command)
    assert command.returncode == 42


def test_Command_output():
    command = Command(_pyscript("print('foo')"))
    assert list(command.output) == ["foo"]


def test_Command_triggers_no_warnings():
    # This exercises the issue where publishing via rsync resulted
    # in ResourceWarnings about unclosed streams.

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        # This is essentially how RsyncPublisher runs rsync.
        with Command(_pyscript("print()")) as client:
            for _ in client:
                pass

        # The ResourceWarnings regarding unclosed files we are checking for
        # are issued during finalization.  Without this extra effort,
        # finalization wouldn't happen until after the test completes.
        client_is_alive = weakref.ref(client)
        del client
        if client_is_alive():
            gc.collect()

    if client_is_alive():
        warnings.warn(
            "Unable to trigger garbage collection of Command instance, "
            "so unable to check for warnings issued during finalization."
        )


@pytest.mark.skipif(
    which("rsync") is None, reason="rsync is not available on this system"
)
@pytest.mark.parametrize("delete", ["yes", "no"])
def test_RsyncPublisher_integration(env, tmp_path, delete):
    # Integration test of local rsync deployment
    # Ensures that RsyncPublisher can successfully invoke rsync
    files = {"file.txt": "content\n"}
    output = tmp_path / "output"
    output.mkdir()
    for path, content in files.items():
        output.joinpath(path).write_text(content)

    target_path = tmp_path / "target"
    target_path.mkdir()
    target = f"rsync://{target_path.resolve()}?delete={delete}"

    event_iter = publish(env, target, output)
    for line in event_iter:
        print(line)

    target_files = {
        os.fspath(_.relative_to(target_path)): _.read_text()
        for _ in target_path.iterdir()
    }
    assert target_files == files


@pytest.fixture
def work_tree(tmp_path):
    work_tree = tmp_path / "work_tree"
    work_tree.mkdir()
    return work_tree


@pytest.fixture
def clean_git_environ(monkeypatch):
    """Delete any GIT_ configuration in the current environment.

    This unsets any existing GIT_SSH_COMMAND, among other things.

    Of note, if one runs tests using git rebase exec, git sets all kinds
    of GIT_* environment variables.
    """
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delitem(os.environ, key)


@pytest.fixture
def gitrepo(work_tree, clean_git_environ):
    if not locate_executable("git"):
        pytest.skip("no git")
    with GitRepo(work_tree) as repo:
        yield repo


def test_GitRepo_popen(gitrepo):
    assert "No commits yet" in list(gitrepo.popen("status"))


def test_GitRepo_run(gitrepo):
    proc = gitrepo.run("status", capture_stdout=True)
    assert "No commits yet" in proc.stdout


@pytest.mark.usefixtures("clean_git_environ")
def test_GitRepo_set_ssh_credentials(gitrepo):
    gitrepo.set_ssh_credentials({"key_file": "/id_foo"})
    assert gitrepo.environ["GIT_SSH_COMMAND"].startswith('ssh -i "/id_foo"')


@pytest.mark.usefixtures("clean_git_environ")
def test_GitRepo_set_ssh_credentials_no_creds(gitrepo):
    gitrepo.set_ssh_credentials({})
    assert "GIT_SSH_COMMAND" not in gitrepo.environ


def test_GitRepo_set_https_credentials(gitrepo):
    gitrepo.set_https_credentials({"username": "user", "password": "pw"})
    with gitrepo.popen("config", "--local", "--list") as output:
        for line in output:
            m = re.match(r'credential\.helper=store\s+--file\s+"(\S+)"', line)
            if m:
                cred_file = m.group(1)
                break
    # pylint: disable=unspecified-encoding
    assert Path(cred_file).read_text().rstrip() == "https://user:pw@github.com"


def test_GitRepo_set_https_credentials_no_cred(gitrepo):
    gitrepo.set_https_credentials({})
    assert not any(
        line.startswith("credential.helper")
        for line in gitrepo.popen("config", "--local", "--list")
    )


def test_GitRepo_add_to_index(gitrepo):
    gitrepo.add_to_index("testfile", "testcontent\n")
    proc = gitrepo.run("diff", "--cached", capture_stdout=True)
    assert "+testcontent" in proc.stdout


class DummyUpstreamRepo:
    def __init__(self, git_dir):
        run(("git", "init", "--bare", git_dir), check=True, stdout=DEVNULL)
        self.git_dir = git_dir

    @property
    def url(self):
        return self.git_dir

    def run(self, args, **kwargs):
        cmd = ("git", "--bare", "--git-dir", self.git_dir) + args
        # XXX: Use text=True instead of encoding for py>3.6
        return run(cmd, stdout=PIPE, encoding="utf-8", check=False)

    def count_commits(self, branch):
        proc = self.run(("log", "--pretty=oneline", branch))
        return len(proc.stdout.splitlines())

    def ls_files(self, treeish):
        return set(self.iter_files(treeish))

    def iter_files(self, treeish, prefix=""):
        # Currently only lists top-level files
        for line in self.run(("ls-tree", treeish)).stdout.splitlines():
            _, typ, oid, name = line.split(maxsplit=3)
            if typ == "blob":
                yield prefix + name
            else:
                assert typ == "tree"
                yield from self.iter_files(oid, prefix=f"{prefix}{name}/")


@pytest.fixture
def upstream_repo(tmp_path, clean_git_environ):
    git_dir = tmp_path / "upstream.git"
    return DummyUpstreamRepo(git_dir.__fspath__())


@pytest.fixture
def no_scary_output(capsys):
    # Check that no scary messages are output to stdout
    def is_scary(line):
        return line.startswith("fatal")

    yield
    captured = capsys.readouterr()
    scary_output = list(
        filter(is_scary, chain(captured.out.splitlines(), captured.err.splitlines()))
    )
    assert len(scary_output) == 0


@pytest.fixture
def publish_ghpages(work_tree, clean_git_environ, no_scary_output):
    # Run publish_ghpages on a fresh GitRepo instance
    if not locate_executable("git"):
        pytest.skip("no git")

    def GitRepo_publish_ghpages(*args, **kwargs):
        with GitRepo(work_tree) as repo:
            rv = yield from repo.publish_ghpages(*args, **kwargs)
            return rv

    return GitRepo_publish_ghpages


def test_GitRepo_publish_ghpages(publish_ghpages, upstream_repo, work_tree):
    test_file = work_tree / "new-file"
    test_file.write_text("test\n")
    for line in publish_ghpages(upstream_repo.url, "gh-pages"):
        print(line)
    assert upstream_repo.count_commits("gh-pages") == 1
    assert upstream_repo.ls_files("gh-pages") == {"new-file"}

    test_file.rename(work_tree / "renamed-file")
    for line in publish_ghpages(upstream_repo.url, "gh-pages"):
        print(line)
    assert upstream_repo.count_commits("gh-pages") == 2
    assert upstream_repo.ls_files("gh-pages") == {"renamed-file"}


def test_GitRepo_publish_ghpages_cname(publish_ghpages, upstream_repo, work_tree):
    for line in publish_ghpages(upstream_repo.url, "gh-pages", "example.org"):
        print(line)
    assert upstream_repo.count_commits("gh-pages") == 1
    assert upstream_repo.ls_files("gh-pages") == {"CNAME"}

    for line in publish_ghpages(upstream_repo.url, "gh-pages"):
        print(line)
    assert upstream_repo.count_commits("gh-pages") == 2
    assert upstream_repo.ls_files("gh-pages") == set()


def test_GitRepo_publish_ghpages_ignores_lektor_dir(
    publish_ghpages, upstream_repo, work_tree
):
    lektor_dir = work_tree / ".lektor"
    lektor_dir.mkdir()
    lektor_dir.joinpath("ignored").write_text("should not be published")
    work_tree.joinpath("included").write_text("should be published")

    for line in publish_ghpages(upstream_repo.url, "gh-pages"):
        print(line)
    assert upstream_repo.count_commits("gh-pages") == 1
    assert upstream_repo.ls_files("gh-pages") == {"included"}


def test_GitRepo_publish_ghpages_no_changes(publish_ghpages, upstream_repo):
    for line in publish_ghpages(upstream_repo.url, "gh-pages", "example.com"):
        print(line)
    assert upstream_repo.ls_files("gh-pages") == {"CNAME"}
    assert any(
        "No changes" in line
        for line in publish_ghpages(upstream_repo.url, "gh-pages", "example.com")
    )


def test_GitRepo_publish_ghpages_discard_history(
    publish_ghpages, upstream_repo, work_tree
):
    for line in publish_ghpages(upstream_repo.url, "gh-pages", "example.com"):
        print(line)
    assert upstream_repo.ls_files("gh-pages") == {"CNAME"}

    work_tree.joinpath("myfile").write_text("contents")
    for line in publish_ghpages(upstream_repo.url, "gh-pages", None, False):
        print(line)
    assert upstream_repo.count_commits("gh-pages") == 1
    assert upstream_repo.ls_files("gh-pages") == {"myfile"}


@pytest.fixture
def output_path(tmp_path):
    return str(tmp_path / "output_path")


@pytest.fixture
def ghp_publisher(env, output_path):
    return GithubPagesPublisher(env, output_path)


@pytest.mark.parametrize(
    "target_url, publish_args, warns",
    [
        (
            "ghpages://owner/project?cname=example.com&preserve_history=no",
            (
                "ssh://git@github.com/owner/project.git",
                "gh-pages",
                "example.com",
                False,
            ),
            False,
        ),
        (
            "ghpages+https://owner/owner.github.io",
            ("https://github.com/owner/owner.github.io.git", "master", None, True),
            True,
        ),
    ],
)
@pytest.mark.skipif(not locate_executable("git"), reason="no git")
def test_GithubPagesPublisher_publish(
    ghp_publisher, output_path, mocker, target_url, publish_args, warns
):
    GitRepo = mocker.patch("lektor.publisher.GitRepo", spec_set=True)
    repo = mocker.Mock(spec_set=GitRepo)
    repo.publish_ghpages.return_value = iter(["Published!"])
    GitRepo.return_value.__enter__.return_value = repo

    url = url_parse(target_url)
    with ExitStack() as stack:
        if warns:
            stack.enter_context(pytest.deprecated_call())
        output = list(ghp_publisher.publish(url))

    GitRepo.assert_called_once_with(output_path)
    if "+https:" in target_url:
        repo.set_https_credentials.assert_called_once_with({})
    else:
        repo.set_ssh_credentials.assert_called_once_with({})
    repo.publish_ghpages.assert_called_once_with(*publish_args)
    if warns:
        assert "WARNING" in " ".join(output)
        output = output[-1:]
    assert output == ["Published!"]


@pytest.mark.usefixtures("no_utils")
def test_GithubPagesPublisher_publish_fails_if_no_git(ghp_publisher):
    url = url_parse("ghpages://owner/project")
    with pytest.raises(PublishError) as exc_info:
        list(ghp_publisher.publish(url))
    assert re.search(r"git.*not found", str(exc_info.value))


@pytest.mark.parametrize(
    "target_url, expected",
    [
        (
            "ghpages://owner/project",
            ("ssh://git@github.com/owner/project.git", "gh-pages", None, True, []),
        ),
        (
            "ghpages://owner/owner.github.io?branch=main",
            ("ssh://git@github.com/owner/owner.github.io.git", "main", None, True, []),
        ),
        (
            "ghpages://owner/project?branch=brnch&cname=example.com",
            (
                "ssh://git@github.com/owner/project.git",
                "brnch",
                "example.com",
                True,
                [],
            ),
        ),
        (
            "ghpages://owner/project?preserve_history=no",
            ("ssh://git@github.com/owner/project.git", "gh-pages", None, False, []),
        ),
        (
            "ghpages://owner/project?preserve_history=yes",
            ("ssh://git@github.com/owner/project.git", "gh-pages", None, True, []),
        ),
        (
            "ghpages+ssh://own/proj",
            ("ssh://git@github.com/own/proj.git", "gh-pages", None, True, []),
        ),
        (
            "ghpages+https://own/proj",
            ("https://github.com/own/proj.git", "gh-pages", None, True, []),
        ),
        (
            "ghpages+ssh://own:22/proj",
            ("ssh://git@github.com/own/proj.git", "gh-pages", None, True, []),
        ),
        (
            "ghpages+https://own:443/proj",
            ("https://github.com/own/proj.git", "gh-pages", None, True, []),
        ),
    ],
)
def test_GithubPagesPublisher_parse_url(ghp_publisher, target_url, expected):
    url = url_parse(target_url)
    assert ghp_publisher._parse_url(url) == expected


def test_GithubPagesPublisher_parse_url_warns_on_default_master_branch(ghp_publisher):
    url = url_parse("ghpages://owner/owner.github.io")
    with pytest.deprecated_call():
        push_url, branch, cname, preserve_history, warnings = ghp_publisher._parse_url(
            url
        )
    assert (push_url, branch, cname, preserve_history) == (
        "ssh://git@github.com/owner/owner.github.io.git",
        "master",
        None,
        True,
    )
    assert len(warnings) > 0
    assert re.search(r"WARNING.*set.*branch", " ".join(warnings))


@pytest.mark.parametrize(
    "target_url, expected",
    [
        ("ghpages:///project", "owner missing"),
        ("ghpages://owner", "project missing"),
        ("ghpages://owner:2222/project", "non-standard port"),
        ("ghpages+https://owner:4430/project", "non-standard port"),
    ],
)
def test_GithubPagesPublisher_parse_url_failures(ghp_publisher, target_url, expected):
    url = url_parse(target_url)
    with pytest.raises(PublishError) as exc_info:
        ghp_publisher._parse_url(url)
    assert expected in str(exc_info.value)


@pytest.mark.parametrize(
    "target_url, credentials, expected",
    [
        ("ghpages://owner/proj", None, {}),
        (
            "ghpages://owner/proj",
            {"username": "user", "password": "pw"},
            {"username": "user", "password": "pw"},
        ),
        ("ghpages://user:pw@owner/proj", None, {"username": "user", "password": "pw"}),
        (
            "ghpages://user:pw@owner/proj",
            {"arbi": "trary"},
            {"username": "user", "password": "pw", "arbi": "trary"},
        ),
        ("ghpages://user:pw@owner/proj", None, {"username": "user", "password": "pw"}),
        (
            "ghpages://user:pw@owner/proj",
            {"password": "secret"},
            {"username": "user", "password": "secret"},
        ),
    ],
)
def test_GithubPagesPublisher_parse_credentials(
    ghp_publisher, credentials, target_url, expected
):
    url = url_parse(target_url)
    assert ghp_publisher._parse_credentials(credentials, url) == expected


def test_publish(env, output_path, mocker):
    Publisher = mocker.Mock()
    env.add_publisher("publishtest", Publisher)
    credentials = {"foo": "bar"}
    rv = publish(env, "publishtest://host/path", output_path, credentials)
    url = url_parse("publishtest://host/path")
    assert Publisher.mock_calls == [
        mocker.call(env, output_path),
        mocker.call().publish(url, credentials),
    ]
    assert rv is Publisher.return_value.publish.return_value


def test_publish_unknown_scheme(env, output_path):
    with pytest.raises(PublishError) as exc_info:
        publish(env, "unknownscheme://host/path", output_path)
    assert "unknown scheme" in str(exc_info.value)
