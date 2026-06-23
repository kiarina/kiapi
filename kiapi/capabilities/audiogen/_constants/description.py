DESCRIPTION = """Sound-effect / ambient audio generation from text.

AudioGen turns a text prompt into short non-musical audio events: environmental
sounds, foley, impacts, ambience, machinery, footsteps, room tone, and similar
SFX. Output is always 16 kHz mono WAV. It is not a music model — for songs,
vocals, cover, repaint, or stem extraction use the ACE-Step family instead.

## Upstream docs
- [AudioGen medium](https://huggingface.co/facebook/audiogen-medium) — the
  upstream model card
- [mlx-audiocraft](https://github.com/theashishmaurya/mlx-audiocraft) — MLX port
  of Meta AudioCraft

## Models
- **medium** (default) — `facebook/audiogen-medium`, 1.5B parameters, native up
  to 10 seconds. The model is CC-BY-NC-4.0, so check the license before use.

Discover variants at `GET /v1/audio/audiogen/models`.

## Prompt Tips
Be concrete and additive. Name the source, action, material, distance, space, and
energy:
- **good**: "heavy rain on a tin roof, distant thunder, wide outdoor ambience"
- **good**: "slow footsteps on wet gravel, close microphone, quiet night street"
- **less useful**: "rain" or "scary sound"

Sampling tweaks matter less than wording. Start with `duration`, `seed`, and
`cfg_coef`; only adjust `top_k`, `top_p`, and `temperature` when exploring
variation.

## Reproducibility
Set `seed` to reproduce a clip with the same prompt and sampling parameters.
Leave it null to explore alternatives; the resolved seed is recorded in the Job
`result.params`.

## Performance
- First request after activate/idle may spend tens of seconds loading weights.
- After loading, the model stays resident until idle TTL or memory budget pressure
  frees it.
- On M4 Max, generation is roughly half realtime: a 5 second clip takes about
  10 seconds of compute.

## Examples

### Generate raw WAV (sync)
```sh
curl -sS http://localhost:${PORT:-8000}/v1/audio/audiogen/generate \\
  -H 'Content-Type: application/json' \\
  -d '{"mode":"sync","prompt":"keyboard typing, office ambience","duration":5}' \\
  -o sfx.wav
```

### Generate as async job
```sh
curl -sS http://localhost:${PORT:-8000}/v1/audio/audiogen/generate \\
  -H 'Content-Type: application/json' \\
  -d '{"mode":"async","prompt":"ocean waves crashing on rocks","duration":5,"seed":42}'
# -> {"job_id": "..."}; poll GET /v1/jobs/{job_id}
```
"""
