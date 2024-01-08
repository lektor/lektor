# Changelog

These are all the changes in Lektor since the first public release.

## 3.4.0b10 (2024-01-07)

### Bugs Fixed

#### Admin Server

- Fix `"re.error: bad escape \u"` exception. ([#1177])

[#1177]: https://github.com/lektor/lektor/pull/1177

## 3.4.0b9 (2023-11-12)

### Compatibility

- Drop support for python 3.7. ([#1173])
- Officially support python 3.12. ([#1167])
- Remove pin on `werkzeug<3`. ([#1172], [#1171])

### Refactorings

This release includes a significant continuation of refactoring of the
code in `lektor.imagetools` which started in [#1104]:

- We now use Pillow to access image file metadata (e.g. dimensions,
  format, and EXIF tags). This replaces some homegrown code for
  reading basic image metadata and `exifread` for EXIF tag access.

- Some internal API has been cleaned up.

- Compatibility with various versions of Pillow has been increased.

See [#1138] for details.

### Features Removed

- Removed `--no-reload` option to the `lektor server` command. This was added in 3.4.0b4 as part of #1027 and seems no longer necessary since now live-reload can be disabled on a per-window bases (see #1164).

### Features Added

- Added Turkish translation. Thank you [\@uyar]! ([#1157])

#### Admin GUI

- Replace the _“Edit Pencil”_ with a toolbar containing both an _Edit_
  button and a toggle that can be used to disable
  _Live-reload_. ([#1164])

### Bugs Fixed

#### Admin GUI

- Use a real link (`<a href=...`) for the "Return to Website" button. ([#1164])

#### Jinja Globals

- Fix `bag()` to object the pad from `site` in the Jinja context, rather than from the Lektor build context. ([#1155])

#### Plugins

- Use symlinks when constructing Lektor's private virtual
  environment. This fixes issues install plugins on macOS. ([#1161],
  [#1159])

### Style

- Update prettier, update eslint rules. ([#1153])
- Update to latest pylint, black, flake8. Use flake8-bugbear. ([#1162])
- Update npm locks, upgrade esbuild, update tests to React 18 APIs. ([#1170])
- Apply `pyupgrade --py38-plus` to codebase ([#1174])

[\@uyar]: https://github.com/uyar
[#1138]: https://github.com/lektor/lektor/pull/1138
[#1153]: https://github.com/lektor/lektor/pull/1153
[#1155]: https://github.com/lektor/lektor/pull/1155
[#1157]: https://github.com/lektor/lektor/pull/1157
[#1159]: https://github.com/lektor/lektor/issues/1159
[#1161]: https://github.com/lektor/lektor/pull/1161
[#1162]: https://github.com/lektor/lektor/pull/1162
[#1164]: https://github.com/lektor/lektor/pull/1164
[#1167]: https://github.com/lektor/lektor/pull/1167
[#1170]: https://github.com/lektor/lektor/issues/1170
[#1171]: https://github.com/lektor/lektor/issues/1171
[#1172]: https://github.com/lektor/lektor/pull/1172
[#1173]: https://github.com/lektor/lektor/pull/1173
[#1174]: https://github.com/lektor/lektor/pull/1174

## 3.4.0b8 (2023-06-06)

### Bugs Fixed

- When there are multiple _asset_ trees being merged (i.e. when
  _themes_ are in use), avoid building shadowed assets. ([#908],
  [#1147])
- Fix asset URL resolution in the dev server when asset extensions
  differ from that of their source. ([#1111], [#1147])

[#908]: https://github.com/lektor/lektor/issues/908
[#1111]: https://github.com/lektor/lektor/issues/1111
[#1147]: https://github.com/lektor/lektor/pull/1147

## 3.4.0b7 (2023-06-04)

### Slightly Breaking Changes

- The `--profile` option has been removed from the `lektor build` command. ([#1137])

### Bugs Fixed

- Pin `watchfiles>=0.12`. (Our tests use the `stop_event` parameter of `watchfiles.watch`.)
- Fix exception from `describe_build_func` when building thumbnails with verbose logging enabled.
- Fix "FATAL: exception not rethrown" message when `lektor server` is stopped. ([#1145])
- Fix multiple browser new tabs when `lektor server --browse` is used with `LEKTOR_DEV` set ([#1145])
- Fix mypy errors in `lektor.admin.modules`.
- Fix `Builder.touch_site_config` so that it actually touches the site
  config. This fixes the _Refresh Build_ button of the admin
  UI. ([#1146])
- Ensure that `Artifact.open` respects the value of its `encoding` argument when opening files. ([#1146])
- Fix logic flaw in `FileInfo.unchanged` which, under certain
  circumstances, causes source files to be considered unchanged even
  if their size (or mtime) is changed. ([#1146])

[#1137]: https://github.com/lektor/lektor/pull/1137
[#1145]: https://github.com/lektor/lektor/pull/1145
[#1146]: https://github.com/lektor/lektor/pull/1146

## 3.4.0b6 (2023-05-05)

### Possibly Breaking Changes

- Our Publisher API has changed. This will eventually require updates
  to any custom Publisher classes provided by Lektor
  plugins. Previously, the `publish` method of `Publisher` subclasses
  was passed a `werkzeug.urls.URL` instance as its `target_url`
  argument. Werkzeug has deprecated the `URL` class, so now the
  `target_url` will be passed as a string. (The publishers are now
  responsible for was parsing the target URL themselves.) For the
  interim, in an effort to avoid immediately breaking existing
  plugins, we pass a fancy subclass of `str` that implements most of
  the attributes and methods of `werkzeug.urls.URL`. ([#1143], [#1142])

- Interpret relative paths passed via the `--output-path` command-line
  parameter relative to the current working directory. Interpret
  relative paths configured for `output_path` in the _project file_
  relative to the directory containing the project file (as the
  [docs](https://www.getlektor.com/docs/project/file/#project) claim
  should happen). Previously, both paths were interpreted —
  incorrectly, in both cases — relative to the _project directory_.
  ([#1103], [#1120])

- The `query` attribute of fields of type `"url"` now returns the
  IRI-encoded (internationalized) version of the URL query. (This
  matches the existing behavior of the `host`, `path`, and `anchor`
  attributes.) ([#1143])

### Deprecations

- The (unused) `lektor.db.Pad.make_absolute_url` method is deprecated. ([#1143])

### Features

- We now use [Pillow] (instead of ImageMagick) to generate image
  thumbnails. Installation of ImageMagick was a significant pain-point
  for some. In addition the Pillow-based thumbnailing code appears to
  be noticeably faster than the ImageMagick version. ([#1104])

- A _Preferences Dialog_ has been added to the admin GUI that allows
  customization of which hotkeys trigger the _Save_, _Edit_,
  _(Save &) Preview_, and _Search_ actions. ([#1052])

### Bugs Fixed

- Re-export `ImprovedRenderer`, `MarkdownConfig`, and `escape` from
  `lektor.markdown`. These were removed in [#992] when support for
  mistune 2.x was added. Restoring them allows most older plugins
  written for Lektor<3.4 to work, so long as mistune is pinned to
  version 0.x. ([#1134])

- Better input validation and error reporting for the `dateformat`,
  `timeformat` and `datetimeformat` jinja filters. Previously, these
  filters did not handle unexpected input types gracefully. ([#1122],
  [#1121])

- Allow the user to customize the python [warnings filter] when
  running the CLI. Previously, Lektor unconditionally set the
  warnings filter to `"default"` (enabling one-shot display of _all_
  warning types.) Now, if the warnings filter has been explicitly set
  (via [PYTHONWARNINGS] or [-W][python-W]) it is left
  alone. ([e2d0274])
- DB-path URL resolution of relative paths from _virtual source objects_. ([#1133])

- Relative URL-path resolution from pages with "." in their slug. ([#1133])

- Avoid the use of `warnings.catch_warnings` which was introduced in
  [#1113]. Its use resets the warnings registry resulting in undesired
  repition of seen warnings. ([#1135]).

### Bit-Rot

- Update frontend npm dependencies. ([#1126])

### Other Changes

- Use [watchfiles] instead of `watchdog` when monitoring for file changes. ([#1136])

- Optimization: Thumbnail file names are now generated based on the
  final thumbnail parameters (e.g. their actual dimensions, rather than
  their requested dimensions.) This minimizes the possibility of generating
  multiple identical thumbnails with different file names. ([#1139])

- Tighten [click] constraints on Path parameters. This results in
  better and earlier error messages when, e.g., a readable file is
  expected, but a path to a directory is passed. ([#1124])

- We reduced the size of our distribution wheel and sdist files by
  roughly factor of two by omitting all but the `.woff2` variants of
  the fonts for the frontend, and by excluding [sourcesContent] from
  the JS and CSS sourcemaps. ([#1130], [#1115])

[e2d0274]: https://github.com/lektor/lektor/commit/e2d02746a488e4a4d05ba8a01443e7a90315a2fb
[#1052]: https://github.com/lektor/lektor/pull/1052
[#1103]: https://github.com/lektor/lektor/issues/1103
[#1104]: https://github.com/lektor/lektor/pull/1104
[#1115]: https://github.com/lektor/lektor/issues/1115
[#1120]: https://github.com/lektor/lektor/pull/1120
[#1121]: https://github.com/lektor/lektor/issues/1121
[#1122]: https://github.com/lektor/lektor/pull/1122
[#1124]: https://github.com/lektor/lektor/pull/1124
[#1126]: https://github.com/lektor/lektor/pull/1126
[#1130]: https://github.com/lektor/lektor/pull/1130
[#1133]: https://github.com/lektor/lektor/pull/1133
[#1134]: https://github.com/lektor/lektor/pull/1134
[#1136]: https://github.com/lektor/lektor/pull/1136
[#1139]: https://github.com/lektor/lektor/pull/1139
[#1142]: https://github.com/lektor/lektor/issues/1142
[#1143]: https://github.com/lektor/lektor/pull/1143
[click]: https://pypi.org/project/click/
[warnings filter]: https://docs.python.org/3/library/warnings.html#the-warnings-filter
[PYTHONWARNINGS]: https://docs.python.org/3/using/cmdline.html#envvar-PYTHONWARNINGS
[python-W]: https://docs.python.org/3/using/cmdline.html#cmdoption-W
[Pillow]: https://pillow.readthedocs.io/en/stable/
[sourcesContent]: https://esbuild.github.io/api/#sources-content
[watchfiles]: https://github.com/samuelcolvin/watchfiles

## 3.4.0b5 (2023-03-08)

### Breaking Changes

- Removed the `lektor dev publish-plugin` command. (To publish a
  plugin to PyPI, use [twine].) ([#1065])

- Removed `SourceObject.iter_virtual_sources()` from our API. ([#1106])

- Removed support for `config["LESSC_EXECUTABLE"]`. (There is no sign
  that it has ever been used.) ([edb35f9])

- Removed support for `BuildState.make_named_temporary` method. It has
  been totally broken for awhile — so clearly it is not used.<br>
  Also remove _context manager_ protocol support from `BuildState` — it was
  only there to support `BuildState.make_named_temporary`. ([6f11bad])

### Bugs Fixed

- Fix several issues involving the installation of local plugin packages.
  We now install plugins into a _bone fide_ virtual environment, rather
  than using pip’s `--target` parameter. ([#1065], [#1028], [#865])

- Fix template `markdown` filter (broken in [#992]). ([#1102] [#1100])

- Fix dependency tracking to record the `alt` of _virtual sources_ as
  well as their `path`. ([#1108], [#1007], [#959])

- Fix equality semantics for `Record` and `VirtualSourceObject`. These
  are now considered “equal” only if their _path_ (including _page
  number_, in the case of pages), _alt_, and _pad_ all match.
  Previously (for the most part) only _path_ (without page number) was
  being checked in `Record.__eq__`. ([#1105], [#1101])

### Cleanup

- Implement our own `@deprecated` decorator, used to mark functions and methods
  as being deprecated. Remove dependency on `deprecated` package. ([#1113])

- Remove (direct) dependency on [pytz]. Since the inclusion of the
  `zoneinfo` module in Python>=3.9 (see [PEP 615]), `pytz` is no long
  necessary. Recent releases of [Babel][babel-2.12] will work with
  either `pytz` or `zoneinfo` (depending on what is available) — now
  we will, too. ([#1110])

### Deprecations

- Deprecate the `Record.contents` property and the use of the
  `lektor.filecontents.FileContents` class. These are unused by
  Lektor itself. While they are in use by at least one other project
  (see [#1026]), the semantics of the `.contents` property is quite
  unclear when _alts_ are in use. ([#1114])

### Packaging

- Use [hatchling] as our PEP 517 build engine. Among other things, this allows
  for installing Lektor directly from a git repository — so long as `npm` is installed
  locally, installing, using `pip` from the git repo will now build the frontend
  JS and CSS, thus resulting in a working installation of Lektor. ([#1112], [#1081])

### Tests

- Require `tox >= 4.1`.

- Disuse `pytest-cov` — just run `coverage` directly.

### Bit-Rot

- Audit and adjust metadata to ensure that we declare all direct dependencies. ([26e700e])

- Update frontend npm dependencies.

- Fix tox config for tox 4.\*.

[26e700e]: https://github.com/lektor/lektor/commit/26e700e62b3c02a18761cfd7cc7f274ee171dd89
[6f11bad]: https://github.com/lektor/lektor/commit/6f11bad5844d73c0ba8f5bb74c1e69f6c78650fc
[edb35f9]: https://github.com/lektor/lektor/commit/edb35f9c1fae1f4e4ae45b51175cdad5e3a52ecd
[#1114]: https://github.com/lektor/lektor/pull/1114
[#1113]: https://github.com/lektor/lektor/pull/1113
[#1112]: https://github.com/lektor/lektor/pull/1112
[#1108]: https://github.com/lektor/lektor/pull/1108
[#1106]: https://github.com/lektor/lektor/pull/1106
[#1105]: https://github.com/lektor/lektor/pull/1105
[#1102]: https://github.com/lektor/lektor/pull/1102
[#1101]: https://github.com/lektor/lektor/issues/1101
[#1100]: https://github.com/lektor/lektor/issues/1100
[#1081]: https://github.com/lektor/lektor/issues/1081
[#1065]: https://github.com/lektor/lektor/pull/1065
[#1028]: https://github.com/lektor/lektor/issues/1028
[#1026]: https://github.com/lektor/lektor/issues/1026
[#1007]: https://github.com/lektor/lektor/pull/1007
[#959]: https://github.com/lektor/lektor/pull/959
[#865]: https://github.com/lektor/lektor/issues/865
[babel-2.12]: https://github.com/python-babel/babel/blob/master/CHANGES.rst#version-2120
[hatchling]: https://pypi.org/project/hatchling/
[pytz]: https://pypi.org/project/pytz/
[pep 615]: https://peps.python.org/pep-0615/

## 3.4.0b4 (2022-11-05)

Test under python 3.11. ([#1084][])

### Features

#### Dev Server

- Add live-reloading of pages when they are rebuilt. ([#1027][])

### Bugs

#### Plugins

- `PluginController.emit` would, under certain circumstances, silently
  ignore `TypeError`s thrown by plugin hook methods. ([#1086][],
  [#1085][])

[#1027]: https://github.com/lektor/lektor/pull/1027
[#1084]: https://github.com/lektor/lektor/pull/1084
[#1085]: https://github.com/lektor/lektor/issues/1085
[#1086]: https://github.com/lektor/lektor/pull/1086

## 3.4.0b3 (2022-10-19)

### Features

#### Mistune

- When configuring `mistune` plugins (from a Lektor plugin), allow
  for specifying third-party plugins as a a string in the format
  `"<module.name>:attr"`. (Plugins which are listed in the
  `mistune.PLUGINS` map may be listed by their key.) ([#1074][])

### Deprecations

- Remove support for the `--build-flag` option to `lektor build` and
  `lektor server`. ([#1062][])

### Bugs

- Fix spelling of `typing-inspect` in dependencies. ([#1058][], continued)

#### Mistune

- When using `mistune>=2`, enable the `url`, `strikethrough`,
  `footnotes`, and `table` plugins for feature parity with
  `mistune==0.*`. ([#1074][])

#### Admin Server

- Fix Admin UI tracking of navigation to URLs with anchors or query
  strings in the preview view. ([#1053][])
- We now test under `node-current` (currently node 18) and
  `node-lts/*` (16). Previously we were testing under
  node 14 and 16. ([#1064][])

#### Bit-Rot

- Disuse `pkg_resources` in favor of `importlib.metadata`. ([#1061][], [#1073][])
- Update frontend dependencies, including upgrade to React version 18. ([#1063][])
- Remove pin on transitive dependency `typing-inspect`.

#### Packaging

- Clean up package to remove a bit of cruft from the sdist. ([#1066][])

[#1053]: https://github.com/lektor/lektor/pull/1053
[#1061]: https://github.com/lektor/lektor/pull/1061
[#1062]: https://github.com/lektor/lektor/pull/1062
[#1063]: https://github.com/lektor/lektor/pull/1063
[#1064]: https://github.com/lektor/lektor/pull/1064
[#1066]: https://github.com/lektor/lektor/pull/1066
[#1073]: https://github.com/lektor/lektor/pull/1073
[#1074]: https://github.com/lektor/lektor/pull/1074

## 3.4.0b2 (2022-08-31)

### Bugs

#### Command Line

- Fix `lektor clean` (broken in [#1048][]). ([#1056][])

#### Bit-Rot

- Pin `typing-inspect` to prevent breakage of `marshmallow_dataclass`.
  ([#1058][], [lovasoa/marshmallow_dataclass#207][md#207])

[#1056]: https://github.com/lektor/lektor/issues/1056
[#1058]: https://github.com/lektor/lektor/issues/1058
[md#207]: https://github.com/lovasoa/marshmallow_dataclass/pull/207

## 3.4.0b1 (2022-08-02)

This release drops support for Python 3.6, which has reached end-of-life in
December 2021.

### Changes

#### Admin Frontend

- The _save_ hotkey (`<ctl>-s`) now always switches to the _preview_
  view. Previously, the _save_ hotkey was disabled unless there were
  changes to be saved. ([#1022][])
- Boolean checkboxes can now be reverted to the "unset" state by
  typing _Delete_ or _Backspace_ into them. This is pertinent, e.g.,
  for the `_hidden` field, where unset mean something different
  (inherit from parent) than either `false` or `true`. ([#1048][])
- Add ability to resize textareas. ([#1050][])

#### Markdown

- Links and image URLs in markdown text are now, by default, resolved
  via the Lektor database. Previously, they were not. Note that this
  behavior may be customized on a per-datamodel-field basis if one
  wants to get the old behavior back. ([#992][])
- Lektor now supports either [mistune][] 2.x or mistune 0.x. The
  configuration API of mistune 2.x differs significantly from that of
  mistune 0.x. If you are using a plugin that customizes the markdown
  rendering, you will likely have to update the plugin to support the
  newer mistune, or pin mistune to the older version. ([#992][])

#### GitHub Pages Publisher

- Add support for specifying which branch to push to by specifying a
  `branch` query param on the target URL. ([#978][], [#995][])
- Add support for force-pushing orphan commits by adding a
  `preserve_history=no` query param to the target URL. ([#995][])

#### Thumbnailing

- The `crop` parameter of the `Image.thumbnail()` method (long since
  depreacted) has been removed. ([#551][], [#960][])
- Implicit thumbnail upscaling has been disabled. ([#551][], [#960][])

### Bugs

#### Admin Server

- Refactor and fix numerous buglets in the admin http server. ([#987][])
- Fix 404 error for `/admin`. ([#1043][], [#1044][])
- Fix URL resolution to hidden pages. ([#1048][])

#### Admin Frontend

- Use [esbuild][] rather than webpack/babel to build the admin js code. ([#1012][])
- Update frontend deps. ([#1025][])
- Make `size = {small|large}` field option work again. ([#1022][])
- Handle hotkeys when the preview iframe has the focus. ([#1022][])
- Fix for spurious page scrolling when typing in textareas. ([#1][],
  [#1038][], [#1050][])

#### Builder

- The `asseturl` filter was not propery tracking build dependencies
  resulting in stale hashes in the asset URL if the asset was
  updated. ([#1020][])
- Fix so that un-hidden children of hidden parents are built. Fix
  pruning logic so that artifacts corresponding to hidden pages are
  pruned. ([#203][], [#1048][])

#### Bit-rot

- Fixes for `click==8.1.3`. ([#1031][], [#1033][])
- Fixes for `werkzeug>=2.2.0`. ([#1019][], [#1018][], [#1051][])
- Update npm package minimist. ([#1021][])
- Remove dependency on the `requests[security]` extra. ([#1036][])
- Remove `build-system.requires` dependencies on `wheel`, and the
  `setuptools_scm[toml]` extra. ([#1036][])

#### CI

- Update pre-commit config to use `black==22.3.0` to avoid breakage
  caused by `click>=8.1.0`. ([#1019][])
- Updateto `pylint=2.13.4`. ([#1025][])

#### Command Line

- Fix exception when `--extra-flag`s are specified. ([#1041][], [#1042][])

#### Packaging

- Declare explicit dependencies on `MarkupSafe` and `pytz`,
  where were transitively implied but are imported directly
  by Lektor code. ([#1036][])

### Refactorings

- Removed unused cruft. ([#1009][])

[mistune]: https://mistune.readthedocs.io/en/latest/
[esbuild]: https://github.com/evanw/esbuild
[#1]: https://github.com/lektor/lektor/issues/1
[#203]: https://github.com/lektor/lektor/issues/203
[#551]: https://github.com/lektor/lektor/pull/551
[#960]: https://github.com/lektor/lektor/pull/960
[#978]: https://github.com/lektor/lektor/issues/978
[#987]: https://github.com/lektor/lektor/pull/987
[#992]: https://github.com/lektor/lektor/pull/992
[#995]: https://github.com/lektor/lektor/pull/995
[#1009]: https://github.com/lektor/lektor/pull/1009
[#1012]: https://github.com/lektor/lektor/pull/1012
[#1018]: https://github.com/lektor/lektor/issues/1018
[#1019]: https://github.com/lektor/lektor/pull/1019
[#1020]: https://github.com/lektor/lektor/issues/1020
[#1021]: https://github.com/lektor/lektor/pull/1021
[#1022]: https://github.com/lektor/lektor/issues/1022
[#1025]: https://github.com/lektor/lektor/pull/1025
[#1031]: https://github.com/lektor/lektor/issues/1031
[#1033]: https://github.com/lektor/lektor/pull/1033
[#1036]: https://github.com/lektor/lektor/pull/1036
[#1038]: https://github.com/lektor/lektor/issues/1038
[#1041]: https://github.com/lektor/lektor/issues/1041
[#1042]: https://github.com/lektor/lektor/pull/1042
[#1043]: https://github.com/lektor/lektor/issues/1043
[#1044]: https://github.com/lektor/lektor/pull/1044
[#1048]: https://github.com/lektor/lektor/pull/1048
[#1050]: https://github.com/lektor/lektor/pull/1050
[#1051]: https://github.com/lektor/lektor/pull/1051

## 3.3.2 (2022-03-01)

### Features

#### Command Line

- Enabled the [Jinja debug extension][jinja-dbg-ext] when the
  `LEKTOR_DEV` env var is set to 1 and `lektor server` is
  used. ([#984][])

### License

- The wording in the LICENSE file was standardized to that of the
  current [BSD 3-Clause License][bsd]. ([#972][])

### Bugs

#### Markdown Renderer

- Fix overzealous HTML-entity escaping of link and image attributes. ([#989][])

#### Admin API

- Fix a bug in `make_editor_session` when editing non-existant pages
  with a non-primary alt. ([#964][])
- Fix the ability to add an initial flowblock to a page. (Broken in 3.3.1.)
- Refactor API views to move business logic back into the `Tree`
  adapter ([#967][]). This fixes [#962][].

#### Admin UI

- Changed the structure of the URLs used by the GUI single-page app ([#976][]).
  This fixes problems with the "edit" pencil when using alternatives ([#975][]),
  and issues when page ids include colons ([#610][]).
- Other React refactors and fixes ([#988][]).

#### Database

- Fix `Attachment.url_path` when _alternatives_ are in use. There is only
  one copy of each attachment emitted — the `url_path` should always be
  that corresponding to the _primary alternative_. ([#958][])
- `Pad.get`, if not passed an explicit value for the `alt` parameter,
  now returns the record for the _primary alternative_ rather than the
  fallback record. Similarly, `Pad.root` now returns the root record
  for the _primary alternative_. ([#958][], [#965][])
- Fix for uncaught `OSError(error=EINVAL)` on Windows when `Pad.get`
  was called with a path containing characters which are not allowed
  in Windows filenames (e.g. `<>*?|\/":`).

#### Builder

- Pages now record a build dependency on their datamodel `.ini` file.
- Fix sqlite version detection so that we use "without rowid" optimization
  with current versions of sqlite. ([#1002][])

#### Command Line

- When running `lektor dev new-theme`: fix check for ability to create symlinks
  under Windows. ([#996][])
- Fix _rsync_ publisher when deletion enabled on macOS. ([#946][], [#954][])

#### Tests

- Fix for test failures when git is not installed. ([#998][], [#1000][])

### Refactorings

- Cleaned up `EditorSession` to split mapping methods (for access to
  record data) to a separate class, now available as
  `EditorSession.data`. ([#969][])

#### Testing

- Cleaned up and moved our `pylint` and `coverage` configuration to
  `pyproject.toml`. ([#990][], [#991][])

#### Admin UI

- Move frontend source from `lektor/admin/static/` to `frontend/`.
  Compiled frontend code moved from `lektor/admin/static/gen/` to
  'lektor/admin/static/`. ([#1003][])

#### Packaging

- Omit `example` subdirectory, frontend source code, developer-centric
  config files, as well as other assorted cruft from sdist. ([#986][])

[bsd]: https://opensource.org/licenses/BSD-3-Clause
[#610]: https://github.com/lektor/lektor/issues/610
[#946]: https://github.com/lektor/lektor/issues/946
[#954]: https://github.com/lektor/lektor/pull/954
[#958]: https://github.com/lektor/lektor/pull/958
[#962]: https://github.com/lektor/lektor/issues/962
[#964]: https://github.com/lektor/lektor/pull/964
[#965]: https://github.com/lektor/lektor/issues/965
[#967]: https://github.com/lektor/lektor/pull/967
[#969]: https://github.com/lektor/lektor/pull/969
[#972]: https://github.com/lektor/lektor/pull/972
[#975]: https://github.com/lektor/lektor/issues/975
[#976]: https://github.com/lektor/lektor/pull/976
[#984]: https://github.com/lektor/lektor/pull/984
[#986]: https://github.com/lektor/lektor/pull/986
[#988]: https://github.com/lektor/lektor/pull/988
[#989]: https://github.com/lektor/lektor/pull/989
[#990]: https://github.com/lektor/lektor/pull/990
[#991]: https://github.com/lektor/lektor/pull/991
[#996]: https://github.com/lektor/lektor/pull/996
[#998]: https://github.com/lektor/lektor/issues/998
[#1000]: https://github.com/lektor/lektor/pull/1000
[#1002]: https://github.com/lektor/lektor/pull/1002
[#1003]: https://github.com/lektor/lektor/pull/1003
[jinja-dbg-ext]: https://jinja.palletsprojects.com/en/latest/extensions/#debug-extension

## 3.3.1 (2022-01-09)

### Bugs Fixed

- Fixed an import cycle which caused in `ImportError` if
  `lektor.types` was imported before `lektor.environemnt`. [#974][]

#### Deprecations

- Disuse deprecated `Thread.setDaemon()`. [#979][]

#### Admin UI

- Fix spastic scroll behavior when editing flow elements. [#640][]
- Fix admin GUI when page contains an unknown flowblock type. [#968][]
- Fix admin GUI layout on mobile devices. [#981][]

#### Tests

- Increased timeout in `test_watcher.IterateInThread` to prevent
  random spurious failures during CI testing.
- Fix `tests/test_prev_next_sibling.py` so as to allow running
  multiple test runs in parallel.
- Use per-testenv coverage files to prevent contention when running `tox --parallel`.
- Mark tests that require a working internet connections with pytest mark `requiresinternet`. [#983][]

### Refactors

#### Admin UI

- Finish rewriting React class-based components to function-based components. [#977][]
- Finish adding types for all API endpoints. [#980][]
- Remove disused event-source polyfill.

[#640]: https://github.com/lektor/lektor/issues/640
[#968]: https://github.com/lektor/lektor/issues/968
[#974]: https://github.com/lektor/lektor/pull/974
[#977]: https://github.com/lektor/lektor/pull/977
[#979]: https://github.com/lektor/lektor/pull/979
[#980]: https://github.com/lektor/lektor/pull/980
[#981]: https://github.com/lektor/lektor/pull/981
[#983]: https://github.com/lektor/lektor/pull/983

## 3.3.0 (2021-12-14)

This release drops support for versions of Python before 3.6.
In particular, Python 2.7 is no longer supported.

Quite a few bugs have been fixed since the previous release.

The Admin UI has seen a major refactor and various performance optimisations.
It has been rewritten in Typescript, and updated to use v5 of the Bootstrap CSS framework.

### Bugs Fixed

#### Database

- Fix queries with offset but without a limit. [#827][]
- Fix the handling of deferred (descriptor-type) model fields when used in `slug_format`
  and when used as a sort key. [#789][]
- Refrain from issuing warning about future change in implicit image
  upscaling behavior in cases that do not involve upscaling. [#885][]
- Fix bug with translation fallback of record label. [#897][]

#### Data Modelling

- Fixed pagination issue which caused child-less paginated pages to
  not be built. [#952][]

#### Publisher

- Allow rsync deployment to a local path. [#830][]
- Clean up subprocess handling in `lektor.publisher`. This fixes
  "ResourceWarning: unclosed file" warnings which were being emitted
  when using the rsync publisher, as well as possible other
  buglets. [#896][]

#### Command Line

- Fix circular imports in `lektor.cli` to allow its use as an executable module (`python -m lektor.cli`).
  [#682][], [#856][]
- Fall back to `watchdog` `PollingObserver` if default `Observer` type fails to start.
  This fixes "OSError: inotify watch limit reached" and perhaps other similar failures.
  [#861][], [#886][]

#### Plugins

- Fix the `Plugin.emit` method so that it works. [#859][]
- Reword the (previously incomprehensible) exception message emitted
  when attempting to load a plugin from an improperly named
  distribution. [#875][], [#879][]

#### Build System

- Fix bug in `lektor.sourcesearch.find_files` which was causing intermittent exceptions.
  [#895][], [#897][]

#### Miscellaneous

- Fix reference cycle in `Environment`. [#882][]
- Fix "unclosed file" `ResourceWarning`s. [#898][]

#### Admin UI

- Fix the checkboxes widget. They were broken so as to be uncheckable. [#812][], [#817][]
- Fix page data being incorrectly marked as _changed_ when flow block is expanded/collapsed in the edit UI. [#828][], [#842][]
- Fix encoding of URLs when opening the admin UI from the pencil button. [#815][], [#837][]
- Rename a CSS class in the admin UI to prevent breakage by ad blockers.
  The class `add-block` was being blocked by the _EasyList FR_ ad blocker. [#785][], [#841][]
- Relax URL checking to allow all valid URLs in URL fields. [#793][], [#840][], [#864][]
- Preview iframe was not always updating when it should. [#844][], [#846][]
- Make the "Save" button always visible (without need to scroll on long pages). [#43][], [#870][]
- Disable the "Save" button unless there are changes. [#872][]
- Add "&lt;ctl&gt;-e" hotkey shortcut to edit page. [#876][]
- Update UI to Bootstrap v4. (This fixes a layout issue with the date picker.) [#648][], [#884][]
- Fix edit page failure for select and checkbox widgets with no choices. [#890][], [#900][]
- Update UI to Bootstrap v5. [#917][], [#926][]
- Add missing translation strings, show error dialogs on top of other dialogs [#934][].

### Internal changes

#### Python code

- Drop python 2 compatibility. [#822][], [#850][], [#871][], [#920][], [#922][]
- Drop python 3.5 compatibility. [#878][], [#880][]
- Support python 3.10. [#938][]
- Switch to [PEP-518][]-compatible (pyproject.toml) build process. [#933][], [#942][]
- Code beautification/reformatting. We now use [black][], [reorder-python-imports][], [flake8][], _and_ [pylint][].
  [#823][], [#916][], [#925][], [#936][]
- Refactor rsync publisher tests. [#836][]
- Restructure code to prevent circular imports. [#856][], [#871][], [#873][]
- Minor docstring fixes. [#874][]
- Enabled pylint's no-self-use policy. [#887][]

#### JS code

- We now require node >= 14. [#940][]
- Update NPM/JS dependencies. Update to webpack v5. [#816][],
  [#834][], [#848][], [#852][], [#860][], [#905][], [#917][],
  [#926][], [#945][], [#957][]
- Use [prettier][] and [eslint][] for JS (and YAML) beautification and style enforcement. [#825][], [#936][]
- Disuse unmaintained `jsdomify` to prevent hanging tests. [#839][]
- Disuse jQuery. [#851][]
- Convert JS code to Typescript. Various other refactoring and cleanups. [#857][], [#869][], [#872][]
- Refactor code to handle hotkeys. [#876][]

### Dependencies

- Relax `werkzeug<1` to `werkzeug<3`. [#829][], [#833][], [#911][], [#923][]
- Drop support for Python 2. [#818][], [#819][]
- We now require `Jinja2>=3.0`. [#921][]

### Testing/CI

- Use `tox` for local testing. [#824][]
- Pin version of `pylint` used for tests. [#891][]
- Complete rewrite of the tests for `lektor.pluginsystem` to increase coverage and reduce running time.
  [#881][].
- Test under Python 3.9. [#845][]
- Test under Node v14 and v16. [#852][], [#927][]
- Do not run `brew update` in MacOS CI workflow. [#853][]
- CI workflow simplification. [#927][]

[black]: https://black.readthedocs.io/en/stable/
[pylint]: https://pylint.org/
[reorder-python-imports]: https://github.com/asottile/reorder_python_imports
[flake8]: https://flake8.pycqa.org/en/latest/
[prettier]: https://prettier.io/
[eslint]: https://eslint.org/
[pep-518]: https://www.python.org/dev/peps/pep-0518/
[#43]: https://github.com/lektor/lektor/issues/43
[#648]: https://github.com/lektor/lektor/issues/648
[#682]: https://github.com/lektor/lektor/issues/682
[#785]: https://github.com/lektor/lektor/issues/785
[#789]: https://github.com/lektor/lektor/pull/789
[#793]: https://github.com/lektor/lektor/issues/793
[#812]: https://github.com/lektor/lektor/issues/812
[#815]: https://github.com/lektor/lektor/issues/815
[#816]: https://github.com/lektor/lektor/pull/816
[#817]: https://github.com/lektor/lektor/pull/817
[#818]: https://github.com/lektor/lektor/issues/818
[#819]: https://github.com/lektor/lektor/pull/819
[#822]: https://github.com/lektor/lektor/pull/822
[#823]: https://github.com/lektor/lektor/pull/823
[#824]: https://github.com/lektor/lektor/pull/824
[#825]: https://github.com/lektor/lektor/pull/825
[#827]: https://github.com/lektor/lektor/pull/827
[#828]: https://github.com/lektor/lektor/issues/828
[#829]: https://github.com/lektor/lektor/issues/829
[#830]: https://github.com/lektor/lektor/pull/830
[#833]: https://github.com/lektor/lektor/pull/833
[#834]: https://github.com/lektor/lektor/pull/834
[#836]: https://github.com/lektor/lektor/pull/836
[#837]: https://github.com/lektor/lektor/pull/837
[#839]: https://github.com/lektor/lektor/pull/839
[#840]: https://github.com/lektor/lektor/pull/840
[#841]: https://github.com/lektor/lektor/pull/841
[#842]: https://github.com/lektor/lektor/pull/842
[#844]: https://github.com/lektor/lektor/issues/844
[#845]: https://github.com/lektor/lektor/pull/845
[#846]: https://github.com/lektor/lektor/pull/846
[#848]: https://github.com/lektor/lektor/pull/848
[#850]: https://github.com/lektor/lektor/pull/850
[#851]: https://github.com/lektor/lektor/pull/851
[#852]: https://github.com/lektor/lektor/pull/852
[#853]: https://github.com/lektor/lektor/pull/853
[#856]: https://github.com/lektor/lektor/pull/856
[#857]: https://github.com/lektor/lektor/pull/857
[#859]: https://github.com/lektor/lektor/pull/859
[#860]: https://github.com/lektor/lektor/pull/860
[#861]: https://github.com/lektor/lektor/issues/861
[#864]: https://github.com/lektor/lektor/pull/864
[#869]: https://github.com/lektor/lektor/pull/869
[#870]: https://github.com/lektor/lektor/pull/870
[#871]: https://github.com/lektor/lektor/pull/871
[#872]: https://github.com/lektor/lektor/pull/872
[#873]: https://github.com/lektor/lektor/pull/873
[#874]: https://github.com/lektor/lektor/pull/874
[#875]: https://github.com/lektor/lektor/pull/875
[#876]: https://github.com/lektor/lektor/pull/876
[#878]: https://github.com/lektor/lektor/issues/878
[#879]: https://github.com/lektor/lektor/pull/879
[#880]: https://github.com/lektor/lektor/pull/880
[#881]: https://github.com/lektor/lektor/pull/881
[#882]: https://github.com/lektor/lektor/pull/882
[#884]: https://github.com/lektor/lektor/pull/884
[#885]: https://github.com/lektor/lektor/pull/885
[#886]: https://github.com/lektor/lektor/pull/886
[#887]: https://github.com/lektor/lektor/pull/887
[#890]: https://github.com/lektor/lektor/issues/890
[#891]: https://github.com/lektor/lektor/pull/891
[#895]: https://github.com/lektor/lektor/issues/895
[#896]: https://github.com/lektor/lektor/pull/896
[#897]: https://github.com/lektor/lektor/pull/897
[#898]: https://github.com/lektor/lektor/pull/898
[#900]: https://github.com/lektor/lektor/pull/900
[#905]: https://github.com/lektor/lektor/pull/905
[#911]: https://github.com/lektor/lektor/pull/911
[#916]: https://github.com/lektor/lektor/pull/916
[#917]: https://github.com/lektor/lektor/pull/917
[#920]: https://github.com/lektor/lektor/pull/920
[#921]: https://github.com/lektor/lektor/pull/921
[#922]: https://github.com/lektor/lektor/pull/922
[#923]: https://github.com/lektor/lektor/pull/923
[#925]: https://github.com/lektor/lektor/pull/925
[#926]: https://github.com/lektor/lektor/pull/926
[#927]: https://github.com/lektor/lektor/pull/927
[#933]: https://github.com/lektor/lektor/pull/933
[#934]: https://github.com/lektor/lektor/pull/934
[#936]: https://github.com/lektor/lektor/pull/936
[#938]: https://github.com/lektor/lektor/pull/938
[#940]: https://github.com/lektor/lektor/pull/940
[#942]: https://github.com/lektor/lektor/pull/942
[#945]: https://github.com/lektor/lektor/pull/945
[#952]: https://github.com/lektor/lektor/pull/952
[#957]: https://github.com/lektor/lektor/pull/957

## 3.2.3 (2021-12-11)

### Compatibility

- Restore python 2.7 compatibility. It was broken in leketor 3.2.2. [#951][]
- Pin inifile>=0.4.1 to support python 3.10 [#943][], [#953][]

[#943]: https://github.com/lektor/lektor/issues/943
[#951]: https://github.com/lektor/lektor/pull/951
[#953]: https://github.com/lektor/lektor/pull/953

## 3.2.2 (2021-09-18)

### Packaging

- Fixes a problem with the uploaded wheel in 3.2.1.

### Compatibility

- Fixes to support werkzeug 2.x. [#911][]

## 3.2.1 (2021-09-18)

### Compatibility

- Pin `pytest-click<1` for python 2.7. [#924][]
- Fixes to support werkzeug 1.x. [#833][]

### Bugs

- Allow rsync deployment to a local path. [#830][], [#836][]
- Fix queries with offset but without a limit. [#827][]

### Admin UI

- Fix select and checkboxes widgets when choices is empty. [#900][]
- Update npm packages. [#848][], [#834][], [#816][]
- Fix updating of the preview iframe. [#846][]
- Allow `ftps:` and `mailto:` URLs in url fields. [#840][]
- Fix the toggling of flow widgets in the admin UI to not mark the content as changed. [#842][]
- Rename CSS class to prevent conflict with EasyList FR adblock list. [#841][]
- Fix the handling of the URLs when opening the admin UI from the pencil button. [#837][]
- Fix the checkboxes widget in the admin UI. [#817][]

### Testing / CI

- Test under python 3.9. [#845][]
- Various CI test fixes. [#932][], [#839][], [#832][], [#826][]
- Added a `tox.ini`. [#824][]

Code Reformatting

- Blackify, reorder-python-imports, flake8. [#823][]
- Reformatted js code with prettier. [#825][]
- Update pylint config. [#822][]

[#826]: https://github.com/lektor/lektor/pull/826
[#832]: https://github.com/lektor/lektor/pull/832
[#924]: https://github.com/lektor/lektor/pull/924
[#932]: https://github.com/lektor/lektor/pull/932

## 3.2.0

Release date 20th of August, 2020

- Fix off-by-one error in pagination's iter_pages in the interpretation of the right_current argument, and adding an appropriate trailing `None` for some uses.
- Add support for setting an output_path in the project file.
- Replaced the slugify backend to handle unicode more effectively. This may break some slugs built from unicode.
- Several modernization and performance improvements to the admin UI
- Improved speed of source info updates.
- Set colorspace to sRGB for thumbnails.
- Now stripping profiles and comments from thumbnails.
- Added support for deleting and excluding files for the rsync deployment publisher.
- Improved speed of flow rendering in the admin UI.
- Bugfix to correctly calculate relative urls from slugs that contain dots.
- Bugfix to allow negative integers in integer fields in the admin UI.
- Improved image-heavy build speeds by reducing the amount of data extracted from EXIFs.
- Added the ability to collapse flow elements in the admin UI.
- Now `extra_flags` is passed to all plugin events.
- Extra flags can now be passed to the `clean` and `dev shell` CLI commands.
- Bugfix where `lektor plugins reinstall` triggered `on_setup_env` instead of just reinstalling plugins.
- Added the ability to generate video thumbnails with ffmpeg.
- Added `mode` and `upscale` thumbnail arguments, changing the preferred method to crop to using `mode`. `mode` can be `crop`, `fit`, or `stretch`. `upscale=False` can now prevent upscaling.
- Added a new CLI command `lektor dev new-theme`.
- Made admin use full UTF-8 version of RobotoSlab. Fixes missing glyphs for some languages
- Bumped minimum Jinja2 version to 2.11
- Bumped filetype dependency to 1.0.7 because of API changes
- Relative urls are now as short as possible.
- Changed default slug creation to use slugify. This should mean greater language support, but this may produce slightly different results than before for some users
- Automatically include setup.cfg configured for universal wheels when creating plugins

## 3.1.3

Release date 26th of January, 2019

- Release with universal build.

## 3.1.2

Release date 7th of September 2018

- Fix pagination and virtual pathing for alts
- Fixing deply from local server in Python 3
- Now passing server_info to publisher from local server, providing better
  support for plugin provided publishers.
- Added a more full-featured example project.
- Adding Jinja2 `do` extension.
- Better new-plugin command.
- More tests.
- Added the ability to sort child pages in admin according to models.
- Better image handling and info detection for JPGs and SVGs
- Lektor can now be ran with `python -m lektor`
- New plugins now come with a more full featured setup.py

## 3.1.1

Release date 18th of April 2018

- Better Image dimension detection.
- Fix backwards compatibility with thumbnail generation.
- Adding safety check when runnning new build in non-empty dir since that could delete data.
- Adding command aliases.

## 3.1.0

Release date 29th of January 2018.

- Adding ability to use Lektor Themes.
- Adding Markdown event hook between instantiating the Renderer and creating the Markdown Processor
- Improving tests for GitHub deployment.
- Added the ability to use IPython in the lektor dev shell if it's available.
- Added ability to publish from different filesystems.
- Adding new option to turn disable editing fields on alternatives.
- Added automated testing for Windows.
- Expanded automated testing environments to Python 2.7, 3.5, 3.6, & Node 6, 7, 8.
- Windows bugfixes.
- Improved exif image data.
- Improved date handling in admin.
- Make GitHub Pages branch detection case insensitive.
- Set sqlite isolation to autocommit.
- Fixed errors in the example project.
- Enabling pylint and standard.js.
- Improved image rotation.
- Now measuring tests and pull requests with code coverage.
- Thumbnails can now have a defined quality.
- Moved Windows cache to local appdata.
- README tweaks.
- Beter translations.
- Better file tracking in watcher.
- Upgraded many node dependencies.
- Upgraded from ES5 to ES6.
- Added mp4 attachment type.
- Bugfixes for Python 3.

## 3.0.1

Released on 13th of June 2017.

- Bugfixes and improved Python 2 / 3 compatibility

## 3.0

Released on 15th of July 2016.

- Switch to newer mistune (markdown parser).
- Rename `--build-flags` to `--extra-flags`, allow the deploy command to also
  accept extra flags.

## 2.4

Released on 7th of July 2016.

- Resolved an issue with unicode errors being caused by the
  quickstart.

## 2.3

Released on 31st of May 2016

- Fixed an issue with `get_alts` not being available in the
  template environment.

## 2.2

Released on 12th of April 2016

- Corrected an issue where certain translations would not make the
  admin panel load.

## 2.1

Released on 12th of April 2016

- Fixed a code signing issue on OS X 10.10.3 and lower.

## 2.0

Released on 11th of April 2016

- Added `_discoverable` system field which controls if a page should show
  up in `children`. The default is that a page is discoverable. Setting it
  to `False` means in practical terms that someone needs to know the URL as
  all collection operations will not return it.
- Added `for_page` function to pagination that returns the pagiantion for a
  specific page.
- Make pagination next_page and prev_page be None on the edges.
- Allow plugins to provide publishers.
- Added `|markdown` filter.
- Added French translations.
- Unicode filenames as final build artifacts are now explicitly disallowed.
- Serve up a 404.html as an error page in the dev server.
- Improvements to the path normalization and alt handling. This should support
  URL generation in more complex cases between alts now.
- Show a clearer error message when URL generation fails because a source
  object is virtual (does not have a path).
- Empty text is now still valid markdown.
- Lektor clean now loads the plugins as well.
- Basic support for type customization.
- Fields that are absent in a content file from an alternative are now pulled
  from the primary content file.
- Development server now resolves index.html for assets as well.
- Markdown processing now correctly adjusts links relative to where the
  rendered output is rendered.
- Added Dutch translations.
- Added Record.get_siblings()
- Added various utilties: build_url, join_path, parse_path
- Added support for virtual paths and made pagination work with it.
- Added support for Query.distinct
- Add support for pagination url resolving on root URL.
- Server information can now also contain extra key/value pairs that
  can be used by publishers to affect the processing.
- The thumbnails will now always have the correct width and height set
  as an attribute.
- added datetime type
- added support for the process_image utility functions so that plugins
  can use it directly.
- added support for included_assets and excluded_assets in the project file.
- added Spanish translations.
- added Japanese translations.
- added support for discovering existing alts of sources.
- added support for image cropping.
- added preliminary support for publishing on windows.
- children and attachments can now have a hidden flag configured explicitly.
  Attachments will also no longer inherit the hidden flag of the parent
  record as that is not a sensible default.
- changed internal sqlite consistency mode to improve performance on HDDs.
- allow SVG files to be treated as images. This is something that does not
  work in all situations yet (in particular thumbnailing does not actually
  do anything for those)

## 1.2.1

Released on 3rd of February 2016

- Bugfix release primarily for OS X which fixes a code signing issue.

## 1.2

Released on 1st of February 2016

- Fixed an error that caused unicode characters in the project
  name to be mishandled in the quickstart.
- Do not create empty folders when the quickstart skips over files.
- Empty values for the slug field now pull in the default.
- Corrected a bug in hashing in the FTP publisher that could cause
  files to not upload correctly.
- Improved error message for when imagemagick cannot be found.
- Fixed scrolling in the admin for firefox and some other browsers.
- Fixed a problem with deleting large projects due to sqlite limitations.
- Fixed admin preview of root page in firefox.
- Changed FTPS data channel to use TLS.

## 1.1

Released on 27th of December 2015

- Fixed a bug where resolving URL paths outside of alts did not
  fall back to asset resolving.
- verbose mode now correctly displays traceback of build failures.
- Fixed a bug that caused build failures not to be remembered.
- Fixed a bad EXIF attribute (longitude was misspelt)
- Use requests for URL fetching instead of urllib. This should fix
  some SSL errors on some Python versions.
- Parent of page now correctly resolves to the right alt.
- Publish from a temporary folder on the same device which solves
  problems on machines with `/tmp` on a different drive.

## 1.0

Released on 21st of December 2015

- Improved ghpages and rsync deployments.
- Implemented options for default URL styles.
- All artifacts now depend on the project file.
- Fixed an issue with renames from tempfile in the quickstart.

## 0.96

Initial test release. Release date 19th of December 2015
