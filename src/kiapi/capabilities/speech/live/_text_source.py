import threading
from typing import Any


class TextSource:
    def __init__(self, max_chars: int = 4096, idle_timeout: float = 30) -> None:
        self.max_chars = max_chars
        self.idle_timeout = idle_timeout
        self.text = ""
        self.closed = False
        self.cancelled = False
        self.ids: list[int] = []
        self.condition = threading.Condition()
        self.version = 0
        self.tokenizer: Any = None

    def bind(self, tokenizer: Any) -> None:
        self.tokenizer = tokenizer

    def push(self, fragment: str) -> None:
        with self.condition:
            if self.closed or self.cancelled:
                raise ValueError("Text source is no longer writable")
            if len(self.text) + len(fragment) > self.max_chars:
                raise ValueError("Text source character budget exceeded")
            self.text += fragment
            self.version += 1
            self.condition.notify_all()

    def close(self) -> None:
        with self.condition:
            self.closed = True
            self.version += 1
            self.condition.notify_all()

    def is_cancelled(self) -> bool:
        with self.condition:
            return self.cancelled

    def cancel(self) -> None:
        with self.condition:
            self.cancelled = True
            self.version += 1
            self.condition.notify_all()

    def poll(self) -> tuple[list[int], bool, int]:
        with self.condition:
            if self.cancelled:
                raise InterruptedError("Generation canceled")
            text, closed, version = self.text, self.closed, self.version
        pieces = self.tokenizer.backend_tokenizer.pre_tokenizer.pre_tokenize_str(text)
        # BPE merges cannot cross regex pre-token boundaries. Hold the last piece.
        boundary = len(text) if closed else (pieces[-1][1][0] if pieces else 0)
        ids: list[int] = self.tokenizer.encode(
            text[:boundary], add_special_tokens=False
        )
        if ids[: len(self.ids)] != self.ids:
            raise RuntimeError("Tokenizer revised committed prefix")
        self.ids = ids
        return ids, closed, version

    def wait(self, version: int) -> None:
        with self.condition:
            if not self.condition.wait_for(
                lambda: self.version != version or self.cancelled, self.idle_timeout
            ):
                raise TimeoutError("No new text; text.done is required")
