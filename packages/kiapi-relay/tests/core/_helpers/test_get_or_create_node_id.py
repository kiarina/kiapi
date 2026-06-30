from pathlib import Path

from kiapi_relay import get_or_create_node_id


def test_generates_and_persists_node_id(tmp_path: Path) -> None:
    node_id = get_or_create_node_id(tmp_path)

    assert node_id
    assert (tmp_path / "node_id").read_text().strip() == node_id


def test_reuses_existing_node_id(tmp_path: Path) -> None:
    first = get_or_create_node_id(tmp_path)
    second = get_or_create_node_id(tmp_path)

    assert first == second


def test_creates_missing_data_dir(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"

    node_id = get_or_create_node_id(nested)

    assert (nested / "node_id").read_text().strip() == node_id
