DESCRIPTION = """Video with stereo audio from text and ordered references, with MiniMax H3.

MiniMax H3 (Hailuo 3.0) is a 33B joint video + audio diffusion transformer.
kiapi runs its **Ref2VA** checkpoint, which takes text plus up to 9 reference
images, 3 reference videos and 3 reference audio clips (12 files at most), and
also generates from text alone.

## Upstream docs
- [MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) — model card, prompting guide, and the MiniMax H3 Community License
- [Prompt guide for references](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt) — the six-section format H3 was trained on
- [mlx-serve](https://github.com/ddalcu/mlx-serve) — the MLX engine kiapi runs
- [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo) — the Turbo LoRA

## How a run works

Each job starts an mlx-serve process, generates, and stops it. kiapi reserves
about 50 GB per run. A run takes tens of minutes, so use `mode=async` and poll
`GET /v1/jobs/{job_id}`; progress reports the denoising step.

Measured on an M4 Max 128 GB at 960x544, 124 frames, Turbo (8 steps):

| References | Time |
|---|---:|
| text or images (any number), voices | about 20 min |
| plus one 3 s reference video | about 31 min |
| plus one 5 s reference video | about 50 min |

Reference video frames join the sequence at every step, so their length drives
the time. Images are resized to the output size and add little. Without Turbo
(20 steps) a run takes about 2.5x as long.

## References and labels

Refer to references in the prompt by type and 1-based position:

- `images` → `<Picture 1>`, `<Picture 2>`, ...
- `videos` → `<Video 1>`, ...
- audio → `<Audio 1>`, ...: with `use_video_audio`, each video's soundtrack takes
  the next label in video order first; then the standalone `audios` follow.

Standalone audio needs at least one image or video. Reference videos are cut to
the generated length.

## Writing prompts

H3 was trained on structured prompts that MiniMax writes with a hosted rewriter
(H3-Context-IR), which is not part of the open release. With `enhance_prompt`
(default) a kiapi chat model rewrites the request into that format first, using
the official guide, the reference images, and frames of the reference videos.
It cannot hear audio, so say what each `<Audio N>` is for. It adds about 2
minutes; the text used is in `params.enhanced_prompt`. To write the structured
prompt yourself, follow the guide above; such a prompt is sent unchanged. Put
dialogue inside `<d>[Japanese] ...</d>`.

## What works well

- Keeping characters from reference images, including back views and several
  characters in one shot.
- Taking setting, camera and motion from reference videos.
- Speaking given lines with a reference voice.

Strictly preserving a source video (editing, continuing from its last frame) is
weaker than MiniMax's hosted service: framing and faces can drift.

## License

The weights are under the MiniMax H3 Community License: not available in the
EU, the UK, South Korea and the United States, commercial use above USD 20M
annual revenue needs a separate license, and redistribution must show
"Powered by MiniMax H3". The Turbo LoRA is Apache-2.0.
"""
