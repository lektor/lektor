# Lektor

Lektor is a static website generator.  It builds out an entire project
from static files into many individual HTML pages and has a built-in
admin UI and minimal desktop app.

<img src="https://raw.githubusercontent.com/lektor/lektor-assets/master/screenshots/admin.png" width="100%">

To see how it works look at the ``example`` folder which contains a
very basic project to get started.

For a more complete website look at [lektor/lektor-website](https://github.com/lektor/lektor-website)
which contains the sourcecode for the official lektor website.

## How do I use this?

This is experimental stuff.  If you really want to use it you better have
a Mac because that's right now the only thing that's really supported.

Downloadable releases are on github: [go to releases](https://github.com/lektor/lektor/releases)

If you want to use the command line version make sure to install it
as Python package into a virtualenv and to build the js files before:

    $ pip install --editable .
    $ make build-js

So how do you use it?  Just launch the app and open a project like the
example project.  If you installe the GUI and you want to get access to the
command line executables you can go to Lektor -> Install Shell Command.

Afterwards you can use the `lektor` executable from the command line.

To build projects:

    lektor build

To open up the admin ui and dev server:

    lektor server --browse
