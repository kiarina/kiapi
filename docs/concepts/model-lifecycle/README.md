# Model Lifecycle

**English** | [日本語](README.ja.md)

This concept describes how kiapi prepares, resolves, loads, accounts for, and
releases inference models and subprocess-backed capabilities.

## Setup Resources

Heavy resources are activated before serving so API requests never trigger an
unexpected first-time download.

| Resource | Status check | Activate | Deactivate |
|---|---|---|---|
| `hf_snapshot` | local snapshot lookup succeeds | download from Hugging Face | remove the matching cache entry |
| `docker_image` | `docker image inspect` succeeds | `docker pull` | `docker image rm` |
| `local_path` | path exists | no-op | remove the path |
| `python_venv` | validation import succeeds | create venv and install packages | remove the venv |

Handlers call `ctx.ensure_model_ready(spec)` before use. Missing setup becomes
an HTTP 503 response with an activation hint.

## Model Registry

Every servable variant is a `ModelSpec` in one global registry.

| Field | Purpose |
|---|---|
| `name`, `aliases` | identifiers accepted by the API |
| `family`, `domain` | resolution and routing keys |
| `modalities_in` | accepted input modalities |
| `weight_gb`, `peak_headroom_gb` | memory-accounting estimates |
| `framework` | cleanup strategy |
| `resident` | whether the payload remains loaded after use |
| `ttl_seconds` | model-specific idle TTL |
| `priority`, `default` | eviction priority and family default |

`resolve(family, model)` resolves variants inside one family. Omitting `model`
selects the family default. A resident model stays loaded until TTL expiry or
eviction; a non-resident model reserves memory for one run and releases it
immediately.

## Memory Budget

All capabilities share `KIAPI_MEMORY_LIMIT_GB`. When unset, the effective
startup budget is 80% of installed memory.

```text
other resident weights
  + current model weight
  + current job peak headroom
  <= memory limit
```

When space is insufficient, residents are released in ascending
`(priority, last_used)` order. Release functions perform framework-specific
cleanup for MLX, Torch/MPS, or subprocess payloads.

## Idle TTL

An unset model TTL inherits `KIAPI_DEFAULT_TTL_S`; a zero or negative value pins
the model. Expired residents are swept before acquisition and by the background
interval configured with `KIAPI_TTL_SWEEP_INTERVAL_S`.

Sweeps execute on the same single worker thread as inference. This preserves MLX
thread affinity and serializes cleanup with generation.

## Resident Subprocesses

Some capabilities load a process instead of a Python model object:

- `acestep` starts an ACE-Step worker from its dedicated Python venv.
- `web/search` starts a resident SearXNG Docker subprocess.
- `web/fetch` starts a resident Crawl4AI Docker subprocess.

Core still sees a payload with `load` and `release` behavior, so memory, TTL,
jobs, and single-flight execution apply uniformly.

## Dependency Isolation

ACE-Step requires a Transformers version incompatible with the main kiapi
environment. `kiapi activate --family acestep` therefore builds a dedicated
venv, and kiapi communicates with its resident worker using line-oriented JSON
over stdin/stdout. Generated artifacts pass by filesystem path.

## Related Concepts

- [Application](../application/)
- [Jobs and Files](../jobs-and-files/)
- [Architecture overview](../../../ARCHITECTURE.md)
