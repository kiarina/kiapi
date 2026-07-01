# GCP Relay

[English](README.md) | **日本語**

## Overview

`GCPRelay` を使うと、閉鎖ネットワーク内の kiapi server が inbound endpoint を公開せずに
API request を受け取れます。

- Firebase Realtime Database（RTDB）で request、progress、result の通知を行います。
- Google Cloud Storage（GCS）で request / response payload を受け渡します。
- relay は process 内の FastAPI app を直接呼び出します。
- relay delivery は 1 件ずつ処理します。

この文書では、GCP resource、認証、権限、kiapi 設定、基本的な end-to-end 検証手順を
まとめます。

## Architecture

```text
requester
  ├─ GCS:  {prefix}/sessions/{session_id}/request.json
  └─ RTDB: {prefix}/nodes/{kiapi_node_id}/requests/{session_id}
                         │
                         ▼
                    GCPRelay
                         │
                         ├─ queued / running 通知
                         ├─ process 内 kiapi API call
                         ├─ GCS response.json / response.body
                         └─ atomic RTDB result + request 削除
```

requester と kiapi relay は別の service account を使用できます。本番環境では identity を
分離し、それぞれに必要な権限だけを付与することを推奨します。

### Node identity and discovery

各側は初回起動時に自分の `node_id` を生成し、user data directory に永続化します。
そのため identity は再起動をまたいで安定し、手動設定は不要です。kiapi node は
`{prefix}/liveness/{node_id}` へ `heartbeat_interval_s` ごとに liveness heartbeat を
publish し、正常終了時に削除します。requester は `{prefix}/liveness` を read し、
`liveness_ttl_s` 以内で最も新しい heartbeat の node を選んで request を送ります。
その window 内に report した node がない場合、request は `no_relay_node` で失敗します。

## Setup

### Prerequisites

Google Cloud Storage client と Google authentication helper を利用できるように、
`relay-gcp` extra 付きで kiapi をインストールしてください。

```sh
uv tool install --python 3.12 "kiapi[relay-gcp]"
```

setup task には relay node 上で次の CLI が必要です。

- `gcloud`（Project Owner 相当のアカウントで `gcloud auth login` 済み）
- `firebase-tools`（`firebase login` 済み）。project-local な dev dependency なので、
  `mise run setup`（またはリポジトリルートで `pnpm install`）で導入され、mise が `PATH`
  に載せます。
- 対話プロンプト用の `fzf` と `jq`

### Automated Setup

`kiapi-relay` パッケージディレクトリから setup task を実行します。

```sh
cd packages/kiapi-relay
mise run gcp:setup
```

task が relay に必要な resource を一括で provision し、`kiapi config edit` に貼り付ける
kiapi YAML を出力します。

- Google Cloud project を選択する
- private で uniform-access な GCS bucket を作成し（default 名 `{project_id}-kiapi`、
  default region `asia-northeast1`）、`{prefix}/sessions/` object を 1 日で削除する
  lifecycle rule を設定する
- project に Firebase を追加し、Realtime Database instance を作成して（default location
  `asia-southeast1`）、正しい `database_url` を導出する
- 認証を設定し、relay identity に bucket の `roles/storage.objectUser` と project の
  `roles/firebasedatabase.admin` を付与する

既存の bucket と RTDB instance は検出してそのまま残すため、task は再実行しても安全です。

> named RTDB instance は Blaze（従量課金）プランが必要です。作成に失敗した場合は
> [Firebase console](https://console.firebase.google.com/) で project をアップグレードして
> task を再実行してください。

### Authentication methods

GCPRelay は
[`kiarina-lib-google`](https://github.com/kiarina/kiarina-python/tree/main/packages/kiarina-lib-google)
から credential を取得します。次の OAuth scope を要求し、後ろの 2 つは RTDB REST API の
必須 scope です。

```text
https://www.googleapis.com/auth/cloud-platform
https://www.googleapis.com/auth/firebase.database
https://www.googleapis.com/auth/userinfo.email
```

task は 3 つの方法を提供します。

- **Application Default Credentials**（default）— 上記 scope 付きで
  `gcloud auth application-default login` を実行します。開発時に便利ですが、login した
  user に relay role が必要です。無人の本番実行に推奨する credential ではありません。
- **Service Account** — JSON key を作成します（default `~/.config/kiapi-relay/gcp/key.json`、
  `chmod 600`）。service account key は長期間有効なため、file を commit したり公開したり
  しないでください。
- **Impersonation** — ADC user に target service account の
  `roles/iam.serviceAccountTokenCreator` を付与し、key の保存を避けます。

`roles/storage.objectUser` は relay が必要とする object read/create/update/delete 権限を
提供します。bucket lifecycle の管理権限は含まないため、task 自身が lifecycle rule を設定し、
`manage_bucket_lifecycle: false` を出力します。`roles/firebasedatabase.admin` は RTDB への
完全な read/write access を付与します。いずれも強い権限のため、組織の least-privilege policy
に照らして割り当てを確認してください。

### kiapi Configuration

task は次のような block（ADC の例）を出力するので、`kiapi config edit` で追加します。

```yaml
kiapi.core.relay:
  default: gcp

kiapi.relay.gcp:
  database_url: https://your-instance.asia-southeast1.firebasedatabase.app
  bucket: your-project-kiapi
  google_settings_key: relay
  manage_bucket_lifecycle: false

kiarina.lib.google:
  default: relay
  configs:
    relay:
      type: default
      project_id: your-project-id
```

service account key の場合は `type: service_account` と `service_account_file` を、
impersonation の場合は `type: default` と `impersonate_service_account` を使用します。

`prefix` は既定で空となり relay object を bucket と database の root 直下に置くため、
ここでは省略しています。1 つの bucket や database を複数の分離した relay で共有する場合
にのみ指定してください。

`kiapi service` で実行する場合は、shell だけの environment variable より YAML を使用して
ください。login や reboot 後も background service が同じ設定を受け取る必要があります。

### Environment Variables

foreground process では次のように設定できます。

```sh
export KIAPI_RELAY_DEFAULT="gcp"
export KIAPI_RELAY_GCP_DATABASE_URL="https://your-instance.asia-southeast1.firebasedatabase.app"
export KIAPI_RELAY_GCP_BUCKET="your-project-kiapi"
export KIAPI_RELAY_GCP_MANAGE_BUCKET_LIFECYCLE="false"

kiapi run
```

`KIAPI_RELAY_DEFAULT="gcp"` の代わりに `kiapi run --relay gcp` も使用できます。

## Start

最初は foreground で起動します。

```sh
kiapi run --relay gcp
```

foreground での確認後、background service を install または restart します。

```sh
kiapi service install
kiapi service start
kiapi service status
```

GCP initialization に失敗した場合、設定済み relay を無視して動作するのではなく、kiapi の
起動自体が失敗します。

## Requester Contract

### GCS Request

最初に次の object を書き込みます。

```text
{prefix}/sessions/{session_id}/request.json
```

例:

```json
{
  "method": "POST",
  "path": "/v1/embedding",
  "headers": {
    "accept": "application/json"
  },
  "body": {
    "model": "qwen3-embedding-8b",
    "input": "hello"
  }
}
```

`path` は `/` で始まる absolute local path である必要があります。external URL は拒否されます。
`KIAPI_AUTH_TOKEN` を設定している場合は、対応する `Authorization: Bearer ...` header を
含めてください。

`POST /v1/files` のような multipart endpoint では、`body` ではなく `multipart` を使います。

```json
{
  "method": "POST",
  "path": "/v1/files",
  "headers": {
    "accept": "application/json"
  },
  "multipart": {
    "files": [
      {
        "field": "file",
        "filename": "input.png",
        "content_type": "image/png",
        "content_base64": "BASE64_ENCODED_BYTES"
      }
    ]
  }
}
```

### RTDB Notification

`request.json` の upload 後、次の path に書き込みます。

```text
{prefix}/nodes/{kiapi_node_id}/requests/{session_id}
```

```json
{
  "session_id": "SESSION_ID",
  "source_node_id": "requester-1"
}
```

requester は次の path を watch します。

```text
{prefix}/nodes/{requester_node_id}/responses/{session_id}
```

### Progress and Result

progress status:

- `queued`: request を検知して relay queue に追加済み
- `running`: relay が local API call を開始済み

terminal status:

- `succeeded`: response object の GCS commit が完了
- `failed`: response commit 前に bridge が失敗

JSON API response は次に保存されます。

```text
{prefix}/sessions/{session_id}/response.json
```

binary API response は次の順序で保存されます。

```text
{prefix}/sessions/{session_id}/response.body
{prefix}/sessions/{session_id}/response.json
```

`response.json` は commit marker で、GCS generation precondition を使って作成します。
restart や duplicate execution 後にすでに存在する場合、relay は API request を再 dispatch
せず、commit 済み response を通知します。

## Verification

setup task で選択した値を設定します（`NODE_ID` は kiapi が自動生成します。node の data
dir の `<data_dir>/node_id`、または `{prefix}/liveness` の一覧から取得してください）。

```sh
export BUCKET="your-project-kiapi"
export DATABASE_URL="https://your-instance.asia-southeast1.firebasedatabase.app"
export PREFIX=""  # root の場合は空、または設定した prefix
export NODE_ID="studio-1"
```

GCS access を確認します。

```sh
gcloud storage ls "gs://${BUCKET}"
```

ADC access token で RTDB の authenticated read を確認します
（`${PREFIX:+${PREFIX}/}` は prefix を設定した場合のみ segment を挿入します）。

```sh
ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"

curl --fail --silent --show-error \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${DATABASE_URL}/${PREFIX:+${PREFIX}/}nodes/${NODE_ID}/requests.json"
```

次に kiapi を起動し、requester から小さな CPU-only request または activate 済み API request
を 1 件送信します。次を確認してください。

1. requester response path に `queued` が表示される
2. `running` に置き換わる
3. GCS に `response.json` が作成される
4. RTDB が `succeeded` になる
5. 元の request notification が削除される

## Troubleshooting

### RTDB Returns 401 or 403

- credential に `firebase.database` と `userinfo.email` scope が含まれることを確認する
- service account または user に Firebase project への access があることを確認する
- `database_url` が対象 RTDB instance の正確な URL であることを確認する
- RTDB Security Rules と IAM assignment を確認する

### GCS Returns 403

- principal が正しい bucket の object access を持つことを確認する
- `manage_bucket_lifecycle: true` の場合は `storage.buckets.get` と
  `storage.buckets.update` も付与する
- `project_id` と `bucket` が意図した同じ environment を指していることを確認する

### Startup Fails While Updating Lifecycle

bucket metadata 権限を付与するか、kiapi 外で lifecycle rule を設定して次を指定します。

```yaml
kiapi.relay.gcp:
  manage_bucket_lifecycle: false
```

### Requests Stay queued

- local kiapi API request が別の relay delivery の後ろで待機していないか確認する
- internal kiapi worker が長時間 job を処理していないか確認する
- request path と JSON body が対象 API schema に一致することを確認する

### Duplicate Processing

各 kiapi process は自分の `node_id` を user data directory から導出し（初回起動時に自動
生成し、以降は再利用）、同じ directory 内の single-instance lock により 2 つめの process
が同じ identity を共有することを防ぎます。別の node を動かす場合は別の data directory から
起動すれば、別の `node_id` になります。GCS はさらに `response.json` commit marker の重複
作成を防ぎます。

## Security Notes

- 専用 private bucket と専用 RTDB prefix を使用する
- requester と relay の identity を分離する
- key file より service account impersonation または workload identity を優先する
- service account key、API auth token、prompt、生成 relay payload を commit しない
- RTDB Security Rules を public にしない
- relay service account を対象 project / bucket に限定する
- request header には kiapi API auth token が含まれ得るため secret として扱う
- random で推測困難な `session_id` を使用する
- `prefix` や GCS object name に secret を含めない

## Settings Reference

| Setting | Environment variable | Default | Description |
|---|---|---:|---|
| `kiapi.core.relay.default` | `KIAPI_RELAY_DEFAULT` | disabled | GCPRelay を有効化するには `gcp` を指定。 |
| `database_url` | `KIAPI_RELAY_GCP_DATABASE_URL` | required | 正確な HTTPS RTDB instance URL。 |
| `bucket` | `KIAPI_RELAY_GCP_BUCKET` | required | `gs://` を除いた private GCS bucket name。 |
| `prefix` | `KIAPI_RELAY_GCP_PREFIX` | 空 | RTDB / GCS で共通の prefix。空の場合は root を直接使用。 |
| `google_settings_key` | `KIAPI_RELAY_GCP_GOOGLE_SETTINGS_KEY` | default Google config | 使用する `kiarina.lib.google` の named credential 設定。 |
| `lifecycle_age_days` | `KIAPI_RELAY_GCP_LIFECYCLE_AGE_DAYS` | `1` | managed GCS delete rule の age。 |
| `manage_bucket_lifecycle` | `KIAPI_RELAY_GCP_MANAGE_BUCKET_LIFECYCLE` | `true` | 起動時に GCPRelay が bucket lifecycle を更新するか。 |
| `reconnect_delay_s` | `KIAPI_RELAY_GCP_RECONNECT_DELAY_S` | `1.0` | RTDB SSE watch の再接続までの delay。 |
| `heartbeat_interval_s` | `KIAPI_RELAY_GCP_HEARTBEAT_INTERVAL_S` | `300.0` | kiapi node が `{prefix}/liveness/{node_id}` の liveness を更新する間隔。 |
| `liveness_ttl_s` | `KIAPI_RELAY_GCP_LIVENESS_TTL_S` | `1800.0` | この時間より新しい heartbeat の node だけが選択対象。client はその中で最新を選ぶ。 |

## Official References

- [Authenticate RTDB REST requests](https://firebase.google.com/docs/database/rest/auth)
- [RTDB REST setup](https://firebase.google.com/docs/database/rest/start)
- [RTDB Security Rules](https://firebase.google.com/docs/database/security)
- [Firebase predefined roles](https://firebase.google.com/docs/projects/iam/roles-predefined)
- [Cloud Storage IAM roles](https://cloud.google.com/storage/docs/access-control/iam-roles)
- [Manage Cloud Storage object lifecycles](https://cloud.google.com/storage/docs/managing-lifecycles)
- [Application Default Credentials login](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login)
