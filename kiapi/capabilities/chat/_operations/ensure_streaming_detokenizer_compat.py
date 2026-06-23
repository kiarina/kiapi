"""Compatibility patch for mlx-vlm's BPE streaming detokenizer.

mlx-vlm 0.6.1's BPEStreamingDetokenizer decodes buffered bytes with strict
UTF-8 in ``add_token``. Some generations can produce byte-token sequences that
are not valid UTF-8 at that flush boundary, which crashes streaming responses.
``finalize`` already handles the same decode leniently; this patch makes the
streaming path equally tolerant.
"""

from typing import Any

_PATCH_FLAG = "_kiapi_utf8_tolerant_add_token"


def ensure_streaming_detokenizer_compat() -> None:
    """Patch mlx-vlm's BPE streaming detokenizer once, if available."""
    try:
        from mlx_vlm.tokenizer_utils import (  # type: ignore[import-untyped]
            BPEStreamingDetokenizer,
            _remove_space,
        )
    except Exception:
        return

    if getattr(BPEStreamingDetokenizer, _PATCH_FLAG, False):
        return

    def add_token(
        self: Any,
        token: int,
        skip_special_token_ids: list[int] | None = None,
    ) -> None:
        if skip_special_token_ids is not None and token in skip_special_token_ids:
            return
        v = self.tokenmap[token]
        if self._byte_decoder[v[0]] == 32:
            current_text = bytearray(
                self._byte_decoder[c] for c in self._unflushed
            ).decode("utf-8", errors="replace")
            if self.text or not self.trim_space:
                self.text += current_text
            else:
                self.text += _remove_space(current_text)
            self._unflushed = v
        else:
            self._unflushed += v

    BPEStreamingDetokenizer.add_token = add_token
    setattr(BPEStreamingDetokenizer, _PATCH_FLAG, True)
