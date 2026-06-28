# ernie

**English** | [日本語](README.ja.md)

[mflux ERNIE-Image](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/ernie_image/README.md) provides image generation, image editing, and LoRA fine tuning functions.

- **generate**: Generate image from text
- **edit**: Prompt editing of single image in Files API
- **train**: Train LoRA adapter from captioned image ZIP

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/ernie/generate` | Image generation | Generate image from prompt. |
| `POST /v1/image/ernie/edit` | Image editing | Files API single image prompt img2img editing. |
| `POST /v1/image/ernie/train` | LoRA learning | Learning LoRA adapter from captioned image ZIP. Always async. |
| `GET /v1/image/ernie/models` | Model list | Returns a list of available models. |
| `GET /v1/image/ernie/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/ernie/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/ernie/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/ernie/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | Uses ERNIE-Image's MLX implementation and LoRA learning function. |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [baidu/ERNIE-Image-Turbo](https://huggingface.co/baidu/ERNIE-Image-Turbo) | Apache-2.0 | Not required | 31.6 GB | ~10 GB | `turbo` (default). Distillation 8 step model. Defaults are `steps: 8`, `guidance: 1.0`, `quantize: 8`. |
| [baidu/ERNIE-Image](https://huggingface.co/baidu/ERNIE-Image) | Apache-2.0 | Not required | 31.6 GB | ~20 GB | `base`. Non-distilled model. Defaults are `steps: 50`, `guidance: 4.0`, `quantize: 8`. |

## Notes

- **Image size**:
  `width` / `height` are multiples of 16, default is `1024x1024`, upper limit is `2048x2048`.
- **edit square guard**:
  With `mflux==0.18.0`, some non-square sizes of ERNIE img2img are latent packing.
  It may fail. kiapi requires `width == height` for `edit` by default.
  To disable it, set `KIAPI_ERNIE_EDIT_REQUIRE_SQUARE=0`.
- **steps/quantize**:
  `steps` is `1..100`. `quantize` uses `3` / `4` / `5` / `6` / `8` / `null`.
  If `quantize` is omitted, the default value for each model will be used.
- **LoRA applied**:
  Pass `[{ "file_id": "...", "scale": 1.0 }]` to `loras` of `generate` / `edit`.
  By default, up to 4 can be applied.
- **LoRA training dataset**:
  Place images at the top level of the ZIP or in a single subfolder within the ZIP. per image
  Requires a `.txt` caption with the same stem. Images starting with `preview*` are captions.
  Excluded from mandatory checks.

## Quickstart

### generate - generate image from text

Returns Job JSON:
```bash
PARAMS=$(
jq -n \
--arg prompt "A quiet Japanese garden after rain, soft morning light, detailed watercolor" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 1024,
  height: 1024,
  steps: 8,
  seed: 404
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq .
```
Save only the image:
```bash
PARAMS=$(
jq -n \
--arg prompt "A barn owl portrait on a mossy branch, natural wildlife photography" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  steps: 8,
  seed: 404
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ernie.png
```
### edit - edit a single image

Upload the input image first:
```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@tests/assets/miineko.png;type=image/png" | jq -r .file_id)
```
Edit the uploaded image:
```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
--arg prompt "Turn this image into a soft watercolor illustration" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  image: {type: "file_id", file_id: $image},
  image_strength: 0.55,
  width: 512,
  height: 512,
  steps: 8,
  seed: 42
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/edit \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ernie_edit.png
```
`image_strength` is `0..1`. The smaller the value, the stronger the original image will remain; the larger the value, the more the prompt side will remain.
The changes will become stronger.

###async
```bash
PARAMS=$(
jq -n \
--arg prompt "A small robot reading a book in a cozy library" \
'{
  model: "turbo",
  mode: "async",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 7
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```
After completion, use the Job's `artifacts[0]` or `result.file_id` to get the image.
```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o ernie_async.png
```
### train - LoRA Fine Tuning

Prepare a ZIP dataset containing a `.txt` caption with the same stem as the image.
```text
dataset/
  sample_00.png
  sample_00.txt
  sample_01.png
  sample_01.txt
```
Upload your dataset and start training.
```bash
DATASET_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@dataset.zip;type=application/zip" | jq -r .file_id)

JOB=$(
jq -n \
--arg dataset "$DATASET_ID" \
'{
  model: "turbo",
  dataset: {type: "file_id", file_id: $dataset},
  num_epochs: 1,
  lora_rank: 16,
  max_resolution: 512
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/train \
-H 'Content-Type: application/json' \
--data-binary @- |
jq -r .job_id
)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```
After completion, `result.adapter_file_id` is the learned adapter.
```bash
ADAPTER=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.adapter_file_id)
```
Apply LoRA during generation and editing.
```bash
PARAMS=$(
jq -n \
--arg adapter "$ADAPTER" \
--arg prompt "portrait in the trained character style" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  loras: [{file: {type: "file_id", file_id: $adapter}, scale: 1.0}]
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ernie_lora.png
```
