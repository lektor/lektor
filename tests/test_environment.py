import sys


def test_jinja2_extensions(env):
    extensions = env.jinja_env.extensions

    assert "jinja2.ext.AutoEscapeExtension" in extensions.keys()
    assert "jinja2.ext.WithExtension" in extensions.keys()
    assert "jinja2.ext.ExprStmtExtension" in extensions.keys()


def test_no_reference_cycle_in_environment(project):
    env = project.make_env(load_plugins=False)
    # reference count should be two: one from our `env` variable, and
    # another from the argument to sys.getrefcount
    assert sys.getrefcount(env) == 2
