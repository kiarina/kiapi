import base64
import struct

import pytest

from kiapi.capabilities.embedding._utils.encode_vector import encode_vector


def test_encode_is_little_endian_float32() -> None:
    decoded = base64.b64decode(encode_vector([0.25, -1.5]))

    assert struct.unpack("<2f", decoded) == pytest.approx((0.25, -1.5))
