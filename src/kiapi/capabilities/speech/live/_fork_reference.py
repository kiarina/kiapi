from typing import Any

from ._copy_state import _copy_state
from ._prepared_reference import PreparedReference


def fork_reference(model: Any, prepared: PreparedReference) -> PreparedReference:
    decoder = model.speech_tokenizer.decoder
    decoder.reset_streaming_state()
    modules = dict(decoder.named_modules())
    # mlx-audio wraps decoder in mx.compile; named_modules returns its real root.
    for name, values in prepared.decoder_state.items():
        for key, value in values.items():
            setattr(modules[name], key, _copy_state(value))
    return PreparedReference(
        prepared.prompt,
        _copy_state(prepared.cache),
        prepared.bridge,
        None,
        prepared.prepared_rows,
        prepared.prep_s,
    )
