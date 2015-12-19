import os
import sys
import click

from .packages import get_package_info, register_package, publish_package
from .cli import pass_context


def ensure_plugin():
    here = os.getcwd()
    if not os.path.isfile(os.path.join(here, 'setup.py')):
        raise click.UsageError('This command must be run in a '
                               'Lektor plugin folder')
    info = get_package_info(here)
    if not info['name'].lower().startswith('lektor-'):
        raise click.UsageError('Python package is misnamed. Needs to start '
                               'with lektor-')
    return info


@click.group(short_help='Development commands.')
def cli():
    """Development commands for Lektor.

    This provides various development support commands for Lektor.  This is
    primarily useful for Lektor plugin development but also if you want to
    extend Lektor itself.  Additional functionality can be unlocked by
    exporting the `LEKTOR_DEV=1` environment variable.
    """


@cli.command('shell', short_help='Starts a python shell.')
@pass_context
def shell_cmd(ctx):
    """Starts a Python shell in the context of a Lektor project.

    This is particularly useful for debugging plugins and to explore the
    API.  To quit the shell just use `quit()`.  Within the shell various
    utilities are available right from the get-go for you.

    \b
    - `project`: the loaded project as object.
    - `env`: an environment for the loaded project.
    - `pad`: a database pad initialized for the project and environment
      that is ready to use.
    """
    ctx.load_plugins()
    import code
    from lektor.db import F, Tree
    from lektor.builder import Builder
    banner = 'Python %s on %s\nLektor Project: %s' % (
        sys.version,
        sys.platform,
        ctx.get_env().root_path,
    )
    ns = {}
    startup = os.environ.get('PYTHONSTARTUP')
    if startup and os.path.isfile(startup):
        with open(startup, 'r') as f:
            eval(compile(f.read(), startup, 'exec'), ns)
    pad = ctx.get_env().new_pad()
    ns.update(
        project=ctx.get_project(),
        env=ctx.get_env(),
        pad=pad,
        tree=Tree(pad),
        config=ctx.get_env().load_config(),
        make_builder=lambda: Builder(ctx.get_env().new_pad(),
                                     ctx.get_default_output_path()),
        F=F
    )
    code.interact(banner=banner, local=ns)


@cli.command('publish-plugin', short_help='Publish a plugin to PyPI.')
def publish_plugin_cmd():
    """Publishes the current version of the plugin in the current folder.

    This generally requires that your setup.py has at least the bare minimum
    configuration for valid publishing to PyPI.
    """
    info = ensure_plugin()
    for key in 'author', 'author_email', 'license', 'url':
        if not info[key]:
            raise click.UsageError('Cannot publish plugin without setting '
                                   '"%s" in setup.py.' % key)
    register_package(info['path'])
    publish_package(info['path'])


@cli.command('new-plugin', short_help='Creates a new plugin')
@click.option('--path', type=click.Path(), help='The destination path')
@click.argument('plugin_name', required=False)
@pass_context
def new_plugin(ctx, **defaults):
    """This command creates a new plugin.

    This will present you with a very short wizard that guides you through
    creation of a new plugin.  At the end of it, it will create a plugin
    in the packages folder of the current project or the path you defined.

    This is the fastest way to creating a new plugin.
    """
    from .quickstart import plugin_quickstart
    project = ctx.get_project(silent=True)
    plugin_quickstart(defaults, project=project)
