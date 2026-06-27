# kiapi

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
[![API Docs](https://img.shields.io/badge/API%20Docs-GitHub%20Pages-green.svg)](https://kiarina.github.io/kiapi/)

[English](README.md) | **日本語**

## Summary

kiapi は、自宅にある Mac Studio M4 Max 128GB を使って、下記の機能を提供する API サーバーです。

| 機能 | 対応内容 |
| --- | --- |
| チャット | OpenAI Chat Completions API 互換<br>text + image + audio + video 入力対応<br>tool call + tool choice (auto, any, specific) + parallel tool calls + stream 対応 |
| 埋め込み | text + image 入力対応 |
| 画像生成 | text2image, image2image, image editing, LoRA 学習対応 |
| 音楽・効果音生成 | text2audio, cover, repaint, extract 対応 |
| 動画生成 | text2video, image2video, audio2video 対応 |
| Web | search + fetch 対応 |

See: [API Documents](https://kiarina.github.io/kiapi/)

> [!NOTE]
> Mac Studio M4 Max 128GB は例です。
> 十分な Unified Memory を持つ Apple Silicon であれば、他のモデルでも動作します。

## Resources

機能を提供するために、下記のリソースの中から、選択されたものをダウンロードして使用します。
使用するリソースのライセンスは、各リソースの upstream license に従います。
商用利用の可否や条件は、必ず upstream license を確認してください。

> [!IMPORTANT] 確認日: 2026-06-23

| Domain | Family | Resource | Kind | Upstream license | Notes |
|---|---|---|---|---|---|
| chat | chat | [mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit) | model weights | Apache-2.0 | MLX 変換版 Qwen3 Omni model。 |
|  |  | [mlx-community/Qwen3.6-27B-4bit](https://huggingface.co/mlx-community/Qwen3.6-27B-4bit) | model weights | Apache-2.0 | MLX 変換版 Qwen3.6 model。 |
| embedding | embedding | [mlx-community/Qwen3-Embedding-8B-mxfp8](https://huggingface.co/mlx-community/Qwen3-Embedding-8B-mxfp8) | model weights | Apache-2.0 | Text embedding model。 |
|  |  | [mlx-community/Qwen3-VL-Embedding-2B-mxfp8](https://huggingface.co/mlx-community/Qwen3-VL-Embedding-2B-mxfp8) | model weights | Apache-2.0 | Text + image embedding model。 |
| image | zimage | [filipstrand/Z-Image-Turbo-mflux-4bit](https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit) | model weights | Tongyi Qianwen License | Quantized MLX-compatible Z-Image Turbo。元の Z-Image Turbo license を継承します。 |
|  |  | [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) | model weights | Apache-2.0 | Base Z-Image model。 |
|  | flux2 | [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) | model weights | FLUX Non-Commercial License | upstream gated model。商用利用前に必ず条件を確認してください。 |
|  |  | [black-forest-labs/FLUX.2-klein-base-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B) | model weights | Apache-2.0 | Open-weight FLUX.2 Klein Base 4B variant。 |
|  |  | [black-forest-labs/FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) | model weights | FLUX Non-Commercial License | upstream gated model。商用利用前に必ず条件を確認してください。 |
|  | qwen | [Qwen/Qwen-Image](https://huggingface.co/Qwen/Qwen-Image) | model weights | Apache-2.0 | Text-to-image model。 |
|  |  | [Qwen/Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) | model weights | Apache-2.0 | Image editing model。 |
|  | ideogram4 | [ideogram-ai/ideogram-4-fp8](https://huggingface.co/ideogram-ai/ideogram-4-fp8) | model weights | Ideogram Non-Commercial Model Agreement | upstream gated model。hosted-service や商用利用の条件を確認してください。 |
|  | ernie | [baidu/ERNIE-Image-Turbo](https://huggingface.co/baidu/ERNIE-Image-Turbo) | model weights | Apache-2.0 | Turbo ERNIE-Image variant。 |
|  |  | [baidu/ERNIE-Image](https://huggingface.co/baidu/ERNIE-Image) | model weights | Apache-2.0 | Base ERNIE-Image variant。 |
|  | seedvr2 | [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) | model weights | Apache-2.0 | SeedVR2 3B / 7B upscaling checkpoints。 |
|  | depthpro | [apple/ml-depth-pro](https://github.com/apple/ml-depth-pro) / [depth_pro.pt](https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt) | code + model file | Apple custom license | GitHub metadata は `NOASSERTION`。再配布や商用利用前に Apple の license text を確認してください。 |
| audio | acestep | [ace-step/ACE-Step-1.5](https://github.com/ace-step/ACE-Step-1.5) | Python package | MIT | ACE-Step 専用 venv にインストールされます。 |
|  |  | [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) | shared checkpoints | MIT | ACE-Step 1.5 の共有 checkpoint resource。 |
|  |  | [ACE-Step/acestep-v15-xl-base](https://huggingface.co/ACE-Step/acestep-v15-xl-base) | model weights | MIT | `xl-base` が使う追加 checkpoint。 |
| audio | audiogen | [facebook/audiogen-medium](https://huggingface.co/facebook/audiogen-medium) | model weights | CC-BY-NC-4.0 | Non-commercial license。 |
| video | ltx2 | [Blaizzy/mlx-video](https://github.com/Blaizzy/mlx-video) | Python package | MIT | LTX-2 inference 用に pinned Git commit からインストールされます。 |
|  |  | [prince-canuma/LTX-2-distilled](https://huggingface.co/prince-canuma/LTX-2-distilled) | model weights | Not declared upstream | model card に license metadata がないため、利用前に権利関係を確認してください。 |
| web | web | [searxng/searxng](https://github.com/searxng/searxng) / `searxng/searxng:latest` | Docker image | AGPL-3.0 | Web search backend。network service では AGPL の義務が重要になる場合があります。 |
|  |  | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) / `unclecode/crawl4ai:latest` | Docker image | Apache-2.0 | Web fetch backend。 |

## Design

**全ての機能を安定して供給できる:**
- 管理系機能以外のリクエストは、処理はキューイングして 1 つずつ実行する
- API サーバーが使うメモリを管理し、破綻させない

**LLM エージェントとの対話的な連携が可能:**
- openapi.json を通じて LLM に I/O 以外に TIPS も提供する
- 生成タスクを sync / async の両方で実行できる
- 非同期タスクの進捗が把握できる

**閉鎖環境内の kiapi に、外部から安全にアクセスできる:**
- **relay 機能:**
  - kiapi に到達するための共有トランスポートの抽象
  - Firebase Realtime Database + Google Cloud Storage による実装
- **proxy サーバー:**
  - HTTP リクエストを relay 経由で kiapi に転送し、結果を返す Proxy サーバ
  - proxy は軽量で OS を問わず動作します

## Packages

このプロジェクトでは、下記の 3 つのパッケージを公開しています。

| Package | 説明 | 動作環境 |
| --- | --- | --- |
| [kiapi](packages/kiapi/README.ja.md) | Apple Silicon と MLX を活用し、生成 AI 機能を提供するローカル API サーバー。<br>kiapi の管理・起動用の kiapi コマンドを提供します。 | Apple Silicon (macOS) |
| [kiapi-relay](packages/kiapi-relay/README.ja.md) | relay 機能を実装したライブラリ。<br>kiapi, kiapi-proxy の双方から利用されます。 | 全プラットフォーム |
| [kiapi-proxy](packages/kiapi-proxy/README.ja.md) | kiapi へのリクエストを relay 機能で中継する Proxy サーバー。<br>OS に依存せず、スペックの低いマシンでも動作します。 | Linux / Windows / macOS |

利用方法は、上記のリンクから各パッケージの README を参照してください。

## Architecture

> [!NOTE]
> アーキテクチャの詳細は [ARCHITECTURE.ja.md](ARCHITECTURE.ja.md) を参照してください。

## Project Status

> [!NOTE]
> kiapi は個人利用を主目的に開発している OSS です。
> API、対応モデル、セットアップ手順は今後変更される可能性があります。
> Issue や Pull Request は歓迎しますが、個人プロジェクトのため対応はベストエフォートです。
