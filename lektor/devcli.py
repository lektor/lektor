# pylint: disable=import-outside-toplevel
import os
import sys

import click

from lektor.cli_utils import AliasedGroup
from lektor.cli_utils import extraflag
from lektor.cli_utils import pass_context

try:
    from IPython import embed
    from traitlets.config.loader import Config
except ImportError:
    pass  # fallback to normal Python InteractiveConsole


@click.group(cls=AliasedGroup, short_help="Development commands.")
def cli():
    """Development commands for Lektor.

    This provides various development support commands for Lektor.  This is
    primarily useful for Lektor plugin development but also if you want to
    extend Lektor itself.  Additional functionality can be unlocked by
    exporting the `LEKTOR_DEV=1` environment variable.
    """


@cli.command("shell", short_help="Starts a python shell.")
@extraflag
@pass_context
def shell_cmd(ctx, extra_flags):
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
    ctx.load_plugins(extra_flags=extra_flags)
    import code
    from lektor.db import F, Tree
    from lektor.builder import Builder

    banner = "Python {} on {}\nLektor Project: {}".format(
        sys.version,
        sys.platform,
        ctx.get_env().root_path,
    )
    ns = {}
    startup = os.environ.get("PYTHONSTARTUP")
    if startup and os.path.isfile(startup):
        with open(startup, encoding="utf-8") as f:
            eval(compile(f.read(), startup, "exec"), ns)  # pylint: disable=eval-used
    pad = ctx.get_env().new_pad()
    ns.update(
        project=ctx.get_project(),
        env=ctx.get_env(),
        pad=pad,
        tree=Tree(pad),
        config=ctx.get_env().load_config(),
        make_builder=lambda: Builder(
            ctx.get_env().new_pad(), ctx.get_default_output_path()
        ),
        F=F,
    )
    try:
        c = Config()
        c.TerminalInteractiveShell.banner2 = banner
        embed(config=c, user_ns=ns)
    except NameError:  # No IPython
        code.interact(banner=banner, local=ns)


@cli.command("new-plugin", short_help="Creates a new plugin")
@click.option("--path", type=click.Path(), help="The destination path")
@click.argument("plugin_name", required=False)
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


@cli.command("new-theme", short_help="Creates a new theme")
@click.option("--path", type=click.Path(), help="The destination path")
@click.argument("theme_name", required=False)
@pass_context
def new_theme(ctx, **defaults):
    """This command creates a new theme.

    This will present you with a very short wizard that guides you through
    creation of a new theme. At the end of it, it will create a theme
    in the packages folder of the current project or the path you defined.

    This is the fastest way to creating a new theme.
    """
    from .quickstart import theme_quickstart

    project = ctx.get_project(silent=True)
    theme_quickstart(defaults, project=project)
