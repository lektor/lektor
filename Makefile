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

test:
	@echo "---> running tests"
	@python setup.py test

osx-dmg:
	$(MAKE) -C gui osx-dmg
