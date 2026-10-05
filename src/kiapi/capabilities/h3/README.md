# h3

[MiniMax H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) (Hailuo 3.0) generates
video with stereo audio. kiapi runs its **Ref2VA** checkpoint through
[mlx-serve](https://github.com/ddalcu/mlx-serve):

- **Text to video + audio**
- **Image references**: keep characters, objects, scenes, or styles (up to 9)
- **Video references**: take setting, camera, or motion; edit or continue (up to 3)
- **Audio references**: speak with a reference voice, or reuse music or sound (up to 3)

At most 12 references in total.

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/video/h3/generate` | Video generation | Generate an MP4 from a JSON body with `images` / `videos` / `audios` FileRef lists. |
| `GET /v1/video/h3/models` | List of models | Return a list of available models. |
| `GET /v1/video/h3/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

- The prompt refers to references as `<Picture N>`, `<Video N>` and `<Audio N>`,
  1-based per type. With `use_video_audio`, each video's soundtrack takes the next
  `<Audio N>` in video order before the standalone `audios`.
- `mode` defaults to `async`: a run takes tens of minutes. Poll
  `GET /v1/jobs/{job_id}`; progress reports the denoising step.
- `turbo` (default `true`) applies the Turbo LoRA at 8 steps. `turbo: false` runs
  the base model at 20 steps, about 2.5x slower.
- `fast` turns on mlx-serve's lossy approximate speed-up. Off by default.
- Reference videos are cut to the generated length. Standalone audio is cut to 15
  seconds and needs an image or video reference.

### Prompts

H3 was trained on six-section prompts that MiniMax writes with a hosted rewriter
(H3-Context-IR) that is not released. Plain sentences work; for faithful use of
references, follow the
[full-reference guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt).
A chat model given the guide and the references can write it. Write dialogue as
`<d>[Japanese] ...</d>`.

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/video/h3/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/video/h3/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/video/h3/redoc.html)

## How it runs

Each job starts mlx-serve on a free loopback port, sends one streaming request,
writes the MP4 with ffmpeg, and stops the process. mlx-serve loads the text
encoder, transformer and VAEs in turn, so they never share memory. The family is
transient (`resident=False`) and reserves 50 GB per run.

`kiapi activate --family h3` downloads the pinned mlx-serve release archive into
the user cache directory; the first job extracts it. The engine needs macOS 26.2
or later and `ffmpeg` on `PATH`.

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-serve](https://github.com/ddalcu/mlx-serve) | MIT | Native MLX server that runs MiniMax H3. kiapi uses release v26.10.1 as a subprocess. |

## Models

| Model | License | Size | Mem | Description |
|---|---|---:|---:|---|
| [ddalcu/MiniMax-H3-REF2VA-MLX-Serve-8bit](https://huggingface.co/ddalcu/MiniMax-H3-REF2VA-MLX-Serve-8bit) | MiniMax H3 Community License | 69.3 GB | ~43 GB | `ref2va-8bit` (aliases `h3`, `minimax-h3`). 8-bit Ref2VA transformer, Qwen3-VL-32B text encoder (layer 50), video and audio VAEs. |
| [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo) | Apache-2.0 | 2.0 GB | — | `minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors`. The diffusers layout of the same LoRA matches none of mlx-serve's module names. |

The MiniMax H3 Community License excludes the EU, the UK, South Korea and the
United States, requires a separate license for commercial use above USD 20M
annual revenue, and requires "Powered by MiniMax H3" on redistribution.

## Measurements

Mac Studio M4 Max 128 GB, mlx-serve v26.10.1, 960x544, 124 frames (5.2 s),
Turbo 8 steps:

| References | Time | Peak |
|---|---:|---:|
| 1 image | 18.6 min | 37 GB |
| 3 images | 20.5 min | 36 GB |
| 2 images + 2 voices | 21.1 min | 36 GB |
| 1 video (3 s) | 30.9 min | 38 GB |
| 1 image + 1 video (5.2 s) | 50.1 min | 43 GB |

Reference images are resized to the output size and add little. Reference video
frames join the packed sequence at every step, and attention cost grows with its
square: a 5.2 s video raised a step from 125 s to 339 s. Without Turbo, 512x512 /
22 frames took 170 s for 20 steps against 83 s for 8 steps with Turbo.

Characters from image references stay recognizable, including back views and
several characters in one shot, and voices speak the given lines. Strict
preservation of a source video is weaker than MiniMax's hosted service: on the
official 768p editing case, the result kept the scene and camera move but drifted
in framing and face (SSIM 0.68 against the official output). The full
evaluation is in the
[labs write-up](https://github.com/kiarina/labs/tree/main/2026/10/04/minimax-h3-ref2va-eval).
