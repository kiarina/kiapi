# ltx2

**English** | [日本語](README.ja.md)

[mlx-video LTX-2](https://github.com/Blaizzy/mlx-video) provides short video generation functionality.

- **T2V**: Generate video from text
- **I2V**: animate image as first or last frame
- **A2V**: Drive motion and timing with voice
- **T2V + Audio**: Generate audio along with video

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/video/ltx2/generate` | Video generation | Generate MP4 from JSON body and any `image` / `end_image` / `audio` FileRef. |
| `GET /v1/video/ltx2/models` | List of models | Return a list of available models. |
| `GET /v1/video/ltx2/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

Inferred mode:

| input | mode |
|---|---|
| No file attachment | T2V — Text to video |
| `image` FileRef | I2V — Animate the first frame |
| `image` + `end_image` FileRef | I2V — Specify first and last frame |
| `end_image` FileRef | I2V — Specify the last frame |
| `audio` FileRef | A2V — Drive motion/timing with audio |
| `image` + `audio` FileRef | A2V + I2V |
| `generate_audio: true` | T2V + Audio — also generates audio |

- `mode: "sync"` waits until completion and returns raw MP4 bytes by default for single artifacts.
  If you want Job JSON, add `Accept: application/json`.
- `mode: "async"` returns `202` and `{job_id}`.
  Check the progress with `GET /v1/jobs/{job_id}` and after completion use `result.file_id` or
  Get MP4 with `artifacts[0]`.
- `audio` files and `generate_audio: true` are exclusive.

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/video/ltx2/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/video/ltx2/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/video/ltx2/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-video](https://github.com/Blaizzy/mlx-video) | MIT | Run LTX-2 distilled pipeline on MLX. `pyproject.toml` pins known good git commits. |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [prince-canuma/LTX-2-distilled](https://huggingface.co/prince-canuma/LTX-2-distilled) | [LTX-2 Community License Agreement](https://huggingface.co/Lightricks/LTX-2/blob/main/LICENSE) (derived from [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2) Compliant with repo itself (no model card / LICENSE) | HF gated. However, use and distribution require license agreement | 101 GB | `distilled` (default). Two-stage distilled pipeline. No CFG, about 11 steps inside. A transient model that loads/releases on every call. |

Key defaults and limits:

| Item | Default value | Constraints |
|---|---:|---|
| `width` | `512` | Positive multiple of 64. Upper limit `768`. |
| `height` | `512` | Positive multiple of 64. Upper limit `768`. |
| `num_frames` | `97` | `1 + 8*k`. Upper limit `721`. |
| `fps` | `24` | Positive integer. |
| `image_strength` | `1.0` | `0.0..1.0`. The degree to which I2V is constrained to the input frame. |

`duration = num_frames / fps`. At 24 fps, `97` takes about 4 seconds, `161` takes about 6.7 seconds,
`241` takes about 10 seconds, `481` takes about 20 seconds, and `721` takes about 30 seconds.

## Notes

- **transient model**:
  LTX-2 is not a permanent model. Load, create, and free each call, and before execution
  Reserve a temporary memory budget of approximately 40 GB with `memory.reserve()`. Therefore, `/health`
  It will not remain in the resident model.
- **Response format**:
  If sync produces only one MP4, it defaults to returning the raw MP4.
  You can trace the metadata from the `X-Kiapi-File-Id` / `X-Kiapi-Job-Id` headers.
  `Accept: application/json` returns Job JSON.
- **distilled has no negative guidance**:
  There is no classifier-free guidance, so there is no negative prompt or `no zoom` / `don't ...`
  Suppression instructions such as this do not work. The movement, composition, and texture you want, not what you want to avoid.
  and adjust it with seed and `image_strength`.
- **I2V's `image_strength`**:
  `1.0` is strongly fixed to the input frame. If you want to move clearly, set it to around `0.7`
  Lowering it makes it easier to tolerate changes.
- **Progress**:
  mlx-video does not expose per-step progress callbacks. kiapi is
  Time-based, relative to `progress_eta_base_s`, scaled by number of frames and resolution.
  Stream synthetic progress.
- **Notes on updating dependencies**:
  `mlx-video` is pinned to git commit because the API is changeable. When updating
  `_models/ltx2.py` calls `generate_video` and routes `PipelineType.DISTILLED`.
  Please check it and verify it on the actual machine using `make verify-ltx2`.

## Quickstart

### generate — T2V
```bash
PARAMS=$(
jq -n \
--arg prompt "a cat walking through tall grass, sunny, shallow depth of field" \
'{
  model: "distilled",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  num_frames: 97,
  fps: 24,
  seed: 1
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2.mp4
```
If you want Job JSON:
```bash
PARAMS=$(
jq -n \
--arg prompt "a small paper boat floating on a quiet pond, gentle ripples" \
'{
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  num_frames: 97,
  seed: 2
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq .
```
### generate — I2V

Upload and reference the image you want to use for the first frame to the Files API.
```bash
IMAGE_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@first_frame.png;type=image/png" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg image "$IMAGE_ID" \
--arg prompt "gentle wind, leaves moving, soft cinematic motion" \
'{
  mode: "sync",
  prompt: $prompt,
  image: {type: "file_id", file_id: $image},
  num_frames: 97,
  image_strength: 0.7,
  seed: 3
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2-i2v.mp4
```
To specify the first and last frame:
```bash
IMAGE_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@first_frame.png;type=image/png" | jq -r .file_id)
END_IMAGE_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@last_frame.png;type=image/png" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg image "$IMAGE_ID" \
--arg end_image "$END_IMAGE_ID" \
--arg prompt "a smooth transition from morning to sunset" \
'{
  mode: "sync",
  prompt: $prompt,
  image: {type: "file_id", file_id: $image},
  end_image: {type: "file_id", file_id: $end_image},
  num_frames: 97,
  image_strength: 0.8,
  end_image_strength: 0.8,
  seed: 4
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2-first-last.mp4
```
### generate — A2V

When you upload and reference audio files to the Files API, audio drives motion, timing, and
Mixed to output MP4.
```bash
AUDIO_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@drums.wav;type=audio/wav" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg audio "$AUDIO_ID" \
--arg prompt "a drummer on stage, energetic performance, stage lighting" \
'{
  mode: "sync",
  prompt: $prompt,
  audio: {type: "file_id", file_id: $audio},
  width: 512,
  height: 512,
  num_frames: 97,
  seed: 5
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2-a2v.mp4
```
### generate — T2V + Audio

Generates audio along with the video without using an audio file.
```bash
PARAMS=$(
jq -n \
--arg prompt "a tiny robot dancing in a neon room, playful electronic beat" \
'{
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  num_frames: 97,
  generate_audio: true,
  seed: 6
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2-audio.mp4
```

### async

```bash
PARAMS=$(
jq -n \
--arg prompt "a cinematic shot of clouds moving over a mountain lake" \
'{
  mode: "async",
  prompt: $prompt,
  width: 512,
  height: 512,
  num_frames: 97,
  seed: 7
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```
Once completed, use the Job's `artifacts[0]` or `result.file_id` to get the MP4.
```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o ltx2-async.mp4
```
