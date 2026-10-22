from dataclasses import dataclass
from typing import Any

from ._clone_prompt import ClonePrompt


@dataclass(frozen=True)
class PreparedReference:
    prompt: ClonePrompt
    cache: Any
    bridge: Any
    decoder_state: Any
    prepared_rows: int
    prep_s: float
    required_tokens: int = 1
