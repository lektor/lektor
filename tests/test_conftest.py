import sys
from contextlib import suppress
from importlib import import_module
from importlib import metadata

# pylint: disable-next=wrong-import-order
from conftest import restore_import_state  # noreorder


def test_restore_import_state_restores_meta_path():
    # Various modules (e.g. setuptools, importlib_metadata), when imported,
    # add their own finders to sys.meta_path.
    meta_path = sys.meta_path.copy()

    with restore_import_state(), suppress(ModuleNotFoundError):
        import_module("importlib_metadata")

    assert sys.meta_path == meta_path


def test_restore_import_state_restores_unneutered_PathFinder():
    # When importlib_metadata is imported, it neuters the stdlib
    # distribution find, and then adds its own finder to meta_path.
    #
    # This tests that restore_import_state manages to unneuter
    # this find.
    distributions_pre = [dist.metadata["name"] for dist in metadata.distributions()]

    with restore_import_state(), suppress(ModuleNotFoundError):
        import_module("importlib_metadata")

    distributions_post = [dist.metadata["name"] for dist in metadata.distributions()]
    assert len(distributions_pre) == len(distributions_post)
    assert set(distributions_pre) == set(distributions_post)
