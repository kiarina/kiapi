# transcription

Speech-to-text, compatible with OpenAI's `audio/transcriptions`.
[Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) 1.7B transcribes 30 languages and
detects the language; Qwen3-ForcedAligner 0.6B times sentences and words.

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/audio/transcriptions` | Transcription | Transcribe an uploaded audio file (`multipart/form-data`). |
| `GET /v1/audio/transcriptions/models` | Model list | Returns a list of available models. |
| `GET /v1/audio/transcriptions/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-audio](https://github.com/Blaizzy/mlx-audio) | MIT | Qwen3-ASR and Qwen3-ForcedAligner on MLX. Pinned to 0.6.0 by the speech family. |
| [nagisa](https://github.com/taishi-i/nagisa) | MIT | Splits Japanese into words for the aligner. |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [mlx-community/Qwen3-ASR-1.7B-bf16](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-bf16) + [mlx-community/Qwen3-ForcedAligner-0.6B-bf16](https://huggingface.co/mlx-community/Qwen3-ForcedAligner-0.6B-bf16) | Apache-2.0 | Not required | 5.9 GB | ~5.5 GB | `qwen3-asr-1.7b` (default, alias `qwen3-asr`). Both models load together. |

## Notes

- **OpenAI compatibility**: `file`, `model`, `language`, `prompt`,
  `response_format` (`json`, `text`, `verbose_json`), `temperature`, and
  `timestamp_granularities[]` (`segment`, `word`) are supported. `srt`, `vtt`,
  `diarized_json`, `stream`, `include[]` (logprobs), and `chunking_strategy` are
  not. `model` must be a kiapi model (omit it for the default), not `whisper-1`.
  `language` also takes names and BCP 47 tags (`japanese`, `ja-JP`).
- **verbose_json**: `segments` are sentences timed by the aligner, and carry
  only `id`, `start`, `end`, and `text` (no `tokens` or log-probabilities).
  `words` have no punctuation; Japanese and Chinese words are dictionary words or
  characters. The aligner covers Chinese, Cantonese, English, German, Spanish,
  French, Italian, Portuguese, Russian, Korean, and Japanese; other languages get
  one segment per decoded part, and asking them for `word` is an error.
- **Long audio**: audio is cut at a quiet point every 3 minutes
  (`KIAPI_TRANSCRIPTION_CHUNK_SECONDS`; `verbose_json` uses at most 5, the
  aligner's limit), and each part is transcribed and its language detected on
  its own. Qwen3-ASR takes up to 20 minutes at once, but memory and time grow
  with the length (see Measured).
- **Queue**: transcription shares kiapi's single worker and has no streaming,
  so a long file holds up every other request until it is done. Uploads are
  capped at 100 MB (`KIAPI_TRANSCRIPTION_MAX_FILE_MB`) and one hour of audio
  (`KIAPI_TRANSCRIPTION_MAX_AUDIO_SECONDS`). A file that takes longer than
  `KIAPI_SYNC_TIMEOUT_S` (default 600 seconds) returns 504 while the job keeps
  running; its result (`text`, `segments`, `words`) is then in `GET /v1/jobs/{id}`.
- **Voices**: the speech family uses this family to transcribe a voice
  reference registered without a transcript.

## Measured

Apple M1 Max, Japanese speech, after the model was loaded (loading takes about
6 seconds):

| Audio | Format | Time | Time / audio length | Peak over the weights |
|---|---|---:|---:|---:|
| 14 s conversation | `json` | 1.1 s | 0.08 | 1.1 GB |
| 14 s conversation | `verbose_json` + words | 2.1 s | 0.15 | — |
| 3 min | `json` | 68 s | 0.37 | 2.3 GB |
| 3 min | `verbose_json` + words | 74 s | 0.40 | 2.3 GB |
| 20 min in one chunk | `json` | 667 s | 0.55 | 11.4 GB |

The last row is why the chunk is 3 minutes. Resident memory is about 5.5 GB.

## Quickstart

### curl

```bash
curl -s http://localhost:8500/v1/audio/transcriptions \
  -F file=@meeting.m4a \
  -F language=ja
```

```bash
curl -s http://localhost:8500/v1/audio/transcriptions \
  -F file=@meeting.m4a \
  -F response_format=verbose_json \
  -F 'timestamp_granularities[]=segment' \
  -F 'timestamp_granularities[]=word'
```

### OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8500/v1", api_key="unused")
with open("meeting.m4a", "rb") as f:
    result = client.audio.transcriptions.create(
        model="qwen3-asr-1.7b", file=f, language="ja"
    )
print(result.text)
```
