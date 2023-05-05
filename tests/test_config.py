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
