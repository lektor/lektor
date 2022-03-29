# coding: utf-8
import os

from lektor.build_programs import BuildError
from lektor.builder import Builder
from lektor.db import Database
from lektor.environment import Environment
from lektor.project import Project
from lektor.reporter import BufferReporter


def get_unicode_builder(tmpdir):
    proj = Project.from_path(os.path.join(os.path.dirname(__file__), "ünicöde-project"))
    env = Environment(proj)
    pad = Database(env).new_pad()

    return pad, Builder(pad, str(tmpdir.mkdir("output")))


def test_unicode_project_folder(tmpdir):
    pad, builder = get_unicode_builder(tmpdir)
    prog, _ = builder.build(pad.root)
    with prog.artifacts[0].open("rb") as f:
        assert f.read() == b"<h1>Hello</h1>\n<p>W\xc3\xb6rld</p>\n\n"


def test_unicode_attachment_filename(tmpdir):
    pad, builder = get_unicode_builder(tmpdir)

    with BufferReporter(builder.env) as reporter:
        prog, _ = builder.build(pad.root.attachments.first())

        failures = reporter.get_failures()
        assert len(failures) == 0

        with prog.artifacts[0].open("rb") as f:
            assert f.read().rstrip() == b"attachment"


def test_bad_file_ignored(tmpdir):
    pad, builder = get_unicode_builder(tmpdir)
    record = pad.root.children.first()
    with BufferReporter(builder.env) as reporter:
        builder.build(record)
        failures = reporter.get_failures()
        assert len(failures) == 1
        exc_info = failures[0]["exc_info"]
        assert exc_info[0] is BuildError
        assert (
            "The URL for this record contains non "
            "ASCII characters" in exc_info[1].message
        )
