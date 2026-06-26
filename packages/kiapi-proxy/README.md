<!-- Language: **English** | [日本語](README.ja.md) -->

# kiapi-proxy

[English](README.md) | [日本語](README.ja.md)

`kiapi-proxy` is a proxy server that accepts HTTP requests, forwards them to a
[kiapi](https://github.com/kiarina/kiapi) instance over a relay, and returns the
result. It relays every kiapi endpoint:

- JSON responses
- file / binary responses
- chat `text/event-stream` responses (re-emitted as Server-Sent Events)

kiapi only runs on capable Apple Silicon Macs, but `kiapi-proxy` runs on Linux,
Windows, and resource-constrained Macs. It depends only on `kiapi-relay` (not on
`kiapi` or MLX), so it installs without any heavy inference dependencies.

## Installation

```bash
pip install kiapi-proxy

# With the GCP relay backend
pip install "kiapi-proxy[gcp]"
```

## Usage

Configure the relay (shared with kiapi via `KIAPI_RELAY_*` environment variables),
then start the proxy:

```bash
# Forward through the local filesystem relay
export KIAPI_RELAY_DEFAULT=local
export KIAPI_RELAY_LOCAL_ROOT=/shared/kiapi/relay

kiapi-proxy run --host 0.0.0.0 --port 8080
# or pick the relay explicitly:
kiapi-proxy run --relay local
```

Then call it as if it were kiapi:

```bash
curl http://localhost:8080/health
curl -X POST http://localhost:8080/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"hello"}],"stream":true}'
```

## Configuration

| Environment variable | Default | Description |
| --- | --- | --- |
| `KIAPI_PROXY_HOST` | `127.0.0.1` | Bind host. |
| `KIAPI_PROXY_PORT` | `8080` | Bind port. |
| `KIAPI_PROXY_RELAY` | (relay default) | Relay specifier to forward through. Falls back to `KIAPI_RELAY_DEFAULT`. |
| `KIAPI_PROXY_REQUEST_TIMEOUT_S` | `1800` | Maximum time to wait for a relayed response. |

Relay backends are configured through `kiapi-relay` (`KIAPI_RELAY_*`). See the
[kiapi-relay documentation](https://github.com/kiarina/kiapi/blob/main/packages/kiapi-relay/README.md).

## License

MIT
