import copy
import importlib
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from kiapi.capabilities.speech.live._clone_prompt import ClonePrompt
from kiapi.capabilities.speech.live._prepared_reference import PreparedReference


def test_fork_restores_underlying_compiled_decoder_and_copies_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_copy = SimpleNamespace(_copy_state=copy.deepcopy)
    monkeypatch.setitem(
        sys.modules, "kiapi.capabilities.speech.live._copy_state", fake_copy
    )
    sys.modules.pop("kiapi.capabilities.speech.live._fork_reference", None)
    fork = importlib.import_module(
        "kiapi.capabilities.speech.live._fork_reference"
    ).fork_reference
    root = SimpleNamespace(_transformer_cache=None)

    class CompiledDecoder:
        __slots__ = ()

        def reset_streaming_state(self) -> None:
            root._transformer_cache = None

        def named_modules(self) -> Any:
            return [("", root)]

    model = SimpleNamespace(speech_tokenizer=SimpleNamespace(decoder=CompiledDecoder()))
    snapshot = PreparedReference(
        ClonePrompt(None, [], None, None, None, None),
        [{"keys": [1, 2]}],
        None,
        {"": {"_transformer_cache": [{"keys": [3, 4]}]}},
        12,
        0.1,
    )
    first = fork(model, snapshot)
    first.cache[0]["keys"].append(9)
    root._transformer_cache[0]["keys"].append(8)
    second = fork(model, snapshot)
    assert second.cache == [{"keys": [1, 2]}]
    assert root._transformer_cache == [{"keys": [3, 4]}]
    assert snapshot.decoder_state == {"": {"_transformer_cache": [{"keys": [3, 4]}]}}
