# zimage

**English** | [日本語](README.ja.md)

[mflux Z-Image](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/z_image/README.md) provides image generation and LoRA fine-tuning functionality.

Z-Image is a relatively lightweight image generation model.
`turbo` is fast with few steps, and `base` is suitable for adjustment using guidance / negative prompt.

- **generate**: Generate image from text
- **train**: Train LoRA adapter from captioned image ZIP

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/zimage/generate` | Image generation | Generate image from prompt. Pass the body of `application/json`. |
| `POST /v1/image/zimage/train` | LoRA learning | Learn LoRA adapter from captioned image ZIP. Always async. |
| `GET /v1/image/zimage/models` | List of models | Return a list of available models. |
| `GET /v1/image/zimage/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/zimage/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/zimage/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/zimage/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | Perform Z-Image generation and LoRA training on MLX. |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [filipstrand/Z-Image-Turbo-mflux-4bit](https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit) | Tongyi Qianwen License | Not required | 5.5 GB | ~14 GB | `turbo` (default). For distillation and small steps. Defaults are `steps: 9`, `guidance: null`, `quantize: null`. |
| [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) | Apache-2.0 | Not required | 19 GB | ~28 GB | `base`. Non-distilled model. Defaults are `steps: 28`, `guidance: 4.0`, `quantize: 8`. |

In kiapi's registered values, `turbo` has a weight of approximately `6.0 GiB` / runtime headroom of approximately `8.0 GiB`,
`base` is expected to have a weight of approximately `12.0 GiB` / runtime headroom of approximately `16.0 GiB`.

## Notes

- **Image size**:
  `width` / `height` are multiples of 16. Default is `1024 x 1024`, upper limit is `2048 x 2048`.
- **steps/guidance**:
  `steps` is `1..100`. If omitted, `turbo` is `9` and `base` is `28`.
  Since `turbo` is a distilled model, `guidance` and `negative_prompt` have no effect.
  `base` can use `guidance` and `negative_prompt`.
- **quantize**:
  `quantize` can specify `3` / `4` / `5` / `6` / `8`. If omitted, the default value for each model will be used.
  `turbo` uses a 4-bit pre-quantized repo, so it is usually omitted.
- **LoRA applied**:
  Pass `[{ "file": {"type": "file_id", "file_id": "..."}, "scale": 1.0 }]` to `loras` of `generate`.
  By default, up to 4 can be applied. Adapter files must be stored in the Files API.
- **transient model**:
  mflux fixes the quantization level and LoRA during model construction. has `loras`, or
  A request to override `quantize` from its default value builds a temporary model for that call.
  It is slower than a plain `turbo` / `base` call because it does not reuse the resident model.
- **Output format**:
  `format` is `png` (default) / `jpeg` / `webp`. `quality` for `jpeg` / `webp`
  Use `1..100` (default `90`).
- **LoRA training dataset**:
  Place images at the top level of the ZIP or in a single subfolder within the ZIP. per image
  Requires a `.txt` caption with the same stem.

## Quickstart

### generate - generate image from text

Save only the image:
```bash
PARAMS=$(
jq -n \
--arg prompt "a red fox in fresh snow, soft morning light, realistic photo" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 1024,
  height: 1024,
  seed: 1
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o zimage.png
```
Returns Job JSON:
```bash
PARAMS=$(
jq -n \
--arg prompt "a small robot watering flowers, clean studio illustration" \
--arg negative_prompt "blurry, low quality" \
'{
  model: "base",
  mode: "sync",
  prompt: $prompt,
  negative_prompt: $negative_prompt,
  width: 512,
  height: 512,
  seed: 2
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq .
```
If you need the `file_id`, you can read it from the response header.
```bash
PARAMS=$(
jq -n \
--arg prompt "a red fox in fresh snow" \
'{
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 1
}'
)

FILE_ID=$(curl -sS -D - -o zimage.png \
-X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
| awk -F': ' 'tolower($1)=="x-kiapi-file-id"{print $2}' | tr -d '\r')

echo "$FILE_ID"
```

### async

```bash
PARAMS=$(
jq -n \
--arg prompt "a cinematic product photo of a glass teapot" \
'{
  model: "turbo",
  mode: "async",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 11
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```
After completion, use the Job's `artifacts[0]` or `result.file_id` to get the image.
```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o zimage-async.png
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
Create a dataset ZIP and upload it to the Files API.
```bash
(cd dataset && zip -q -r - .) > dataset.zip

DATASET_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@dataset.zip;type=application/zip" | jq -r .file_id)
```
Start learning. train is always async.
```bash
JOB=$(
jq -n \
--arg dataset "$DATASET_ID" \
'{
  model: "turbo",
  dataset: {type: "file_id", file_id: $dataset},
  num_epochs: 10,
  lora_rank: 16,
  max_resolution: 512
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/train \
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
Apply LoRA on generation.
```bash
PARAMS=$(
jq -n \
--arg prompt "<your trigger word> in a magical garden" \
--arg adapter "$ADAPTER" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 7,
  loras: [{file: {type: "file_id", file_id: $adapter}, scale: 1.0}]
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o zimage-lora.png
```
`scale` is the strength of the effect. Every request using `loras` builds a temporary model.
