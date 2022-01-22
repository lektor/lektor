"""Test that all modules/packages in the lektor tree are importable in any order

Here we import each module by itself, one at a time, each in a new
python interpreter.

"""
import pkgutil
import sys
from subprocess import run

import pytest

import lektor
from lektor.markdown import MISTUNE_VERSION


ignored = set()

# Do not check importability of module for the non-installed version of mistune
if MISTUNE_VERSION.startswith("2"):
    ignored.add("lektor.markdown.mistune0")
else:
    ignored.add("lektor.markdown.mistune2")


def iter_lektor_modules():
    for module in pkgutil.walk_packages(lektor.__path__, f"{lektor.__name__}."):
        if module.name not in ignored:
            yield module.name


@pytest.fixture(params=iter_lektor_modules())
def module(request):
    return request.param


def test_import(module):
    python = sys.executable
    assert run([python, "-c", f"import {module}"], check=False).returncode == 0
