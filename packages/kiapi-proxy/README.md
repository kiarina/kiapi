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
pip install "kiapi-proxy[relay-gcp]"
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
curl http://localhost:8080/openapi.json
curl -X POST http://localhost:8080/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"hello"}],"stream":true}'
```

## Command line interface

`kiapi-proxy` mirrors the `kiapi` command layout, with its own settings file and
service registration so the proxy is managed independently from kiapi.

```bash
kiapi-proxy run       # start the proxy server
kiapi-proxy check     # check the relay link to kiapi without starting the server
kiapi-proxy config    # manage the user settings file
kiapi-proxy service   # manage the launchd user service (macOS)
```

### Settings file

The proxy keeps its own user settings file, separate from kiapi's:

```bash
kiapi-proxy config init      # create it if it does not exist
kiapi-proxy config show      # print the current file
kiapi-proxy config edit      # open it in $EDITOR / $VISUAL
kiapi-proxy config template  # print the full commented template
```

The file lives in the user config directory (for example
`~/.config/kiapi-proxy/settings.yaml`) and holds the proxy settings
(`kiapi_proxy.api`) and the relay settings (`kiapi_relay`). Values set here are
loaded on every command; environment variables still take precedence.

### Health check

Confirm that requests can travel over the relay to a live kiapi node without
starting the proxy server:

```bash
kiapi-proxy check --relay local
kiapi-proxy check --relay gcp
```

`check` sends a single request (default `/health`) through the relay and prints
the response. Use `--path` to probe another endpoint and `--timeout` to bound the
wait. Without `--relay` it falls back to the configured proxy/relay default. It
reuses the proxy's persistent relay node ID and holds the single-instance lock,
so it fails fast if the proxy server is already running.

### Service (macOS)

Register a launchd user agent (`io.github.kiarina.kiapi-proxy`) that runs
`kiapi-proxy run`, independent from the kiapi service:

```bash
kiapi-proxy service install
kiapi-proxy service start
kiapi-proxy service status    # includes an end-to-end /health probe through the relay
kiapi-proxy service stop
kiapi-proxy service uninstall
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
