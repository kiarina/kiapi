DESCRIPTION = """Monocular depth estimation from a single image (Apple Depth Pro via mflux).

This is **image-to-depth**, not prompt-driven image generation: you give one
image and get back a metric depth map.

## Upstream docs
- [mflux](https://github.com/filipstrand/mflux) — the MLX engine kiapi runs
- [apple/DepthPro](https://huggingface.co/apple/DepthPro) — model weights
- [apple/ml-depth-pro](https://github.com/apple/ml-depth-pro) — original Depth Pro code and paper

## What you get back
- A grayscale depth **PNG** where brighter pixels are nearer and darker pixels
  are farther — ready to display or overlay.
- Optionally (default on, `include_depth_data=true`) a compressed **NPZ**
  containing the raw float depth array plus `min_depth` / `max_depth` in meters,
  for downstream numeric use (point clouds, masking, measurement).

The depth array is loadable with NumPy: `np.load(path)["depth"]`, with scalar
`min_depth` / `max_depth` also stored in the same archive.

## Models
- **base** (default) — `apple/DepthPro`. The only variant today.

## Quantization
`quantize` selects the model's bit-width (one of 3, 4, 5, 6, 8; server default
8). The warmed, resident model uses the server default; requesting a *different*
`quantize` builds a one-off transient model for that call, which loads weights
fresh and is therefore slower and not reused. Keep `quantize` unset (or equal to
the default) for the fast resident path.

## TIPS
- For a quick visual, leave `include_depth_data=false` and call `sync` — you get
  the PNG bytes straight back (`curl -o depth.png`).
- For measurement or 3D work, keep `include_depth_data=true` and read the NPZ.
- Large uploads are bounded by an input pixel cap; downscale very large images
  before sending. Depth Pro resizes internally, so modest inputs are fine.
- First use downloads Apple's Depth Pro weights; run `kiapi activate` ahead of
  time to avoid a cold-start download on the first request.
"""
