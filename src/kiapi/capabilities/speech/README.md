# speech

Text-to-speech in a registered voice, compatible with OpenAI's `audio/speech`.
[Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) 1.7B Base clones the voice from a few
seconds of reference audio and its transcript.

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/audio/speech` | Speech | Speak `input` in a registered voice. Streams PCM while it is generated, or returns one WAV. |
| `POST /v1/audio/voices` | Register a voice | Register reference audio (and its transcript, transcribed when omitted) as a voice. |
| `GET /v1/audio/voices` | Voice list | Registered voices, oldest first. |
| `GET /v1/audio/voices/{id}` | Voice | One registered voice. |
| `DELETE /v1/audio/voices/{id}` | Delete a voice | Remove a voice and its reference audio. |
| `GET /v1/audio/speech/models` | Model list | Returns a list of available models. |
| `GET /v1/audio/speech/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-audio](https://github.com/Blaizzy/mlx-audio) | MIT | Qwen3-TTS on MLX. Pinned to 0.6.0 (see Notes). |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16) | Apache-2.0 | Not required | 4.5 GB | ~4.6 GB | `qwen3-tts-1.7b` (default, alias `qwen3-tts`). Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, and Italian. |

## Notes

- **Voices**: there are no built-in voices. Register one, then pass its `id` as `voice`.
  The reference is converted to 24 kHz mono, cut to 30 seconds, and kept under
  `speech/voices` in the user data directory (`KIAPI_SPEECH_VOICES_DIR`).
  Without a `transcript`, kiapi transcribes the (cut) reference with the
  [transcription](../transcription/README.md) family and stores that text; the
  returned voice shows it, so check it. Set `KIAPI_SPEECH_TRANSCRIBE_REFERENCE=false`
  to turn this off. While the transcription model is not activated the voice is
  registered without a transcript, and is then cloned from the speaker embedding
  only and sounds less like the reference. Only clone voices you have the right
  to use.
- **Streaming**: `response_format: pcm` (default) returns raw 24 kHz, 16-bit, mono,
  little-endian PCM in 0.5-second chunks while it is generated
  (`X-Kiapi-Sample-Rate: 24000`). Closing the connection stops the generation at the
  next chunk. Errors before the first chunk return an HTTP status; after that the
  stream just ends.
- **Queue**: speech shares kiapi's single worker. While another job runs, the request
  waits; time the first chunk on the client and fall back if it is too slow.
- **OpenAI compatibility**: `model`, `input`, `voice`, `response_format` (`pcm`, `wav`),
  and `stream_format: audio` are supported. `speed` must be 1.0 and `instructions`
  must be empty. kiapi adds `language` (BCP 47 or name; omit to detect) and `seed`.
- **mlx-audio patches**: each MLX module matches the PyTorch reference (qwen-tts
  0.1.1), but mlx-audio 0.6.0 generates voice clones with a repetition penalty of at
  least 1.5 over the last 64 tokens and a different prompt layout, and its streaming
  decoder starts without the reference as left context. Listeners heard all three.
  kiapi uses the reference's penalty (1.05 over all tokens) and layout, and primes
  the streaming decoder with the last 12 reference codes (about 1 second,
  `KIAPI_SPEECH_PRIME_TOKENS`). The measurements are in
  [kiarina/labs `japanese-zero-shot-tts-compare`](https://github.com/kiarina/labs/tree/main/2026/10/20/japanese-zero-shot-tts-compare).
  Re-verify before bumping mlx-audio.

## Measured

A 6.6-second reference with its transcript, Japanese sentences of 3.6 to 10.9 seconds,
after the model was loaded (the first request after a load takes 6 to 10 seconds more):

| Measure | Apple M4 Max (over Tailscale) | Apple M1 Max (local) |
|---|---|---|
| First PCM chunk | 0.22 to 0.23 s | 0.37 to 0.38 s |
| Generation time / audio length | 0.30 to 0.32 | 0.52 to 0.56 |
| Resident memory | ~4.3 GB | ~4.9 GB |

## Quickstart

### Register a voice

```bash
curl -s http://localhost:8500/v1/audio/voices \
  -H 'Content-Type: application/json' \
  -d '{
    "audio": {"type": "data_url", "data_url": "data:audio/wav;base64,..."},
    "name": "narrator",
    "transcript": "What the reference says, word for word."
  }'
```

### Stream speech

```bash
curl -sN http://localhost:8500/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"input": "こんにちは。今日はいい天気ですね。", "voice": "voice_0123456789abcdef", "language": "ja"}' \
  | ffplay -f s16le -ar 24000 -ch_layout mono -nodisp -autoexit -
```

### One WAV file

```bash
curl -s http://localhost:8500/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"input": "Hello.", "voice": "voice_0123456789abcdef", "response_format": "wav"}' \
  -o speech.wav
```
