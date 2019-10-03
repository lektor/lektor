def test_jinja2_extensions(env):
    extensions = env.jinja_env.extensions

    assert "jinja2.ext.AutoEscapeExtension" in extensions.keys()
    assert "jinja2.ext.WithExtension" in extensions.keys()
    assert "jinja2.ext.ExprStmtExtension" in extensions.keys()
