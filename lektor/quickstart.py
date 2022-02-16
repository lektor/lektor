import getpass
import os
import re
import shutil
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from importlib import import_module
from subprocess import PIPE
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Optional

import click
from jinja2 import Environment
from jinja2 import PackageLoader

from lektor.utils import locate_executable
from lektor.utils import slugify

pwd = import_module("pwd") if os.name != "nt" else None


_var_re = re.compile(r"@([^@]+)@")


class Generator:
    def __init__(self, base):
        self.question = 0
        self.jinja_env = Environment(
            loader=PackageLoader("lektor", "quickstart-templates/%s" % base),
            line_statement_prefix="%%",
            line_comment_prefix="##",
            variable_start_string="${",
            variable_end_string="}",
            block_start_string="<%",
            block_end_string="%>",
            comment_start_string="/**",
            comment_end_string="**/",
        )
        self.options = {}
        # term width in [1, 78]
        self.term_width = min(max(shutil.get_terminal_size()[0], 1), 78)
        self.e = click.secho
        self.w = partial(click.wrap_text, width=self.term_width)

    @staticmethod
    def abort(message):
        click.echo("Error: %s" % message, err=True)
        raise click.Abort()

    def prompt(self, text, default=None, info=None):
        self.question += 1
        self.e("")
        self.e("Step %d:" % self.question, fg="yellow")
        if info is not None:
            self.e(click.wrap_text(info, self.term_width, "| ", "| "))
        text = "> " + click.style(text, fg="green")

        if default is True or default is False:
            return click.confirm(text, default=default)
        return click.prompt(text, default=default, show_default=True)

    def title(self, title):
        self.e(title, fg="cyan")
        self.e("=" * len(title), fg="cyan")
        self.e("")

    def warn(self, text):
        self.e(self.w(text), fg="magenta")

    def text(self, text):
        self.e(self.w(text))

    def confirm(self, prompt):
        self.e("")
        click.confirm(prompt, default=True, abort=True, prompt_suffix=" ")

    @contextmanager
    def make_target_directory(self, path):
        here = os.path.abspath(os.getcwd())
        path = os.path.abspath(path)
        if here != path:
            try:
                os.makedirs(path)
            except OSError as e:
                self.abort("Could not create target folder: %s" % e)

        if os.path.isdir(path):
            try:
                if len(os.listdir(path)) != 0:
                    raise OSError("Directory not empty")
            except OSError as e:
                self.abort("Bad target folder: %s" % e)

        with TemporaryDirectory() as scratch:
            yield scratch

            # Use shutil.move here in case we move across a file system
            # boundary.
            for filename in os.listdir(scratch):
                shutil.move(
                    os.path.join(scratch, filename), os.path.join(path, filename)
                )

    @staticmethod
    def expand_filename(base, ctx, template_filename):
        def _repl(match):
            return ctx[match.group(1)]

        return os.path.join(base, _var_re.sub(_repl, template_filename))[:-3]

    def run(self, ctx, path):
        with self.make_target_directory(path) as scratch:
            for template in self.jinja_env.list_templates():
                if not template.endswith(".in"):
                    continue
                fn = self.expand_filename(scratch, ctx, template)
                tmpl = self.jinja_env.get_template(template)
                rv = tmpl.render(ctx).strip("\r\n")
                if rv:
                    directory = os.path.dirname(fn)
                    try:
                        os.makedirs(directory)
                    except OSError:
                        pass
                    with open(fn, "wb") as f:
                        f.write((rv + "\n").encode("utf-8"))


def get_default_author() -> str:
    """Attempt to guess an the name of the current user."""
    if pwd is not None:
        try:
            pw_gecos = pwd.getpwuid(os.getuid()).pw_gecos
        except KeyError:
            pass
        else:
            full_name = pw_gecos.split(",", 1)[0].strip()
            if full_name:
                return full_name

    return getpass.getuser()


def get_default_author_email() -> Optional[str]:
    """Attempt to guess an email address for the current user.

    May return an empty string if not reasonable guess can be made.
    """
    git = locate_executable("git")
    if git:
        proc = run(
            (git, "config", "user.email"), stdout=PIPE, errors="strict", check=False
        )
        if proc.returncode == 0:
            return proc.stdout.strip()

    email = os.environ.get("EMAIL", "").strip()
    if email:
        return email
    # We could fall back to f"{getpass.getuser()}@{socket.getfqdn()}",
    # but it is probably better just to go with no default in that
    # case.
    return None


def project_quickstart(defaults=None):
    if not defaults:
        defaults = {}

    g = Generator("project")

    g.title("Lektor Quickstart")
    g.text(
        "This wizard will generate a new basic project with some sensible "
        "defaults for getting started quickly.  We just need to go through "
        "a few questions so that the project is set up correctly for you."
    )

    name = defaults.get("name")
    if name is None:
        name = g.prompt(
            "Project Name",
            None,
            "A project needs a name.  The name is primarily used for the admin "
            "UI and some other places to refer to your project to not get "
            "confused if multiple projects exist.  You can change this at "
            "any later point.",
        )

    author_name = g.prompt(
        "Author Name",
        get_default_author(),
        "Your name.  This is used in a few places in the default template "
        "to refer to in the default copyright messages.",
    )

    path = defaults.get("path")
    if path is None:
        default_project_path = os.path.join(os.getcwd(), name)
        path = g.prompt(
            "Project Path",
            default_project_path,
            "This is the path where the project will be located.  You can "
            "move a project around later if you do not like the path.  If "
            "you provide a relative path it will be relative to the working "
            "directory.",
        )
        path = os.path.expanduser(path)

    with_blog = g.prompt(
        "Add Basic Blog",
        True,
        "Do you want to generate a basic blog module?  If you enable this "
        "the models for a very basic blog will be generated.",
    )

    g.confirm("That's all. Create project?")

    g.run(
        {
            "project_name": name,
            "project_slug": slugify(name),
            "project_path": path,
            "with_blog": with_blog,
            "this_year": datetime.utcnow().year,
            "today": datetime.utcnow().strftime("%Y-%m-%d"),
            "author_name": author_name,
        },
        path,
    )


def plugin_quickstart(defaults=None, project=None):
    if defaults is None:
        defaults = {}

    g = Generator("plugin")

    plugin_name = defaults.get("plugin_name")
    if plugin_name is None:
        plugin_name = g.prompt(
            "Plugin Name",
            default=None,
            info="This is the human readable name for this plugin",
        )

    plugin_id = plugin_name.lower()
    if plugin_id.startswith("lektor"):
        plugin_id = plugin_id[6:]
    if plugin_id.endswith("plugin"):
        plugin_id = plugin_id[:-6]
    plugin_id = slugify(plugin_id)

    path = defaults.get("path")
    if path is None:
        if project is not None:
            default_path = os.path.join(project.tree, "packages", plugin_id)
        else:
            if len(os.listdir(".")) == 0:
                default_path = os.getcwd()
            else:
                default_path = os.path.join(os.getcwd(), plugin_id)
        path = g.prompt(
            "Plugin Path",
            default_path,
            "The place where you want to initialize the plugin",
        )

    author_name = g.prompt(
        "Author Name",
        get_default_author(),
        "Your name as it will be embedded in the plugin metadata.",
    )

    author_email = g.prompt(
        "Author E-Mail",
        get_default_author_email(),
        "Your e-mail address for the plugin info.",
    )

    g.confirm("Create Plugin?")

    g.run(
        {
            "plugin_name": plugin_name,
            "plugin_id": plugin_id,
            "plugin_class": plugin_id.title().replace("-", "") + "Plugin",
            "plugin_module": "lektor_" + plugin_id.replace("-", "_"),
            "author_name": author_name,
            "author_email": author_email,
        },
        path,
    )


def theme_quickstart(defaults=None, project=None):
    if defaults is None:
        defaults = {}

    g = Generator("theme")

    theme_name = defaults.get("theme_name")
    if theme_name is None:
        theme_name = g.prompt(
            "Theme Name",
            default=None,
            info="This is the human readable name for this theme",
        )

    theme_id = theme_name.lower()
    if theme_id != "lektor" and theme_id.startswith("lektor"):
        theme_id = theme_id[6:].strip()
    if theme_id != "theme" and theme_id.startswith("theme"):
        theme_id = theme_id[5:]
    if theme_id != "theme" and theme_id.endswith("theme"):
        theme_id = theme_id[:-5]
    theme_id = slugify(theme_id)

    path = defaults.get("path")
    if path is None:
        if project is not None:
            default_path = os.path.join(
                project.tree, "themes", "lektor-theme-{}".format(theme_id)
            )
        else:
            if len(os.listdir(".")) == 0:
                default_path = os.getcwd()
            else:
                default_path = os.path.join(os.getcwd(), theme_id)
        path = g.prompt(
            "Theme Path",
            default_path,
            "The place where you want to initialize the theme",
        )

    author_name = g.prompt(
        "Author Name",
        get_default_author(),
        "Your name as it will be embedded in the theme metadata.",
    )

    author_email = g.prompt(
        "Author E-Mail",
        get_default_author_email(),
        "Your e-mail address for the theme info.",
    )

    g.confirm("Create Theme?")

    g.run(
        {
            "theme_name": theme_name,
            "theme_id": theme_id,
            "author_name": author_name,
            "author_email": author_email,
        },
        path,
    )

    # symlink
    theme_dir = os.getcwd()
    example_themes = os.path.join(path, "example-site/themes")
    os.makedirs(example_themes)
    os.chdir(example_themes)
    try:
        os.symlink(
            "../../../lektor-theme-{}".format(theme_id),
            "lektor-theme-{}".format(theme_id),
        )
    except OSError as exc:
        # Windows, by default, only allows members of the "Administrators" group
        # to create symlinks. For users who are not allowed to create symlinks,
        # error Code 1314 - "A required privilege is not held by the client"
        # is raised.
        if getattr(exc, "winerror", None) != 1314:
            raise
        g.warn(
            "Could not automatically make a symlink to have your example-site"
            "easily pick up your theme."
        )
    os.chdir(theme_dir)

    # Sample image
    os.makedirs(os.path.join(path, "images"))
    source_image_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "quickstart-templates/theme/images/homepage.png",
    )
    destination_image_path = os.path.join(path, "images/homepage.png")
    with open(source_image_path, "rb") as f:
        image = f.read()
    with open(destination_image_path, "wb") as f:
        f.write(image)
