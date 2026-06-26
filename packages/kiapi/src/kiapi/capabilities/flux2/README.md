# flux2

**English** | [日本語](README.ja.md)

[mflux FLUX.2 Klein](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/flux2/README.md) provides image generation, image editing, and LoRA learning functions.

- **generate**:
  - txt2img / img2img
- **edit**:
  - Multi-reference editing using one or more reference images from the Files API
- **train**:
  - Learn LoRA adapter from your own dataset ZIP

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/flux2/generate` | Image generation | Generate image from prompt. `init_image` img2img if FileRef exists. |
| `POST /v1/image/flux2/edit` | Image editing | Edit the `images` FileRef array of Files API as a reference image. |
| `POST /v1/image/flux2/train` | LoRA learning | Learn LoRA adapter from dataset ZIP. **Always async**. |
| `GET /v1/image/flux2/models` | List of models | Return the list of available models. |
| `GET /v1/image/flux2/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/flux2/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/flux2/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/flux2/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | FLUX.2 Execute Klein generation, editing, and LoRA learning on MLX. |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) | FLUX Non-Commercial License | Required | 52.9 GB | `klein-9b` (default). 9B Klein for small steps. Defaults are `steps: 4`, `guidance: 1.0`, `quantize: null`. Can be used for generation and editing. |
| [black-forest-labs/FLUX.2-klein-base-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B) | Apache-2.0 | Not required | 23.7 GB | `klein-base-4b`. base variant. Defaults are `steps: 40`, `guidance: 1.0`, `quantize: 8`. Can be used for generation, editing, and LoRA learning. |
| [black-forest-labs/FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) | FLUX Non-Commercial License | Required | 52.9 GB | `klein-base-9b`. base variant. Defaults are `steps: 40`, `guidance: 1.0`, `quantize: 8`. Can be used for generation, editing, and LoRA learning. |

## Notes

- **Size constraints**:
  `width` / `height` are multiples of 16. Default is `1024 x 1024`, upper limit is `2048 x 2048`.
  The upper limit of `steps` is `100`.
- **LoRA applied**:
  Apply the learned adapter with `loras: [{"file": {"type": "file_id", "file_id": "..."}, "scale": 1.0}]`.
  Up to 4. `scale` is the strength of the effect.
- **LoRA training dataset**:
  ZIP puts images into a top-level or single subfolder.
  `training_mode: "text"` requires each image to have a `.txt` caption with the same stem.
  `training_mode: "edit"` requires `*_in.*` / `*_out.*` image pairs and `*_in.txt` prompt.
- **Memory guideline**:
  `klein-9b` has a peak measurement of about 29 GiB, and edit has a peak measurement of about 31.6 GiB.
  `klein-base-4b` is about 9.1 GiB with q8 / 512 / 40 steps,
  `klein-base-9b` is approximately 16.8 GiB. train is `KIAPI_FLUX2_TRAIN_RESERVE_GB`
  Reserve default 24 GiB.

## Quickstart

### generate — txt2img
```bash
jq -n \
'{
  model: "klein-9b",
  mode: "sync",
  prompt: "a cafe storefront, a sign clearly reads CAFE, bright daylight",
  width: 512,
  height: 512,
  seed: 1
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Content-Type: application/json' \
--data-binary @- \
-o flux2.png
```
If you want Job JSON:
```bash
jq -n \
'{
  model: "klein-9b",
  mode: "sync",
  prompt: "a small robot watering flowers, clean studio illustration",
  width: 512,
  height: 512,
  seed: 2
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary @- |
jq .
```
### generate — img2img

Upload the source image first:
```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@source.png" | jq -r .file_id)
```

```bash
jq -n \
--arg img "$IMG" \
'{
  model: "klein-9b",
  mode: "sync",
  prompt: "turn this into a polished cozy illustration",
  init_image: {type: "file_id", file_id: $img},
  image_strength: 0.45,
  width: 1024,
  height: 576,
  seed: 7
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Content-Type: application/json' \
--data-binary @- \
-o flux2-img2img.png
```
`image_strength` is 0-1. The smaller the value, the stronger the input image remains, and the larger the value, the closer it is to the prompt side.

### edit — Editing with multiple reference images
```bash
REF1=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@mascot.png" | jq -r .file_id)
REF2=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@object.png" | jq -r .file_id)

jq -n \
--arg ref1 "$REF1" \
--arg ref2 "$REF2" \
'{
  model: "klein-9b",
  mode: "sync",
  prompt: "make a playful illustration combining the mascot and object",
  images: [{type: "file_id", file_id: $ref1}, {type: "file_id", file_id: $ref2}],
  width: 1024,
  height: 576,
  seed: 9
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/edit \
-H 'Content-Type: application/json' \
--data-binary @- \
-o flux2-edit.png
```

### async

```bash
JOB=$(
jq -n \
'{
  model: "klein-9b",
  mode: "async",
  prompt: "a cinematic product photo of a glass teapot",
  width: 512,
  height: 512,
  seed: 11
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary @- |
jq -r .job_id
)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```
Once completed, use the Job's `artifacts[0]` or `result.file_id` to get the image:
```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o flux2-async.png
```
### train — LoRA

Example dataset for `training_mode: "text"`:
```text
my_lora/
  sample_01.png
  sample_01.txt
  sample_02.png
  sample_02.txt
```
Create a dataset ZIP and upload it to the Files API:
```bash
(cd my_lora && zip -q -r - .) > dataset.zip

DS=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@dataset.zip" | jq -r .file_id)
```
Start learning. train is always async:
```bash
JOB=$(
jq -n \
--arg ds "$DS" \
'{
  model: "klein-base-4b",
  dataset: {type: "file_id", file_id: $ds},
  training_mode: "text",
  num_epochs: 10,
  lora_rank: 8
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/train \
-H 'Content-Type: application/json' \
--data-binary @- |
jq -r .job_id
)

echo "$JOB"
```
Poll until completion and get the learned adapter's `file_id`:
```bash
until STATUS=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .status) && \
  [ "$STATUS" != "queued" ] && [ "$STATUS" != "running" ]; do
  sleep 5
done

ADAPTER=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.adapter_file_id)
echo "$ADAPTER"
```
### Generated with trained LoRA
```bash
jq -n \
--arg adapter "$ADAPTER" \
'{
  model: "klein-base-4b",
  mode: "sync",
  prompt: "<your trigger word> as a clean editorial illustration",
  width: 512,
  height: 512,
  seed: 13,
  loras: [{file: {type: "file_id", file_id: $adapter}, scale: 1.0}]
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Content-Type: application/json' \
--data-binary @- \
-o flux2-lora.png
```
