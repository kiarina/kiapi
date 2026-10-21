DESCRIPTION = """Speech-to-text (OpenAI `audio/transcriptions` compatible).

Send the audio as `multipart/form-data` with a `file` field, as the OpenAI SDKs
do (`client.audio.transcriptions.create(file=..., model="qwen3-asr-1.7b")`).
The language is detected unless `language` is given.

`response_format: verbose_json` adds the language, the duration, and sentence
`segments` timed by Qwen3-ForcedAligner; `timestamp_granularities[]=word` adds
`words`. Audio in a language the aligner does not cover gets one segment per
decoded part instead.

Requests share kiapi's single worker with every other capability: a long file
makes other requests wait, so audio is capped at
`KIAPI_TRANSCRIPTIONS_MAX_AUDIO_SECONDS` (default 3600).

## Upstream docs
- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) — the model family
- [mlx-audio](https://github.com/Blaizzy/mlx-audio) — the MLX implementation

## Models
- **qwen3-asr-1.7b** (default, alias `qwen3-asr`) —
  `mlx-community/Qwen3-ASR-1.7B-bf16`, Apache-2.0, with
  `mlx-community/Qwen3-ForcedAligner-0.6B-bf16` (Apache-2.0) for timestamps.
  Transcribes 30 languages; timestamps cover Chinese, Cantonese, English,
  German, Spanish, French, Italian, Portuguese, Russian, Korean, and Japanese.

Discover models at `GET /v1/audio/transcriptions/models`.

## Tips
- Put names and terms the audio may contain in `prompt`.
- Give `language` when you know it: detection reads each part on its own.
"""
