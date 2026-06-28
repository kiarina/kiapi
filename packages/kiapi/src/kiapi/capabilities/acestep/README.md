# acestep

**English** | [日本語](README.ja.md)

[ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) provides the following functions.
- Music generation
- Style conversion of existing songs
- Regenerate part of a song
- Sound source separation

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/audio/acestep/generate` | Music generation | Generate a song by specifying prompt, poem, time, and language. |
| `POST /v1/audio/acestep/cover` | Style conversion | Convert an existing song to a different style while preserving its structure. |
| `POST /v1/audio/acestep/repaint` | Partial regeneration | Regenerate the time range of the song. |
| `POST /v1/audio/acestep/extract` | Sound source separation | Separate the sound sources such as vocals and drums of a song. |
| `GET /v1/audio/acestep/models` | Model list | Returns a list of available models. |
| `GET /v1/audio/acestep/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/audio/acestep/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/audio/acestep/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/audio/acestep/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [ace-step](https://github.com/ace-step/ACE-Step-1.5) | MIT | ACE-Step 1.5 main body. |
| [transformers](https://github.com/huggingface/transformers) | Apache-2.0 | 4.x version required by ace-step. |
| [PyTorch](https://github.com/pytorch/pytorch) | BSD-3-Clause | Introduced as a dependency of ace-step. |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [ACE-Step/acestep-v15-xl-base](https://huggingface.co/ACE-Step/acestep-v15-xl-base) | MIT | Not required | 19 GB | ~33 GB | `xl-base` (default). 32 steps / `guidance_scale=7.0`, highest quality. Approximately 25 seconds with 30 seconds of audio (M4 Max). |
| [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) | MIT | Not required | 9.4 GB | ~16 GB | In addition to `turbo` (8 steps, ignoring `guidance_scale`) DiT, 5Hz LM, VAE, and Qwen3-Embedding-0.6B are included. Focusing on speed, 15 seconds is about 4 seconds (M4 Max). |
| [Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | Apache-2.0 | Not required | 1.1 GB | — (bundled) | Text encoder. Included with ACE-Step/Ace-Step1.5. |

## Notes

- **Isolation of transformers 4.x**:
  ACE-Step 1.5 pins **transformers 4.x** and conflicts with **transformers 5.x**, which requires the entire stack.
  Therefore, ace-step is executed as a subprocess in a dedicated **venv**.
  The main process does not import `acestep`.
- **Local placement**:
  `KIAPI_ACESTEP_PYTHON_PATH`, `KIAPI_ACESTEP_PROJECT_ROOT`, `KIAPI_ACESTEP_CHECKPOINT_DIR`
  If is not specified, venv / project / checkpoints for ACE-Step is
  Place it in `acestep/` under the user data dir of `core/app`.
- **IPC**:
  The main process communicates with workers using a small line-oriented JSON protocol on stdin/stdout.
  Prefix each line with `@@KIAPI@@` sentinel. Other stdout is treated as noise.
  In addition, audio I/O is exchanged using file paths.
  The progress callback is forwarded to the job's `ProgressReporter`.

## Quickstart

### generate - music generation
```bash
jq -n \
--arg prompt "Modern J-Pop, 132 BPM, bright piano, emotional electric guitar, upbeat drums" \
--arg lyrics '[Verse 1]
加速する世界の中で
君の声が聴こえてくる

[Chorus]
僕らは光を追いかける
終わらない夢の向こうへ
' \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  lyrics: $lyrics,
  duration: 30,
  lang: "ja",
  seed: 1
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/acestep/generate \
-H 'Content-Type: application/json' \
--data-binary @- \
-o song.wav
```
### cover - style conversion
```bash
SRC=$(
curl -sS -X POST http://localhost:${PORT:-8000}/v1/files -F "file=@song.wav" |
jq -r .file_id
)

jq -n \
--arg src "$SRC" \
--arg prompt "City Pop, groovy bass, smooth guitar, laid-back 80s production" \
'{
  model: "turbo",
  mode: "sync",
  source: {type: "file_id", file_id: $src},
  prompt: $prompt,
  strength: 0.7,
  seed: 1
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/acestep/cover \
-H 'Content-Type: application/json' \
--data-binary @- \
-o cover.wav
```
`strength`: 0.3 = loose reinterpretation. 0.7 = Change style while keeping composition. 1.0 = strict.

### repaint - regenerate time range
```bash
SRC=$(
curl -sS -X POST http://localhost:${PORT:-8000}/v1/files -F "file=@song.wav" |
jq -r .file_id
)

jq -n \
--arg src "$SRC" \
--arg prompt "Dramatic orchestral strings, emotional swell, cinematic" \
'{
  model: "turbo",
  mode: "sync",
  source: {type: "file_id", file_id: $src},
  prompt: $prompt,
  start: 15,
  end: 30,
  strength: 0.6,
  seed: 1
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/acestep/repaint \
-H 'Content-Type: application/json' \
--data-binary @- \
-o repainted.wav
```
`start`/`end` is in seconds (`end: -1` = until the end).

### extract - sound source separation
```bash
SRC=$(
curl -sS -X POST http://localhost:${PORT:-8000}/v1/files -F "file=@song.wav" |
jq -r .file_id
)

RESP=$(
jq -n \
--arg src "$SRC" \
'{
  model: "turbo",
  mode: "sync",
  source: {type: "file_id", file_id: $src},
  targets: ["vocals", "drums", "bass", "other"]
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/acestep/extract \
-H 'Content-Type: application/json' \
-H 'Accept: application/json' \
--data-binary @-
)

# 各音源をダウンロード（stems[] にターゲット名が入る）
echo "$RESP" | jq -c '.result.stems[]' | while read -r s; do
  TARGET=$(echo "$s" | jq -r .target); FID=$(echo "$s" | jq -r .file_id)
  curl -o "${TARGET}.wav" http://localhost:${PORT:-8000}/v1/files/$FID/download
done
```
