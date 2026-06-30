# GCP Relay

**English** | [日本語](README.ja.md)

## Overview

`GCPRelay` lets a kiapi server inside a closed network receive API requests
without exposing an inbound endpoint.

- Firebase Realtime Database (RTDB) carries request, progress, and result
  notifications.
- Google Cloud Storage (GCS) carries request and response payloads.
- The relay calls the in-process FastAPI app directly.
- Relay deliveries are processed one at a time.

This document covers the GCP resources, authentication, permissions, kiapi
configuration, and a basic end-to-end verification.

## Architecture

```text
requester
  ├─ GCS:  {prefix}/sessions/{session_id}/request.json
  └─ RTDB: {prefix}/nodes/{kiapi_node_id}/requests/{session_id}
                         │
                         ▼
                    GCPRelay
                         │
                         ├─ queued / running notifications
                         ├─ in-process kiapi API call
                         ├─ GCS response.json / response.body
                         └─ atomic RTDB result + request deletion
```

The requester and kiapi relay can use separate service accounts. In production,
separate identities are recommended so each side receives only the permissions
it needs.

### Node identity and discovery

Each side generates its own `node_id` on first start and persists it in its user
data directory, so identities are stable across restarts and never configured by
hand. The kiapi node publishes a liveness heartbeat at
`{prefix}/liveness/{node_id}` every `heartbeat_interval_s` and removes it on a
clean shutdown. A requester reads `{prefix}/liveness`, picks the node with the
most recent heartbeat within `liveness_ttl_s`, and addresses its request there.
When no node has reported within that window, the request fails with
`no_relay_node`.

## Prerequisites

- A Google Cloud project added to Firebase
- A Firebase Realtime Database instance
- A private GCS bucket
- Google Cloud CLI (`gcloud`) for the command examples
- kiapi installed on the relay node
- Permission to configure IAM, RTDB, and the GCS bucket

Set the values used in the examples:

```sh
export PROJECT_ID="your-project-id"
export REGION="asia-northeast1"
export BUCKET="your-private-kiapi-relay-bucket"
export DATABASE_URL="https://your-database.firebaseio.com"
# kiapi generates its own node_id; set this only for the manual REST walkthrough
# below. Read it from the node's data dir (`<data_dir>/node_id`) or from the
# `{prefix}/liveness` list.
export NODE_ID="studio-1"
export PREFIX="private/kiapi"
export RELAY_SERVICE_ACCOUNT="kiapi-relay@${PROJECT_ID}.iam.gserviceaccount.com"
```

Depending on the RTDB location, the database URL can use either the
`firebaseio.com` or `firebasedatabase.app` domain. Copy the exact URL displayed
by the Firebase console.

## GCP Setup

### Create Firebase RTDB

1. Open the [Firebase console](https://console.firebase.google.com/).
2. Add Firebase to the target Google Cloud project if needed.
3. Open **Build > Realtime Database**.
4. Create a database and select its region.
5. Copy the database URL into `DATABASE_URL`.

Do not enable public read/write rules for the relay. RTDB Security Rules deny
access by default, and authenticated server access should be used.

The relay performs these operations:

- continuously reads
  `{prefix}/nodes/{kiapi_node_id}/requests`;
- writes progress and results below
  `{prefix}/nodes/{requester_node_id}/responses`;
- deletes the processed request notification;
- uses a root multi-location `PATCH` to publish the terminal result and delete
  the request atomically.

See the official documentation for
[RTDB Security Rules](https://firebase.google.com/docs/database/security) and
[REST authentication](https://firebase.google.com/docs/database/rest/auth).

### Create GCS Bucket

Create a dedicated bucket with uniform bucket-level access:

```sh
gcloud storage buckets create "gs://${BUCKET}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --uniform-bucket-level-access
```

Do not make the bucket public. Request bodies, prompts, generated content, and
binary response files can all be stored there.

### Configure Lifecycle

Relay session objects should be deleted automatically.

There are two supported approaches.

#### Recommended: Manage Lifecycle Outside kiapi

Create `lifecycle.json`:

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

Apply and verify it:

```sh
gcloud storage buckets update "gs://${BUCKET}" \
  --lifecycle-file=lifecycle.json

gcloud storage buckets describe "gs://${BUCKET}" \
  --format="default(lifecycle_config)"
```

Then set `manage_bucket_lifecycle: false` in kiapi. This keeps bucket metadata
administration outside the relay runtime.

#### Alternative: Let GCPRelay Manage Lifecycle

The default `manage_bucket_lifecycle: true` makes GCPRelay install a
prefix-scoped delete rule at startup.

The relay identity then requires:

- `storage.buckets.get`
- `storage.buckets.update`

`roles/storage.admin` includes these permissions but is broad. A custom role
containing only the required bucket permissions is preferable.

Cloud Storage notes that lifecycle configuration changes can take up to 24
hours to fully take effect. See
[Manage object lifecycles](https://cloud.google.com/storage/docs/managing-lifecycles).

### Create Service Account and IAM

Create a relay service account:

```sh
gcloud iam service-accounts create kiapi-relay \
  --project="${PROJECT_ID}" \
  --display-name="kiapi GCP relay"
```

Grant object access on the relay bucket:

```sh
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${RELAY_SERVICE_ACCOUNT}" \
  --role="roles/storage.objectUser"
```

Grant the Firebase Realtime Database product role:

```sh
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RELAY_SERVICE_ACCOUNT}" \
  --role="roles/firebasedatabase.admin"
```

`roles/storage.objectUser` supplies the object read/create/update/delete
permissions needed to read requests, detect completed responses, and write
responses. It does not grant bucket lifecycle administration.

`roles/firebasedatabase.admin` is the product-level role for full RTDB
read/write access. A Firebase Admin SDK service account can also be used.
These identities are privileged; review the assignment against your
organization's least-privilege policy.

Official references:

- [Firebase product-level IAM roles](https://firebase.google.com/docs/projects/iam/roles-predefined-product)
- [Cloud Storage IAM roles](https://cloud.google.com/storage/docs/access-control/iam-roles)

## Authentication

GCPRelay obtains credentials through
[`kiarina-lib-google`](https://github.com/kiarina/kiarina-python/tree/main/packages/kiarina-lib-google).
Install kiapi with the `relay-gcp` extra so the Google Cloud Storage client and
Google authentication helper are available:

```sh
python3.12 -m pip install --upgrade "kiapi[relay-gcp]"
uv tool install --python 3.12 "kiapi[relay-gcp]"
```

It requests these OAuth scopes:

```text
https://www.googleapis.com/auth/cloud-platform
https://www.googleapis.com/auth/firebase.database
https://www.googleapis.com/auth/userinfo.email
```

The last two are required by the RTDB REST API.

### Application Default Credentials

For local testing, log in to ADC with all required scopes:

```sh
gcloud auth application-default login \
  --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/firebase.database,https://www.googleapis.com/auth/userinfo.email"

gcloud config set project "${PROJECT_ID}"
```

The logged-in user still needs the GCS and Firebase permissions described
above. ADC created by `gcloud auth application-default login` is convenient for
development but is not the preferred unattended production credential.

See
[`gcloud auth application-default login`](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login).

### Service Account Key

If your environment requires a service account key, store the key outside the
repository and configure it through kiapi's YAML:

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

Service account keys are long-lived credentials. Never commit the key file,
copy it into an application image, or expose it to requester nodes.

### Service Account Impersonation

Service account impersonation avoids storing a long-lived target service
account key:

```yaml
kiarina.lib.google:
  default: relay
  configs:
    relay:
      type: default
      project_id: your-project-id
      impersonate_service_account: kiapi-relay@your-project-id.iam.gserviceaccount.com
```

The source principal needs
`roles/iam.serviceAccountTokenCreator` on the target relay service account. The
target service account needs the RTDB and GCS permissions.

## kiapi Configuration

### YAML

Run `kiapi config edit` and add:

```yaml
kiapi.core.relay:
  default: gcp

kiapi.relay.gcp:
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

Use YAML rather than shell-only environment variables when kiapi runs through
`kiapi service`, because the background service must receive the same
configuration after login or reboot.

### Environment Variables

For a foreground process:

```sh
export KIAPI_RELAY_DEFAULT="gcp"
export KIAPI_RELAY_GCP_DATABASE_URL="${DATABASE_URL}"
export KIAPI_RELAY_GCP_BUCKET="${BUCKET}"
export KIAPI_RELAY_GCP_PREFIX="${PREFIX}"
export KIAPI_RELAY_GCP_MANAGE_BUCKET_LIFECYCLE="false"

kiapi run
```

`kiapi run --relay gcp` can be used instead of
`KIAPI_RELAY_DEFAULT="gcp"`.

## Start

Start in the foreground first:

```sh
kiapi run --relay gcp
```

After foreground verification, install or restart the background service:

```sh
kiapi service install
kiapi service start
kiapi service status
```

If GCP initialization fails, kiapi startup fails rather than silently running
without the configured relay.

## Requester Contract

### GCS Request

Write this object first:

```text
{prefix}/sessions/{session_id}/request.json
```

Example:

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

`path` must be an absolute local path beginning with `/`. External URLs are
rejected. If `KIAPI_AUTH_TOKEN` is configured, include the corresponding
`Authorization: Bearer ...` header.

For multipart endpoints such as `POST /v1/files`, use `multipart` instead of
`body`:

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

After `request.json` has been uploaded, write:

```text
{prefix}/nodes/{kiapi_node_id}/requests/{session_id}
```

```json
{
  "session_id": "SESSION_ID",
  "source_node_id": "requester-1"
}
```

The requester watches:

```text
{prefix}/nodes/{requester_node_id}/responses/{session_id}
```

### Progress and Result

Progress statuses:

- `queued`: detected and placed in the relay queue
- `running`: the relay started the local API call

Terminal statuses:

- `succeeded`: response objects were committed to GCS
- `failed`: the bridge failed before committing a response

JSON API responses are stored in:

```text
{prefix}/sessions/{session_id}/response.json
```

Binary API responses are stored in this order:

```text
{prefix}/sessions/{session_id}/response.body
{prefix}/sessions/{session_id}/response.json
```

`response.json` is the commit marker and is created with a GCS generation
precondition. If it already exists after a restart or duplicate execution, the
relay reports the committed response without dispatching the API request again.

## Verification

Verify GCS access:

```sh
gcloud storage ls "gs://${BUCKET}"
```

Verify an authenticated RTDB read with an ADC access token:

```sh
ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"

curl --fail --silent --show-error \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${DATABASE_URL}/${PREFIX}/nodes/${NODE_ID}/requests.json"
```

Then start kiapi and submit one small CPU-safe or already-activated API request
from the requester. Confirm:

1. `queued` appears in the requester response path.
2. `running` replaces it.
3. `response.json` appears in GCS.
4. RTDB changes to `succeeded`.
5. The original request notification is deleted.

## Troubleshooting

### RTDB Returns 401 or 403

- Confirm the credential includes the `firebase.database` and
  `userinfo.email` scopes.
- Confirm the service account or user has access to the Firebase project.
- Confirm `database_url` is the exact URL of the intended RTDB instance.
- Check RTDB Security Rules and IAM assignments.

### GCS Returns 403

- Confirm the principal has object access on the exact bucket.
- If `manage_bucket_lifecycle: true`, also grant `storage.buckets.get` and
  `storage.buckets.update`.
- Confirm `project_id` and `bucket` refer to the same intended environment.

### Startup Fails While Updating Lifecycle

Either grant the bucket metadata permissions or configure the lifecycle rule
outside kiapi and set:

```yaml
kiapi.relay.gcp:
  manage_bucket_lifecycle: false
```

### Requests Stay queued

- Check whether the local kiapi API request is waiting behind another relay
  delivery.
- Check whether the internal kiapi worker is processing a long-running job.
- Confirm the request path and JSON body match the target API schema.

### Duplicate Processing

Each kiapi process derives its `node_id` from its user data directory (auto
generated on first start and reused afterwards), and a single-instance lock in
that directory prevents a second process from sharing the same identity. Run a
second node from a separate data directory to give it a distinct `node_id`. GCS
additionally protects the `response.json` commit marker from duplicate creation.

## Security Notes

- Use a dedicated private bucket and a dedicated RTDB prefix.
- Use separate requester and relay identities.
- Prefer service account impersonation or workload identity over key files.
- Never commit service account keys, API auth tokens, prompts, or generated
  relay payloads.
- Keep RTDB Security Rules non-public.
- Restrict the relay's service account to the intended project and bucket.
- Treat request headers as secrets because they can contain the kiapi API auth
  token.
- Use a random, unguessable `session_id`.
- Avoid placing secrets in the `prefix` or GCS object names.

## Settings Reference

| Setting | Environment variable | Default | Description |
|---|---|---:|---|
| `kiapi.core.relay.default` | `KIAPI_RELAY_DEFAULT` | disabled | Relay specifier; use `gcp` to enable GCPRelay. |
| `database_url` | `KIAPI_RELAY_GCP_DATABASE_URL` | required | Exact HTTPS RTDB instance URL. |
| `bucket` | `KIAPI_RELAY_GCP_BUCKET` | required | Private GCS bucket name without `gs://`. |
| `prefix` | `KIAPI_RELAY_GCP_PREFIX` | `kiapi` | Shared RTDB/GCS root prefix. |
| `google_settings_key` | `KIAPI_RELAY_GCP_GOOGLE_SETTINGS_KEY` | default Google config | Named `kiarina.lib.google` credential configuration. |
| `lifecycle_age_days` | `KIAPI_RELAY_GCP_LIFECYCLE_AGE_DAYS` | `1` | Age used by the managed GCS delete rule. |
| `manage_bucket_lifecycle` | `KIAPI_RELAY_GCP_MANAGE_BUCKET_LIFECYCLE` | `true` | Whether GCPRelay updates the bucket lifecycle at startup. |
| `reconnect_delay_s` | `KIAPI_RELAY_GCP_RECONNECT_DELAY_S` | `1.0` | Delay before reconnecting the RTDB SSE watch. |
| `heartbeat_interval_s` | `KIAPI_RELAY_GCP_HEARTBEAT_INTERVAL_S` | `300.0` | How often the kiapi node refreshes its liveness entry under `{prefix}/liveness/{node_id}`. |
| `liveness_ttl_s` | `KIAPI_RELAY_GCP_LIVENESS_TTL_S` | `1800.0` | A node is selectable only when its last heartbeat is newer than this; clients pick the most recent one within it. |

## Official References

- [Authenticate RTDB REST requests](https://firebase.google.com/docs/database/rest/auth)
- [RTDB REST setup](https://firebase.google.com/docs/database/rest/start)
- [RTDB Security Rules](https://firebase.google.com/docs/database/security)
- [Firebase predefined roles](https://firebase.google.com/docs/projects/iam/roles-predefined)
- [Cloud Storage IAM roles](https://cloud.google.com/storage/docs/access-control/iam-roles)
- [Manage Cloud Storage object lifecycles](https://cloud.google.com/storage/docs/managing-lifecycles)
- [Application Default Credentials login](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login)
