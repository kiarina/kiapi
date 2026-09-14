DESCRIPTION = """Image generation, editing, and LoRA training (ERNIE-Image via mflux).

Three operations on Baidu's ERNIE-Image models: `/generate` (text-to-image),
`/edit` (single-image image-to-image), and `/train` (LoRA finetune).

## Upstream docs
- [mflux — ERNIE-Image](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/ernie_image/README.md) — the MLX engine kiapi runs
- [baidu/ERNIE-Image-Turbo](https://huggingface.co/baidu/ERNIE-Image-Turbo) — `turbo` weights
- [baidu/ERNIE-Image](https://huggingface.co/baidu/ERNIE-Image) — `base` weights

## Models
- **turbo** (default) — `baidu/ERNIE-Image-Turbo`. Fast, few steps (default 8),
  guidance 1.0. The everyday choice.
- **base** — `baidu/ERNIE-Image`. Higher quality but slower: more steps
  (default 50) and stronger guidance (default 4.0).

Pick the variant with `model` (aliases like `ernie-image-turbo` are accepted);
discover variants at `GET /v1/image/ernie/models`. Variant-dependent defaults
(`steps` / `guidance` / `quantize`) are filled in server-side when omitted, and
the resolved values are recorded in the result `params`.

## Resident vs transient runs
The warmed, resident model uses the server-default quantization. A request that
either supplies `loras` or sets a `quantize` differing from the resident model
builds a **one-off transient model** for that call — weights load fresh, so it is
slower and not reused. For the fast path, omit `loras` and leave `quantize` unset.

## LoRA workflow
Train an adapter from a captioned image set via `/train` (always async), then
apply it on `/generate` or `/edit` by passing its `adapter_file_id` in `loras`
(up to 4, each `{file, scale}`). Dataset = a ZIP uploaded to the Files API with a
same-stem `.txt` caption next to each image (`cat.png` + `cat.txt`); images may
sit at the top level or in a single subfolder, and `preview*` images are exempt
from the caption requirement.

```
dataset.zip
├── cat_01.png      # image
├── cat_01.txt      # same-stem caption: "a photo of a tabby cat"
├── cat_02.jpg
├── cat_02.txt
└── preview.png     # optional preview, no caption needed
```

A single wrapping subfolder is also accepted (the images just need to live
together under one directory):

```
dataset.zip
└── cats/
    ├── cat_01.png
    ├── cat_01.txt
    └── ...
```

## TIPS
- For a quick image, call `sync` without `Accept: application/json` to get the
  raw bytes straight back (`curl -o out.png`).
- `width`/`height` must be multiples of 16 and at most 2048x2048. `edit`
  additionally requires square sizes by default — set
  `KIAPI_ERNIE_EDIT_REQUIRE_SQUARE=0` to lift the guard (mflux 0.18.0 can fail on
  some non-square ERNIE img2img sizes).
- First use downloads the ERNIE-Image weights; run `kiapi activate` ahead of time
  to avoid a cold-start download on the first request.

## Performance
- **turbo**: q8 512x512 generation around 15s after cache load, peak RSS ~5-6 GiB.
- **base**: slower and uses more steps; prefer turbo unless you need its quality.
- Transient runs (any `loras` or a `quantize` override) rebuild the model each
  call and are slower than the resident path.
"""
