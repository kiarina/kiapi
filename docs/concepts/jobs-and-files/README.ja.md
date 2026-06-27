# Jobs and Files

[English](README.md) | **日本語**

この concept は request execution、直列化、進捗報告、artifact storage を説明します。

## Processing Flow

capability request は job になり、単一の single-flight worker に投入されます。

```text
request
  -> router が input を検証
  -> Job を enqueue
  -> memory.acquire(model)
  -> capability handler が進捗を報告して output を生成
  -> files.put(...) が artifact を保存
  -> raw bytes または Job JSON を返す
```

同期 generation は `KIAPI_SYNC_TIMEOUT_S` まで待ちます。非同期 generation は
`job_id` と HTTP 202 を返し、client は `/v1/jobs/{id}` を poll して、完了した artifact
を Files API から download します。chat と embedding も内部では job ですが、async
mode は公開しません。

## Single-Flight Worker

すべての処理を global `ThreadPoolExecutor(max_workers=1)` と queue 上で実行します。
これにより MLX thread affinity を保ち、GPU 処理を直列化し、peak-memory accounting を
決定的にします。並列 deployment では、個別の memory budget を持つ kiapi process を
複数使用します。

queued job は cancel できます。実行中の推論は確実には中断できません。chat streaming
も generation 中は同じ worker を占有します。

## Job Model

```text
Job:
  id: str
  type: str
  status: queued | running | succeeded | failed | canceled
  params: dict
  result: dict
  artifacts: [file_id]
  error: str | None
  created_at / started_at / finished_at
  progress: float | None
  progress_label: str | None
```

job は memory 上にあり、process restart で消えます。

## Progress Reporting

worker は job 実行前に `contextvar` を通じて `ProgressReporter` を bind します。
capability code は `ProgressReporter.current().update(...)` または `.step(...)` を
呼びます。job 外で `current()` を呼ぶと silent no-op reporter を返します。

client は `GET /v1/jobs/{id}` から最新の進捗を観測します。

## File Lifecycle

Files API は upload、生成 artifact、展開した URL または data URL input を、安定した
`file_id` で保存します。storage root が利用可能な間、file は in-memory job より長く
存続します。

| Purpose | Setting | Default |
|---|---|---|
| upload と生成 artifact | `KIAPI_FILES_ROOT` | `/tmp/kiapi/files` |
| request 中の intermediate work | `KIAPI_TMP_ROOT` | `/tmp/kiapi/work` |

artifact を長期保存する場合は永続的な `KIAPI_FILES_ROOT` を使用します。

## Sync Response Negotiation

同期 generation response の artifact が 1 つなら、既定で raw bytes を返します。
`X-Kiapi-File-Id` と `X-Kiapi-Job-Id` により、保存した file と job を参照できます。

`Accept: application/json`、複数 artifact、非同期 response の場合は Job JSON を返します。

## Related Concepts

- [Model Lifecycle](../model-lifecycle/README.ja.md)
- [API](../api/README.ja.md)
- [Architecture overview](../../../ARCHITECTURE.ja.md)
