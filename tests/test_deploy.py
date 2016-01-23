def test_get_server(env):
    server = env.load_config().get_server('production')
    assert server.name == 'Production'
    assert server.name_i18n['de'] == 'Produktion'
    assert server.target == 'rsync://myserver.com/path/to/website'
    assert server.extra == {'extra_field': 'extra_value'}
