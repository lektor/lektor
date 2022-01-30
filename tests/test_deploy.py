from os.path import dirname
from os.path import join

import pytest
from werkzeug.urls import url_parse

from lektor.publisher import RsyncPublisher


def test_get_server(env):
    server = env.load_config().get_server("production")
    assert server.name == "Production"
    assert server.name_i18n["de"] == "Produktion"
    assert server.target == "rsync://myserver.com/path/to/website"
    assert server.extra == {"extra_field": "extra_value"}


def test_rsync_command_credentials(tmpdir, mocker, env):
    output_path = tmpdir.mkdir("output")
    publisher = RsyncPublisher(env, str(output_path))
    target_url = url_parse("http://example.com")
    credentials = {
        "username": "fakeuser",
        "password": "fakepass",
    }
    mock_popen = mocker.patch("lektor.publisher.portable_popen")
    with publisher.get_command(target_url, credentials):
        assert mock_popen.called
        assert mock_popen.call_args[0] == (
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                str(output_path) + "/",
                "fakeuser@example.com:/",
            ],
        )


output_path = join(dirname(__file__), "OUTPUT_PATH")


@pytest.mark.parametrize(
    "target_url,called_command",
    [
        (
            "http://example.com",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://fakeuser@example.com",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                str(output_path) + "/",
                "fakeuser@example.com:/",
            ],
        ),
        (
            "http://example.com?exclude=file",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--exclude",
                "file",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://example.com?exclude=file_one&exclude=file_two",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--exclude",
                "file_one",
                "--exclude",
                "file_two",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            """http://example.com?exclude='user's "special" file name'""",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--exclude",
                "'user's \"special\" file name'",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            'http://example.com?exclude="file name"',
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--exclude",
                '"file name"',
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://example.com?delete",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--delete-after",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://example.com?delete=yes",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--delete-after",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://example.com?delete=no",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "file:///path/to/directory",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                str(output_path) + "/",
                "/path/to/directory/",
            ],
        ),
    ],
)
def test_rsync_publisher(target_url, called_command, tmpdir, mocker, env):
    publisher = RsyncPublisher(env, str(output_path))
    target_url = url_parse(target_url)
    mock_popen = mocker.patch("lektor.publisher.portable_popen")
    with publisher.get_command(target_url, credentials=None):
        assert mock_popen.called
        assert mock_popen.call_args[0] == (called_command,)
