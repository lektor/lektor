# Lektor

[![CI/CD Badge]][CI/CD]
[![Code Coverage](https://codecov.io/gh/lektor/lektor/branch/master/graph/badge.svg)](https://codecov.io/gh/lektor/lektor)
[![PyPI version](https://badge.fury.io/py/Lektor.svg)](https://pypi.org/project/Lektor/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/Lektor.svg)](https://pypi.org/project/Lektor/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Join the chat at https://gitter.im/lektor/lektor](https://badges.gitter.im/lektor/lektor.svg)](https://gitter.im/lektor/lektor?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[CI/CD Badge]: https://github.com/lektor/lektor/actions/workflows/ci-cd.yml/badge.svg?branch=master
[CI/CD]: https://github.com/lektor/lektor/actions/workflows/ci-cd.yml

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

This gets you started (assuming you have Python, npm, and pre-commit
installed):

```bash
$ git clone https://github.com/lektor/lektor
$ cd lektor
$ python -m venv _venv
$ . _venv/bin/activate

# pip>=25.1 is required for PEP 735 support
$ pip install -U "pip>=25.1"

$ pip install --group dev --editable .

# build the frontend javascript (requires npm to be installed)
$ make build-js

# If you plan on committing:
$ pre-commit install

# Run the Lektor server
$ export LEKTOR_DEV=1
$ cp -r example example-project
$ lektor --project example-project server
```

If you want to run the whole test suite, under various versions of
python, etc. (you'll need tox installed):

```sh
$ tox
```

Or run the tests directly in your dev environment

```sh
$ pytest [...]
```
