# kiapi

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
[![API Docs](https://img.shields.io/badge/API%20Docs-GitHub%20Pages-green.svg)](https://kiarina.github.io/kiapi/)

**English** | [日本語](README.ja.md)

## Summary

kiapi is an API server that uses a Mac Studio M4 Max with 128GB of memory at home to provide the following capabilities.

| Capability | Support |
| --- | --- |
| Chat | OpenAI Chat Completions API compatible<br>text + image + audio + video input support<br>tool call + tool choice (auto, any, specific) + parallel tool calls + streaming support |
| Embedding | text + image input support |
| Image generation | text2image, image2image, image editing, and LoRA training support |
| Music and sound-effect generation | text2audio, cover, repaint, and extract support |
| Video generation | text2video, image2video, and audio2video support |
| Web | search + fetch support |

See: [API Documents](https://kiarina.github.io/kiapi/)

> [!NOTE]
> The Mac Studio M4 Max with 128GB of memory is an example.
> Other Apple Silicon models will also work if they have sufficient unified memory.

## Resources

To provide its capabilities, kiapi downloads and uses selected resources from the list below.
Each resource is governed by its upstream license.
Always review the upstream license to confirm the terms and whether commercial use is permitted.

> [!IMPORTANT] Review date: 2026-06-23

| Domain | Family | Resource | Kind | Upstream license | Notes |
|---|---|---|---|---|---|
| chat | [chat](packages/kiapi/src/kiapi/capabilities/chat/README.md) | [mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit) | model weights | Apache-2.0 | MLX-converted Qwen3 Omni model. |
|  |  | [mlx-community/Qwen3.6-27B-4bit](https://huggingface.co/mlx-community/Qwen3.6-27B-4bit) | model weights | Apache-2.0 | MLX-converted Qwen3.6 model. |
| embedding | [embedding](packages/kiapi/src/kiapi/capabilities/embedding/README.md) | [mlx-community/Qwen3-Embedding-8B-mxfp8](https://huggingface.co/mlx-community/Qwen3-Embedding-8B-mxfp8) | model weights | Apache-2.0 | Text embedding model. |
|  |  | [mlx-community/Qwen3-VL-Embedding-2B-mxfp8](https://huggingface.co/mlx-community/Qwen3-VL-Embedding-2B-mxfp8) | model weights | Apache-2.0 | Text + image embedding model. |
| image | [zimage](packages/kiapi/src/kiapi/capabilities/zimage/README.md) | [filipstrand/Z-Image-Turbo-mflux-4bit](https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit) | model weights | Tongyi Qianwen License | Quantized MLX-compatible Z-Image Turbo; inherits the original Z-Image Turbo license. |
|  |  | [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) | model weights | Apache-2.0 | Base Z-Image model. |
|  | [flux2](packages/kiapi/src/kiapi/capabilities/flux2/README.md) | [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) | model weights | FLUX Non-Commercial License | Gated upstream model. Confirm terms before any commercial use. |
|  |  | [black-forest-labs/FLUX.2-klein-base-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B) | model weights | Apache-2.0 | Open-weight FLUX.2 Klein Base 4B variant. |
|  |  | [black-forest-labs/FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) | model weights | FLUX Non-Commercial License | Gated upstream model. Confirm terms before any commercial use. |
|  | [qwen](packages/kiapi/src/kiapi/capabilities/qwen/README.md) | [Qwen/Qwen-Image](https://huggingface.co/Qwen/Qwen-Image) | model weights | Apache-2.0 | Text-to-image model. |
|  |  | [Qwen/Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) | model weights | Apache-2.0 | Image editing model. |
|  | [ideogram4](packages/kiapi/src/kiapi/capabilities/ideogram4/README.md) | [ideogram-ai/ideogram-4-fp8](https://huggingface.co/ideogram-ai/ideogram-4-fp8) | model weights | Ideogram Non-Commercial Model Agreement | Gated upstream model. Confirm hosted-service and commercial-use terms. |
|  | [ernie](packages/kiapi/src/kiapi/capabilities/ernie/README.md) | [baidu/ERNIE-Image-Turbo](https://huggingface.co/baidu/ERNIE-Image-Turbo) | model weights | Apache-2.0 | Turbo ERNIE-Image variant. |
|  |  | [baidu/ERNIE-Image](https://huggingface.co/baidu/ERNIE-Image) | model weights | Apache-2.0 | Base ERNIE-Image variant. |
|  | [seedvr2](packages/kiapi/src/kiapi/capabilities/seedvr2/README.md) | [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) | model weights | Apache-2.0 | SeedVR2 3B and 7B upscaling checkpoints. |
|  | [depthpro](packages/kiapi/src/kiapi/capabilities/depthpro/README.md) | [apple/ml-depth-pro](https://github.com/apple/ml-depth-pro) / [depth_pro.pt](https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt) | code + model file | Apple custom license | GitHub reports `NOASSERTION`; review Apple's license text before redistribution or commercial use. |
| audio | [acestep](packages/kiapi/src/kiapi/capabilities/acestep/README.md) | [ace-step/ACE-Step-1.5](https://github.com/ace-step/ACE-Step-1.5) | Python package | MIT | Installed into the ACE-Step dedicated venv. |
|  |  | [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) | shared checkpoints | MIT | Shared ACE-Step 1.5 checkpoint resources. |
|  |  | [ACE-Step/acestep-v15-xl-base](https://huggingface.co/ACE-Step/acestep-v15-xl-base) | model weights | MIT | Extra checkpoint used by `xl-base`. |
| audio | [audiogen](packages/kiapi/src/kiapi/capabilities/audiogen/README.md) | [facebook/audiogen-medium](https://huggingface.co/facebook/audiogen-medium) | model weights | CC-BY-NC-4.0 | Non-commercial license. |
| video | [ltx2](packages/kiapi/src/kiapi/capabilities/ltx2/README.md) | [Blaizzy/mlx-video](https://github.com/Blaizzy/mlx-video) | Python package | MIT | Installed from a pinned Git commit for LTX-2 inference. |
|  |  | [prince-canuma/LTX-2-distilled](https://huggingface.co/prince-canuma/LTX-2-distilled) | model weights | Not declared upstream | The model card has no license metadata; verify rights before use. |
| web | [web](packages/kiapi/src/kiapi/capabilities/web/README.md) | [searxng/searxng](https://github.com/searxng/searxng) / `searxng/searxng:latest` | Docker image | AGPL-3.0 | Web search backend. AGPL obligations can matter for network services. |
|  |  | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) / `unclecode/crawl4ai:latest` | Docker image | Apache-2.0 | Web fetch backend. |

## Design

**Reliably provide every capability:**

- Queue non-administrative requests and process them one at a time
- Manage API server memory to prevent overcommit failures

**Support interactive integration with LLM agents:**

- Provide LLMs with tips as well as I/O specifications through `openapi.json`
- Run generation tasks in both sync and async modes
- Make asynchronous task progress observable

**Provide secure external access to kiapi inside a closed network:**

- **Relay:**
  - Provide a pluggable shared transport for reaching the kiapi server (watch / request)
  - Provide the [gcp](packages/kiapi-relay/src/kiapi_relay/gcp/README.md) implementation backed by Firebase Realtime Database and Google Cloud Storage
- **Proxy server:**
  - A proxy server that forwards HTTP requests to kiapi over the relay and returns the results
  - The proxy is lightweight and runs on any OS

> [!NOTE]
> See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

## Packages

This project publishes the following three packages.

| Package | Description | Runs on |
| --- | --- | --- |
| [kiapi](packages/kiapi/README.md) | Local API server that uses Apple Silicon and MLX to provide generative AI capabilities.<br>Provides the `kiapi` command for managing and starting kiapi. | Apple Silicon (macOS) |
| [kiapi-relay](packages/kiapi-relay/README.md) | Library that implements the relay functionality.<br>Used by both kiapi and kiapi-proxy. | Any platform |
| [kiapi-proxy](packages/kiapi-proxy/README.md) | Proxy server that relays requests to kiapi.<br>Runs on low-spec machines regardless of OS. | Linux / Windows / macOS |

See each package README linked above for usage instructions.

## Project Status

> [!NOTE]
> kiapi is OSS developed mainly for personal use.
> The API, supported models, and setup instructions may change in the future.
> Issues and pull requests are welcome, but support is best-effort because this is a personal project.
