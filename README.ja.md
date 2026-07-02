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
| chat | [chat](packages/kiapi/src/kiapi/capabilities/chat/README.ja.md) | [mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit) | model weights | Apache-2.0 | MLX 変換版 Qwen3 Omni model。 |
|  |  | [mlx-community/Qwen3.6-27B-4bit](https://huggingface.co/mlx-community/Qwen3.6-27B-4bit) | model weights | Apache-2.0 | MLX 変換版 Qwen3.6 model。 |
| embedding | [embedding](packages/kiapi/src/kiapi/capabilities/embedding/README.ja.md) | [mlx-community/Qwen3-Embedding-8B-mxfp8](https://huggingface.co/mlx-community/Qwen3-Embedding-8B-mxfp8) | model weights | Apache-2.0 | Text embedding model。 |
|  |  | [mlx-community/Qwen3-VL-Embedding-2B-mxfp8](https://huggingface.co/mlx-community/Qwen3-VL-Embedding-2B-mxfp8) | model weights | Apache-2.0 | Text + image embedding model。 |
| image | [zimage](packages/kiapi/src/kiapi/capabilities/zimage/README.ja.md) | [filipstrand/Z-Image-Turbo-mflux-4bit](https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit) | model weights | Tongyi Qianwen License | Quantized MLX-compatible Z-Image Turbo。元の Z-Image Turbo license を継承します。 |
|  |  | [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) | model weights | Apache-2.0 | Base Z-Image model。 |
|  | [flux2](packages/kiapi/src/kiapi/capabilities/flux2/README.ja.md) | [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) | model weights | FLUX Non-Commercial License | upstream gated model。商用利用前に必ず条件を確認してください。 |
|  |  | [black-forest-labs/FLUX.2-klein-base-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B) | model weights | Apache-2.0 | Open-weight FLUX.2 Klein Base 4B variant。 |
|  |  | [black-forest-labs/FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) | model weights | FLUX Non-Commercial License | upstream gated model。商用利用前に必ず条件を確認してください。 |
|  | [qwen](packages/kiapi/src/kiapi/capabilities/qwen/README.ja.md) | [Qwen/Qwen-Image](https://huggingface.co/Qwen/Qwen-Image) | model weights | Apache-2.0 | Text-to-image model。 |
|  |  | [Qwen/Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) | model weights | Apache-2.0 | Image editing model。 |
|  | [ideogram4](packages/kiapi/src/kiapi/capabilities/ideogram4/README.ja.md) | [ideogram-ai/ideogram-4-fp8](https://huggingface.co/ideogram-ai/ideogram-4-fp8) | model weights | Ideogram Non-Commercial Model Agreement | upstream gated model。hosted-service や商用利用の条件を確認してください。 |
|  | [ernie](packages/kiapi/src/kiapi/capabilities/ernie/README.ja.md) | [baidu/ERNIE-Image-Turbo](https://huggingface.co/baidu/ERNIE-Image-Turbo) | model weights | Apache-2.0 | Turbo ERNIE-Image variant。 |
|  |  | [baidu/ERNIE-Image](https://huggingface.co/baidu/ERNIE-Image) | model weights | Apache-2.0 | Base ERNIE-Image variant。 |
|  | [seedvr2](packages/kiapi/src/kiapi/capabilities/seedvr2/README.ja.md) | [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) | model weights | Apache-2.0 | SeedVR2 3B / 7B upscaling checkpoints。 |
|  | [depthpro](packages/kiapi/src/kiapi/capabilities/depthpro/README.ja.md) | [apple/ml-depth-pro](https://github.com/apple/ml-depth-pro) / [depth_pro.pt](https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt) | code + model file | Apple custom license | GitHub metadata は `NOASSERTION`。再配布や商用利用前に Apple の license text を確認してください。 |
| audio | [acestep](packages/kiapi/src/kiapi/capabilities/acestep/README.ja.md) | [ace-step/ACE-Step-1.5](https://github.com/ace-step/ACE-Step-1.5) | Python package | MIT | ACE-Step 専用 venv にインストールされます。 |
|  |  | [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) | shared checkpoints | MIT | ACE-Step 1.5 の共有 checkpoint resource。 |
|  |  | [ACE-Step/acestep-v15-xl-base](https://huggingface.co/ACE-Step/acestep-v15-xl-base) | model weights | MIT | `xl-base` が使う追加 checkpoint。 |
| audio | [audiogen](packages/kiapi/src/kiapi/capabilities/audiogen/README.ja.md) | [facebook/audiogen-medium](https://huggingface.co/facebook/audiogen-medium) | model weights | CC-BY-NC-4.0 | Non-commercial license。 |
| video | [ltx2](packages/kiapi/src/kiapi/capabilities/ltx2/README.ja.md) | [Blaizzy/mlx-video](https://github.com/Blaizzy/mlx-video) | Python package | MIT | LTX-2 inference 用に pinned Git commit からインストールされます。 |
|  |  | [prince-canuma/LTX-2-distilled](https://huggingface.co/prince-canuma/LTX-2-distilled) | model weights | Not declared upstream | model card に license metadata がないため、利用前に権利関係を確認してください。 |
| web | [web](packages/kiapi/src/kiapi/capabilities/web/README.ja.md) | [searxng/searxng](https://github.com/searxng/searxng) / `searxng/searxng:latest` | Docker image | AGPL-3.0 | Web search backend。network service では AGPL の義務が重要になる場合があります。 |
|  |  | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) / `unclecode/crawl4ai:latest` | Docker image | Apache-2.0 | Web fetch backend。 |

> [!NOTE]
> 全てのリソースを同時に使用する場合、合計で 600GB 弱のディスク容量が必要です。
> また、Max で 50GB 弱のメモリを消費します。
> 各リソースのサイズ・消費メモリは、上記の family ごのリンク先を参照してください。

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
  - kiapi サーバーに到達するための、プラガブルな共有トランスポートを提供する (watch / request)
  - [gcp](packages/kiapi-relay/src/kiapi_relay/impl/gcp/README.ja.md) 実装（Firebase Realtime Database + Google Cloud Storage）を提供
- **proxy サーバー:**
  - HTTP リクエストを relay 経由で kiapi に転送し、結果を返す Proxy サーバ
  - proxy は軽量で OS を問わず動作します

> [!NOTE]
> 詳細は [ARCHITECTURE.ja.md](ARCHITECTURE.ja.md) を参照してください。

## Packages

このプロジェクトでは、下記の 3 つのパッケージを PyPI に公開しています。

| Package | 説明 | 動作環境 |
| --- | --- | --- |
| [kiapi](packages/kiapi/README.ja.md) | Apple Silicon と MLX を活用し、生成 AI 機能を提供するローカル API サーバー。<br>kiapi の管理・起動用の kiapi コマンドを提供します。 | Apple Silicon (macOS) |
| [kiapi-relay](packages/kiapi-relay/README.ja.md) | relay 機能を実装したライブラリ。<br>kiapi, kiapi-proxy の双方から利用されます。 | 全プラットフォーム |
| [kiapi-proxy](packages/kiapi-proxy/README.ja.md) | kiapi へのリクエストを relay 機能で中継する Proxy サーバー。<br>OS に依存せず、スペックの低いマシンでも動作します。 | Linux / Windows / macOS |

利用方法は、上記のリンクから各パッケージの README を参照してください。

## Quick Start

### kiapi

**kiapi のセットアップ:**
```sh
# kiapi インストール
python3.12 -m pip install --upgrade kiapi  # uv を使えない場合
uv tool install --python 3.12 kiapi        # uv を使える場合

# デフォルトのホスト・ポートやメモリ予算を変更（必要な場合）
kiapi config init  # 設定ファイルを作成
kiapi config edit  # 設定ファイルをエディタで編集

# セットアップ状態の確認
kiapi status

# モデル重み、Docker image、専用 venv 環境の準備
kiapi activate                   # リストから選択してセットアップする場合
kiapi activate --all             # 全てをセットアップする場合 (600GB 弱)
kiapi activate --family acestep  # 指定した family だけをセットアップする場合

# 動作確認
kiapi check        # リストから選択して動作確認する場合
kiapi check --all  # 全てを動作確認する場合
```

**LLM エージェントから使う:**
```sh
# kiapi サーバーを起動
kiapi run                             # 設定ファイルに基づいて起動 (default: 127.0.0.1:8000)
kiapi run --host 0.0.0.0 --port 8500  # ポートを指定して起動する場合

# エージェントとの連携例
codex e "
http://localhost:8000/openapi.json を把握してください。
音楽生成 API を使って、~/Downloads/bgm.wav に、「雨の中を歩く人」というテーマの 20 秒の BGM を生成してください。
"

# 生成されたファイルを確認
open ~/Downloads/bgm.wav
```

**background サービスとして起動する:**
```sh
# kiapi
kiapi service install    # 登録
kiapi service start      # 起動
kiapi service status     # 状態とログ末尾の確認
kiapi service stop       # 停止
kiapi service uninstall  # 削除
```

### kiapi[relay-gcp] + kiapi-proxy

**pre-requisite:**
- GCP プロジェクトを作成し、課金を有効化する
- Firebase プロジェクトを作成し、Blaze Plan にアップグレードする
- [gcloud](https://cloud.google.com/sdk/docs/install) をインストール
- [firebase-tools](https://firebase.google.com/docs/cli) をインストール
- [mise](https://mise.jdx.dev/getting-started.html) をインストール

**GCP 環境のセットアップ:**
対話形式で、GCS バケット、Realtime Database、認証の設定を行います。
```sh
gcloud login
firebase login
make setup-relay-gcp
```
生成された YAML テキストは kiapi, kiapi-proxy の設定ファイルに貼り付けます。
```yaml
kiapi_relay:
  default: gcp

kiapi_relay.impl.gcp:
  database_url: {database_url}
  bucket: {bucket}
  google_settings_key: relay
  manage_bucket_lifecycle: false

kiarina.lib.google:
  default: relay
  configs:
    relay:
      type: default
      project_id: {project_id}
```

**kiapi のセットアップ:**
```sh
python3.12 -m pip install --upgrade 'kiapi[relay-gcp]'  # uv を使えない場合
uv tool install --python 3.12 'kiapi[relay-gcp]'        # uv を使える場合

kiapi config init  # 設定ファイルを作成
kiapi config edit  # 設定ファイルをエディタで編集
# setup で出力された内容を貼り付けます

kiapi run --relay gcp  # GCP relay 機能を有効にして起動
```

**kiapi-proxy のセットアップ:**
kiapi-proxy は、kiapi とは別のマシンや OS でも動作します。
```sh
gcloud login

python3.12 -m pip install --upgrade 'kiapi-proxy[relay-gcp]'
uv tool install --python 3.12 'kiapi-proxy[relay-gcp]'

kiapi-proxy config init  # 設定ファイルを作成
kiapi-proxy config edit  # 設定ファイルをエディタで編集
# setup で出力された内容を貼り付けます

kiapi-proxy run --relay gcp  # GCP relay 機能を有効にして起動
```

**エージェントとの連携例**
kiapi-proxy を起動しているマシンで下記を実行します。
```sh
codex e "
http://localhost:8080/openapi.json を把握してください。
音楽生成 API を使って、~/Downloads/bgm.wav に、「雨の中を歩く人」というテーマの 20 秒の BGM を生成してください。
"

# 生成されたファイルを確認
open ~/Downloads/bgm.wav
```

## Development

```sh
make init     # 依存のインストール・テストデータのダウンロード・venv 環境の作成
make update   # 依存の同期
make upgrade  # 依存のアップグレード

# ... 実装

make       # フォーマット・型チェック・動的ドキュメントの再生成
make test  # unit test
make dev   # 開発サーバーを起動 (auto-reload 対応)

# GPU を使った機能テスト・回帰テスト
make verify       # 全て実行
make verify-fast  # 全てのcapabilityを、軽いテストだけ実行
make verify-one   # 1つのcapabilityだけ実行
```

## Release

PyPI へのリリースは、GitHub Actions の workflow によって自動化されています。

> [!NOTE]
> リリース手順の詳細は [docs/runbooks/release/](docs/runbooks/release/README.ja.md) を参照してください。

## Project Status

> [!NOTE]
> kiapi は個人利用を主目的に開発している OSS です。
> API、対応モデル、セットアップ手順は今後変更される可能性があります。
> Issue や Pull Request は歓迎しますが、個人プロジェクトのため対応はベストエフォートです。
