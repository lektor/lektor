all: build-js

.PHONY: build-js
build-js: lektor/admin/node_modules
	@echo "---> building static files"
	@cd lektor/admin; npm run webpack

lektor/admin/node_modules: lektor/admin/package-lock.json
	@echo "---> installing npm dependencies"
	@cd lektor/admin; npm install
	@touch -m lektor/admin/node_modules

# Run tests on Python files.
test-python:
	@echo "---> running python tests"
	tox -e py

# Run tests on the Frontend code.
test-js: lektor/admin/node_modules
	@echo "---> running javascript tests"
	@cd lektor/admin; npx tsc
	@cd lektor/admin; npm test

.PHONY: lint
# Lint code.
lint:
	pre-commit run -a
	tox -e lint

.PHONY: test
test: lint test-python test-js

.PHONY: test-all
# Run tests on all supported Python versions.
test-all: test-js
	pre-commit run -a
	tox

# This creates source distribution and a wheel.
dist: build-js setup.cfg MANIFEST.in
	rm -r build dist
	python -m build

# Before making a release, CHANGES.md needs to be updated and
# a tag should be created (and pushed with `git push --tags`).
.PHONY: upload
upload: dist
	twine upload dist/*
