from importlib import import_module
from typing import TYPE_CHECKING

from ._text_source import TextSource

if TYPE_CHECKING:
    from ._clone_prompt import ClonePrompt
    from ._fork_reference import fork_reference
    from ._generate_prepared import generate_prepared
    from ._generation import generate_live
    from ._prepare_clone import prepare_clone
    from ._prepare_reference import prepare_reference
    from ._prepared_reference import PreparedReference

__all__ = [  # noqa: RUF022
    # Text buffering
    "TextSource",
    # Worker-thread generation
    "ClonePrompt",
    "generate_live",
    "prepare_clone",
    # Prepared reference sessions
    "PreparedReference",
    "prepare_reference",
    "fork_reference",
    "generate_prepared",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(name)
    module_map = {
        # Prepared reference sessions
        "PreparedReference": "._prepared_reference",
        "prepare_reference": "._prepare_reference",
        "fork_reference": "._fork_reference",
        "generate_prepared": "._generate_prepared",
        # Prompt schema
        "ClonePrompt": "._clone_prompt",
        # Worker-thread operations
        "generate_live": "._generation",
        "prepare_clone": "._prepare_clone",
    }
    value = getattr(import_module(module_map[name], __name__), name)
    globals()[name] = value
    return value
