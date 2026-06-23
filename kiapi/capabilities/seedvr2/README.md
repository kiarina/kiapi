# seedvr2

**English** | [日本語](README.ja.md)

[mflux SeedVR2](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/seedvr2/README.md) provides single-image diffusion-based super-resolution/upscaling functionality.
SeedVR2 is an image-to-image super-resolution model that reconstructs details based on input images rather than prompt-driven image generation.

- **upscale**:
  - Reference images already uploaded to Files API with `image` FileRef
  - Specify the output size by the target number of pixels on the shortest side or by a scaling factor like `"2x"`


## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/seedvr2/upscale` | Image upscaling | Super-resolve the Files API image and generate one image. |
| `GET /v1/image/seedvr2/models` | Model list | Returns a list of available models. |
| `GET /v1/image/seedvr2/openapi.json` | OpenAPI | Return detailed input/output specifications, constraints, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/seedvr2/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/seedvr2/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/seedvr2/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | Uses SeedVR2's MLX implementation. |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) | Apache-2.0 | Not required | 7.3 GB | `3b` (default). Lightweight variant. Defaults are `resolution: "2x"`, `softness: 0.0`, `quantize: 8`. |
| [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) | Apache-2.0 | Not required | 17 GB | `7b`. High capacity variant. It is heavier than `3b`, and the registered value of kiapi is expected to have a weight of about `7.0 GiB` and a runtime headroom of about `4.0 GiB`. |

Model weights can be replaced with `KIAPI_SEEDVR2_MODEL_REPO`.
Default is `numz/SeedVR2_comfyUI`.

## Notes

- **resolution**:
  `resolution` is an integer shortest edge target or a scaling factor such as `"2x"` / `"1.5x"`.
  The default is `16..2048` for integers, and `> 0` and less than or equal to `4.0x` for scale factors.
- **softness**:
  `softness` is `0..1`. Default is `0.0`. Adjusts the softness of detail reconstruction of the input image.
- **seed**:
  If `seed` is omitted, a random seed will be assigned for each request.
  Please specify if reproducibility is required.
- **quantize override**:
  `quantize` is `3` / `4` / `5` / `6` / `8` / `null`. Normally, the default `8` uses the resident model.
  If you specify `quantize` that is different from the default value in the request, it will be loaded, executed, and released as a one-time temporary model.
- **Response format**:
  If you generate one artifact with sync, it will return the raw image bytes unless you specify `Accept: application/json`.
  You can reference saved artifacts and Jobs from the `X-Kiapi-File-Id` and `X-Kiapi-Job-Id` headers.
  If you want Job JSON or async, use `Accept: application/json`.
- **Output format**:
  `format` is `png` (default) / `jpeg` / `webp`. `quality` for `jpeg` / `webp`
  Use `1..100` (default `90`).
- **Memory guideline**:
  `3b` is the weight approximately `2.7 GiB`, runtime headroom is approximately `1.5 GiB`, `7b` is the weight approximately
  Registered as `7.0 GiB`, runtime headroom approximately `4.0 GiB`.
- **Not supported**:
  We do not publish text prompts, image editing instructions, LoRA learning, or multiple image input.

## Quickstart

### upscale - Upload image

First, upload the source image to the Files API.
```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@source.png" | jq -r .file_id)
```
### upscale - Specify by scale factor

Save only the image:
```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  model: "3b",
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: "2x",
  softness: 0.0,
  seed: 42
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o seedvr2-2x.png
```
Returns Job JSON:
```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  model: "3b",
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: "2x",
  format: "webp",
  quality: 92,
  seed: 7
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq .
```
### upscale - Specified by the number of pixels on the shortest side

Upscale the shortest side to `768px`.
```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: 768,
  softness: 0.15,
  seed: 11
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o seedvr2-768.png
```
Passing a string like `"768" to `resolution` will also be interpreted as an integer target.

### 7b variant
```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  model: "7b",
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: "2x",
  seed: 13
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o seedvr2-7b.png
```

### async

```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  mode: "async",
  image: {type: "file_id", file_id: $image},
  resolution: "2x",
  seed: 17
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```
After completion, use the Job's `artifacts[0]` or `result.file_id` to get the image.
```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o seedvr2-async.png
```
### quantize override

Specify `quantize` if you want to try a different quantization than the default. This call calls the resident model
Build a temporary model without reusing it.
```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  model: "3b",
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: "1.5x",
  quantize: 6,
  seed: 19
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o seedvr2-q6.png
```
### Model list and help
```bash
curl -sS http://localhost:${PORT:-8000}/v1/image/seedvr2/models | jq .
curl -sS http://localhost:${PORT:-8000}/v1/image/seedvr2/openapi.json | jq .
```
