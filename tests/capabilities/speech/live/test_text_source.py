import threading
from types import SimpleNamespace

import pytest

from kiapi.capabilities.speech.live import TextSource


def source() -> TextSource:
    value = TextSource(max_chars=12, idle_timeout=0.05)
    value.bind(
        SimpleNamespace(
            backend_tokenizer=SimpleNamespace(
                pre_tokenizer=SimpleNamespace(
                    pre_tokenize_str=lambda text: [
                        (c, (i, i + 1)) for i, c in enumerate(text)
                    ]
                )
            ),
            encode=lambda text, **kwargs: [ord(c) for c in text],
        )
    )
    return value


def test_hold_last_japanese_piece_until_done() -> None:
    value = source()
    value.push("あいう")
    assert value.poll()[0] == [ord("あ"), ord("い")]
    value.push("え")
    assert value.poll()[0] == [ord(c) for c in "あいう"]
    value.close()
    assert value.poll()[:2] == ([ord(c) for c in "あいうえ"], True)
    with pytest.raises(ValueError):
        value.push("お")


def test_cancel_releases_wait() -> None:
    value = source()
    waiter = threading.Thread(target=lambda: value.wait(0))
    waiter.start()
    value.cancel()
    waiter.join(timeout=1)
    assert not waiter.is_alive()
    with pytest.raises(InterruptedError):
        value.poll()


def test_limits_and_idle_timeout() -> None:
    value = source()
    with pytest.raises(ValueError):
        value.push("a" * 13)
    with pytest.raises(TimeoutError):
        value.wait(0)
