OSX_ARCH=x64
BUILD_DIR=build
OSX_BUNDLE_BASE=$(BUILD_DIR)/Lektor-darwin-$(OSX_ARCH)
OSX_BUNDLE=$(OSX_BUNDLE_BASE)/Lektor.app
OSX_BUNDLE_RES=$(OSX_BUNDLE)/Contents/Resources

# The identity to use for code signing
CODESIGN_IDENTITY='Developer ID Application'
CODESIGN_FLAGS=--force --verbose --strict --sign $(CODESIGN_IDENTITY) --preserve-metadata=i,e,req --timestamp=none

REBUILD_CMD=./node_modules/.bin/electron-rebuild -w runas

npm-install:
	cd ../lektor/admin/; npm install
	npm install
	$(REBUILD_CMD)

run-only:
	./bin/run

run: npm-install run-only

$(BUILD_DIR)/Python.framework:
	./bin/compile-python-framework

build-wheels: $(BUILD_DIR)/Python.framework
	./bin/build-wheels

build/Lektor.icns:
	./bin/make-mac-icons

build/ProjectFile.icns:
	./bin/make-mac-icons

icons: build/Lektor.icns build/ProjectFile.icns

build/imagemagick/convert:
	./bin/compile-imagemagick

osx-bundle: build/imagemagick/convert icons build-wheels
	cd ../lektor/admin; npm install
	npm install
	npm install --production
	$(REBUILD_CMD)
	cd static; ../node_modules/.bin/webpack
	mkdir -p $(OSX_BUNDLE_BASE) && rm -rf $(OSX_BUNDLE)
	cp -RH node_modules/electron-prebuilt/dist/Electron.app $(OSX_BUNDLE)
	mv $(OSX_BUNDLE)/Contents/Frameworks/{Electron,Lektor}\ Helper\ EH.app
	mv $(OSX_BUNDLE)/Contents/Frameworks/Lektor\ Helper\ EH.app/Contents/MacOS/{Electron,Lektor}\ Helper\ EH
	sed -i '' s/Electron/Lektor/ $(OSX_BUNDLE)/Contents/Frameworks/Lektor\ Helper\ EH.app/Contents/Info.plist
	mv $(OSX_BUNDLE)/Contents/Frameworks/{Electron,Lektor}\ Helper\ NP.app
	mv $(OSX_BUNDLE)/Contents/Frameworks/Lektor\ Helper\ NP.app/Contents/MacOS/{Electron,Lektor}\ Helper\ NP
	sed -i '' s/Electron/Lektor/ $(OSX_BUNDLE)/Contents/Frameworks/Lektor\ Helper\ NP.app/Contents/Info.plist
	mv $(OSX_BUNDLE)/Contents/Frameworks/{Electron,Lektor}\ Helper.app
	mv $(OSX_BUNDLE)/Contents/Frameworks/Lektor\ Helper.app/Contents/MacOS/{Electron,Lektor}\ Helper
	sed -i '' s/Electron/Lektor/ $(OSX_BUNDLE)/Contents/Frameworks/Lektor\ Helper.app/Contents/Info.plist
	mkdir -p $(OSX_BUNDLE_RES)/app/static
	cp -R package.json $(OSX_BUNDLE_RES)/app
	cp -R static/{images,gen,index.html} $(OSX_BUNDLE_RES)/app/static
	cp resources/Lektor-Info.plist $(OSX_BUNDLE)/Contents/Info.plist
	cp build/Lektor.icns $(OSX_BUNDLE_RES)
	cp build/ProjectFile.icns $(OSX_BUNDLE_RES)
	cp build/File.icns $(OSX_BUNDLE_RES)
	mkdir -p $(OSX_BUNDLE_RES)/local/bin
	cp build/imagemagick/convert $(OSX_BUNDLE_RES)/local/bin
	cp resources/lektor-mac-proxy $(OSX_BUNDLE_RES)/local/bin/lektor-proxy
	cp resources/lektor $(OSX_BUNDLE_RES)/lektor
	rm $(OSX_BUNDLE_RES)/atom.icns
	rm -rf $(OSX_BUNDLE_RES)/default_app
	# Manually copy over native modules we depend on
	mkdir -p $(OSX_BUNDLE_RES)/app/node_modules
	cp -R node_modules/runas $(OSX_BUNDLE_RES)/app/node_modules/runas
	cp -R node_modules/nan $(OSX_BUNDLE_RES)/app/node_modules/nan
	cp -R $(BUILD_DIR)/Python.framework $(OSX_BUNDLE)/Contents/Frameworks/Python.framework
	rm $(OSX_BUNDLE)/Contents/Frameworks/Python.framework/Versions/2.7/bin/python{w,w2,w2.7}
	./bin/make-python-framework-relocatable $(OSX_BUNDLE)/Contents/Frameworks/Python.framework
	./bin/install-wheels $(OSX_BUNDLE)/Contents/Frameworks/Python.framework/Versions/Current/lib/python2.7/site-packages
	find $(OSX_BUNDLE)/Contents -name '.DS_Store' -exec rm {} \;

osx-signed-bundle: osx-bundle
	find $(OSX_BUNDLE) -name '*.dylib' -exec codesign $(CODESIGN_FLAGS) {} \;
	find $(OSX_BUNDLE) -name '*.so' -exec codesign $(CODESIGN_FLAGS) {} \;
	find $(OSX_BUNDLE) -type f -perm +0111 -exec codesign $(CODESIGN_FLAGS) {} \;
	codesign --force --verbose --sign $(CODESIGN_IDENTITY) $(OSX_BUNDLE)/Contents/Frameworks/Python.framework/Versions/Current/Resources/Python.app
	find $(OSX_BUNDLE) -name '*.app' -exec codesign $(CODESIGN_FLAGS) {} \;
	find $(OSX_BUNDLE) -name '*.framework' -exec codesign $(CODESIGN_FLAGS) {} \;
	codesign $(CODESIGN_FLAGS) $(OSX_BUNDLE)/Contents/MacOS/Electron
	codesign $(CODESIGN_FLAGS) $(OSX_BUNDLE_RES)/local/bin/lektor-proxy
	codesign $(CODESIGN_FLAGS) $(OSX_BUNDLE)
	codesign --verify --verbose --deep $(OSX_BUNDLE)

node_modules/.bin/appdmg:
	npm install appdmg

osx-dmg-only:
	rm -rf $(OSX_BUNDLE_BASE)/Lektor.dmg
	./node_modules/.bin/appdmg dmg-config.json $(OSX_BUNDLE_BASE)/Lektor.dmg

osx-dmg: node_modules/.bin/appdmg osx-signed-bundle osx-dmg-only

.PHONY: npm-install run-only run build-wheels icons osx-bundle osx-dmg-only osx-dmg
