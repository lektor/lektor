all: build-js

build-js:
	@echo "---> building static files"
	@cd lektor/admin; npm install .
	@cd lektor/admin/static; ../node_modules/.bin/webpack

pex:
	virtualenv pex-build-cache
	pex-build-cache/bin/pip install --upgrade pip
	pex-build-cache/bin/pip install pex requests wheel
	pex-build-cache/bin/pip wheel -w pex-build-cache/wheelhouse .
	pex-build-cache/bin/pex \
		-v -o lektor.pex -e lektor.cli:cli \
		-f pex-build-cache/wheelhouse \
		--disable-cache \
		--not-zip-safe Lektor
	rm -rf pex-build-cache

test-python:
	@echo "---> running python tests"
	@cd tests; py.test . --tb=short -v --cov=lektor

coverage-python: test-python
	@cd tests; coverage xml

test-js: build-js
	@echo "---> running javascript tests"
	@cd lektor/admin; npm test

coverage-js: test-js
	@cd lektor/admin; npm run report-coverage

test: test-python test-js

coverage: coverage-python coverage-js

osx-dmg:
	$(MAKE) -C gui osx-dmg
