# Relay

[English](README.md) | **日本語**

relay は、直接到達できない場合がある kiapi instance に HTTP request を配送する、
任意の background subsystem です。

## Package Boundaries

`kiapi-relay` は安定した `Relay`、`RelayDelivery` protocol、request client、schema、
plugin registry を定義します。次の transport を提供します。

- `kiapi_relay.local`: local verification 用の filesystem-backed transport
- `kiapi_relay.gcp`: GCS と Realtime Database を使う transport

`kiapi` が relay runner を host します。`kiapi-proxy` は同じ request client を使い、
kiapi や MLX に依存せず conventional HTTP boundary を公開します。

## Delivery Flow

```text
requester
  -> GCS request.json を write
  -> RTDB request notification を publish
      |
GCP relay SSE listener
  -> RTDB queued に更新
  -> local delivery を enqueue
  -> RTDB running に更新
  -> ASGI 経由で in-process FastAPI app に dispatch
  -> GCS response.body を write
  -> GCS response.json commit marker を create
  -> terminal status の publish と request の削除を atomic に実行
```

listener と delivery runner は独立しているため、1 件を実行中でも listener は request を
queue に追加できます。runner は delivery を直列に消費し、API worker はこれとは別に
GPU 処理の直列化を管理します。

## Commit and Recovery

GCS は body を metadata より先に publish します。`response.json` が commit marker で、
`if_generation_match=0` により 1 process だけが commit できます。

queued delivery の消費時に marker が存在する場合、relay は response metadata を復旧し、
terminal notification を再 publish して API dispatch を skip します。これにより、
commit 済み処理を意図的に繰り返さず、notification を at-least-once で処理します。

terminal Realtime Database update は root-level multi-location `PATCH` を使用し、
response の publish と request notification の削除を atomic にします。

## Local Transport

LocalRelay は local root 以下に GCP object layout を再現します。

```text
{root}/{prefix}/
  nodes/{node_id}/requests/{session_id}.json
  nodes/{source_node_id}/responses/{session_id}.json
  sessions/{session_id}/request.json
  sessions/{session_id}/response.body
  sessions/{session_id}/response.json
```

`response.body` を `response.json` より先に write し、terminal status の commit 時だけ
request notification を削除します。

## Related Concepts

- [Application](../application/README.ja.md)
- [Jobs and Files](../jobs-and-files/README.ja.md)
- [Architecture overview](../../../ARCHITECTURE.ja.md)
