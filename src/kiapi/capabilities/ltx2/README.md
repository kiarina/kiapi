# ltx2

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

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [prince-canuma/LTX-2-distilled](https://huggingface.co/prince-canuma/LTX-2-distilled) | [LTX-2 Community License Agreement](https://huggingface.co/Lightricks/LTX-2/blob/main/LICENSE) (derived from [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2) Compliant with repo itself (no model card / LICENSE) | HF gated. However, use and distribution require license agreement | 101 GB | ~40 GB (transient) | `distilled` (default). Two-stage distilled pipeline. No CFG, about 11 steps inside. A transient model that loads/releases on every call. |

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

## LTX-2.5 upstream development status

> [!IMPORTANT]
> LTX-2.5 is not part of the current kiapi capability. The installed `mlx-video`
> pin and the `distilled` model above remain the production implementation until
> the upstream work is merged, pinned, and verified through kiapi.

LTX-2.5 support is being developed upstream in
[Blaizzy/mlx-video#52](https://github.com/Blaizzy/mlx-video/pull/52). The PR
keeps the existing `mlx_video.models.ltx_2` pipeline and legacy model layouts,
and separates each feature into its own commit for review.

### Architecture and resources

LTX-2.5 is not a model-repository swap for the current 19B checkpoint:

- The video/audio transformer has 22B parameters and uses a fixed distilled
  schedule with ancestral Euler sampling in stage 1.
- The encode path requires the LTX-specific Gemma 4 Unified 12B checkpoint and
  its embedded tokenizer and projections.
- Official weights are split into transformer, text encoder, video VAE, audio
  VAE/vocoder, spatial upscaler, and optional duration-head files.
- Prompt enhancement cannot use the encode-only Gemma 4 Unified checkpoint.
  It uses a separate generative Gemma 4 E2B-it checkpoint.
- The LTX-2.5 weights use the LTX-2.x Community License. Access requires
  accepting the model terms on Hugging Face.

The upstream PR currently verifies these paths on Apple Silicon:

- T2V and I2V, including first/last-frame conditioning
- synchronized audio-video generation, A2V, and A2V + I2V
- prompt-based automatic duration prediction on the `8k+1` frame grid
- T2V prompt enhancement and reference-image-aware I2V prompt enhancement
- the lighter convolutional video VAE

### Measurements

The following measurements used a Mac Studio M4 Max with 128GB unified memory,
768x512 output, 121 frames, and 24 fps. They measure direct `mlx-video`
generation, not kiapi request overhead.

| Mode | LTX-2.5 | Current LTX-2 | Difference |
|---|---:|---:|---:|
| T2V | 108.7s / 37.81GB peak | 96.9s / 37.48GB peak | LTX-2.5 was about 12% slower |
| I2V | 120.8s / 39.54GB peak | 101.7s / 39.35GB peak | LTX-2.5 was about 19% slower |
| Generated audio | 118.1s / 37.81GB peak | — | 48kHz stereo AAC |
| A2V | 106.4s / 37.81GB peak | — | input audio preserved as 16kHz stereo AAC |

All representative outputs contained 121 H.264 frames. Image checks found no
NaNs, gray-frame output, or static output; audio checks found no NaNs or
infinities. In the tested ocean scene, LTX-2.5 produced more natural color,
finer wave/reflection detail, and better temporal consistency than the current
LTX-2 model.

Automatic duration prediction also completed end to end: a short prompt
predicted 4.72 seconds / 113 frames, and the generated MP4 contained exactly
113 frames. Prompt enhancement can feed the expanded caption into this duration
prediction before generation.

### Diffusion video VAE boundary

The high-quality diffusion video decoder is not implemented in MLX yet. Its
final stage uses eight blocks of 11x11x11 3D neighborhood attention. At
768x512 / 121 frames, the final stage contains 694,272 query positions and
about 924 million query-neighbor pairs per block before head/channel work.

The official CUDA implementation uses a fused NATTEN kernel for production and
describes its eager fallback as compatibility-only. A practical Apple Silicon
port therefore needs a dedicated tiled Metal kernel with online softmax,
boundary-window shifting, and integrated RoPE. Building the decoder around an
unfused MLX gather would create prohibitive temporary tensors and runtime.

An inference-only MLX Metal prototype now provides NATTEN-compatible 3D window
geometry, BF16 inputs, float32 accumulation, and a two-pass online softmax
without materializing attention scores. It matches the eager reference for
small boundary cases and runs an 11x11x11 / head-dim-64 smoke test. A
16x16x16 / 16-head / head-dim-64 warm run took 20.8 ms with an 80 MiB peak.
The prototype assigns one query/head to each thread and is a correctness
baseline; it still needs the SIMD-group and threadgroup K/V tiling ideas from
the open NATTEN Metal PR #312 before integrating the five-stage decoder.

### Remaining adoption work

Native multishot behavior has been verified through the existing distilled T2V
pipeline at 768x512 / 241 frames. LTX-2.5 followed a three-shot prompt while
preserving the subject and wardrobe, but cut timing remained model-controlled
and an explicit hard cut could become a smooth transition. The older LTX-2
model also changed framing, although it followed the requested three-shot
structure less closely. Since no separate inference path is required,
`mlx-video` documents the prompt pattern and limitations instead of adding a
new structured API.

An initial convolutional-VAE DFR path is implemented in the upstream branch. It
generates keyframe slots on the official 24/32-frame segment grid, spatially
upsamples the base video and slots, and performs a second pass using the
half-resolution video as an in-context reference with the official detailing
IC-LoRA. At 768x512 / 121 frames it took 179.6 seconds and 41.25 GB peak memory,
compared with 103.4 seconds and 37.81 GB for the regular distilled path. The DFR
output showed finer fur, edge, and grass detail and more stable subject shape.
This initial path supports T2V and optional generated audio; I2V, A2V, temporal
upscaling, streaming, and diffusion-VAE decoding remain out of scope.

1. Treat the diffusion VAE Metal kernel as a separate optimization milestone,
   even if its commit remains in the same upstream PR branch.
2. After upstream review stabilizes, pin the accepted `mlx-video` commit in
   kiapi, update setup resources and API fields, and run full kiapi regression
   verification before changing the default model.

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
