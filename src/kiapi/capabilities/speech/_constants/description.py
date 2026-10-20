DESCRIPTION = """Text-to-speech in a registered voice (OpenAI `audio/speech` compatible).

Register a voice once from a few seconds of reference audio and its transcript
(`POST /v1/audio/voices`), then pass its id as `voice` to `POST /v1/audio/speech`.
The speech clones that voice: there are no built-in voices.

`response_format: pcm` (default) streams raw 24 kHz, 16-bit, mono, little-endian
PCM while it is generated, so playback can start on the first chunk (about half a
second on Apple M1 Max). `wav` returns one file when generation finishes. Closing
the connection stops the generation.

Requests share kiapi's single worker with every other capability: while another
job runs, speech waits for it.

## Upstream docs
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) — the model family
- [mlx-audio](https://github.com/Blaizzy/mlx-audio) — the MLX implementation

## Models
- **qwen3-tts-1.7b** (default, alias `qwen3-tts`) —
  `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16`, Apache-2.0. Speaks Chinese,
  English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, and
  Italian.

Discover models at `GET /v1/audio/speech/models`.

## Voice Tips
- Use 5 to 15 seconds of one clear speaker, without music or noise.
- Give the transcript word for word. Without it the voice is cloned from the
  speaker embedding only and sounds less like the reference.
- Only clone voices you have the right to use.
"""
