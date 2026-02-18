from pathlib import Path

import pytest

from lektor.cli_utils import ResolvedPath


@pytest.mark.parametrize("file_exists", [True, False])
def test_ResolvedPath_resolves_relative_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file_exists: bool
) -> None:
    resolved_path = ResolvedPath()
    monkeypatch.chdir(tmp_path)
    if file_exists:
        Path(tmp_path, "filename").touch()

    resolved = resolved_path.convert("filename", None, None)
    assert isinstance(resolved, str)
    assert resolved == str(Path.cwd().resolve() / "filename")
