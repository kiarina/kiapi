DESCRIPTION = """Short video generation with LTX-2.5 and LTX-2 distilled.

LTX-2.5 (default) and LTX-2 generate short MP4 videos from text, optional image
conditioning, and optional audio.

## Upstream docs
- [mlx-video](https://github.com/Blaizzy/mlx-video) — the MLX engine kiapi runs
- [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) — LTX-2.5 model card, weights, and license
- [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2) — LTX-2 model card and license source
- [prince-canuma/LTX-2-distilled](https://huggingface.co/prince-canuma/LTX-2-distilled) — LTX-2 distilled MLX weights used by kiapi

## Models

- **`ltx-2.5-distilled`** (default): 22B LTX-2.5 transformer, Gemma 4 text
  encoder, two-stage distilled pipeline. kiapi reserves about 44 GB per run.
- **`distilled`**: the previous 19B LTX-2 distilled model. kiapi reserves about
  40 GB per run. It does not accept the LTX-2.5 options below.

Both are transient: the pipeline is loaded for each job, run, then freed.

The distilled pipelines do not use classifier-free guidance. Negative prompts
and suppression phrases such as `no zoom`, `do not move`, or `avoid blur` are not
reliable controls. Describe the desired subject, motion, framing, camera behavior,
lighting, and texture directly.

## Modes

The generation mode is inferred from attached inputs:

- **T2V**: prompt only
- **I2V**: prompt + `image`
- **I2V(first+last)**: prompt + `image` + `end_image`
- **I2V(last)**: prompt + `end_image`
- **A2V**: prompt + `audio`
- **A2V+I2V**: prompt + `image` + `audio`
- **T2V+Audio**: prompt + `generate_audio=true`

An uploaded or referenced `audio` file drives timing and is muxed into the MP4.
It cannot be combined with `generate_audio=true`.

## LTX-2.5 options

- `auto_duration=true`: predict the length from the prompt (1 to 20 seconds)
  instead of passing `num_frames`. The result `params.num_frames` reports it.
- `enhance_prompt=true`: expand a short prompt into a detailed caption with
  Gemma 4 E2B first. For I2V the enhancer also sees the image.
- `pipeline="dfr"`: Diffusion Fidelity Rendering. Finer texture and steadier
  shapes at roughly 1.7x the time. T2V only; `generate_audio` is allowed.
- `video_decoder="diffusion"`: experimental diffusion video VAE at roughly 1.5
  to 2x the time. In tests it gave a smoother, more temporally stable rendering
  (less flicker in grass and fur) rather than harder edges.

## Practical Defaults

The server defaults target a useful quality/speed balance:

- `width`: 512
- `height`: 512
- `num_frames`: 97
- `fps`: 24

At 24 fps, common frame counts are roughly:

- `97`: about 4 seconds
- `161`: about 6.7 seconds
- `241`: about 10 seconds
- `481`: about 20 seconds
- `721`: about 30 seconds

`num_frames` must be `1 + 8*k`, and width/height must be multiples of 64.

## Tips

- Prefer positive direction over negative constraints. Write what should happen,
  not what should be prevented.
- For I2V, `image_strength=1.0` keeps the first frame very stable. Lower values
  around `0.7` allow more visible motion or composition change.
- Phrases like `looking at the camera` can encourage push-in/zoom behavior. If a
  stable gaze is desired, try wording such as `looking ahead`.
- Use seed sweeps for composition, pose, and camera variation. A few seeds are
  often more effective than over-constraining the prompt.
- 512x512 is the sweet spot for general use. Larger resolutions and longer frame
  counts hold the single-flight queue for longer.
- LTX-2.5 follows multi-shot prompts (for example a medium shot, then a
  close-up, then a wide shot) better than LTX-2 at 241 frames.

## Performance Notes

Generation time depends heavily on frame count and resolution. A 512x512,
97-frame job is the baseline used for synthetic progress; shorter/lower
resolution jobs complete faster, while long 721-frame jobs can occupy the worker
for much longer. LTX-2.5 is about 10 to 20% slower than LTX-2 at the same size.

Because kiapi is single-flight, one LTX-2 job blocks all other heavy jobs until
it finishes. Use `mode="async"` for longer videos so clients can poll
`/v1/jobs/{job_id}` instead of holding an HTTP request open.
"""
