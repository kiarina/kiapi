type FrameworkName = str
"""The backend that owns a model's memory and knows how to measure/free it —
``"mlx"`` (Metal allocator) or ``"rss"`` (framework-agnostic process-RSS
fallback). Matches :class:`ModelSpec.framework`; selects a FrameworkStrategy."""
