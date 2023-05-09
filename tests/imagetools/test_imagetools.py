from pathlib import Path

import pytest

from lektor.imagetools import compute_dimensions
from lektor.imagetools import get_quality


HERE = Path(__file__).parent
EXAMPLE = HERE / "../../example"


def test_compute_dimensions():
    assert compute_dimensions(10, 10, 200, 100) == (10, 5)


@pytest.mark.parametrize(
    "image, expected",
    [
        (HERE / "exif-test-1.jpg", 85),
        (EXAMPLE / "content/logo.png", 75),
    ],
)
def test_get_quality(image, expected):
    with pytest.deprecated_call():
        assert get_quality(image) == expected
