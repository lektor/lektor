def test_custom_attachment_types(env):
    attachment_types = env.load_config().values['ATTACHMENT_TYPES']
    assert attachment_types['.foo'] == 'text'
