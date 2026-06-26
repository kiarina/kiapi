"""ACE-Step generate (text2music) request model."""

from pydantic import Field

from .ace_step_base import AceStepBase


class GenerateRequest(AceStepBase):
    prompt: str = Field(
        default="Modern J-Pop, 132 BPM, bright piano, emotional electric guitar, upbeat drums",
        description=(
            "Music style description — the SOUND (genre, tempo, instruments, mood, "
            "production), not the lyric content. A narrative sentence works better "
            "than a keyword list."
        ),
    )
    lyrics: str = Field(
        default="[Instrumental]",
        description=(
            "Lyrics, using [Verse 1]/[Chorus]/[Bridge]/… section tags at the start "
            "of a line. Use `[Instrumental]` for a fully instrumental output. Match "
            "the lyric length to `duration` — sparse lyrics over a long duration hurt "
            "quality."
        ),
    )
    duration: int = Field(
        default=60,
        ge=5,
        le=300,
        description=(
            "Output length in seconds (5-300). Also capped server-side by the "
            "acestep `max_duration` setting (422 if exceeded)."
        ),
    )
    lang: str = Field(
        default="ja",
        description=(
            "Vocal language as an ISO 639-1 code: ja / en / ko / zh / yue / es / fr / "
            "de / …. `unknown` auto-detects (may reduce quality). Ignored for "
            "`[Instrumental]` lyrics."
        ),
    )

    def gen_params(self) -> dict:
        return {
            "prompt": self.prompt,
            "lyrics": self.lyrics,
            "duration": self.duration,
            "lang": self.lang,
            "seed": self.seed,
            "inference_steps": self.inference_steps,
            "guidance_scale": self.guidance_scale,
            "shift": self.shift,
        }
