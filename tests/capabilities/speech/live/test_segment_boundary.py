import threading

import pytest

from kiapi.capabilities.speech.live import TextSource
from kiapi.capabilities.speech.live._segment_boundary import segment_boundary


def test_lab_plain_japanese_and_english() -> None:
    ja = "うん、今日はいい天気ですね。少し散歩してから、駅前のカフェでコーヒーを飲みませんか\uff1f"
    first = "うん、今日はいい天気ですね。"
    assert segment_boundary(ja, "japanese", False) == len(first)
    tail = ja[len(first) :]
    assert segment_boundary(tail, "japanese", False) == len("少し散歩してから、")
    en = "Tokyo is a busy city with quiet gardens and many small cafes. We can take a short walk and have some tea later."
    assert segment_boundary(en, "english", False) == en.index(".") + 2
    assert segment_boundary(
        "Tokyo is a busy city with quiet", "japanese", False
    ) == len("Tokyo is a busy city with ")


def test_script_and_caps() -> None:
    assert segment_boundary("あ" * 25, "english", False) == 24
    assert segment_boundary("abcdefghijk", "japanese", False) == 0
    assert segment_boundary("Hello、世界ですね。", "english", False) > 0
    assert segment_boundary(
        "  one  two\nthree four five six ", "english", False
    ) == len("  one  two\nthree four five six ")


def test_decimal_and_tiny_tails() -> None:
    assert segment_boundary("The value is 3.14", "japanese", False) == 0
    assert segment_boundary("The value is 3.", "english", False) == 0
    assert segment_boundary("The value is 3.14.", "english", True) == len(
        "The value is 3.14."
    )
    assert segment_boundary("はい", "japanese", False) == 0
    assert segment_boundary("はい", "japanese", True) == 2
    assert segment_boundary("ok", "japanese", True) == 2
    assert segment_boundary(" ", "english", True) == 1
    assert segment_boundary("", "japanese", True) == 0


def test_parent_cancel_releases_wait_without_source_cancel() -> None:
    source = TextSource(idle_timeout=3)
    canceled = threading.Event()
    stopped = threading.Event()

    def wait() -> None:
        with pytest.raises(InterruptedError):
            source.wait(0, cancel_requested=canceled.is_set)
        stopped.set()

    thread = threading.Thread(target=wait)
    thread.start()
    canceled.set()
    assert stopped.wait(0.5)
    thread.join()
