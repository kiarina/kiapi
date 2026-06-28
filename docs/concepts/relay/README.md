# Relay

**English** | [日本語](README.ja.md)

The relay is an optional background subsystem that delivers HTTP requests to a
kiapi instance that may not be directly reachable.

## Package Boundaries

`kiapi-relay` defines the stable `Relay` and `RelayDelivery` protocols, request
client, schemas, and plugin registry. It provides:

- `kiapi_relay.impl.local`, a filesystem-backed transport for local verification.
- `kiapi_relay.impl.gcp`, a GCS and Realtime Database transport.

`kiapi` hosts the relay runner. `kiapi-proxy` uses the same request client to
expose a conventional HTTP boundary without depending on kiapi or MLX.

## Delivery Flow

```text
requester
  -> write GCS request.json
  -> publish RTDB request notification
      |
GCP relay SSE listener
  -> mark RTDB queued
  -> enqueue local delivery
  -> mark RTDB running
  -> dispatch to the in-process FastAPI app through ASGI
  -> write GCS response.body
  -> create GCS response.json commit marker
  -> atomically publish terminal status and remove the request
```

The listener and delivery runner are independent, so the listener can queue
requests while one is running. The runner consumes deliveries serially, and the
API worker separately controls GPU serialization.

## Commit and Recovery

GCS publishes the body before metadata. `response.json` is the commit marker and
is created with `if_generation_match=0`, so only one process can commit it.

If the marker already exists when a queued delivery is consumed, the relay
recovers response metadata, republishes the terminal notification, and skips
API dispatch. Notifications are therefore handled at least once without
intentionally repeating committed work.

The terminal Realtime Database update uses a root-level multi-location `PATCH`
so publishing the response and deleting the request notification are atomic.

## Local Transport

LocalRelay mirrors the GCP object layout under a local root:

```text
{root}/{prefix}/
  nodes/{node_id}/requests/{session_id}.json
  nodes/{source_node_id}/responses/{session_id}.json
  sessions/{session_id}/request.json
  sessions/{session_id}/response.body
  sessions/{session_id}/response.json
```

It writes `response.body` before `response.json` and removes the request
notification only when terminal status is committed.

## Related Concepts

- [Application](../application/)
- [Jobs and Files](../jobs-and-files/)
- [Architecture overview](../../../ARCHITECTURE.md)
