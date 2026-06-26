DESCRIPTION = """Typography-focused text-to-image generation (Ideogram 4 FP8 via mflux).

One operation: `/generate` (text-to-image). Ideogram 4 excels at rendering legible
text and typography. There is no image-to-image, no training, and no hosted Magic
Prompt API.

## Upstream docs
- [mflux — Ideogram 4](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/ideogram4/README.md) — the MLX engine kiapi runs
- [ideogram-ai/ideogram-4-fp8](https://huggingface.co/ideogram-ai/ideogram-4-fp8) — the `fp8` weights (gated)

## Models
- **fp8** (default) — `ideogram-ai/ideogram-4-fp8`. The only variant; discover it
  at `GET /v1/image/ideogram4/models`. The Hugging Face repo is **gated**: approve
  access to `ideogram-ai/ideogram-4-fp8` before the first download. Non-FP8
  checkpoint layouts are not supported.

## Prompting (JSON caption preferred)
Ideogram 4 follows a **structured JSON caption** far better than plain text,
especially for laying out and spelling words. Plain text is accepted but usually
weaker. See the official prompt guide for the full caption schema, key-order
rules, bbox layout, and color-palette conditioning:
- [Ideogram 4 prompting guide](https://github.com/ideogram-oss/ideogram-4/blob/main/docs/prompting.md)

A caption looks like:

```json
{
  "high_level_description": "A clean studio photo of a white notebook with the word MFLUX on the cover.",
  "style_description": "Soft daylight, shallow depth of field, product-photography aesthetic.",
  "compositional_deconstruction": {
    "background": "Warm wooden desk with soft window light.",
    "elements": [
      {
        "type": "text",
        "bbox": [420, 420, 620, 560],
        "text": "MFLUX",
        "desc": "Crisp black uppercase letters centered on the notebook."
      }
    ]
  }
}
```

- `bbox` is `[x1, y1, x2, y2]` in normalized **0-1000** layout coordinates.
- `type` is `text` (needs a `text` field) or `obj`.
- Set `strict_caption_validation=true` to fail (400) on mflux caption-schema
  warnings; `warn_on_caption_issues` (default true) just surfaces them.

## Presets
`preset` bundles steps + guidance + noise schedule. Trade speed for quality:
`V4_TURBO_12` (fast, 12 steps) → `V4_DEFAULT_20` (balanced) → `V4_QUALITY_48`
(best, 48 steps).

## TIPS
- For a quick image, call `sync` without `Accept: application/json` to get the raw
  bytes straight back (`curl -o out.png`).
- `width`/`height` must be multiples of 16 and within 256..2048 (default 1024).
- First use downloads the gated FP8 weights; run `kiapi activate` ahead of time to
  avoid a cold-start download on the first request.

## Performance
- **fp8**: roughly 26-28 GiB peak RSS at 1024x1024 / V4_DEFAULT_20.
- **first request**: may be much slower if gated weights are still being
  downloaded from Hugging Face.
"""
