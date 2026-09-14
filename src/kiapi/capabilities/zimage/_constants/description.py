DESCRIPTION = """Fast text-to-image generation and LoRA training (Z-Image via mflux).

Two operations on Alibaba's Z-Image models: `/generate` (text-to-image) and
`/train` (LoRA finetune). Z-Image is txt2img only — there is no image-to-image
edit endpoint. To edit an existing image, use the ernie / qwen / flux2 families.

## Upstream docs
- [mflux — Z-Image](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/z_image/README.md) — the MLX engine kiapi runs
- [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) — `base` weights

## Models
- **turbo** (default) — `filipstrand/Z-Image-Turbo-mflux-4bit`. Distilled,
  few-step (default 9), pre-quantized 4-bit, no guidance. The everyday choice.
- **base** — `Tongyi-MAI/Z-Image`. The full model: more steps (default 28) and
  guidance (default 4.0), 8-bit by default. Higher quality but slower.

Pick the variant with `model`; discover variants at
`GET /v1/image/zimage/models`. Variant-dependent defaults (`steps` / `guidance` /
`quantize`) are filled in server-side when omitted, and the resolved values are
recorded in the result `params`. `negative_prompt` is most effective on `base`
with guidance > 1; on the distilled `turbo` (no guidance) it has little effect.

## Resident vs transient runs
The warmed, resident model uses the server-default quantization. A request that
either supplies `loras` or sets a `quantize` differing from the resident model
builds a **one-off transient model** for that call — mflux bakes those in at load
time, so weights load fresh and the run is slower and not reused. For the fast
path, omit `loras` and leave `quantize` unset.

## LoRA workflow
Train an adapter from a captioned image set via `/train` (always async), then
apply it on `/generate` by passing its `adapter_file_id` in `loras` (up to 4,
each `{file, scale}`). Dataset = a ZIP uploaded to the Files API with a same-stem
`.txt` caption next to each image (`cat.png` + `cat.txt`); images may sit at the
top level or in a single subfolder, and `preview*` images are exempt from the
caption requirement.

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
- `width`/`height` must be multiples of 16 and at most 2048x2048.
- First use downloads the Z-Image weights; run `kiapi activate` ahead of time to
  avoid a cold-start download on the first request.

## Performance
- **turbo**: ~9 steps, pre-quantized 4-bit; the fast default.
- **base**: full model, many steps, 8-bit by default — prefer turbo unless you
  need its quality.
- First request is slower while weights load + convert; then the model is
  resident until its TTL frees it.
- Transient runs (any `loras` or a `quantize` override) rebuild the model each
  call and are slower than the resident path.
"""
