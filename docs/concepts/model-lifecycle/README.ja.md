# Model Lifecycle

[English](README.md) | **日本語**

この concept は、kiapi が推論モデルと subprocess 型 capability を準備、解決、load、
memory accounting、release する方法を説明します。

## Setup Resources

API request 中に予期しない初回 download が発生しないよう、重い resource は serving
開始前に activate します。

| Resource | Status check | Activate | Deactivate |
|---|---|---|---|
| `hf_snapshot` | local snapshot の参照に成功 | Hugging Face から download | 対応する cache entry を削除 |
| `docker_image` | `docker image inspect` に成功 | `docker pull` | `docker image rm` |
| `local_path` | path が存在 | no-op | path を削除 |
| `python_venv` | validation import に成功 | venv を作成して package を install | venv を削除 |

handler は使用前に `ctx.ensure_model_ready(spec)` を呼びます。setup がなければ、
activation hint 付きの HTTP 503 response に変換します。

## Model Registry

serving 可能なすべての variant を、単一 global registry の `ModelSpec` として管理します。

| Field | Purpose |
|---|---|
| `name`, `aliases` | API が受け付ける identifier |
| `family`, `domain` | resolution と routing の key |
| `modalities_in` | 受け付ける input modality |
| `weight_gb`, `peak_headroom_gb` | memory accounting の推定値 |
| `framework` | cleanup strategy |
| `resident` | 使用後も payload を load したままにするか |
| `ttl_seconds` | model 固有の idle TTL |
| `priority`, `default` | eviction priority と family default |

`resolve(family, model)` は同一 family 内の variant を解決します。`model` を省略すると
family default を選びます。resident model は TTL expiry または eviction まで保持し、
non-resident model は 1 回分の memory を reserve して直ちに release します。

## Memory Budget

全 capability が `KIAPI_MEMORY_LIMIT_GB` を共有します。未設定時は搭載 memory の 80% を
起動時の実効 budget とします。

```text
other resident weights
  + current model weight
  + current job peak headroom
  <= memory limit
```

空きが不足すると、resident を `(priority, last_used)` の昇順で release します。
release function は MLX、Torch/MPS、subprocess payload ごとの cleanup を行います。

## Idle TTL

model TTL が未設定なら `KIAPI_DEFAULT_TTL_S` を継承し、0 以下なら model を pin します。
期限切れ resident は acquire 前と、`KIAPI_TTL_SWEEP_INTERVAL_S` で設定した background
interval の両方で sweep します。

sweep は推論と同じ単一 worker thread で実行します。これにより MLX thread affinity を
保ち、cleanup と generation を直列化します。

## Resident Subprocesses

一部の capability は Python model object ではなく process を load します。

- `acestep` は専用 Python venv から ACE-Step worker を起動します。
- `web/search` は resident SearXNG Docker subprocess を起動します。
- `web/fetch` は resident Crawl4AI Docker subprocess を起動します。

core からは `load` と `release` を持つ payload として扱えるため、memory、TTL、job、
single-flight execution を同じように適用できます。

## Dependency Isolation

ACE-Step は kiapi main environment と互換性のない Transformers version を必要とします。
このため `kiapi activate --family acestep` が専用 venv を構築し、kiapi は resident
worker と stdin/stdout 上の line-oriented JSON で通信します。生成 artifact は
filesystem path で受け渡します。

## Related Concepts

- [Application](../application/README.ja.md)
- [Jobs and Files](../jobs-and-files/README.ja.md)
- [Architecture overview](../../../ARCHITECTURE.ja.md)
