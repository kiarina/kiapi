DESCRIPTION = """Image generation and editing (Qwen-Image via mflux).

Two operations on Alibaba's Qwen-Image models: `/generate` (text-to-image, or
image-to-image when `init_image` is supplied) and `/edit` (natural-language
single/multi-image editing). Qwen-Image is strong at rendered text and
instruction-following edits.

## Upstream docs
- [mflux — Qwen Image](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/qwen/README.md) — the MLX engine kiapi runs
- [Qwen/Qwen-Image](https://huggingface.co/Qwen/Qwen-Image) — generate weights
- [Qwen/Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) — edit weights
- [Qwen/Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1) — unified generate/edit weights (non-commercial)

## Models
- **image** (default) — text-to-image / img2img. The only variant `/generate`
  accepts.
- **edit-2509** — instruction-based editing. The default for `/edit`.
- **image-2.1** — Qwen-Image-2.1, accepted by both `/generate` and `/edit`.
  One resident model, RGBA output, up to 10 reference images, up to 2752 px.
  Its weights are under the Qwen Research License: **non-commercial use only**.
  Listed only when the server runs the mflux build with 2.1 editing.

Omit `model` for each endpoint's default; discover variants at
`GET /v1/image/qwen/models`. Omitted
`steps`/`guidance`/`quantize`/size are filled in server-side and the resolved
values are recorded in the result `params`.

## generate vs edit
- **generate** is text-to-image; pass `init_image` (+ optional `image_strength`
  in 0..1) to seed an img2img run from one image.
- **edit** takes a list of reference `images` for single- or multi-image editing
  / composition under one natural-language prompt.

## image-2.1
- Defaults: `steps` 40, `guidance` 1.0 (trained guidance-free), q8. With
  `guidance` above 1, `negative_prompt` drives true CFG at about twice the time.
- Size: multiples of 32, up to 2752x2752. An edit without `width`/`height` takes
  the last image's aspect ratio at about 1024x1024 pixels.
- Transparency: ask for it in the prompt, e.g. "This is an RGBA image with
  transparency. ... The background is transparent." `png`/`webp` keep alpha;
  `jpeg` flattens onto white.
- Not supported: `init_image` (pass the image in `images` on `/edit`), `loras`,
  and `scheduler` (ignored).

## Resident vs transient runs
The warmed, resident model uses the server-default quantization (q8). A request
that either supplies `loras` or sets a `quantize` differing from the resident
model builds a **one-off transient model** for that call — weights load fresh, so
it is slower and not reused. For the fast path, omit `loras` and leave `quantize`
unset.

## LoRA
Apply adapters by passing their `file` ids in `loras` (up to 4, each
`{file, scale}`). Any lora forces a transient run.

## TIPS
- For a quick image, call `sync` without `Accept: application/json` to get the
  raw bytes straight back (`curl -o out.png`).
- `width`/`height` must be multiples of 16 and at most 2048x2048 (default 1024);
  `image-2.1` needs multiples of 32 and allows up to 2752.
- Qwen-Image renders legible text well — describe the wanted text explicitly in
  the prompt.
- First use downloads the Qwen weights (~58 GB full); run `kiapi activate` ahead
  of time to avoid a cold-start download on the first request.

## Performance
- Upstream weights are large (~58 GB full); kiapi defaults to q8.
- Transient runs (any `loras` or a `quantize` override) rebuild the model each
  call and are slower than the resident path.
"""
