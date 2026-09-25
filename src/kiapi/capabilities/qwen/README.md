# qwen

[mflux Qwen Image](https://github.com/mflux-community/mflux/blob/main/src/mflux/models/qwen/README.md) and
[mflux Qwen Image 2.1](https://github.com/mflux-community/mflux/blob/main/src/mflux/models/qwen21/README.md) provide image generation and image editing functions.
Qwen Image is a strong model for multilingual prompts and text in images.

- **generate**:
  - Generate images from text
  - img2img if you pass `init_image` FileRef
- **edit**:
  - Natural language editing using one or more reference images from the Files API

`image-2.1` ([Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1)) serves both
operations with one resident model, outputs RGBA, and takes up to 10 reference images.
Its weights are **non-commercial** (Qwen Research License).


## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/qwen/generate` | Image generation | Generate image from prompt and reference image. |
| `POST /v1/image/qwen/edit` | Image editing | Generate an image from multiple reference images. |
| `GET /v1/image/qwen/models` | Model list | Returns a list of available models. |
| `GET /v1/image/qwen/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/qwen/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/qwen/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/qwen/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/mflux-community/mflux) | MIT | Run Qwen Image / Qwen Image Edit / Qwen-Image-2.1 on MLX. |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [Qwen/Qwen-Image](https://huggingface.co/Qwen/Qwen-Image) | Apache-2.0 | Not required | 58 GB | ~30 GB | `image` (default). Used with `generate`. txt2img/img2img. Defaults are `steps: 30`, `guidance: 4.0`, `quantize: 8`. |
| [Qwen/Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) | Apache-2.0 | Not required | 58 GB | ~30 GB | `edit-2509`. Used with `edit`. Single/multiple reference image editing. Defaults are `steps: 30`, `guidance: 2.5`, `quantize: 8`. |
| [Qwen/Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1) | Qwen Research License | Non-commercial only | 33 GB | ~30 GB | `image-2.1`. Used with both `generate` and `edit`. txt2img, editing with up to 10 references, RGBA output. Defaults are `steps: 40`, `guidance: 1.0`, `quantize: 8`. |

`POST /v1/image/qwen/generate` accepts `image` (default) and `image-2.1`.
`POST /v1/image/qwen/edit` accepts `edit-2509` (default) and `image-2.1`.
Each endpoint fills in its model's defaults, so `model` can be omitted for the
default variant.

## Notes

- **Image size**:
  `width` / `height` are multiples of 16. The default is `1024 x 1024` and the upper limit
  is `2048 x 2048`.
- **steps / guidance**:
  `steps` is `1..100`. If omitted, it is `30` for both generate and edit. `guidance` defaults
  to `4.0` for generate and `2.5` for edit.
- **quantize**:
  The default is `8`. You can override it with `3` / `4` / `5` / `6` / `8`. An omitted or
  `null` value uses the default.
- **LoRA**:
  Apply adapters with `loras: [{"file": {"type": "file_id", "file_id": "..."}, "scale": 1.0}]`,
  up to 4. Adapter files must be stored in the Files API.
- **Transient model**:
  mflux fixes the quantization level and LoRA when it builds a model. A request with `loras`,
  or with a `quantize` that differs from the default, builds a one-off model for that call.
  It is slower than a plain call because it does not reuse the resident model.
- **Output format**:
  `format` is `png` (default) / `jpeg` / `webp`. `quality` applies to `jpeg` / `webp`
  (`1..100`, default `90`).
- **Memory**:
  `image` / `edit-2509` are both large. kiapi budgets about `22.0 GiB` of weights and
  `8.0 GiB` of runtime headroom for each.

### image-2.1

- **One model, two endpoints**: `/generate` runs text-to-image, `/edit` runs editing with
  1 to 10 `images`. Both use the same resident model. Reference order matters.
- **Image size**: multiples of 32, up to `2752 x 2752` (native 2K; the upstream examples
  use `2048 x 2048`). An edit that omits `width` / `height` takes the last reference's
  aspect ratio at about 1024² pixels.
- **steps / guidance**: `steps` is `2..100`, default `40`. The model is trained
  guidance-free; `guidance` defaults to `1.0`. Above `1.0`, true CFG runs with
  `negative_prompt` (empty if omitted) and roughly doubles the time.
- **Transparency**: output is always RGBA. Ask for transparency in the prompt, for example
  `This is an RGBA image with transparency. ... The background is transparent.`
  `png` / `webp` keep the alpha channel; `jpeg` flattens it onto white.
  RGBA references keep their alpha.
- **Not supported**: `init_image` (use `/edit` with `images`), `loras`, and `scheduler`
  (ignored). A differing `quantize` builds a transient model, as above.
- **Engine**: editing comes from a pinned [mflux fork](https://github.com/kiarina/mflux/tree/qwen-image-2.1-edit)
  ([#741](https://github.com/mflux-community/mflux/pull/741)). With official mflux,
  `image-2.1` is not registered.
- **License**: the weights are for research and evaluation only. Do not use its outputs
  in commercial work without a separate license from Alibaba; use `image` / `edit-2509`
  (Apache-2.0) instead.

## Quickstart

### generate - generate image from text

Save only the image:
```bash
PARAMS=$(
jq -n \
--arg prompt "a cafe storefront, a wooden sign clearly reads カフェ, bright daylight" \
--arg negative_prompt "blurry, low quality, distorted text" \
'{
  model: "image",
  mode: "sync",
  prompt: $prompt,
  negative_prompt: $negative_prompt,
  width: 512,
  height: 512,
  seed: 1
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o qwen.png
```
Returns Job JSON:
```bash
PARAMS=$(
jq -n \
--arg prompt "a clean product label design, the main text reads KIAPI, white background" \
'{
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 2
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq .
```
### generate - img2img

Upload the source image first.
```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@source.png" | jq -r .file_id)
```
Generate based on the uploaded image.
```bash
PARAMS=$(
jq -n \
--arg img "$IMG" \
--arg prompt "turn this into a polished cozy illustration" \
'{
  model: "image",
  mode: "sync",
  prompt: $prompt,
  init_image: {type: "file_id", file_id: $img},
  image_strength: 0.45,
  width: 1024,
  height: 576,
  seed: 7
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o qwen-img2img.png
```
`image_strength` is `0..1`. The smaller the value, the stronger the input image will remain, and the larger the value, the stronger the prompt side.
The changes will become stronger.

### edit - Edit single/multiple images
```bash
REF1=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@mascot.png" | jq -r .file_id)
REF2=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@object.png" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg ref1 "$REF1" \
--arg ref2 "$REF2" \
--arg prompt "combine the mascot and object into a bright product key visual; keep the mascot recognizable" \
'{
  model: "edit-2509",
  mode: "sync",
  prompt: $prompt,
  images: [{type: "file_id", file_id: $ref1}, {type: "file_id", file_id: $ref2}],
  width: 1024,
  height: 576,
  seed: 9
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/edit \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o qwen-edit.png
```
`images` is one or more. For editing a single image or for compositing and reconstructing using multiple reference images.
You can use it.

### async
```bash
PARAMS=$(
jq -n \
--arg prompt "a typography poster, large readable text says LOCAL AI" \
'{
  mode: "async",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 11
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```
After completion, use the Job's `artifacts[0]` or `result.file_id` to get the image.
```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o qwen-async.png
```
### Generated by applying LoRA

Upload `.safetensors`, such as learned adapters, to the Files API and reference them with `loras`.
```bash
ADAPTER=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@adapter.safetensors" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg adapter "$ADAPTER" \
--arg prompt "<your trigger word> as a clean editorial illustration" \
'{
  model: "image",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 13,
  loras: [{file: {type: "file_id", file_id: $adapter}, scale: 1.0}]
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o qwen-lora.png
```
`scale` is the strength of the effect. Every request using `loras` builds a temporary model.

### image-2.1 - transparent sticker
```bash
PARAMS=$(
jq -n \
--arg prompt "This is an RGBA image with transparency. A cute orange cat sticker. The image has alpha channel and the background is transparent." \
'{
  model: "image-2.1",
  mode: "sync",
  prompt: $prompt,
  width: 1024,
  height: 1024,
  seed: 42
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o sticker.png
```
### image-2.1 - edit with references
```bash
PARAMS=$(
jq -n \
--arg ref1 "$REF1" \
--arg ref2 "$REF2" \
--arg prompt "Place the mascot from image 1 in the setting of image 2." \
'{
  model: "image-2.1",
  mode: "sync",
  prompt: $prompt,
  images: [{type: "file_id", file_id: $ref1}, {type: "file_id", file_id: $ref2}],
  seed: 9
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/edit \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o qwen21-edit.png
```
With `width` / `height` omitted, the output takes the aspect ratio of the last image.
