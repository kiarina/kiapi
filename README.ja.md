# kiapi

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Apple%20Silicon-lightgrey.svg)
[![API Docs](https://img.shields.io/badge/API%20Docs-GitHub%20Pages-green.svg)](https://kiarina.github.io/kiapi/)

[English](README.md) | **日本語**

## Summary

kiapi は、**Mac Studio M4 Max 128GB** を使って、
**LLM エージェント**に下記の能力を提供するための **API サーバー**です。

- **チャット:**
  - OpenAI Chat Completions API 互換
  - text + image + audio + video 入力対応
  - tool call + tool choice (auto, any, specific) + parallel tool calls + stream 対応
- **埋め込み:**
  - text + image 入力対応
- **画像生成:**
  - text2image, image2image, image editing, LoRA 学習対応
- **音楽・効果音生成:**
  - text2audio, cover, repaint, extract 対応
- **動画生成:**
  - text2video, image2video, audio2video 対応
- **Web:**
  - search + fetch 対応

1 台の PC で全ての能力を安定して供給するために、下記のような特徴を持ちます。

- GPU を使う処理はキューイングして **1 つずつ実行** する
- アプリが使う **メモリを管理** し、破綻させない

また、LLM エージェントが、kiapi の能力を把握しやすいようにしています。

- API サーバー自体が、LLM に対して **使い方を説明できる**
- 非同期タスクの **進捗が把握できる**
- 生成タスクを **sync / async** の両方で実行できる

> [!IMPORTANT]
>
> kiapi は MIT ライセンスの OSS ですが、提供するパッケージやモデルのライセンスは様々です。
> 利用前に、各機能の詳細ページで、依存パッケージやモデルを確認し、
> 利用するモデルのライセンスを確認してください。

## Model and Dependency Licenses

下記は、kiapi が activate できる既定モデルと
runtime resource の upstream ライセンスをまとめた確認用一覧です。
法的助言ではありません。

ライセンス表記や gated 状態は upstream 側で変更される可能性があるため、
商用利用、再配布、hosted service としての提供を行う前に、
必ずリンク先の原文を確認してください。

確認日: 2026-06-23。

| Domain | Family | Resource | Kind | Upstream license | Notes |
|---|---|---|---|---|---|
| chat | chat | [mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit) | model weights | Apache-2.0 | MLX 変換版 Qwen3 Omni model。 |
| chat | chat | [mlx-community/Qwen3.6-27B-4bit](https://huggingface.co/mlx-community/Qwen3.6-27B-4bit) | model weights | Apache-2.0 | MLX 変換版 Qwen3.6 model。 |
| embedding | embedding | [mlx-community/Qwen3-Embedding-8B-mxfp8](https://huggingface.co/mlx-community/Qwen3-Embedding-8B-mxfp8) | model weights | Apache-2.0 | Text embedding model。 |
| embedding | embedding | [mlx-community/Qwen3-VL-Embedding-2B-mxfp8](https://huggingface.co/mlx-community/Qwen3-VL-Embedding-2B-mxfp8) | model weights | Apache-2.0 | Text + image embedding model。 |
| image | zimage | [filipstrand/Z-Image-Turbo-mflux-4bit](https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit) | model weights | Tongyi Qianwen License | Quantized MLX-compatible Z-Image Turbo。元の Z-Image Turbo license を継承します。 |
| image | zimage | [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) | model weights | Apache-2.0 | Base Z-Image model。 |
| image | flux2 | [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) | model weights | FLUX Non-Commercial License | upstream gated model。商用利用前に必ず条件を確認してください。 |
| image | flux2 | [black-forest-labs/FLUX.2-klein-base-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B) | model weights | Apache-2.0 | Open-weight FLUX.2 Klein Base 4B variant。 |
| image | flux2 | [black-forest-labs/FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) | model weights | FLUX Non-Commercial License | upstream gated model。商用利用前に必ず条件を確認してください。 |
| image | qwen | [Qwen/Qwen-Image](https://huggingface.co/Qwen/Qwen-Image) | model weights | Apache-2.0 | Text-to-image model。 |
| image | qwen | [Qwen/Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) | model weights | Apache-2.0 | Image editing model。 |
| image | ideogram4 | [ideogram-ai/ideogram-4-fp8](https://huggingface.co/ideogram-ai/ideogram-4-fp8) | model weights | Ideogram Non-Commercial Model Agreement | upstream gated model。hosted-service や商用利用の条件を確認してください。 |
| image | ernie | [baidu/ERNIE-Image-Turbo](https://huggingface.co/baidu/ERNIE-Image-Turbo) | model weights | Apache-2.0 | Turbo ERNIE-Image variant。 |
| image | ernie | [baidu/ERNIE-Image](https://huggingface.co/baidu/ERNIE-Image) | model weights | Apache-2.0 | Base ERNIE-Image variant。 |
| image | seedvr2 | [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) | model weights | Apache-2.0 | SeedVR2 3B / 7B upscaling checkpoints。 |
| image | depthpro | [apple/ml-depth-pro](https://github.com/apple/ml-depth-pro) / [depth_pro.pt](https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt) | code + model file | Apple custom license | GitHub metadata は `NOASSERTION`。再配布や商用利用前に Apple の license text を確認してください。 |
| audio | acestep | [ace-step/ACE-Step-1.5](https://github.com/ace-step/ACE-Step-1.5) | Python package | MIT | ACE-Step 専用 venv にインストールされます。 |
| audio | acestep | [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) | shared checkpoints | MIT | ACE-Step 1.5 の共有 checkpoint resource。 |
| audio | acestep | [ACE-Step/acestep-v15-xl-base](https://huggingface.co/ACE-Step/acestep-v15-xl-base) | model weights | MIT | `xl-base` が使う追加 checkpoint。 |
| audio | audiogen | [facebook/audiogen-medium](https://huggingface.co/facebook/audiogen-medium) | model weights | CC-BY-NC-4.0 | Non-commercial license。 |
| video | ltx2 | [Blaizzy/mlx-video](https://github.com/Blaizzy/mlx-video) | Python package | MIT | LTX-2 inference 用に pinned Git commit からインストールされます。 |
| video | ltx2 | [prince-canuma/LTX-2-distilled](https://huggingface.co/prince-canuma/LTX-2-distilled) | model weights | Not declared upstream | model card に license metadata がないため、利用前に権利関係を確認してください。 |
| web | web | [searxng/searxng](https://github.com/searxng/searxng) / `searxng/searxng:latest` | Docker image | AGPL-3.0 | Web search backend。network service では AGPL の義務が重要になる場合があります。 |
| web | web | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) / `unclecode/crawl4ai:latest` | Docker image | Apache-2.0 | Web fetch backend。 |

## API

| Domain | Family | Endpoint | Description |
|---|---|---|---|
| chat |  | `POST /v1/chat` | [Chat API の詳細はこちら](./kiapi/capabilities/chat/README.ja.md) |
| embedding |  | `POST /v1/embedding` | [Embedding API の詳細はこちら](./kiapi/capabilities/embedding/README.ja.md) |
| image | zimage | `POST /v1/image/zimage` | [Z-Image API の詳細はこちら](./kiapi/capabilities/zimage/README.ja.md) |
|  | flux2 | `POST /v1/image/flux2` | [FLUX.2 API の詳細はこちら](./kiapi/capabilities/flux2/README.ja.md) |
|  | qwen | `POST /v1/image/qwen` | [Qwen Image API の詳細はこちら](./kiapi/capabilities/qwen/README.ja.md) |
|  | ideogram4 | `POST /v1/image/ideogram4` | [Ideogram 4 API の詳細はこちら](./kiapi/capabilities/ideogram4/README.ja.md) |
|  | ernie | `POST /v1/image/ernie` | [ERNIE-Image API の詳細はこちら](./kiapi/capabilities/ernie/README.ja.md) |
|  | seedvr2 | `POST /v1/image/seedvr2` | [SeedVR2 API の詳細はこちら](./kiapi/capabilities/seedvr2/README.ja.md) |
|  | depthpro | `POST /v1/image/depthpro` | [Depth Pro API の詳細はこちら](./kiapi/capabilities/depthpro/README.ja.md) |
| audio | acestep | `POST /v1/audio/acestep` | [ACE-Step API の詳細はこちら](./kiapi/capabilities/acestep/README.ja.md) |
|  | audiogen | `POST /v1/audio/audiogen` | [AudioGen API の詳細はこちら](./kiapi/capabilities/audiogen/README.ja.md) |
| video | ltx2 | `POST /v1/video/ltx2` | [LTX-2 API の詳細はこちら](./kiapi/capabilities/ltx2/README.ja.md) |
| web |  | `POST /v1/web` | [Web API の詳細はこちら](./kiapi/capabilities/web/README.ja.md) |
| core | files | `POST /v1/files` | 入力ファイルや LoRA adapter などをアップロードし、`file_id` を発行する。 |
|  |  | `GET /v1/files` | 保存済みファイルの一覧を返す。 |
|  |  | `GET /v1/files/{file_id}` | ファイルメタデータを返す。 |
|  |  | `GET /v1/files/{file_id}/download` | ファイル本体をダウンロードする。 |
|  |  | `DELETE /v1/files/{file_id}` | 保存済みファイルを削除する。 |
|  | jobs | `GET /v1/jobs` | 生成ジョブの一覧を返す。 |
|  |  | `GET /v1/jobs/{job_id}` | ジョブの状態、進捗、結果、成果物 `file_id` を返す。 |
|  |  | `DELETE /v1/jobs/{job_id}` | ジョブストアからジョブを削除する。実行中ジョブは中断されない。 |
|  | openapi | `GET /openapi.json` | 共通 API と各 capability のドキュメント URL を返す。 |
|  |  | `GET /v1/{domain}/{family}/openapi.json` | 各 family の詳細な入出力仕様、使い方、TIPS、例を返す。 |
|  | health | `GET /health` | サーバー状態、warmup、キュー長、メモリ使用状況を返す。 |

## API Docs

- [kiapi API Docs](https://kiarina.github.io/kiapi/)
  - [OpenAPI JSON](https://kiarina.github.io/kiapi/openapi.json)
  - [Swagger UI](https://kiarina.github.io/kiapi/docs.html)
  - [ReDoc](https://kiarina.github.io/kiapi/redoc.html)

## Requirements

- macOS / Apple Silicon
- Python `>=3.12,<3.13`
- `uv`（任意。CLI tool として隔離インストールしたい場合や、`kiapi activate` が行う venv 作成・package install を高速化したい場合に推奨）
- `mise`（開発で使用）
- Docker（Web capability を使う場合）
- モデル重みや Docker image を保存するための十分なディスク容量

kiapi は主に **Mac Studio M4 Max 128GB** での個人利用を想定して開発しています。
他の Apple Silicon 環境でも一部または全部の機能が動作する可能性はありますが、
主な検証対象ではありません。

メモリ予算は `KIAPI_MEMORY_LIMIT_GB` で明示指定できます。未指定の場合は、
起動時に搭載メモリの 80% を自動で実効予算にします。モデルの必要メモリが
この予算に収まらない場合、リクエストはメモリ予算不足として 503 を返します。

`kiapi activate --all` は、モデル重みや Docker image を含めて
600GB 弱のディスク容量を使用します。最初は必要な capability だけを
`kiapi activate` で選択してセットアップすることをおすすめします。

## Quick Start

**インストールからエージェント連携まで:**

```sh
# kiapi 本体のインストール
python3.12 -m pip install --upgrade kiapi  # uv を使えない場合
uv tool install --python 3.12 kiapi  # uv を使える場合

# デフォルトのホスト・ポートやメモリ予算を変更（必要な場合）
kiapi config init
kiapi config edit

# セットアップ状態の確認
kiapi status

# モデル重み、Docker image、専用 venv の明示的なセットアップ
kiapi activate  # 表示されるリストから対象を選択してセットアップする場合
kiapi activate --all  # 全てをセットアップする場合 (600GB 弱)
kiapi activate --family acestep  # 指定した family だけをセットアップする場合

# 動作確認
kiapi check  # 表示されるリストから対象を選択して動作確認する場合
kiapi check --all  # 全てを動作確認する場合

# API サーバーの起動
kiapi run  # 127.0.0.1:8000 で起動
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
# サービスへの登録
kiapi service install

# サービス起動
kiapi service start

# サービス状態とログ末尾の確認
kiapi service status

# サービス停止
kiapi service stop

# サービス削除
kiapi service uninstall
```

## Remote Job Relay

オプションの GCP relay を使うと、閉鎖ネットワーク内の kiapi node に inbound socket を
公開せず API 処理を依頼できます。小さな通知は Firebase Realtime Database、request /
response body は Cloud Storage で受け渡します。
有効にするには、`relay-gcp` extra 付きで kiapi をインストールしてください。

```sh
python3.12 -m pip install --upgrade "kiapi[relay-gcp]"
uv tool install --python 3.12 "kiapi[relay-gcp]"
```

```sh
export KIAPI_RELAY_GCP_NODE_ID="studio-1"
export KIAPI_RELAY_GCP_DATABASE_URL="https://PROJECT.firebaseio.com"
export KIAPI_RELAY_GCP_BUCKET="PRIVATE_RELAY_BUCKET"
export KIAPI_RELAY_GCP_PREFIX="private/kiapi"

# 既定では Application Default Credentials を使用
kiapi run --relay gcp
```

requester は GCS の
`{prefix}/sessions/{session_id}/request.json` を書き込んだ後、RTDB の
`{prefix}/nodes/{node_id}/requests/{session_id}` へ通知を書き込みます。relay は
requester node の `responses` path へ `queued`、`running`、terminal result を通知します。

- request は process 内の FastAPI app へ直接 dispatch され、relay が 1 件ずつ処理します。
- JSON response は `response.json`、binary response は `response.body` の後に
  `response.json` を書き込みます。
- `response.json` は GCS の create-only generation precondition で排他します。再起動後に
  完了済み response が見つかった場合、API を再実行せず結果を再通知します。
- terminal RTDB response の通知と request 削除は 1 回の atomic multi-location update
  で行います。
- 起動時に session object を 1 日後に削除する prefix 限定 lifecycle rule を設定します。
  infrastructure 側で管理する場合は
  `KIAPI_RELAY_GCP_MANAGE_BUCKET_LIFECYCLE=false` を指定してください。

専用 bucket と必要最小限の RTDB / GCS 権限を使用してください。Google credential は
[`kiarina-lib-google`](https://github.com/kiarina/kiarina-python/tree/main/packages/kiarina-lib-google)
で設定します。

resource 作成、IAM、認証、設定、検証手順は
[GCP Relay setup](kiapi/relay/gcp/README.ja.md) を参照してください。

## Architecture

> [!NOTE]
>
> kiapi のアーキテクチャの詳細は [ARCHITECTURE.ja.md](./ARCHITECTURE.ja.md) を参照してください。

## Local Storage

kiapi が実行中にローカルへ書き込む主な場所は次の通りです。

| 用途 | 設定 | 既定値 | 備考 |
|---|---|---|---|
| Files API のアップロード・生成成果物・URL/data URL 入力 | `KIAPI_FILES_ROOT` | `/tmp/kiapi/files` | `file_id` で参照される保存先。既定では OS の再起動や tmp cleanup で消える可能性があります。長期保存したい場合は `~/.kiapi/files` や外部ディスクに変更してください。 |
| リクエスト処理中の一時作業ディレクトリ | `KIAPI_TMP_ROOT` | `/tmp/kiapi/work` | chat/embedding の入力展開、生成前の中間ファイル、LoRA 学習作業など。 |
| Web backend subprocess log | `KIAPI_WEB_BACKEND_LOG_DIR` | `/tmp/kiapi/logs/web` | SearXNG / Crawl4AI Docker subprocess の stdout/stderr。 |
| ACE-Step 専用 venv / project / checkpoints | `KIAPI_ACESTEP_PYTHON_PATH`, `KIAPI_ACESTEP_PROJECT_ROOT`, `KIAPI_ACESTEP_CHECKPOINT_DIR` | `KIAPI_USER_DATA_DIR` または platformdirs の user data dir 配下の `acestep/` | `python_path`, `project_root`, `checkpoint_dir` が未指定の場合、ACE-Step 用の永続ディレクトリに venv と checkpoint を配置します。 |

上記を除くモデル重みやライブラリキャッシュは Hugging Face、mflux、Docker など
各ライブラリ・ツールの管理下に置き、kiapi は原則として独自の保存先へ移しません。

## Project Status

kiapi は個人利用を主目的に開発している OSS です。
API、対応モデル、セットアップ手順は今後変更される可能性があります。

Issue や Pull Request は歓迎しますが、個人プロジェクトのため対応はベストエフォートです。

## Security

既定では `kiapi run` は `127.0.0.1:8000` で起動します。
`--host 0.0.0.0` を指定すると他のマシンから到達できる可能性があるため、
信頼できるネットワーク内でのみ使用してください。

## Development

```sh
# 依存のインストール・テストデータのダウンロード・venv 環境の作成
make init

# 依存の同期
make update

# 依存のアップグレード
make upgrade

# ... 実装

# フォーマット・型チェック・public/ 以下のドキュメント再生成
make

# unit test
make test

# 開発サーバーを起動 (auto-reload 対応)
make dev

# GPU を使った機能テスト・回帰テスト
make verify  # 全て実行
make verify-fast  # 全てのcapabilityを、軽いテストだけ実行
make verify-one  # 1つのcapabilityだけ実行
```

## Release

kiapi のリリースは `pydantic-settings-manager` と同じく、version 更新、
changelog 更新、tag push を起点にした GitHub Release / PyPI publish で行います。

```sh
# version と CHANGELOG.md のリリース項目を更新
make bump-version

# version を明示する場合
mise run bump-version 0.2.0

# ローカル確認
make test
make
make build

# リリース commit と tag
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): prepare v0.2.0"
git tag v0.2.0
git push origin main --tags
```

`v*.*.*` tag が push されると、GitHub Actions の release workflow が
package build、`CHANGELOG.md` からの release notes 抽出、GitHub Release 作成、
PyPI publish を実行します。
