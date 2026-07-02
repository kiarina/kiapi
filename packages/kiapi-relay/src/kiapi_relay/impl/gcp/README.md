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
  ├─ GCS:  sessions/{session_id}/request.json
  └─ RTDB: nodes/{kiapi_node_id}/requests/{session_id}
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
`liveness/{node_id}` every `heartbeat_interval_s` and removes it on a
clean shutdown. A requester reads `liveness`, picks the node with the
most recent heartbeat within `liveness_ttl_s`, and addresses its request there.
When no node has reported within that window, the request fails with
`no_relay_node`.

## Setup

### Prerequisites

Install kiapi with the `relay-gcp` extra so the Google Cloud Storage client and
Google authentication helper are available:

```sh
uv tool install --python 3.12 "kiapi[relay-gcp]"
```

The setup task needs these CLIs on the relay node:

- `gcloud`, logged in with a Project Owner-equivalent account
  (`gcloud auth login`).
- `firebase-tools`, logged in with `firebase login`. It is a project-local dev
  dependency, so `mise run setup` (or `pnpm install` at the repository root)
  installs it and mise puts it on `PATH`.
- `fzf` and `jq` for the interactive prompts.

### Automated Setup

Run the setup task from the `kiapi-relay` package directory:

```sh
cd packages/kiapi-relay
mise run gcp:setup
```

The task provisions everything the relay needs and prints the kiapi YAML to
paste with `kiapi config edit`:

- selects the Google Cloud project;
- creates a private, uniform-access GCS bucket (default name
  `{project_id}-kiapi`, default region `asia-northeast1`) and installs the
  lifecycle rule that deletes `sessions/` objects after one day;
- adds Firebase to the project and creates a Realtime Database instance
  (default location `asia-southeast1`), deriving the correct `database_url`;
- configures authentication and grants the relay identity
  `roles/storage.objectUser` on the bucket and `roles/firebasedatabase.admin`
  on the project.

Existing buckets and RTDB instances are detected and left untouched, so the
task is safe to re-run.

> If RTDB creation fails, check `firebase-debug.log` in the current directory
> for the underlying error. Two common causes:
>
> - `firebase-tools` is not logged in and falls back to Application Default
>   Credentials, which fails the Realtime Database calls with a quota-project
>   403 on `firebasedatabase.googleapis.com`. Run `firebase login` and re-run
>   the task. (A `firebase projects:list` that works via ADC is not enough.)
> - A named RTDB instance requires the Blaze (pay-as-you-go) billing plan.
>   Upgrade the project in the
>   [Firebase console](https://console.firebase.google.com/) and re-run the task.

### Authentication methods

GCPRelay obtains credentials through
[`kiarina-lib-google`](https://github.com/kiarina/kiarina-python/tree/main/packages/kiarina-lib-google).

The task offers three methods:

- **Application Default Credentials** (default) — runs
  `gcloud auth application-default login`. Convenient for development; the
  logged-in user needs the relay roles. It is not the preferred unattended
  production credential.
- **Service Account** — creates a JSON key (default
  `~/.config/kiapi-relay/gcp/key.json`, `chmod 600`). Service account keys are
  long-lived; never commit or share the file.
- **Impersonation** — runs `gcloud auth application-default login` and grants
  that user `roles/iam.serviceAccountTokenCreator` on the target service
  account, so it mints short-lived SA tokens without a stored key.

`roles/storage.objectUser` supplies the object read/create/update/delete
permissions the relay needs; it does not grant bucket lifecycle administration,
so the task manages the lifecycle rule directly and emits
`manage_bucket_lifecycle: false`. `roles/firebasedatabase.admin` grants full
RTDB read/write access. Both identities are privileged; review the assignment
against your organization's least-privilege policy.

### kiapi Configuration

The task prints a block like the following (ADC example) to add with
`kiapi config edit`:

```yaml
kiapi_relay:
  default: gcp

kiapi_relay.impl.gcp:
  database_url: https://your-instance.asia-southeast1.firebasedatabase.app
  bucket: your-project-kiapi
  google_settings_key: kiapi
  manage_bucket_lifecycle: false

kiarina.lib.google:
  default: kiapi
  configs:
    kiapi:
      type: default
      project_id: your-project-id
```

For a service account key, use `type: service_account` with
`service_account_file`; for impersonation, use `type: default` with
`impersonate_service_account`.

Relay objects live at the bucket and database roots. Use a dedicated bucket and
RTDB instance per relay deployment rather than sharing one across environments.

Use YAML rather than shell-only environment variables when kiapi runs through
`kiapi service`, because the background service must receive the same
configuration after login or reboot.

### Environment Variables

For a foreground process:

```sh
export KIAPI_RELAY_DEFAULT="gcp"
export KIAPI_RELAY_GCP_DATABASE_URL="https://your-instance.asia-southeast1.firebasedatabase.app"
export KIAPI_RELAY_GCP_BUCKET="your-project-kiapi"
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
sessions/{session_id}/request.json
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
nodes/{kiapi_node_id}/requests/{session_id}
```

```json
{
  "session_id": "SESSION_ID",
  "source_node_id": "requester-1"
}
```

The requester watches:

```text
nodes/{requester_node_id}/responses/{session_id}
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
sessions/{session_id}/response.json
```

Binary API responses are stored in this order:

```text
sessions/{session_id}/response.body
sessions/{session_id}/response.json
```

`response.json` is the commit marker and is created with a GCS generation
precondition. If it already exists after a restart or duplicate execution, the
relay reports the committed response without dispatching the API request again.

## Verification

Set the values the setup task chose (kiapi generates its own `NODE_ID`; read it
from the node's data dir at `<data_dir>/node_id` or from the `liveness`
list):

```sh
export BUCKET="your-project-kiapi"
export DATABASE_URL="https://your-instance.asia-southeast1.firebasedatabase.app"
export NODE_ID="studio-1"
```

Verify GCS access:

```sh
gcloud storage ls "gs://${BUCKET}"
```

Verify an authenticated RTDB read with an ADC access token:

```sh
ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"

curl --fail --silent --show-error \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${DATABASE_URL}/nodes/${NODE_ID}/requests.json"
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
kiapi_relay.impl.gcp:
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

- Use a dedicated private bucket and a dedicated RTDB instance.
- Use separate requester and relay identities.
- Prefer service account impersonation or workload identity over key files.
- Never commit service account keys, API auth tokens, prompts, or generated
  relay payloads.
- Keep RTDB Security Rules non-public.
- Restrict the relay's service account to the intended project and bucket.
- Treat request headers as secrets because they can contain the kiapi API auth
  token.
- Use a random, unguessable `session_id`.
- Avoid placing secrets in GCS object names.

## Settings Reference

| Setting | Environment variable | Default | Description |
|---|---|---:|---|
| `kiapi_relay.default` | `KIAPI_RELAY_DEFAULT` | disabled | Relay specifier; use `gcp` to enable GCPRelay. |
| `database_url` | `KIAPI_RELAY_GCP_DATABASE_URL` | required | Exact HTTPS RTDB instance URL. |
| `bucket` | `KIAPI_RELAY_GCP_BUCKET` | required | Private GCS bucket name without `gs://`. |
| `google_settings_key` | `KIAPI_RELAY_GCP_GOOGLE_SETTINGS_KEY` | default Google config | Named `kiarina.lib.google` credential configuration. |
| `lifecycle_age_days` | `KIAPI_RELAY_GCP_LIFECYCLE_AGE_DAYS` | `1` | Age used by the managed GCS delete rule. |
| `manage_bucket_lifecycle` | `KIAPI_RELAY_GCP_MANAGE_BUCKET_LIFECYCLE` | `true` | Whether GCPRelay updates the bucket lifecycle at startup. |
| `reconnect_delay_s` | `KIAPI_RELAY_GCP_RECONNECT_DELAY_S` | `1.0` | Delay before reconnecting the RTDB SSE watch. |
| `heartbeat_interval_s` | `KIAPI_RELAY_GCP_HEARTBEAT_INTERVAL_S` | `300.0` | How often the kiapi node refreshes its liveness entry under `liveness/{node_id}`. |
| `liveness_ttl_s` | `KIAPI_RELAY_GCP_LIVENESS_TTL_S` | `1800.0` | A node is selectable only when its last heartbeat is newer than this; clients pick the most recent one within it. |

## Official References

- [Authenticate RTDB REST requests](https://firebase.google.com/docs/database/rest/auth)
- [RTDB REST setup](https://firebase.google.com/docs/database/rest/start)
- [RTDB Security Rules](https://firebase.google.com/docs/database/security)
- [Firebase predefined roles](https://firebase.google.com/docs/projects/iam/roles-predefined)
- [Cloud Storage IAM roles](https://cloud.google.com/storage/docs/access-control/iam-roles)
- [Manage Cloud Storage object lifecycles](https://cloud.google.com/storage/docs/managing-lifecycles)
- [Application Default Credentials login](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login)
