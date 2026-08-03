# coding: utf-8
import os

from lektor.builder import Builder
from lektor.db import Database
from lektor.environment import Environment
from lektor.project import Project


def get_databag_builder(tmpdir):
    proj = Project.from_path(
        os.path.join(os.path.dirname(__file__), "databag-project")
    )
    env = Environment(proj)
    pad = Database(env).new_pad()

    return pad, Builder(pad, str(tmpdir.mkdir("output")))


def test_databag_project_folder(tmpdir):
    pad, builder = get_databag_builder(tmpdir)
    prog, _ = builder.build(pad.root)
    with prog.artifacts[0].open("rb") as f:
        contents = f.read()
        print(contents)
        assert contents.find(b"Text from an ini databag") > -1
        assert contents.find(b"Text from a json databag") > -1
        assert contents.find(b"Text from a yaml databag") > -1
