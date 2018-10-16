from lektor.db import DatabaseCache


def test_custom_attachment_types(env):
    attachment_types = env.load_config().values['ATTACHMENT_TYPES']
    assert attachment_types['.foo'] == 'text'


def test_database_cache_disabled_ondefault(env):
    enabled = DatabaseCache.is_cache_enabled(env)
    assert enabled is False
    assert DatabaseCache._cache_datamodels is None
