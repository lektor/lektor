# Lektor

[![Tests master](https://github.com/lektor/lektor/workflows/Tests%20master/badge.svg)](https://github.com/lektor/lektor/actions?query=workflow%3A%22Tests+master%22)
[![Code Coverage](https://codecov.io/gh/lektor/lektor/branch/master/graph/badge.svg)](https://codecov.io/gh/lektor/lektor)
[![PyPI version](https://badge.fury.io/py/Lektor.svg)](https://pypi.org/project/Lektor/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/Lektor.svg)](https://pypi.org/project/Lektor/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Join the chat at https://gitter.im/lektor/lektor](https://badges.gitter.im/lektor/lektor.svg)](https://gitter.im/lektor/lektor?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Lektor is a static website generator. It builds out an entire project
from static files into many individual HTML pages and has a built-in
admin UI and minimal desktop app.

<img src="https://raw.githubusercontent.com/lektor/lektor-assets/master/screenshots/admin.png" width="100%">

To see how it works look at the top-level `example/` folder, which contains
a showcase of the wide variety of Lektor's features.

For a more complete example look at the [lektor/lektor-website](https://github.com/lektor/lektor-website)
repository, which contains the sourcecode for the official lektor website.

## How do I use this?

For installation instructions head to the official documentation:

- [Installation](https://www.getlektor.com/docs/installation/)
- [Quickstart](https://www.getlektor.com/docs/quickstart/)

## Want to develop on Lektor?

This gets you started (assuming you have Python, pip, Make and pre-commit
installed):

```
$ git clone https://github.com/lektor/lektor
$ cd lektor
$ virtualenv venv
$ . venv/bin/activate
$ pip install --editable .
$ make build-js
$ pre-commit install
$ export LEKTOR_DEV=1
$ cp -r example example-project
$ lektor --project example-project server
```

If you want to run the test suite (you'll need tox installed):

```
$ tox
```
