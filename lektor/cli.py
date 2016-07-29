import os
import sys
import json
import time
import click
import pkg_resources

from .i18n import get_default_lang, is_valid_language
from .utils import secure_url
from .project import Project


version = pkg_resources.get_distribution('Lektor').version


def echo_json(data):
    click.echo(json.dumps(data, indent=2).rstrip())


def pruneflag(cli):
    return click.option(
        '--prune/--no-prune', default=True,
        help='Controls if old '
        'artifacts should be pruned.  "prune" is the default.')(cli)


def buildflag(cli):
    return click.option(
        '-f', '--build-flag', 'build_flags', multiple=True,
        help='Defines an arbitrary build flag.  These can be used by plugins '
        'to customize the build process.  More information can be found in '
        'the documentation of affected plugins.')(cli)


class Context(object):

    def __init__(self):
        self._project_path = os.environ.get('LEKTOR_PROJECT') or None
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
                raise click.UsageError('Could not automatically discover '
                                       'project.  A Lektor project must '
                                       'exist in the working directory or '
                                       'any of the parent directories.')
            raise click.UsageError('Could not find project "%s"' %
                                   self._project_path)
        self._project = rv
        return rv

    def get_default_output_path(self):
        rv = os.environ.get('LEKTOR_OUTPUT_PATH')
        if rv is not None:
            return rv
        return self.get_project().get_output_path()

    def get_env(self):
        if self._env is not None:
            return self._env
        from lektor.environment import Environment
        env = Environment(self.get_project(), load_plugins=False)
        self._env = env
        return env

    def load_plugins(self, reinstall=False):
        from .packages import load_packages
        from .pluginsystem import initialize_plugins
        load_packages(self.get_env(), reinstall=reinstall)
        initialize_plugins(self.get_env())


pass_context = click.make_pass_decorator(Context, ensure=True)


def validate_language(ctx, param, value):
    if value is not None and not is_valid_language(value):
        raise click.BadParameter('Unsupported language "%s".' % value)
    return value


@click.group()
@click.option('--project', type=click.Path(),
              help='The path to the lektor project to work with.')
@click.option('--language', default=None, callback=validate_language,
              help='The UI language to use (overrides autodetection).')
@click.version_option(prog_name='Lektor', version=version)
@pass_context
def cli(ctx, project=None, language=None):
    """The lektor management application.

    This command can invoke lektor locally and serve up the website.  It's
    intended for local development of websites.
    """
    if language is not None:
        ctx.ui_lang = language
    if project is not None:
        ctx.set_project_path(project)


@cli.command('build')
@click.option('-O', '--output-path', type=click.Path(), default=None,
              help='The output path.')
@click.option('--watch', is_flag=True, help='If this is enabled the build '
              'process goes into an automatic loop where it watches the '
              'file system for changes and rebuilds.')
@pruneflag
@click.option('-v', '--verbose', 'verbosity', count=True,
              help='Increases the verbosity of the logging.')
@click.option('--source-info-only', is_flag=True,
              help='Instead of building only updates the source infos.  The '
              'source info is used by the web admin panel to quickly find '
              'information about the source files (for instance jump to '
              'files).')
@click.option('--buildstate-path', type=click.Path(), default=None,
              help='Path to a directory that Lektor will use for coordinating '
              'the state of the build. Defaults to a directory named '
              '`.lektor` inside the output path.')
@buildflag
@click.option('--profile', is_flag=True,
              help='Enable build profiler.')
@pass_context
def build_cmd(ctx, output_path, watch, prune, verbosity,
              source_info_only, buildstate_path, profile, build_flags):
    """Builds the entire project into the final artifacts.

    The default behavior is to build the project into the default build
    output path which can be discovered with the `project-info` command
    but an alternative output folder can be provided with the `--output-path`
    option.

    The default behavior is to perform a build followed by a pruning step
    which removes no longer referenced artifacts from the output folder.
    Lektor will only build the files that require rebuilding if the output
    folder is reused.

    To enforce a clean build you have to issue a `clean` command first.

    If the build fails the exit code will be `1` otherwise `0`.  This can be
    used by external scripts to only deploy on successful build for instance.
    """
    from lektor.builder import Builder
    from lektor.reporter import CliReporter

    if output_path is None:
        output_path = ctx.get_default_output_path()

    ctx.load_plugins()

    env = ctx.get_env()

    def _build():
        builder = Builder(env.new_pad(), output_path,
                          buildstate_path=buildstate_path,
                          build_flags=build_flags)
        if source_info_only:
            builder.update_all_source_infos()
            return True

        if profile:
            from .utils import profile_func
            failures = profile_func(builder.build_all)
        else:
            failures = builder.build_all()
        if prune:
            builder.prune()
        return failures == 0

    reporter = CliReporter(env, verbosity=verbosity)
    with reporter:
        success = _build()
        if not watch:
            return sys.exit(0 if success else 1)

        from lektor.watcher import watch
        click.secho('Watching for file system changes', fg='cyan')
        last_build = time.time()
        for ts, _, _ in watch(env):
            if ts > last_build:
                _build()
                last_build = time.time()


@cli.command('clean')
@click.option('-O', '--output-path', type=click.Path(), default=None,
              help='The output path.')
@click.option('-v', '--verbose', 'verbosity', count=True,
              help='Increases the verbosity of the logging.')
@click.confirmation_option(help='Confirms the cleaning.')
@pass_context
def clean_cmd(ctx, output_path, verbosity):
    """Cleans the entire build folder.

    If not build folder is provided, the default build folder of the project
    in the Lektor cache is used.
    """
    from lektor.builder import Builder
    from lektor.reporter import CliReporter

    if output_path is None:
        output_path = ctx.get_default_output_path()

    ctx.load_plugins()
    env = ctx.get_env()

    reporter = CliReporter(env, verbosity=verbosity)
    with reporter:
        builder = Builder(env.new_pad(), output_path)
        builder.prune(all=True)


@cli.command('deploy', short_help='Deploy the website.')
@click.argument('server', required=False)
@click.option('-O', '--output-path', type=click.Path(), default=None,
              help='The output path.')
@click.option('--username', envvar='LEKTOR_DEPLOY_USERNAME',
              help='An optional username to override the URL.')
@click.option('--password', envvar='LEKTOR_DEPLOY_PASSWORD',
              help='An optional password to override the URL or the '
              'default prompt.')
@click.option('--key-file', envvar='LEKTOR_DEPLOY_KEY_FILE',
              help='The path to a key file that should be used for the '
              'authentication of the deployment.')
@click.option('--key', envvar='LEKTOR_DEPLOY_KEY',
              help='The contents of a key file directly a string that should '
              'be used for authentication of the deployment.')
@pass_context
def deploy_cmd(ctx, server, output_path, **credentials):
    """This command deploys the entire contents of the build folder
    (`--output-path`) onto a configured remote server.  The name of the
    server must fit the name from a target in the project configuration.
    If no server is supplied then the default server from the config is
    used.

    The deployment credentials are typically contained in the project config
    file but it's also possible to supply them here explicitly.  In this
    case the `--username` and `--password` parameters (as well as the
    `LEKTOR_DEPLOY_USERNAME` and `LEKTOR_DEPLOY_PASSWORD` environment
    variables) can override what's in the URL.

    For more information see the deployment chapter in the documentation.
    """
    from lektor.publisher import publish, PublishError

    if output_path is None:
        output_path = ctx.get_default_output_path()

    ctx.load_plugins()
    env = ctx.get_env()
    config = env.load_config()

    if server is None:
        server_info = config.get_default_server()
        if server_info is None:
            raise click.BadParameter('No default server configured.',
                                     param_hint='server')
    else:
        server_info = config.get_server(server)
        if server_info is None:
            raise click.BadParameter('Server "%s" does not exist.' % server,
                                     param_hint='server')

    try:
        event_iter = publish(env, server_info.target, output_path,
                             credentials=credentials, server_info=server_info)
    except PublishError as e:
        raise click.UsageError('Server "%s" is not configured for a valid '
                               'publishing method: %s' % (server, e))

    click.echo('Deploying to %s' % server_info.name)
    click.echo('  Build cache: %s' % output_path)
    click.echo('  Target: %s' % secure_url(server_info.target))
    try:
        for line in event_iter:
            click.echo('  %s' % click.style(line, fg='cyan'))
    except PublishError as e:
        click.secho('Error: %s' % e, fg='red')
    else:
        click.echo('Done!')


@cli.command('server', short_help='Launch a local server.')
@click.option('-h', '--host', default='127.0.0.1',
              help='The network interface to bind to.  The default is the '
              'loopback device, but by setting it to 0.0.0.0 it becomes '
              'available on all network interfaces.')
@click.option('-p', '--port', default=5000, help='The port to bind to.',
              show_default=True)
@click.option('-O', '--output-path', type=click.Path(), default=None,
              help='The dev server will build into the same folder as '
              'the build command by default.')
@pruneflag
@click.option('-v', '--verbose', 'verbosity', count=True,
              help='Increases the verbosity of the logging.')
@buildflag
@click.option('--browse', is_flag=True)
@pass_context
def server_cmd(ctx, host, port, output_path, prune, verbosity, build_flags,
               browse):
    """The server command will launch a local server for development.

    Lektor's development server will automatically build all files into
    pages similar to how the build command with the `--watch` switch
    works, but also at the same time serve up the website on a local
    HTTP server.
    """
    from lektor.devserver import run_server
    if output_path is None:
        output_path = ctx.get_default_output_path()
    ctx.load_plugins()
    click.echo(' * Project path: %s' % ctx.get_project().project_path)
    click.echo(' * Output path: %s' % output_path)
    run_server((host, port), env=ctx.get_env(), output_path=output_path,
               prune=prune, verbosity=verbosity, ui_lang=ctx.ui_lang,
               build_flags=build_flags,
               lektor_dev=os.environ.get('LEKTOR_DEV') == '1',
               browse=browse)


@cli.command('project-info', short_help='Shows the info about a project.')
@click.option('as_json', '--json', is_flag=True,
              help='Prints out the data as json.')
@click.option('ops', '--name', is_flag=True, multiple=True,
              flag_value='name', help='Print the project name')
@click.option('ops', '--project-file', is_flag=True, multiple=True,
              flag_value='project_file',
              help='Print the path to the project file.')
@click.option('ops', '--tree', is_flag=True, multiple=True,
              flag_value='tree', help='Print the path to the tree.')
@click.option('ops', '--output-path', is_flag=True, multiple=True,
              flag_value='default_output_path',
              help='Print the path to the default output path.')
@pass_context
def project_info_cmd(ctx, as_json, ops):
    """Prints out information about the project.  This is particular
    useful for script usage or for discovering information about a
    Lektor project that is not immediately obvious (like the paths
    to the default output folder).
    """
    project = ctx.get_project()
    if as_json:
        echo_json(project.to_json())
        return

    if ops:
        data = project.to_json()
        for op in ops:
            click.echo(data.get(op, ''))
    else:
        click.echo('Name: %s' % project.name)
        click.echo('File: %s' % project.project_file)
        click.echo('Tree: %s' % project.tree)
        click.echo('Output: %s' % project.get_output_path())


@cli.command('content-file-info', short_help='Provides information for '
             'a set of lektor files.')
@click.option('as_json', '--json', is_flag=True,
              help='Prints out the data as json.')
@click.argument('files', nargs=-1, type=click.Path())
@pass_context
def content_file_info_cmd(ctx, files, as_json):
    """Given a list of files this returns the information for those files
    in the context of a project.  If the files are from different projects
    an error is generated.
    """
    project = None

    def fail(msg):
        if as_json:
            echo_json({'success': False, 'error': msg})
            sys.exit(1)
        raise click.UsageError('Could not find content file info: %s' % msg)

    for filename in files:
        this_project = Project.discover(filename)
        if this_project is None:
            fail('no project found')
        if project is None:
            project = this_project
        elif project.project_path != this_project.project_path:
            fail('multiple projects')

    if project is None:
        fail('no file indicated a project')

    project_files = []
    for filename in files:
        content_path = project.content_path_from_filename(filename)
        if content_path is not None:
            project_files.append(content_path)

    if not project_files:
        fail('no files resolve in project')

    if as_json:
        echo_json({
            'success': True,
            'project': project.to_json(),
            'paths': project_files,
        })
    else:
        click.echo('Project:')
        click.echo('  Name: %s' % project.name)
        click.echo('  File: %s' % project.project_file)
        click.echo('  Tree: %s' % project.tree)
        click.echo('Paths:')
        for project_file in project_files:
            click.echo('  - %s' % project_file)


@cli.group('plugins', short_help='Manages plugins.')
def plugins_cmd():
    """This command group provides various helpers to manages plugins
    in a Lektor project.
    """


@plugins_cmd.command('add', short_help='Adds a new plugin to the project.')
@click.argument('name')
@pass_context
def plugins_add_cmd(ctx, name):
    """This command can add a new plugin to the project.  If just given
    the name of the plugin the latest version of that plugin is added to
    the project.

    The argument is either the name of the plugin or the name of the plugin
    suffixed with `@version` with the version.  For instance to install
    the version 0.1 of the plugin demo you would do `demo@0.1`.
    """
    project = ctx.get_project()
    from .packages import add_package_to_project

    try:
        info = add_package_to_project(project, name)
    except RuntimeError as e:
        click.echo('Error: %s' % e, err=True)
    else:
        click.echo('Package %s (%s) was added to the project' % (
            info['name'],
            info['version'],
        ))


@plugins_cmd.command('remove', short_help='Removes a plugin from the project.')
@click.argument('name')
@pass_context
def plugins_remove_cmd(ctx, name):
    """This command can remove a plugin to the project again.  The name
    of the plugin is the only argument to the function.
    """
    project = ctx.get_project()
    from .packages import remove_package_from_project
    try:
        old_info = remove_package_from_project(project, name)
    except RuntimeError as e:
        click.echo('Error: %s' % e, err=True)
    else:
        if old_info is None:
            click.echo('Package was not registered with the project.  '
                       'Nothing was removed.')
        else:
            click.echo('Removed package %s (%s)' % (
                old_info['name'],
                old_info['version'],
            ))


@plugins_cmd.command('list', short_help='List all plugins.')
@click.option('as_json', '--json', is_flag=True,
              help='Prints out the data as json.')
@click.option('-v', '--verbose', 'verbosity', count=True,
              help='Increases the verbosity of the output.')
@pass_context
def plugins_list_cmd(ctx, as_json, verbosity):
    """This returns a list of all currently actively installed plugins
    in the project.  By default it only prints out the plugin IDs and
    version numbers but the entire information can be returned by
    increasing verbosity with `-v`.  Additionally JSON output can be
    requested with `--json`.
    """
    ctx.load_plugins()
    env = ctx.get_env()
    plugins = sorted(env.plugins.values(), key=lambda x: x.id.lower())

    if as_json:
        echo_json({
            'plugins': [x.to_json() for x in plugins]
        })
        return

    if verbosity == 0:
        for plugin in plugins:
            click.echo('%s (version %s)' % (plugin.id, plugin.version))
        return

    for idx, plugin in enumerate(plugins):
        if idx:
            click.echo()
        click.echo('%s (%s)' % (plugin.name, plugin.id))
        for line in plugin.description.splitlines():
            click.echo('  %s' % line)
        if plugin.path is not None:
            click.echo('  path: %s' % plugin.path)
        click.echo('  version: %s' % plugin.version)
        click.echo('  import-name: %s' % plugin.import_name)


@plugins_cmd.command('flush-cache', short_help='Flushes the plugin '
                     'installation cache.')
@pass_context
def plugins_flush_cache_cmd(ctx):
    """This uninstalls all plugins in the cache.  On next usage the plugins
    will be reinstalled automatically.  This is mostly just useful during
    plugin development when the cache got corrupted.
    """
    click.echo('Flushing plugin cache ...')
    from .packages import wipe_package_cache
    wipe_package_cache(ctx.get_env())
    click.echo('All done!')


@plugins_cmd.command('reinstall', short_help='Reinstall all plugins.')
@pass_context
def plugins_reinstall_cmd(ctx):
    """Forces a re-installation of all plugins.  This will download the
    requested versions of the plugins and install them into the plugin
    cache folder.  Alternatively one can just use `flush-cache` to
    flush the cache and on next build Lektor will automatically download
    the plugins again.
    """
    ctx.load_plugins(reinstall=True)


@cli.command('quickstart', short_help='Starts a new empty project.')
@click.option('--name', help='The name of the project.')
@click.option('--path', type=click.Path(), help='Output directory')
@pass_context
def quickstart_cmd(ctx, **options):
    """Starts a new empty project with a minimum boilerplate."""
    from lektor.quickstart import project_quickstart
    project_quickstart(options)


from .devcli import cli as devcli
cli.add_command(devcli, 'dev')


main = cli
