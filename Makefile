all: build-js

.PHONY: build-js
build-js: frontend/node_modules
	@echo "---> building static files"
	@cd frontend; npm run webpack

frontend/node_modules: frontend/package-lock.json
	@echo "---> installing npm dependencies"
	@cd frontend; npm install
	@touch -m frontend/node_modules

# Run tests on Python files.
test-python:
	@echo "---> running python tests"
	tox -e py

# Run tests on the Frontend code.
test-js: frontend/node_modules
	@echo "---> running javascript tests"
	@cd frontend; npx tsc
	@cd frontend; npm test

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
