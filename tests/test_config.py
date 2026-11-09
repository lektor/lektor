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


def test_is_server_disabled(servers_config):
    assert servers_config.is_server_disabled("staging")
    assert not servers_config.is_server_disabled("production")
    assert not servers_config.is_server_disabled("nosuchserver")


def test_server_info_enabled_is_deprecated(servers_config):
    server = servers_config.get_server("production")
    with pytest.deprecated_call(match="'enabled' is deprecated"):
        assert server.enabled is True


def test_server_info_to_json_does_not_warn(servers_config, recwarn):
    server = servers_config.get_server("production")
    assert server.to_json()["enabled"] is True
    assert not recwarn.list
