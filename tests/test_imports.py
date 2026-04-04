"""Test that all modules/packages in the lektor tree are importable in any order

Here we import each module by itself, one at a time, each in a new
python interpreter.

"""

import pkgutil
import sys
from subprocess import run

import pytest

import lektor
from lektor.markdown import MISTUNE_MAJOR_VERSION


# Do not check importability of module for the non-installed version of mistune
ignored = {
    f"lektor.markdown.mistune{mistune_version}"
    for mistune_version in (0, 2, 3)
    if mistune_version != MISTUNE_MAJOR_VERSION
}


def iter_lektor_modules():
    for module in pkgutil.walk_packages(lektor.__path__, f"{lektor.__name__}."):
        if module.name not in ignored:
            yield module.name


@pytest.fixture(params=iter_lektor_modules())
def module(request):
    return request.param


@pytest.mark.slowtest
def test_import(module):
    python = sys.executable
    assert run([python, "-c", f"import {module}"], check=False).returncode == 0
