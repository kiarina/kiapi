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

## Prerequisites

- Firebase に追加された Google Cloud project
- Firebase Realtime Database instance
- private GCS bucket
- command 例で使用する Google Cloud CLI（`gcloud`）
- relay node にインストール済みの kiapi
- IAM、RTDB、GCS bucket を設定できる権限

例で使用する値を設定します。

```sh
export PROJECT_ID="your-project-id"
export REGION="asia-northeast1"
export BUCKET="your-private-kiapi-relay-bucket"
export DATABASE_URL="https://your-database.firebaseio.com"
export NODE_ID="studio-1"
export PREFIX="private/kiapi"
export RELAY_SERVICE_ACCOUNT="kiapi-relay@${PROJECT_ID}.iam.gserviceaccount.com"
```

RTDB の location により、database URL は `firebaseio.com` または
`firebasedatabase.app` domain になります。Firebase console に表示される正確な URL を
コピーしてください。

## GCP Setup

### Create Firebase RTDB

1. [Firebase console](https://console.firebase.google.com/) を開きます。
2. 必要であれば対象の Google Cloud project に Firebase を追加します。
3. **Build > Realtime Database** を開きます。
4. database と region を選択して作成します。
5. database URL を `DATABASE_URL` に設定します。

relay のために public read/write rule を有効化しないでください。RTDB Security Rules は
既定で access を拒否するため、認証済み server access を使用します。

relay は次の操作を行います。

- `{prefix}/nodes/{kiapi_node_id}/requests` を継続的に read する
- `{prefix}/nodes/{requester_node_id}/responses` 以下へ progress / result を write する
- 処理済み request notification を delete する
- root multi-location `PATCH` で terminal result の公開と request 削除を atomic に行う

公式文書の
[RTDB Security Rules](https://firebase.google.com/docs/database/security) と
[REST authentication](https://firebase.google.com/docs/database/rest/auth) も確認してください。

### Create GCS Bucket

uniform bucket-level access を有効にした専用 bucket を作成します。

```sh
gcloud storage buckets create "gs://${BUCKET}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --uniform-bucket-level-access
```

bucket を public にしないでください。request body、prompt、生成内容、binary response
file などが保存される可能性があります。

### Configure Lifecycle

relay session object は自動削除する必要があります。

2 つの方法を利用できます。

#### Recommended: Manage Lifecycle Outside kiapi

`lifecycle.json` を作成します。

```json
{
  "rule": [
    {
      "action": {
        "type": "Delete"
      },
      "condition": {
        "age": 1,
        "matchesPrefix": [
          "private/kiapi/sessions/"
        ]
      }
    }
  ]
}
```

適用して確認します。

```sh
gcloud storage buckets update "gs://${BUCKET}" \
  --lifecycle-file=lifecycle.json

gcloud storage buckets describe "gs://${BUCKET}" \
  --format="default(lifecycle_config)"
```

その後、kiapi に `manage_bucket_lifecycle: false` を設定します。これにより、bucket
metadata の管理を relay runtime から分離できます。

#### Alternative: Let GCPRelay Manage Lifecycle

既定の `manage_bucket_lifecycle: true` では、GCPRelay が起動時に prefix 限定の delete
rule を設定します。

relay identity には次の権限も必要です。

- `storage.buckets.get`
- `storage.buckets.update`

`roles/storage.admin` にはこれらの権限が含まれますが、広い権限です。必要な bucket
権限だけを含む custom role を推奨します。

Cloud Storage では lifecycle 設定変更の反映に最大 24 時間かかる場合があります。
[Manage object lifecycles](https://cloud.google.com/storage/docs/managing-lifecycles)
を参照してください。

### Create Service Account and IAM

relay service account を作成します。

```sh
gcloud iam service-accounts create kiapi-relay \
  --project="${PROJECT_ID}" \
  --display-name="kiapi GCP relay"
```

relay bucket の object access を付与します。

```sh
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${RELAY_SERVICE_ACCOUNT}" \
  --role="roles/storage.objectUser"
```

Firebase Realtime Database の product role を付与します。

```sh
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RELAY_SERVICE_ACCOUNT}" \
  --role="roles/firebasedatabase.admin"
```

`roles/storage.objectUser` は request の read、完了済み response の検出、response の write
に必要な object read/create/update/delete 権限を提供します。bucket lifecycle の管理権限は
含みません。

`roles/firebasedatabase.admin` は RTDB への完全な read/write access を付与する product-level
role です。Firebase Admin SDK service account も使用できます。これらは強い権限を持つため、
組織の least-privilege policy に照らして割り当てを確認してください。

公式 reference:

- [Firebase product-level IAM roles](https://firebase.google.com/docs/projects/iam/roles-predefined-product)
- [Cloud Storage IAM roles](https://cloud.google.com/storage/docs/access-control/iam-roles)

## Authentication

GCPRelay は
[`kiarina-lib-google`](https://github.com/kiarina/kiarina-python/tree/main/packages/kiarina-lib-google)
から credential を取得します。

次の OAuth scope を要求します。

```text
https://www.googleapis.com/auth/cloud-platform
https://www.googleapis.com/auth/firebase.database
https://www.googleapis.com/auth/userinfo.email
```

後ろの 2 つは RTDB REST API の必須 scope です。

### Application Default Credentials

local test では、必要な scope をすべて指定して ADC に login します。

```sh
gcloud auth application-default login \
  --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/firebase.database,https://www.googleapis.com/auth/userinfo.email"

gcloud config set project "${PROJECT_ID}"
```

login した user にも、前述した GCS / Firebase 権限が必要です。
`gcloud auth application-default login` で作成した ADC は開発時には便利ですが、無人の
本番実行に推奨する credential ではありません。

[`gcloud auth application-default login`](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login)
も参照してください。

### Service Account Key

環境上 service account key が必要な場合は、repository 外に key を保存し、kiapi の YAML
で設定します。

```sh
gcloud iam service-accounts keys create \
  "/absolute/path/to/kiapi-relay-key.json" \
  --iam-account="${RELAY_SERVICE_ACCOUNT}"
```

```yaml
kiarina.lib.google:
  default: relay
  configs:
    relay:
      type: service_account
      project_id: your-project-id
      service_account_file: /absolute/path/to/kiapi-relay-key.json
```

service account key は長期間有効な credential です。key file を commit したり、application
image にコピーしたり、requester node へ公開したりしないでください。

### Service Account Impersonation

service account impersonation を使うと、長期間有効な target service account key を保存せずに
済みます。

```yaml
kiarina.lib.google:
  default: relay
  configs:
    relay:
      type: default
      project_id: your-project-id
      impersonate_service_account: kiapi-relay@your-project-id.iam.gserviceaccount.com
```

source principal には target relay service account に対する
`roles/iam.serviceAccountTokenCreator` が必要です。target service account には RTDB /
GCS 権限が必要です。

## kiapi Configuration

### YAML

`kiapi config edit` を実行し、次の設定を追加します。

```yaml
kiapi.core.relay:
  default: gcp

kiapi.relay.gcp:
  node_id: studio-1
  database_url: https://your-database.firebaseio.com
  bucket: your-private-kiapi-relay-bucket
  prefix: private/kiapi
  google_settings_key: relay
  lifecycle_age_days: 1
  manage_bucket_lifecycle: false
  reconnect_delay_s: 1.0

kiarina.lib.google:
  default: relay
  configs:
    relay:
      type: service_account
      project_id: your-project-id
      service_account_file: /absolute/path/to/kiapi-relay-key.json
```

`kiapi service` で実行する場合は、shell だけの environment variable より YAML を使用して
ください。login や reboot 後も background service が同じ設定を受け取る必要があります。

### Environment Variables

foreground process では次のように設定できます。

```sh
export KIAPI_RELAY_DEFAULT="gcp"
export KIAPI_RELAY_GCP_NODE_ID="${NODE_ID}"
export KIAPI_RELAY_GCP_DATABASE_URL="${DATABASE_URL}"
export KIAPI_RELAY_GCP_BUCKET="${BUCKET}"
export KIAPI_RELAY_GCP_PREFIX="${PREFIX}"
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

GCS access を確認します。

```sh
gcloud storage ls "gs://${BUCKET}"
```

ADC access token で RTDB の authenticated read を確認します。

```sh
ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"

curl --fail --silent --show-error \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${DATABASE_URL}/${PREFIX}/nodes/${NODE_ID}/requests.json"
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

実行中の各 kiapi process に unique な `node_id` を使用してください。GCS は
`response.json` commit marker の重複作成を防ぎますが、同じ node ID を使用する 2 process
が同じ API request を同時に実行する可能性は残ります。

## Security Notes

- 専用 private bucket と専用 RTDB prefix を使用する
- requester と relay の identity を分離する
- key file より service account impersonation または workload identity を優先する
- service account key、API auth token、prompt、生成 relay payload を commit しない
- RTDB Security Rules を public にしない
- relay service account を対象 project / bucket に限定する
- request header には kiapi API auth token が含まれ得るため secret として扱う
- random で推測困難な `session_id` を使用する
- `node_id`、`prefix`、GCS object name に secret を含めない

## Settings Reference

| Setting | Environment variable | Default | Description |
|---|---|---:|---|
| `kiapi.core.relay.default` | `KIAPI_RELAY_DEFAULT` | disabled | GCPRelay を有効化するには `gcp` を指定。 |
| `node_id` | `KIAPI_RELAY_GCP_NODE_ID` | required | kiapi relay node の unique ID。 |
| `database_url` | `KIAPI_RELAY_GCP_DATABASE_URL` | required | 正確な HTTPS RTDB instance URL。 |
| `bucket` | `KIAPI_RELAY_GCP_BUCKET` | required | `gs://` を除いた private GCS bucket name。 |
| `prefix` | `KIAPI_RELAY_GCP_PREFIX` | `kiapi` | RTDB / GCS で共通の root prefix。 |
| `google_settings_key` | `KIAPI_RELAY_GCP_GOOGLE_SETTINGS_KEY` | default Google config | 使用する `kiarina.lib.google` の named credential 設定。 |
| `lifecycle_age_days` | `KIAPI_RELAY_GCP_LIFECYCLE_AGE_DAYS` | `1` | managed GCS delete rule の age。 |
| `manage_bucket_lifecycle` | `KIAPI_RELAY_GCP_MANAGE_BUCKET_LIFECYCLE` | `true` | 起動時に GCPRelay が bucket lifecycle を更新するか。 |
| `reconnect_delay_s` | `KIAPI_RELAY_GCP_RECONNECT_DELAY_S` | `1.0` | RTDB SSE watch の再接続までの delay。 |

## Official References

- [Authenticate RTDB REST requests](https://firebase.google.com/docs/database/rest/auth)
- [RTDB REST setup](https://firebase.google.com/docs/database/rest/start)
- [RTDB Security Rules](https://firebase.google.com/docs/database/security)
- [Firebase predefined roles](https://firebase.google.com/docs/projects/iam/roles-predefined)
- [Cloud Storage IAM roles](https://cloud.google.com/storage/docs/access-control/iam-roles)
- [Manage Cloud Storage object lifecycles](https://cloud.google.com/storage/docs/managing-lifecycles)
- [Application Default Credentials login](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login)
