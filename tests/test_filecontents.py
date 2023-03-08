import pytest

from lektor.filecontents import FileContents


def test_FileContents_is_deprecated():
    with pytest.deprecated_call(match=r"FileContents") as warnings:
        FileContents(__file__)
    assert warnings[0].filename == __file__


def test_FileContents_is_a_type():
    assert isinstance(FileContents, type)
