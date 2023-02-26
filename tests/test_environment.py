import re
import sys
from html import unescape
from pathlib import Path

import pytest

import lektor.context


@pytest.fixture
def scratch_project_data(scratch_project_data):
    # Add a sub-page to the scratch project
    data = {"_model": "page", "title": "Subpage", "body": "Subpage body"}
    subpage_lr = scratch_project_data / "content/sub-page/contents.lr"
    subpage_lr.parent.mkdir()
    subpage_lr.write_text("".join(lektor.metaformat.serialize(data.items())))
    return scratch_project_data


@pytest.fixture
def compile_template(scratch_env):
    def compile_template(source, name="tmpl.html"):
        Path(scratch_env.root_path, "templates", name).write_text(
            source, encoding="utf-8"
        )
        return scratch_env.jinja_env.get_template(name)

    return compile_template


@pytest.fixture
def source_path():
    return "/"


@pytest.fixture
def bogus_context(scratch_pad, source_path):
    # Construct a Context that has a source, without going through all
    # all the steps necessary to construct an Artifact.
    with lektor.context.Context(pad=scratch_pad) as ctx:
        if source_path is not None:
            ctx.source = scratch_pad.get(source_path)
        yield


def test_jinja2_feature_autoescape(compile_template):
    tmpl = compile_template("{{ value }}", "tmpl.html")
    rendered = tmpl.render(value="<tag>")
    assert unescape(rendered) == "<tag>"
    assert "<" not in rendered


def test_jinja2_feature_with(compile_template):
    tmpl = compile_template("{% with x = 'good' %}{{ x }}{% endwith %}")
    assert tmpl.render() == "good"


def test_jinja2_feature_do(compile_template):
    tmpl = compile_template(
        "{% set x = ['a'] %}{% do x.append('b') %}{{ x|join('-') }}"
    )
    assert tmpl.render() == "a-b"


@pytest.mark.parametrize("source_path", [None, "/"])
@pytest.mark.usefixtures("bogus_context")
def test_jinja2_markdown_filter(compile_template):
    tmpl = compile_template("{{ '**word**' | markdown }}")
    assert "<strong>word</strong>" in tmpl.render()


@pytest.mark.usefixtures("bogus_context")
def test_jinja2_markdown_filter_resolve_links(compile_template):
    tmpl = compile_template(
        "{{ '[subpage](sub-page)' | markdown(resolve_links='always') }}"
    )
    assert re.search(r"<a.*\bhref=(['\"])sub-page/\1.*>subpage</a>", tmpl.render())


@pytest.mark.parametrize(
    "source_path, resolve_links",
    [
        (None, "if-possible"),
        (None, "never"),
        ("/", "never"),
    ],
)
@pytest.mark.usefixtures("bogus_context")
def test_jinja2_markdown_filter_noresolve_links(compile_template, resolve_links):
    tmpl = compile_template(
        f"{{{{ '[subpage](sub-page)' | markdown(resolve_links={resolve_links!r}) }}}}"
    )
    assert re.search(r"<a.*\bhref=(['\"])sub-page\1.*>subpage</a>", tmpl.render())


@pytest.mark.parametrize("source_path", [None])
@pytest.mark.usefixtures("bogus_context")
def test_jinja2_markdown_filter_resolve_raises_if_no_source_obj(compile_template):
    tmpl = compile_template(
        "{{ '[subpage](sub-page)' | markdown(resolve_links='always') }}"
    )
    with pytest.raises(RuntimeError) as exc_info:
        tmpl.render()
    assert re.search(r"\bsource object\b.*\brequired\b", str(exc_info.value))


def test_no_reference_cycle_in_environment(project):
    env = project.make_env(load_plugins=False)
    # reference count should be two: one from our `env` variable, and
    # another from the argument to sys.getrefcount
    assert sys.getrefcount(env) == 2
