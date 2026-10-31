import base64
import struct


def encode_vector(vector: list[float]) -> str:
    return base64.b64encode(struct.pack(f"<{len(vector)}f", *vector)).decode("ascii")
