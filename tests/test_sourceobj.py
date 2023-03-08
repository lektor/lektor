import pytest


@pytest.mark.parametrize(
    "key1, key2, is_eq",
    [
        ({"path": "/"}, {"path": "/"}, True),
        ({"path": "/"}, {"path": "/", "alt": "en"}, True),
        ({"path": "/"}, {"path": "/blog"}, False),
        ({"path": "/blog/post1"}, {"path": "/blog/post1@siblings"}, False),
        ({"path": "/"}, {"path": "/", "page_num": 1}, False),
        ({"path": "/"}, {"path": "/", "alt": "de"}, False),
        ({"path": "/", "alt": "en"}, {"path": "/", "alt": "de"}, False),
    ],
)
def test_records_eq(pad, key1, key2, is_eq):
    r1 = pad.get(**key1)
    pad.cache.flush()
    r2 = pad.get(**key2)
    if is_eq:
        assert r1 == r2
        assert hash(r1) == hash(r2)
    else:
        assert r1 != r2


def test_records_from_different_pads_ne(env):
    pad1 = env.new_pad()
    pad2 = env.new_pad()
    assert pad1.get("/") == pad1.get("/")
    assert pad1.get("/") != pad2.get("/")


def test_asset_ne_record(pad):
    record = pad.get("/")
    asset = pad.get_asset("/")
    assert record != asset
    assert asset != record
