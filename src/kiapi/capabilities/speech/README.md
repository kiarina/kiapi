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
| `PATCH /v1/audio/voices/{id}` | Update a voice | Change its name or transcript. |
| `GET /v1/audio/voices/{id}/audio` | Reference audio | The stored reference (24 kHz, 16-bit, mono WAV). |
| `DELETE /v1/audio/voices/{id}` | Delete a voice | Remove a voice and its reference audio. |
| `GET /v1/audio/speech/models` | Model list | Returns a list of available models. |
| `GET /v1/audio/speech/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-audio](https://github.com/Blaizzy/mlx-audio) | MIT | Qwen3-TTS on MLX. Pinned to 0.6.1 (see Notes). |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16) | Apache-2.0 | Not required | 4.5 GB | ~4.6 GB | `qwen3-tts-1.7b` (default, alias `qwen3-tts`). Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, and Italian. |

## Notes

- **Voices**: there are no built-in voices. Register one, then pass its `id` as `voice`.
  The reference is converted to 24 kHz mono, cut to 30 seconds, and kept under
  `speech/voices` in the user data directory (`KIAPI_SPEECH_VOICES_DIR`).
  Without a `name`, the voice is named after the uploaded file (without its
  extension), or after the first 20 characters of its transcript when the audio
  came as a data URL.
  Without a `transcript`, kiapi transcribes the (cut) reference with the
  [transcriptions](../transcriptions/README.md) family and stores that text; the
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
  0.1.1), but mlx-audio 0.6.1 generates voice clones with a repetition penalty of at
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

## Bidirectional speech stream (legacy protocol)

Connect a WebSocket to `/v1/audio/speech/stream`, with the same optional
`Authorization: Bearer <token>` header as HTTP. One connection is one utterance.

1. Send `{"type":"start","voice":"voice_…","language":"ja"}`. Optional
   `model` and integer `seed` select the model and seed.
2. Receive `session.created` with `job_id`, `sample_rate: 24000`, `channels: 1`,
   and `format: "pcm_s16le"`. The job shares the global inference queue.
3. Append `{"type":"text.append","text":"こんにちは。"}` as text arrives.
   Input can arrive while queued or loading. No Japanese separator is needed.
4. `ready` reports `required_prefix_tokens` after clone preparation. Audio may
   still wait for enough committed text; this is reference-dependent.
5. Send `{"type":"text.done"}` when the utterance is complete. Receive binary
   24 kHz mono signed little-endian int16 PCM and finally `{"type":"done",…}`.

`{"type":"cancel"}` requests cancellation and returns `canceled`. Closing the
socket also cancels queued or running work. Discard buffered playback on
interruption. After a terminal event the socket closes; audio never resumes on
that connection. Failures, including failures after audio, return
`{"type":"error","code":"speech_stream_error","message":"…"}`.

A registered voice must have a reference transcript. The input character limit
is shared with HTTP speech. Input inactivity and blocked output time out after
30 seconds. PCM buffering is bounded to eight chunks and applies backpressure
to the single inference worker. Streamed PCM is transient and is not stored as a
Files artifact. The existing full-input HTTP endpoint is unchanged.

The engine implementation and extraction boundary are documented in
[live/README.md](live/README.md).

### Worker ownership (legacy protocol)

An accepted legacy live job holds the single inference worker while waiting for text as
well as while generating audio. Other jobs, including chat, queue behind it.
If the transcript producer waits for a chat/tool request to this same kiapi
instance before sending more text, the requests can wait on each other until
the 30-second input idle limit ends speech. This endpoint does not suspend and
resume the worker between fragments.

Use one connection per assistant response, send `text.done` at response end,
and cancel immediately on interruption. Do not keep a live speech connection
open across turns or across a dependency on another same-instance inference
request. `session.created` means accepted/possibly queued; `ready` means model
and voice preparation finished and text may still be needed before audio.

## Persistent call protocol (version 2)

Set `protocol: 2` in the initial `start` message to prepare the registered full
reference once at call start. `session.created` includes `protocol: 2`; `ready`
arrives after reference text EOS, reference codec EOS and a fresh
role/language/speaker prefix have been prefilled, and the streaming decoder has
been primed with the full reference. `required_prefix_tokens` is 1. The existing
protocol remains available when `protocol` is omitted.

For each response send `utterance.start` with a unique positive uint32
`utterance_id`, followed by `text.append` and `text.done` carrying that same ID.
Every binary message starts with the four-byte little-endian uint32 ID,
followed by 24 kHz mono PCM16LE. `utterance.done` or `utterance.canceled` carries
that ID and leaves the socket open. Send `cancel` with the ID and wait for its
acknowledgment before starting the next response. Old canceled/completed text
is ignored; IDs cannot be reused. Discard playback for canceled IDs. An `error`
is fatal to the session. `session.close` ends the call; disconnect also cancels
outstanding work. There is no input idle timeout between responses; transport
WebSocket ping/pong handles keepalive.

The reference is an immutable snapshot of the voice at session start. Changes
or deletion of that registered voice affect later sessions. GPU snapshots live
in a two-entry model-owned LRU and are independently forked for each utterance;
preceding output never becomes the next reference. Model eviction releases the
cache; later use rebuilds it from the same CPU reference snapshot. Retained GPU
snapshot bytes participate in resident memory accounting.

Preparation and active generation share the single worker. Between utterances,
and after `utterance.start` before the first nonempty `text.append`, the worker
is free for other capabilities. Once generation begins, input waits retain it
with a 30-second timeout. Finish each response with `text.done`, and cancel on
interruption. The full reference is never shortened for low latency. The fresh
boundary is an experimentally verified layout, not an upstream model API.

### Cached short spans

Set `generation: "segments"` in protocol-2 `start`. Require the matching
`generation: "segments"` in `ready` before streaming transcript text. Omitting
this selector retains the existing token-by-token generation mode.

The server commits received punctuation after at least 8 characters for CJK
text, or 14 for Latin text. Without such punctuation, it uses 24 characters for
CJK or six complete whitespace-delimited words for Latin. These thresholds
count received Unicode characters, including spaces. CJK script in the pending
span takes precedence; Latin captions use word boundaries even when the session
language is Japanese. Session language still controls model conditioning.
Periods/commas/colons between digits are not boundaries; a trailing separator
after a digit waits for lookahead or `text.done`. Final nonempty tails flush at
`text.done`; whitespace-only tails produce no audio. Ordinary Japanese/English
inputs preserve the lab's received-punctuation-first policy, so batching and
arrival timing can affect span boundaries.

Every span forks the same prepared full reference and has its own target EOS,
code history and decoder state. It never reuses preceding generated audio as a
reference or repeats speaker extraction/reference prefill. All PCM stays under
the same utterance ID; only completion of the outer input and all spans emits
`utterance.done`. Cancellation interrupts the current span as well as boundary
waits. Span completion is internal: clients buffer/play continuous outer audio
and do not interpret individual spans as turn completion. No initial playback
buffer is added on the server; clients own playout timing.
