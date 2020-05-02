def test_jinja2_extensions(env):
    extensions = env.jinja_env.extensions

    assert 'jinja2.ext.DebugExtension' in extensions.keys()
    assert 'jinja2.ext.ExprStmtExtension' in extensions.keys()
    assert 'jinja2.ext.LoopControlExtension' in extensions.keys()
