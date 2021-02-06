# pylint: disable=import-outside-toplevel
import json
import os
import warnings

import click

from lektor.i18n import get_default_lang
from lektor.i18n import is_valid_language
from lektor.project import Project


def echo_json(data):
    click.echo(json.dumps(data, indent=2).rstrip())


def pruneflag(cli):
    return click.option(
        "--prune/--no-prune",
        default=True,
        help="Controls if old " 'artifacts should be pruned.  "prune" is the default.',
    )(cli)


def extraflag(cli):
    return click.option(
        "-f",
        "--extra-flag",
        "extra_flags",
        multiple=True,
        help="Defines an arbitrary flag.  These can be used by plugins "
        "to customize the build and deploy process.  More information can be "
        "found in the documentation of affected plugins.",
    )(cli)


def _buildflag_deprecated(ctx, param, value):
    if value:
        warnings.warn(
            "use --extra-flag instead of --build-flag",
            DeprecationWarning,
        )
    return value


def buildflag(cli):
    return click.option(
        "--build-flag",
        "build_flags",
        multiple=True,
        help="Deprecated. Use --extra-flag instead.",
        callback=_buildflag_deprecated,
    )(cli)


class AliasedGroup(click.Group):

    # pylint: disable=inconsistent-return-statements
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        if not matches:
            return None
        if len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail("Too many matches: %s" % ", ".join(sorted(matches)))


class Context:
    def __init__(self):
        self._project_path = os.environ.get("LEKTOR_PROJECT") or None
        self._project = None
        self._env = None
        self._ui_lang = None

    def _get_ui_lang(self):
        rv = self._ui_lang
        if rv is None:
            rv = self._ui_lang = get_default_lang()
        return rv

    def _set_ui_lang(self, value):
        self._ui_lang = value

    ui_lang = property(_get_ui_lang, _set_ui_lang)
    del _get_ui_lang, _set_ui_lang

    def set_project_path(self, value):
        self._project_path = value
        self._project = None

    def get_project(self, silent=False):
        if self._project is not None:
            return self._project
        if self._project_path is not None:
            rv = Project.from_path(self._project_path)
        else:
            rv = Project.discover()
        if rv is None:
            if silent:
                return None
            if self._project_path is None:
                raise click.UsageError(
                    "Could not automatically discover "
                    "project.  A Lektor project must "
                    "exist in the working directory or "
                    "any of the parent directories."
                )
            raise click.UsageError('Could not find project "%s"' % self._project_path)
        self._project = rv
        return rv

    def get_default_output_path(self):
        rv = os.environ.get("LEKTOR_OUTPUT_PATH")
        if rv is not None:
            return rv
        return self.get_project().get_output_path()

    def get_env(self, extra_flags=None):
        if self._env is not None:
            return self._env
        from lektor.environment import Environment

        env = Environment(
            self.get_project(), load_plugins=False, extra_flags=extra_flags
        )
        self._env = env
        return env

    def load_plugins(self, reinstall=False, extra_flags=None):
        from .packages import load_packages

        load_packages(self.get_env(extra_flags=extra_flags), reinstall=reinstall)

        if not reinstall:
            from .pluginsystem import initialize_plugins

            initialize_plugins(self.get_env())


pass_context = click.make_pass_decorator(Context, ensure=True)


def validate_language(ctx, param, value):
    if value is not None and not is_valid_language(value):
        raise click.BadParameter('Unsupported language "%s".' % value)
    return value
