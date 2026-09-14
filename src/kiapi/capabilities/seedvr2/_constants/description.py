DESCRIPTION = """Image super-resolution upscaling (SeedVR2 via mflux).

One operation: `/upscale` takes an input image and produces a higher-resolution
version. SeedVR2 is diffusion-based super-resolution, **not** prompt-driven image
generation — there is no prompt. To create or edit images from text, use the
qwen / flux2 / zimage / ideogram4 families instead.

## Upstream docs
- [mflux — SeedVR2](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/seedvr2/README.md) — the MLX engine kiapi runs
- [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) — weights

## Models
- **3b** (default) — faster, lighter; good general upscaler.
- **7b** — larger variant, higher quality at a higher memory/time cost.

Discover variants at `GET /v1/image/seedvr2/models`. An omitted `quantize` uses
the resident model's quantization (q8); the resolved values are recorded in the
result `params`.

## Sizing the output
`resolution` accepts either form:
- an **integer** shortest-edge pixel target (16..2048), or
- a **scale factor** string like `2x` or `1.5x` (> 0 and at most 4.0x).

`softness` (0..1) trades sharpness for smoothing; leave it at 0 for the crispest
result.

## Resident vs transient runs
The warmed, resident model uses the server-default quantization (q8). A request
that sets a `quantize` differing from the resident model builds a **one-off
transient model** for that call — weights load fresh, so it is slower and not
reused. For the fast path, leave `quantize` unset.

## TIPS
- For a quick result, call `sync` without `Accept: application/json` to get the
  raw bytes straight back (`curl -o out.png`).
- Upscaling a large source image to a high `resolution` raises peak memory; the
  request can 503 if it does not fit the global memory budget — try the `3b`
  variant or a smaller target.
- First use downloads the SeedVR2 weights; run `kiapi activate` ahead of time to
  avoid a cold-start download on the first request.

## Performance
- **3b**: 256→512 q8 first-run peak ~3929 MiB; cached 256→768 peak ~1756 MiB.
- **7b**: larger variant; estimate only until measured locally.
"""
