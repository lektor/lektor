# pylint: disable=import-outside-toplevel
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

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
        help="Whether outdated artifacts are pruned. The default is to prune.",
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
        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")


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
                    "Could not automatically discover a "
                    "project in the working or ancestor directories. "
                    "The --project global parameter or the "
                    "LEKTOR_PROJECT environment variable may be used "
                    "to explicitly specify the path to the project."
                )
            raise click.UsageError(f'Could not find project "{self._project_path}"')
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
        raise click.BadParameter(f'Unsupported language "{value}".')
    return value


class ResolvedPath(click.Path):
    """A click paramter type for a resolved path.

    We could just use ``click.Path(resolve_path=True)`` except that that
    fails sometimes under Windows running python <= 3.9.

    See https://github.com/pallets/click/issues/2466
    """

    def __init__(self, writable=False, file_okay=True):
        super().__init__(
            resolve_path=True, allow_dash=False, writable=writable, file_okay=file_okay
        )

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> Any:
        abspath = Path(value).absolute()
        # fsdecode to ensure that the return value is a str.
        # (with click<8.0.3 Path.convert will return Path if passed a Path)
        return os.fsdecode(super().convert(abspath, param, ctx))
