import pytest

from kiapi.capabilities.embedding._utils.resize_vector import resize_vector


def test_resize_keeps_vector_without_dimensions() -> None:
    assert resize_vector([0.6, 0.8], None) == [0.6, 0.8]


def test_resize_truncates_and_normalizes() -> None:
    assert resize_vector([3.0, 4.0, 12.0], 2) == pytest.approx([0.6, 0.8])


def test_resize_keeps_zero_vector() -> None:
    assert resize_vector([0.0, 0.0, 1.0], 2) == [0.0, 0.0]
