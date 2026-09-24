"""Raise this process's open-file soft limit.

mlx-vlm's memory-mapped PLE storage keeps every PLE shard open (128 for
Qwen3.8-Flash-Next), which exceeds the macOS default soft limit of 256 together
with the server's own descriptors (``OSError: [Errno 24] Too many open files``).
"""

import logging
import resource

logger = logging.getLogger(__name__)


def raise_open_file_limit(minimum: int = 65536) -> None:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    target = minimum if hard == resource.RLIM_INFINITY else min(minimum, hard)
    if soft == resource.RLIM_INFINITY or soft >= target:
        return
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
    except (ValueError, OSError) as exc:
        logger.warning("could not raise open-file limit to %d: %s", target, exc)
