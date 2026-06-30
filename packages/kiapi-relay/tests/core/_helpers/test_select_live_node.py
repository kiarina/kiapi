from kiapi_relay.core._helpers.select_live_node import select_live_node


def test_picks_most_recent_node_within_ttl() -> None:
    entries = {
        "old": {"ts": 100.0},
        "new": {"ts": 150.0},
    }

    assert select_live_node(entries, ttl_s=100.0, now=200.0) == "new"


def test_ignores_nodes_outside_ttl() -> None:
    entries = {
        "stale": {"ts": 10.0},
        "fresh": {"ts": 190.0},
    }

    assert select_live_node(entries, ttl_s=60.0, now=200.0) == "fresh"


def test_returns_none_when_all_stale() -> None:
    entries = {"stale": {"ts": 10.0}}

    assert select_live_node(entries, ttl_s=60.0, now=200.0) is None


def test_skips_malformed_records() -> None:
    entries = {
        "missing-ts": {},
        "not-a-dict": "nope",
        "bool-ts": {"ts": True},
        "good": {"ts": 190.0},
    }

    assert select_live_node(entries, ttl_s=60.0, now=200.0) == "good"


def test_returns_none_for_non_dict_input() -> None:
    assert select_live_node(None, ttl_s=60.0) is None
