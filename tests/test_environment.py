import datetime
import sys
from html import unescape
from pathlib import Path

import pytest

import lektor.context
from lektor.environment import Environment


@pytest.fixture
def scratch_project_data(scratch_project_data):
    # Add a sub-page to the scratch project
    data = {"_model": "page", "title": "Subpage", "body": "Subpage body"}
    subpage_lr = scratch_project_data / "content/sub-page/contents.lr"
    subpage_lr.dirpath().ensure_dir()
    subpage_lr.write_text("".join(lektor.metaformat.serialize(data.items())), "utf-8")
    return scratch_project_data


@pytest.fixture
def compile_template(scratch_env):
    def compile_template(source, name="tmpl.html"):
        Path(scratch_env.root_path, "templates", name).write_text(
            source, encoding="utf-8"
        )
        return scratch_env.jinja_env.get_template(name)

    return compile_template


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


def test_no_reference_cycle_in_environment(project):
    env = project.make_env(load_plugins=False)
    # reference count should be two: one from our `env` variable, and
    # another from the argument to sys.getrefcount
    assert sys.getrefcount(env) == 2


@pytest.fixture
def render_string(env):
    def render_string(s, **kwargs):
        template = env.jinja_env.from_string(s)
        return template.render(**kwargs)

    return render_string


def test_dateformat_filter(render_string):
    tmpl = "{{ dt | dateformat('yyyy-MM-dd') }}"
    dt = datetime.date(2001, 2, 3)
    assert render_string(tmpl, dt=dt) == "2001-02-03"


def test_datetimeformat_filter_not_inlined(pad):
    template = pad.env.jinja_env.from_string("{{ 1678749806 | datetimeformat }}")
    en_date = template.render()
    with lektor.context.Context(pad=pad) as ctx:
        ctx.source = pad.get("/", alt="de")
        de_date = template.render()
    assert en_date != de_date


def test_datetimeformat_filter(render_string):
    tmpl = "{{ dt | datetimeformat('yyyy-MM-ddTHH:mm') }}"
    dt = datetime.datetime(2001, 2, 3, 4, 5, 6)
    assert render_string(tmpl, dt=dt) == "2001-02-03T04:05"


def test_timeformat_filter(render_string):
    tmpl = "{{ dt | datetimeformat('HH:mm') }}"
    dt = datetime.time(1, 2, 3)
    assert render_string(tmpl, dt=dt) == "01:02"


@pytest.fixture(params=["dateformat", "datetimeformat", "timeformat"])
def dates_filter(request: pytest.FixtureRequest) -> str:
    return request.param


def test_dates_format_filter_handles_undefined(
    env: Environment, dates_filter: str
) -> None:
    template = env.jinja_env.from_string("{{ undefined | %s }}" % dates_filter)
    assert template.render() == ""


def test_dates_format_filter_raises_type_error_on_bad_arg(
    env: Environment, dates_filter: str
) -> None:
    template = env.jinja_env.from_string("{{ obj | %s }}" % dates_filter)
    with pytest.raises(TypeError, match="unexpected exception"):
        template.render(obj=object())


def test_dates_format_filter_raises_type_error_on_bad_format(
    env: Environment, dates_filter: str
) -> None:
    template = env.jinja_env.from_string("{{ now | %s(42) }}" % dates_filter)
    with pytest.raises(TypeError, match="should be a str"):
        template.render(now=datetime.datetime.now())


@pytest.mark.parametrize("arg", ["locale", "tzinfo"])
def test_dates_format_filter_raises_type_error_on_bad_kwarg(
    env: Environment, dates_filter: str, arg: str
) -> None:
    template = env.jinja_env.from_string("{{ now | %s(%s=42) }}" % (dates_filter, arg))
    with pytest.raises(TypeError):
        template.render(now=datetime.datetime.now())
