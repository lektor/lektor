import os
import sys
from xml.sax.saxutils import unescape

import pytest


@pytest.fixture
def compile_template(scratch_env):
    def compile_template(source, name="tmpl.html"):
        path = os.path.join(scratch_env.root_path, "templates", name)
        with open(path, "w") as fp:
            fp.write(source)
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
