from pathlib import Path

import pytest

from kiapi.capabilities import CapabilityError
from kiapi.capabilities.embedding._operations.parse_inputs import parse_inputs


def test_text_passes_through(tmp_path: Path) -> None:
    assert parse_inputs({"text": "a"}, tmp_path, allow={"text"}) == {"text": "a"}


def test_rejects_empty_text(tmp_path: Path) -> None:
    with pytest.raises(CapabilityError, match="empty input"):
        parse_inputs({"text": ""}, tmp_path, allow={"text"})


def test_rejects_empty_item(tmp_path: Path) -> None:
    with pytest.raises(CapabilityError, match="item is empty"):
        parse_inputs({}, tmp_path, allow={"text"})


def test_rejects_unsupported_modality(tmp_path: Path) -> None:
    with pytest.raises(CapabilityError, match="not supported"):
        parse_inputs({"image": "aGk="}, tmp_path, allow={"text"})
