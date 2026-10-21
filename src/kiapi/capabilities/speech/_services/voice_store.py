"""Registered voices on disk: ``<root>/<id>/reference.wav`` and ``voice.json``."""

import json
import secrets
import shutil
import time
from pathlib import Path

from kiapi.capabilities import ValidationError

from .._views.voice import Voice

SAMPLE_RATE = 24_000


class VoiceNotFoundError(KeyError):
    pass


class VoiceStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create(
        self,
        source: Path,
        *,
        name: str | None,
        transcript: str | None,
        min_seconds: float,
        max_seconds: float,
    ) -> Voice:
        import numpy as np
        import soundfile as sf  # type: ignore
        from mlx_audio.utils import load_audio  # type: ignore

        try:
            audio = np.array(
                load_audio(str(source), sample_rate=SAMPLE_RATE, duration=max_seconds)
            )
        except Exception as exc:
            raise ValidationError(f"could not read the reference audio: {exc}") from exc
        if audio.ndim > 1:
            audio = audio.mean(axis=-1)
        duration = len(audio) / SAMPLE_RATE
        if duration < min_seconds:
            raise ValidationError(
                f"reference audio is {duration:.2f}s; it must be at least {min_seconds}s"
            )

        voice = Voice(
            id=f"voice_{secrets.token_hex(8)}",
            name=name or None,
            transcript=(transcript or "").strip() or None,
            duration_s=round(duration, 3),
            created_at=int(time.time()),
        )
        directory = self.root / voice.id
        directory.mkdir(parents=True)
        sf.write(directory / "reference.wav", audio, SAMPLE_RATE, subtype="PCM_16")
        (directory / "voice.json").write_text(voice.model_dump_json(indent=2))
        return voice

    def set_transcript(self, voice_id: str, transcript: str) -> Voice:
        voice = self.get(voice_id).model_copy(
            update={"transcript": transcript.strip() or None}
        )
        path = self._directory(voice_id) / "voice.json"
        path.write_text(voice.model_dump_json(indent=2))
        return voice

    def get(self, voice_id: str) -> Voice:
        path = self._directory(voice_id) / "voice.json"
        if not path.is_file():
            raise VoiceNotFoundError(voice_id)
        return Voice.model_validate(json.loads(path.read_text()))

    def reference_path(self, voice_id: str) -> Path:
        self.get(voice_id)
        return self._directory(voice_id) / "reference.wav"

    def list(self) -> list[Voice]:
        if not self.root.is_dir():
            return []
        voices = []
        for path in self.root.glob("*/voice.json"):
            voices.append(Voice.model_validate(json.loads(path.read_text())))
        return sorted(voices, key=lambda v: v.created_at)

    def delete(self, voice_id: str) -> None:
        self.get(voice_id)
        shutil.rmtree(self._directory(voice_id))

    def _directory(self, voice_id: str) -> Path:
        # Ids are generated here; anything else cannot name a stored voice.
        if not voice_id.startswith("voice_") or not voice_id[6:].isalnum():
            raise VoiceNotFoundError(voice_id)
        return self.root / voice_id
