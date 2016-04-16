import time
import traceback
from contextlib import contextmanager

import click
from click import style
from werkzeug.local import LocalProxy, LocalStack

from lektor._compat import text_type


_reporter_stack = LocalStack()
_build_buffer_stack = LocalStack()


def describe_build_func(func):
    self = getattr(func, '__self__', None)
    if self is not None and any(x.__name__ == 'BuildProgram'
                                for x in self.__class__.__mro__):
        return self.__class__.__module__ + '.' + self.__class__.__name__
    return func.__module__ + '.' + func.__name__


class Reporter(object):

    def __init__(self, env, verbosity=0):
        self.env = env
        self.verbosity = verbosity

        self.builder_stack = []
        self.artifact_stack = []
        self.source_stack = []

    def push(self):
        _reporter_stack.push(self)

    def pop(self):
        _reporter_stack.pop()

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()

    @property
    def builder(self):
        if self.builder_stack:
            return self.builder_stack[-1]

    @property
    def current_artifact(self):
        if self.artifact_stack:
            return self.artifact_stack[-1]

    @property
    def current_source(self):
        if self.source_stack:
            return self.source_stack[-1]

    @property
    def show_build_info(self):
        return self.verbosity >= 1

    @property
    def show_tracebacks(self):
        return self.verbosity >= 1

    @property
    def show_current_artifacts(self):
        return self.verbosity >= 2

    @property
    def show_artifact_internals(self):
        return self.verbosity >= 3

    @property
    def show_source_internals(self):
        return self.verbosity >= 3

    @property
    def show_debug_info(self):
        return self.verbosity >= 4

    @contextmanager
    def build(self, activity, builder):
        now = time.time()
        self.builder_stack.append(builder)
        self.start_build(activity)
        try:
            yield
        finally:
            self.builder_stack.pop()
            self.finish_build(activity, now)

    def start_build(self, activity):
        pass

    def finish_build(self, activity, start_time):
        pass

    @contextmanager
    def build_artifact(self, artifact, build_func, is_current):
        now = time.time()
        self.artifact_stack.append(artifact)
        self.start_artifact_build(is_current)
        self.report_build_func(build_func)
        try:
            yield
        finally:
            self.finish_artifact_build(now)
            self.artifact_stack.pop()

    def start_artifact_build(self, is_current):
        pass

    def finish_artifact_build(self, start_time):
        pass

    def report_failure(self, artifact, exc_info):
        pass

    def report_build_all_failure(self, failures):
        pass

    def report_dependencies(self, dependencies):
        for dep in dependencies:
            self.report_debug_info('dependency', dep[1])

    def report_dirty_flag(self, value):
        pass

    def report_write_source_info(self, info):
        pass

    def report_prune_source_info(self, source):
        pass

    def report_sub_artifact(self, artifact):
        pass

    def report_build_func(self, build_func):
        pass

    def report_debug_info(self, key, value):
        pass

    def report_generic(self, message):
        pass

    def report_pruned_artifact(self, artifact_name):
        pass

    @contextmanager
    def process_source(self, source):
        now = time.time()
        self.source_stack.append(source)
        self.enter_source()
        try:
            yield
        finally:
            self.leave_source(now)
            self.source_stack.pop()

    def enter_source(self):
        pass

    def leave_source(self, start_time):
        pass


class NullReporter(Reporter):
    pass


class BufferReporter(Reporter):

    def __init__(self, env, verbosity=0):
        Reporter.__init__(self, env, verbosity)
        self.buffer = []

    def clear(self):
        self.buffer = []

    def get_recorded_dependencies(self):
        rv = set()
        for event, data in self.buffer:
            if event == 'debug-info' and \
               data['key'] == 'dependency':
                rv.add(data['value'])
        return sorted(rv)

    def get_major_events(self):
        rv = []
        for event, data in self.buffer:
            if event not in ('debug-info', 'dirty-flag', 'write-source-info'):
                rv.append((event, data))
        return rv

    def get_failures(self):
        rv = []
        for event, data in self.buffer:
            if event == 'failure':
                rv.append(data)
        return rv

    def _emit(self, _event, **extra):
        self.buffer.append((_event, extra))

    def start_build(self, activity):
        self._emit('start-build', activity=activity)

    def finish_build(self, activity, start_time):
        self._emit('finish-build', activity=activity)

    def start_artifact_build(self, is_current):
        self._emit('start-artifact-build', artifact=self.current_artifact,
                   is_current=is_current)

    def finish_artifact_build(self, start_time):
        self._emit('finish-artifact-build', artifact=self.current_artifact)

    def report_build_all_failure(self, failures):
        self._emit('build-all-failure', failures=failures)

    def report_failure(self, artifact, exc_info):
        self._emit('failure', artifact=artifact, exc_info=exc_info)

    def report_dirty_flag(self, value):
        self._emit('dirty-flag', artifact=self.current_artifact,
                   value=value)

    def report_write_source_info(self, info):
        self._emit('write-source-info', info=info,
                   artifact=self.current_artifact)

    def report_prune_source_info(self, source):
        self._emit('prune-source-info', source=source)

    def report_build_func(self, build_func):
        self._emit('build-func', func=describe_build_func(build_func))

    def report_sub_artifact(self, artifact):
        self._emit('sub-artifact', artifact=artifact)

    def report_debug_info(self, key, value):
        self._emit('debug-info', key=key, value=value)

    def report_generic(self, message):
        self._emit('generic', message=message)

    def enter_source(self):
        self._emit('enter-source', source=self.current_source)

    def leave_source(self, start_time):
        self._emit('leave-source', source=self.current_source)

    def report_pruned_artifact(self, artifact_name):
        self._emit('pruned-artifact', artifact_name=artifact_name)


class CliReporter(Reporter):

    def __init__(self, env, verbosity=0):
        Reporter.__init__(self, env, verbosity)
        self.indentation = 0

    def indent(self):
        self.indentation += 1

    def outdent(self):
        self.indentation -= 1

    def _write_line(self, text):
        click.echo(' ' * (self.indentation * 2) + text)

    def _write_kv_info(self, key, value):
        self._write_line('%s: %s' % (key, style(text_type(value), fg='yellow')))

    def start_build(self, activity):
        self._write_line(style('Started %s' % activity, fg='cyan'))
        if not self.show_build_info:
            return
        self._write_line(style('  Tree: %s' % self.env.root_path, fg='cyan'))
        self._write_line(style('  Output path: %s' %
                               self.builder.destination_path, fg='cyan'))

    def finish_build(self, activity, start_time):
        self._write_line(style('Finished %s in %.2f sec' % (
            activity, time.time() - start_time), fg='cyan'))

    def start_artifact_build(self, is_current):
        artifact = self.current_artifact
        if is_current:
            if not self.show_current_artifacts:
                return
            sign = click.style('X', fg='cyan')
        else:
            sign = click.style('U', fg='green')
        self._write_line('%s %s' % (sign, artifact.artifact_name))

        self.indent()

    def finish_artifact_build(self, start_time):
        self.outdent()

    def report_build_all_failure(self, failures):
        self._write_line(click.style(
            'Error: Build failed with %s failure%s.' % (
                failures, failures != 1 and 's' or ''), fg='red'))

    def report_failure(self, artifact, exc_info):
        sign = click.style('E', fg='red')
        err = ' '.join(''.join(traceback.format_exception_only(
            *exc_info[:2])).splitlines()).strip()
        self._write_line('%s %s (%s)' % (
            sign, artifact.artifact_name, err))

        if not self.show_tracebacks:
            return

        tb = traceback.format_exception(*exc_info)
        for line in ''.join(tb).splitlines():
            if line.startswith('Traceback '):
                line = click.style(line, fg='red')
            elif line.startswith('  File '):
                line = click.style(line, fg='yellow')
            elif not line.startswith('    '):
                line = click.style(line, fg='red')
            self._write_line('  ' + line)

    def report_dirty_flag(self, value):
        if self.show_artifact_internals and (value or self.show_debug_info):
            self._write_kv_info('forcing sources dirty', value)

    def report_write_source_info(self, info):
        if self.show_artifact_internals and self.show_debug_info:
            self._write_kv_info('writing source info', '%s [%s]' % (
                info.title_i18n['en'], info.type))

    def report_prune_source_info(self, source):
        if self.show_artifact_internals and self.show_debug_info:
            self._write_kv_info('pruning source info', source)

    def report_build_func(self, build_func):
        if self.show_artifact_internals:
            self._write_kv_info('build program',
                                describe_build_func(build_func))

    def report_sub_artifact(self, artifact):
        if self.show_artifact_internals:
            self._write_kv_info('sub artifact', artifact.artifact_name)

    def report_debug_info(self, key, value):
        if self.show_debug_info:
            self._write_kv_info(key, value)

    def report_generic(self, message):
        self._write_line(style(text_type(message), fg='cyan'))

    def enter_source(self):
        if not self.show_source_internals:
            return
        self._write_line('Source %s' % style(repr(
            self.current_source), fg='magenta'))
        self.indent()

    def leave_source(self, start_time):
        if self.show_source_internals:
            self.outdent()

    def report_pruned_artifact(self, artifact_name):
        self._write_line('%s %s' % (style('D', fg='red'), artifact_name))


null_reporter = NullReporter(None)


@LocalProxy
def reporter():
    rv = _reporter_stack.top
    if rv is None:
        rv = null_reporter
    return rv
