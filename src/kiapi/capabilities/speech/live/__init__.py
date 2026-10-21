from importlib import import_module
from typing import TYPE_CHECKING

from ._text_source import TextSource

if TYPE_CHECKING:
    from ._clone_prompt import ClonePrompt
    from ._generation import generate_live
    from ._prepare_clone import prepare_clone

__all__ = [  # noqa: RUF022
    # Text buffering
    "TextSource",
    # Worker-thread generation
    "ClonePrompt",
    "generate_live",
    "prepare_clone",
]


def __getattr__(name: str) -> object:
    if name not in {"ClonePrompt", "generate_live", "prepare_clone"}:
        raise AttributeError(name)
    module_map = {
        # Prompt schema
        "ClonePrompt": "._clone_prompt",
        # Worker-thread operations
        "generate_live": "._generation",
        "prepare_clone": "._prepare_clone",
    }
    value = getattr(import_module(module_map[name], __name__), name)
    globals()[name] = value
    return value
