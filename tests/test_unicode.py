# coding: utf-8
import os


def get_unicode_builder(tmpdir):
    from lektor.project import Project
    from lektor.environment import Environment
    from lektor.db import Database
    from lektor.builder import Builder

    proj = Project.from_path(os.path.join(os.path.dirname(__file__),
                                          u'ünicöde-project'))
    env = Environment(proj)
    pad = Database(env).new_pad()

    return pad, Builder(pad, str(tmpdir.mkdir('output')))


def test_unicode_project_folder(tmpdir):
    pad, builder = get_unicode_builder(tmpdir)
    prog, _ = builder.build(pad.root)
    with prog.artifacts[0].open('rb') as f:
        assert f.read() == b'<h1>Hello</h1>\n<p>W\xc3\xb6rld</p>\n\n'


def test_bad_file_ignored(tmpdir):
    from lektor.reporter import BufferReporter
    from lektor.build_programs import BuildError

    pad, builder = get_unicode_builder(tmpdir)
    record = pad.root.children.first()
    with BufferReporter(builder.env) as reporter:
        prog, _ = builder.build(record)
        failures = reporter.get_failures()
        assert len(failures) == 1
        exc_info = failures[0]['exc_info']
        assert exc_info[0] is BuildError
        assert 'The URL for this record contains non ' \
            'ASCII characters' in exc_info[1].message
