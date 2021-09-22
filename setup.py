# Stub setup.py.
#
# XXX: This is deprecated in favor of PEP-517-aware tools and should probably be deleted.
#
# The canonical way to build an sdist and wheel is now:
#
#     pip install build
#     python -m build
#
# NB: Recent versions of pip are PEP-517-aware so that:
#
#     pip install -e .
#
# will work fine without this stub.
#
from setuptools import setup

setup(use_scm_version=True)
