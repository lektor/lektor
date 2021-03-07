from pathlib import Path
from textwrap import dedent

from lektor.packages import load_manifest
from lektor.packages import write_manifest


def test_read_write_manifest(tmp_path: Path):
    manifest_path = tmp_path / "manifest"
    packages = {"@test": None, "pypi-package": "0.2"}
    write_manifest(manifest_path, packages)
    contents = manifest_path.read_text()
    assert contents == dedent(
        """\
        @test
        pypi-package=0.2
        """
    )
    loaded = load_manifest(manifest_path)
    assert loaded == packages
