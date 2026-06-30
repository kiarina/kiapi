# kiapi

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Apple%20Silicon-lightgrey.svg)
[![API Docs](https://img.shields.io/badge/API%20Docs-GitHub%20Pages-green.svg)](https://kiarina.github.io/kiapi/)

[English](README.md) | **日本語**

## Summary

kiapi は、Apple Silicon と MLX を活用し、LLM エージェントに生成 AI 機能を提供するローカル API サーバーです。

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

See: [kiapi API Docs](https://kiarina.github.io/kiapi/)

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
export KIAPI_RELAY_GCP_DATABASE_URL="https://PROJECT.firebaseio.com"
export KIAPI_RELAY_GCP_BUCKET="PRIVATE_RELAY_BUCKET"
export KIAPI_RELAY_GCP_PREFIX="private/kiapi"

# 既定では Application Default Credentials を使用
kiapi run --relay gcp
```

各 node は初回起動時に自分の `node_id` を生成して user data directory に永続化し、
`{prefix}/liveness` 以下へ liveness heartbeat を publish します。requester は最も新しく
観測された node を選び、GCS の `{prefix}/sessions/{session_id}/request.json` を書き込んだ
後、RTDB の `{prefix}/nodes/{node_id}/requests/{session_id}` へ通知を書き込みます。relay は
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
[GCP Relay setup](../kiapi-relay/src/kiapi_relay/impl/gcp/README.ja.md) を参照してください。

GCP を使わずに relay を検証したい場合は `local` を使えます。同じ process 内 dispatch
経路を使い、通知と payload をローカルディレクトリ配下に保存します。

```sh
export KIAPI_RELAY_LOCAL_ROOT="/tmp/kiapi/relay"
export KIAPI_RELAY_LOCAL_PREFIX="private/kiapi"

kiapi run --relay local
```

requester は `{root}/{prefix}/sessions/{session_id}/request.json` を書き込んだ後、
`{root}/{prefix}/nodes/{node_id}/requests/{session_id}.json` に
`{"session_id":"...","source_node_id":"..."}` を書き込みます。relay は bridge status を
`{root}/{prefix}/nodes/{source_node_id}/responses/{session_id}.json` に書き込み、
committed response を session directory に保存します。

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

## Security

既定では `kiapi run` は `127.0.0.1:8000` で起動します。
`--host 0.0.0.0` を指定すると他のマシンから到達できる可能性があるため、
信頼できるネットワーク内でのみ使用してください。
