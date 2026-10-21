from dataclasses import dataclass
from typing import Any


@dataclass
class ClonePrompt:
    prefix: Any
    ref_text_ids: list[int]
    ref_codes: Any
    codec_embeds: Any
    pad: Any
    eos: Any

    @property
    def required_prefix_tokens(self) -> int:
        return max(0, int(self.codec_embeds.shape[1]) - len(self.ref_text_ids))
