all: build-js

build-js: lektor/admin/node_modules
	@echo "---> building static files"
	@cd lektor/admin; npm run webpack

lektor/admin/node_modules: lektor/admin/package-lock.json
	@echo "---> installing npm dependencies"
	@cd lektor/admin; npm install
	@touch -m lektor/admin/node_modules

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
	pylint lektor
	pytest . --tb=long -vv --cov=lektor

coverage-python: test-python
	coverage xml

test-js: build-js
	@echo "---> running javascript tests"
	@cd lektor/admin; npm run lint
	@cd lektor/admin; npm test

coverage-js: test-js
	@cd lektor/admin; npm run report-coverage

test: test-python test-js

coverage: coverage-python coverage-js

osx-dmg:
	$(MAKE) -C gui osx-dmg

install-git-hooks:
	ln -sT $(PWD)/bin/pre-commit .git/hooks/pre-commit
