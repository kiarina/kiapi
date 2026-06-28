# ideogram4

**English** | [日本語](README.ja.md)

[mflux Ideogram 4 FP8](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/ideogram4/README.md) provides typography-friendly text image generation functionality.
Ideogram 4 is a model suitable for situations where you want to handle text, signs, labels, logo-like text, etc. in images.
kiapi only exposes txt2img and saves the generated results as Files API artifacts.

- **generate**:
  - Generate images from Ideogram 4's JSON caption or regular text prompts


## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/ideogram4/generate` | Image generation | Generate one image from JSON caption or text prompt. |
| `GET /v1/image/ideogram4/models` | Model list | Returns a list of available models. |
| `GET /v1/image/ideogram4/openapi.json` | OpenAPI | Returns detailed input/output specifications, prompt shapes, constraints, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/ideogram4/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/ideogram4/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/ideogram4/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | Uses the MLX implementation of Ideogram 4 FP8. |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [ideogram-ai/ideogram-4-fp8](https://huggingface.co/ideogram-ai/ideogram-4-fp8) | Ideogram license (non-commercial) | Required | 27.5 GB | ~30 GB | `fp8` (default). Hugging Face's gated repo. Default is `1024x1024`, `preset: V4_DEFAULT_20`, `quantize: null`. |

## Notes

- **Hugging Face's gated repo**:
  The model weights are obtained from `ideogram-ai/ideogram-4-fp8`.
  Before running it for the first time, you need to approve access on Hugging Face and authenticate in the local environment.
- **JSON caption recommended**:
  Although it accepts regular string prompts, Ideogram 4 performs best with structured JSON captions.
  If you want to target the text in the image, set `type: "text"` to `compositional_deconstruction.elements[]`,
  The basics are to include `bbox`, `text`, and `desc`.
- **bbox coordinates**:
  `bbox` in JSON caption has the format `[x1, y1, x2, y2]`.
  Ideogram 4's prompting guide treats them as normalized layout coordinates from 0-1000.
- **Preset**:
  `preset` is one of `V4_DEFAULT_20` / `V4_QUALITY_48` / `V4_TURBO_12`.
  Default is `V4_DEFAULT_20`. If quality is your priority, use `V4_QUALITY_48`, and if speed is your priority, use `V4_TURBO_12`.
- **Image size**:
  `width` / `height` are multiples of 16, defaulting to `1024x1024`.
  The default upper limit is `2048x2048` and the lower limit is `256x256`.
- **quantize override**:
  `quantize` is `3` / `4` / `5` / `6` / `8` / `null`.
  If you specify `quantize` that is different from the default value in the request, it will be loaded, executed, and released as a one-time temporary model.
- **Response format**:
  If you generate one artifact with sync, it will return the raw image bytes unless you specify `Accept: application/json`.
  You can reference saved artifacts and Jobs from the `X-Kiapi-File-Id` and `X-Kiapi-Job-Id` headers.
  If you want Job JSON or async, use `Accept: application/json`.
- **Output format**:
  `format` is `png` / `jpeg` / `webp`. Default is `png`.
  `quality` is the encoding quality of `jpeg` / `webp`, `1..100`, default is `90`.
- **Safety Filter**:
  Some prompts may return `Image blocked by safety filter` images, including false positives.
  kiapi does not make this an HTTP error, but instead stores the returned image as an artifact.
- **Not supported**:
  We do not publish image-to-image, image editing, LoRA learning, hosted Magic Prompt API, or checkpoint layouts other than FP8.

## Prompt JSON

This is the recommended basic form of JSON caption.
```json
{
  "high_level_description": "Overall scene description.",
  "style_description": "Optional style, lighting, medium, and color guidance.",
  "compositional_deconstruction": {
    "background": "Background and layout description.",
    "elements": [
      {
        "type": "text",
        "bbox": [360, 420, 640, 560],
        "text": "HELLO",
        "desc": "Crisp black uppercase letters centered on the sign."
      }
    ]
  }
}
```
For detailed instructions, please also refer to [Ideogram 4 prompting guide](https://github.com/ideogram-oss/ideogram4/blob/main/docs/prompting.md).

## Quickstart

### generate - Generate an image with text using JSON caption

Returns Job JSON:
```bash
PARAMS=$(jq -n '{
  model: "fp8",
  mode: "sync",
  prompt: {
    high_level_description: "A clean studio photo of a white notebook with the word MFLUX on the cover.",
    style_description: "Minimal product photography, soft window light, realistic paper texture.",
    compositional_deconstruction: {
      background: "Warm wooden desk with soft shadows.",
      elements: [
        {
          type: "text",
          bbox: [390, 430, 610, 560],
          text: "MFLUX",
          desc: "Crisp black uppercase letters centered on the notebook cover."
        }
      ]
    }
  },
  width: 1024,
  height: 1024,
  preset: "V4_DEFAULT_20",
  seed: 42
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ideogram4/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq .
```
Save only the image:
```bash
PARAMS=$(jq -n '{
  model: "fp8",
  mode: "sync",
  prompt: {
    high_level_description: "A square cafe poster with the large word KIASA.",
    style_description: "Clean editorial poster, warm morning colors, sharp typography.",
    compositional_deconstruction: {
      background: "Cream wall with a simple coffee cup illustration.",
      elements: [
        {
          type: "text",
          bbox: [260, 320, 740, 500],
          text: "KIASA",
          desc: "Large bold serif letters, perfectly readable."
        }
      ]
    }
  },
  width: 1024,
  height: 1024,
  seed: 7
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ideogram4/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ideogram4.png
```
### generate - plain text
```bash
PARAMS=$(jq -n '{
  mode: "sync",
  prompt: "A vintage travel poster for TOKYO, the word TOKYO is large and perfectly readable, bright flat colors",
  width: 768,
  height: 1024,
  preset: "V4_QUALITY_48",
  seed: 11
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ideogram4/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ideogram4-text.png
```

### async

```bash
PARAMS=$(jq -n '{
  mode: "async",
  prompt: {
    high_level_description: "A clean packaging mockup for a tea box labeled HIKARI.",
    compositional_deconstruction: {
      background: "Soft green studio backdrop.",
      elements: [
        {
          type: "text",
          bbox: [330, 360, 670, 520],
          text: "HIKARI",
          desc: "Elegant uppercase letters printed on the front of the box."
        }
      ]
    }
  },
  width: 1024,
  height: 1024,
  preset: "V4_TURBO_12"
}')

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ideogram4/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```
After completion, use the Job's `artifacts[0]` or `result.file_id` to get the image.
```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o ideogram4-async.png
```
### Model list and help
```bash
curl -sS http://localhost:${PORT:-8000}/v1/image/ideogram4/models | jq .
curl -sS http://localhost:${PORT:-8000}/v1/image/ideogram4/openapi.json | jq .
```
