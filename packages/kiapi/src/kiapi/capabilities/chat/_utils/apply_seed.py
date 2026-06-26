"""Seed MLX's RNG for a reproducible generation (no-op when ``seed`` is None)."""


def apply_seed(seed: int | None) -> None:
    if seed is not None:
        import mlx.core as mx

        mx.random.seed(seed)
