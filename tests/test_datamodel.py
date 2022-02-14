# -*- coding: utf-8 -*-
import re

import pytest

from lektor.datamodel import ChildConfig
from lektor.datamodel import DataModel
from lektor.datamodel import PaginationConfig
from lektor.reporter import BufferReporter


@pytest.fixture
def slug_format():
    return None


@pytest.fixture
def datamodel(env, slug_format):
    id_ = "test"
    name_i18n = {"en": "test"}
    child_config = ChildConfig(slug_format=slug_format)
    return DataModel(env, id_, name_i18n, child_config=child_config)


@pytest.mark.parametrize(
    "per_page, expected",
    [
        (-1, ValueError),
        (-1.5, TypeError),
        ("5", TypeError),
    ],
)
def test_PaginationConfig_init_raises_on_invalid_per_page(env, per_page, expected):
    with pytest.raises(expected):
        PaginationConfig(env, per_page=per_page)


@pytest.mark.parametrize(
    "slug_format, expected_slug",
    [
        (None, "child-id"),
        ("fmt-{{ this._id }}", "fmt-child-id"),
        ("{{ unknown.attr }}", "temp-child-id"),
    ],
)
def test_get_default_child_slug(datamodel, pad, expected_slug):
    data = {
        "_id": "child-id",
    }
    assert datamodel.get_default_child_slug(pad, data) == expected_slug


@pytest.mark.parametrize("slug_format", ["{{ unknown.attr }}"])
def test_get_default_child_slug_reports_failure(datamodel, pad):
    data = {"_id": "id"}
    with BufferReporter(pad.env) as reporter:
        assert datamodel.get_default_child_slug(pad, data) == "temp-id"
    _, event_data = reporter.buffer[-1]
    message = event_data["message"]
    assert re.search(r"failed to expand\b.*\bslug_format\b", message, re.I)
