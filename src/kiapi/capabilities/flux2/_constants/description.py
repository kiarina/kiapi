DESCRIPTION = """Image generation, editing, and LoRA training (FLUX.2 Klein via mflux).

Three operations on Black Forest Labs' FLUX.2 Klein models: `/generate`
(text-to-image, or image-to-image when `init_image` is supplied), `/edit`
(multi-reference image editing), and `/train` (LoRA finetune).

## Upstream docs
- [mflux — FLUX.2](https://github.com/mflux-community/mflux/blob/main/src/mflux/models/flux2/README.md) — the MLX engine kiapi runs
- [FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) — distilled `klein-9b` weights
- [FLUX.2-klein-base-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B) / [base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) — trainable base weights

## Models
- **klein-9b** (default) — distilled. Fast, few steps (default 4), unquantized.
  The everyday choice for generate/edit.
- **klein-base-4b** — base. Slower (default 40 steps, q8) but trainable; the
  default `/train` target.
- **klein-base-9b** — base. Highest quality of the three, slowest; also trainable.

Pick the variant with `model` (aliases like `flux2-klein-9b` are accepted);
discover variants at `GET /v1/image/flux2/models`. Variant-dependent defaults
(`steps` / `guidance` / `quantize`) are filled in server-side when omitted, and
the resolved values are recorded in the result `params`. Only base variants are
trainable — `klein-9b` is rejected by `/train`.

## generate vs edit
- **generate** is text-to-image; pass `init_image` (+ optional `image_strength`)
  to seed an img2img run from one image.
- **edit** takes a list of reference `images` for multi-reference editing /
  composition under a single prompt.

## Resident vs transient runs
The warmed, resident model uses the server-default quantization. A request that
either supplies `loras` or sets a `quantize` differing from the resident model
builds a **one-off transient model** for that call — weights load fresh, so it is
slower and not reused. For the fast path, omit `loras` and leave `quantize` unset.

## LoRA workflow
Train an adapter via `/train` (always async, base variants only), then apply it on
`/generate` or `/edit` by passing its `file` id in `loras` (up to 4, each
`{file, scale}`). The dataset is a ZIP uploaded to the Files API; its layout
depends on `training_mode`.

**`training_mode=text`** — each image has a same-stem `.txt` caption:

```
dataset.zip
├── cat_01.png      # image
├── cat_01.txt      # same-stem caption: "a photo of a tabby cat"
├── cat_02.jpg
└── cat_02.txt
```

**`training_mode=edit`** — `*_in.*` / `*_out.*` image pairs, the `*_in.txt`
holding the edit prompt:

```
dataset.zip
├── 01_in.png       # source image
├── 01_in.txt       # edit prompt: "make it snow"
├── 01_out.png      # target image
├── 02_in.jpg
├── 02_in.txt
└── 02_out.jpg
```

## TIPS
- For a quick image, call `sync` without `Accept: application/json` to get the
  raw bytes straight back (`curl -o out.png`).
- `width`/`height` must be multiples of 16 and at most 2048x2048 (default 1024).
- `klein-9b` is the fast default; reach for the base variants only when you need
  their quality or want to train.
- First use downloads the FLUX.2 weights; run `kiapi activate` ahead of time to
  avoid a cold-start download on the first request.

## Performance
- **klein-9b**: ~29 GiB peak RSS for 512 text/img2img, ~31.6 GiB for edit.
- **klein-base-4b**: ~9.1 GiB peak at q8/512/40 steps.
- **klein-base-9b**: ~16.8 GiB peak at q8/512/40 steps.
- Transient runs (any `loras` or a `quantize` override) rebuild the model each
  call and are slower than the resident path.
"""
