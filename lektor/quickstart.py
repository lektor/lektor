import os
import re
import shutil
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime
from functools import partial

import click
from jinja2 import Environment, PackageLoader

from .utils import fs_enc, slugify
from lektor._compat import text_type


_var_re = re.compile(r'@([^@]+)@')


class Generator(object):

    def __init__(self, base):
        self.question = 0
        self.jinja_env = Environment(
            loader=PackageLoader('lektor', 'quickstart-templates/%s' % base),
            line_statement_prefix='%%',
            line_comment_prefix='##',
            variable_start_string='${',
            variable_end_string='}',
            block_start_string='<%',
            block_end_string='%>',
            comment_start_string='/**',
            comment_end_string='**/',
        )
        self.options = {}
        self.term_width = min(click.get_terminal_size()[0], 78)
        self.e = click.secho
        self.w = partial(click.wrap_text, width=self.term_width)

    def abort(self, message):
        click.echo('Error: %s' % message, err=True)
        raise click.Abort()

    def prompt(self, text, default=None, info=None):
        self.question += 1
        self.e('')
        self.e('Step %d:' % self.question, fg='yellow')
        if info is not None:
            self.e(click.wrap_text(info, self.term_width - 2, '| ', '| '))
        text = '> ' + click.style(text, fg='green')

        if default is True or default is False:
            rv = click.confirm(text, default=default)
        else:
            rv = click.prompt(text, default=default, show_default=True)
        return rv

    def title(self, title):
        self.e(title, fg='cyan')
        self.e('=' * len(title), fg='cyan')
        self.e('')

    def text(self, text):
        self.e(self.w(text))

    def confirm(self, prompt):
        self.e('')
        click.confirm(prompt, default=True, abort=True, prompt_suffix=' ')

    @contextmanager
    def make_target_directory(self, path):
        here = os.path.abspath(os.getcwd())
        path = os.path.abspath(path)
        if here != path:
            try:
                os.makedirs(path)
            except OSError as e:
                self.abort('Could not create target folder: %s' % e)

        if os.path.isdir(path):
            try:
                if len(os.listdir(path)) != 0:
                    raise OSError('Directory not empty')
            except OSError as e:
                self.abort('Bad target folder: %s' % e)

        scratch = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex)
        os.makedirs(scratch)
        try:
            yield scratch
        except:
            shutil.rmtree(scratch)
            raise
        else:
            # Use shutil.move here in case we move across a file system
            # boundary.
            for filename in os.listdir(scratch):
                if not isinstance(path, text_type):
                    filename = filename.decode(fs_enc)
                shutil.move(os.path.join(scratch, filename),
                            os.path.join(path, filename))
            os.rmdir(scratch)

    def expand_filename(self, base, ctx, template_filename):
        def _repl(match):
            return ctx[match.group(1)]
        return os.path.join(base, _var_re.sub(_repl, template_filename))[:-3]

    def run(self, ctx, path):
        with self.make_target_directory(path) as scratch:
            for template in self.jinja_env.list_templates():
                if not template.endswith('.in'):
                    continue
                fn = self.expand_filename(scratch, ctx, template)
                tmpl = self.jinja_env.get_template(template)
                rv = tmpl.render(ctx).strip('\r\n')
                if rv:
                    directory = os.path.dirname(fn)
                    try:
                        os.makedirs(directory)
                    except OSError:
                        pass
                    with open(fn, 'wb') as f:
                        f.write((rv + '\n').encode('utf-8'))


def get_default_author():
    import getpass

    if os.name == 'nt':
        return getpass.getuser().decode('mbcs')

    import pwd
    ent = pwd.getpwuid(os.getuid())
    if ent and ent.pw_gecos:
        name = ent.pw_gecos
        if isinstance(name, text_type):
            return name
        else:
            return name.decode('utf-8', 'replace')

    name = getpass.getuser()
    if isinstance(name, text_type):
        return name
    else:
        return name.decode('utf-8', 'replace')


def get_default_author_email():
    try:
        value = subprocess.Popen(['git', 'config', 'user.email'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).communicate()[0].strip()
        return value.decode('utf-8')
    except Exception:
        return None


def project_quickstart(defaults=None):
    if not defaults:
        defaults = {}

    g = Generator('project')

    g.title('Lektor Quickstart')
    g.text(
        'This wizard will generate a new basic project with some sensible '
        'defaults for getting started quickly.  We just need to go through '
        'a few questions so that the project is set up correctly for you.'
    )

    name = defaults.get('name')
    if name is None:
        name = g.prompt('Project Name', None,
            'A project needs a name.  The name is primarily used for the admin '
            'UI and some other places to refer to your project to not get '
            'confused if multiple projects exist.  You can change this at '
            'any later point.')

    author_name = g.prompt('Author Name', get_default_author(),
        'Your name.  This is used in a few places in the default template '
        'to refer to in the default copyright messages.')

    path = defaults.get('path')
    if path is None:
        here = os.path.abspath(os.getcwd())
        default_project_path = None
        try:
            if len(os.listdir(here)) == []:
                default_project_path = here
        except OSError:
            pass
        if default_project_path is None:
            default_project_path = os.path.join(os.getcwd(), name)
        path = g.prompt('Project Path', default_project_path,
            'This is the path where the project will be located.  You can '
            'move a project around later if you do not like the path.  If '
            'you provide a relative path it will be relative to the working '
            'directory.')
        path = os.path.expanduser(path)

    with_blog = g.prompt('Add Basic Blog', True,
        'Do you want to generate a basic blog module?  If you enable this '
        'the models for a very basic blog will be generated.')

    g.confirm('That\'s all. Create project?')

    g.run({
        'project_name': name,
        'project_slug': slugify(name),
        'project_path': path,
        'with_blog': with_blog,
        'this_year': datetime.utcnow().year,
        'today': datetime.utcnow().strftime('%Y-%m-%d'),
        'author_name': author_name,
    }, path)


def plugin_quickstart(defaults=None, project=None):
    if defaults is None:
        defaults = {}

    g = Generator('plugin')

    plugin_name = defaults.get('plugin_name')
    if plugin_name is None:
        plugin_name = g.prompt('Plugin Name', None,
            'This is the human readable name for this plugin')

    plugin_id = plugin_name.lower()
    if plugin_id.startswith('lektor'):
        plugin_id = plugin_id[6:]
    if plugin_id.endswith('plugin'):
        plugin_id = plugin_id[:-6]
    plugin_id = slugify(plugin_id)

    path = defaults.get('path')
    if path is None:
        if project is not None:
            default_path = os.path.join(project.tree, 'packages',
                                        plugin_id)
        else:
            if len(os.listdir('.')) == 0:
                default_path = os.getcwd()
            else:
                default_path = os.path.join(os.getcwd(), plugin_id)
        path = g.prompt('Plugin Path', default_path,
            'The place where you want to initialize the plugin')

    author_name = g.prompt('Author Name', get_default_author(),
        'Your name as it will be embedded in the plugin metadata.')

    author_email = g.prompt('Author E-Mail', get_default_author_email(),
        'Your e-mail address for the plugin info.')

    g.confirm('Create Plugin?')

    g.run({
        'plugin_name': plugin_name,
        'plugin_id': plugin_id,
        'plugin_class': plugin_id.title().replace('-', '') + 'Plugin',
        'plugin_module': 'lektor_' + plugin_id.replace('-', '_'),
        'author_name': author_name,
        'author_email': author_email,
    }, path)
