from importlib import import_module
from typing import TYPE_CHECKING

from ._text_source import TextSource

if TYPE_CHECKING:
    from ._generation import ClonePrompt, generate_live, prepare_clone

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
    value = getattr(import_module("._generation", __name__), name)
    globals()[name] = value
    return value
