"""Test that all modules/packages in the lektor tree are importable in any order

Here we import each module by itself, one at a time, each in a new
python interpreter.

"""
import pkgutil
import sys
from subprocess import run

import pytest

import lektor


def iter_lektor_modules():
    for module in pkgutil.walk_packages(lektor.__path__, f"{lektor.__name__}."):
        yield module.name


@pytest.fixture(params=iter_lektor_modules())
def module(request):
    return request.param


def test_import(module):
    python = sys.executable
    assert run([python, "-c", f"import {module}"], check=False).returncode == 0
