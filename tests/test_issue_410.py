"""Test for issue `#410`_.

This tests for at least one of the bugs reported in `#410`_, namely
 that paginated pages were not being built if they had no children.

.. _#410: https://github.com/lektor/lektor/issues/410

"""
import os

import pytest


@pytest.fixture(
    params=[
        pytest.param(True, id="paginated"),
        pytest.param(False, id="non-paginated"),
    ]
)
def scratch_project_data(scratch_project_data, request):
    # Specialize the inherited scratch project (from conftest.py)
    # by (possibly) enabling pagination for models/page.ini.
    is_paginated = request.param
    page_ini = scratch_project_data / "models/page.ini"
    if is_paginated:
        page_ini.write_text(
            "\n".join(
                [
                    page_ini.read_text("utf-8"),
                    "[pagination]",
                    "enabled = yes",
                    "",
                ]
            ),
            "utf-8",
        )
    return scratch_project_data


def test_build_childless_page(scratch_builder):
    # Test that a basic childless page gets built (whether it is
    # paginated or not)
    scratch_builder.build_all()
    index_html = os.path.join(scratch_builder.destination_path, "index.html")
    assert os.path.exists(index_html)
