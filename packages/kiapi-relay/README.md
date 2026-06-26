<!-- Language: **English** | [日本語](README.ja.md) -->

# kiapi-relay

[English](README.md) | [日本語](README.ja.md)

Shared relay transport for [kiapi](https://github.com/kiarina/kiapi). It provides
the relay protocol, the request/response schemas, the in-process request runner,
and a client for issuing requests to a kiapi instance over a relay.

This package is platform-agnostic and is depended on by both `kiapi` (the server
side, which runs the relay runner) and `kiapi-proxy` (the client side, which
forwards HTTP requests over a relay).

## Installation

```bash
pip install kiapi-relay

# With the GCP relay backend
pip install "kiapi-relay[gcp]"
```

## Backends

| Module | Description | Extra |
| --- | --- | --- |
| `kiapi_relay.local` | Filesystem-backed relay for local development and verification. | — |
| `kiapi_relay.gcp` | GCP relay (GCS payloads + Firebase Realtime Database notifications). | `gcp` |

## Usage

```python
from kiapi_relay import RelayRequest, RelayResponse, relay_registry

# Resolve a configured relay and issue a request over it.
relay = relay_registry.get("local")
response: RelayResponse = await relay.request(
    RelayRequest(method="GET", path="/health")
)
```

See the [kiapi documentation](https://kiarina.github.io/kiapi/) for the full relay
architecture.

## License

MIT
