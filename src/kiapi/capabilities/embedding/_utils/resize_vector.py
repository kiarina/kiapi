import math


def resize_vector(vector: list[float], dimensions: int | None) -> list[float]:
    if dimensions is None:
        return vector

    resized = vector[:dimensions]
    norm = math.sqrt(sum(value * value for value in resized))
    return [value / norm for value in resized] if norm else resized
