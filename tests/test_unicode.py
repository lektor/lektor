import pytest

from lektor.build_programs import BuildError
from lektor.builder import Builder
from lektor.project import Project
from lektor.reporter import BufferReporter


@pytest.fixture
def pad(data_path):
    proj = Project.from_path(data_path / "ünicöde-project")
    return proj.make_env().new_pad()


@pytest.fixture
def builder(pad, tmp_path):
    output_path = tmp_path / "output"
    output_path.mkdir()
    return Builder(pad, str(output_path))


def test_unicode_project_folder(pad, builder):
    prog, _ = builder.build(pad.root)
    with prog.artifacts[0].open("rb") as f:
        assert f.read() == b"<h1>Hello</h1>\n<p>W\xc3\xb6rld</p>\n\n"


def test_unicode_attachment_filename(pad, builder):
    with BufferReporter(builder.env) as reporter:
        prog, _ = builder.build(pad.root.attachments.first())

        failures = reporter.get_failures()
        assert len(failures) == 0

        with prog.artifacts[0].open("rb") as f:
            assert f.read().rstrip() == b"attachment"


def test_bad_file_ignored(pad, builder):
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
