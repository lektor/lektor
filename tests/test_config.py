import inspect

import pytest

from lektor.environment.config import Config


def test_custom_attachment_types(env):
    attachment_types = env.load_config().values["ATTACHMENT_TYPES"]
    assert attachment_types[".foo"] == "text"


@pytest.fixture(scope="function")
def config(tmp_path, project_url):
    projectfile = tmp_path / "scratch.lektorproject"
    projectfile.write_text(
        inspect.cleandoc(
            f"""
            [project]
            url = {project_url}
            """
        )
    )
    return Config(projectfile)


@pytest.mark.parametrize(
    "project_url, expected",
    [
        ("", None),
        ("/path/", None),
        ("https://example.org", "https://example.org/"),
    ],
)
def test_base_url(config, expected):
    assert config.base_url == expected


@pytest.mark.parametrize(
    "project_url, expected",
    [
        ("", "/"),
        ("/path", "/path/"),
        ("/path/", "/path/"),
        ("https://example.org", "/"),
        ("https://example.org/pth", "/pth/"),
    ],
)
def test_base_path(config, expected):
    assert config.base_path == expected


@pytest.fixture
def servers_config(tmp_path):
    projectfile = tmp_path / "servers.lektorproject"
    projectfile.write_text(
        inspect.cleandoc(
            """
            [servers.production]
            target = rsync://example.org/www
            default = yes

            [servers.staging]
            target = rsync://staging.example.org/www
            enabled = no
            """
        )
    )
    return Config(projectfile)


def test_get_server_ignores_disabled_server(servers_config):
    assert servers_config.get_server("production").target == "rsync://example.org/www"
    assert servers_config.get_server("staging") is None


def test_get_servers_ignores_disabled_server(servers_config):
    assert set(servers_config.get_servers()) == {"production"}


def test_get_default_server_ignores_disabled_server(tmp_path):
    projectfile = tmp_path / "servers.lektorproject"
    projectfile.write_text(
        inspect.cleandoc(
            """
            [servers.production]
            target = rsync://example.org/www

            [servers.staging]
            target = rsync://staging.example.org/www
            enabled = no
            default = yes
            """
        )
    )
    server = Config(projectfile).get_default_server()
    assert server is not None
    assert server.id == "production"
