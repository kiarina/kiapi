# Application

**English** | [日本語](README.ja.md)

This concept describes the workspace boundary, the `kiapi` source layout, and
application startup.

## Workspace

The repository is a uv workspace with three packages:

```text
packages/
  kiapi/        # Apple Silicon / MLX inference API server
  kiapi-relay/  # platform-independent relay transport
  kiapi-proxy/  # cross-platform HTTP proxy over the relay
```

`kiapi` and `kiapi-proxy` both depend on `kiapi-relay`. `kiapi-proxy` does not
depend on `kiapi`, so it installs and runs without MLX.

## Source Layout

The main package separates the capability-independent foundation, capability
implementations, and HTTP boundary:

```text
kiapi/
  core/
    app/       # AppContext, startup wiring, user directories
    model/     # model registry
    setup/     # resource activation
    memory/    # memory budget and TTL eviction
    worker/    # single-flight executor and queue
    job/       # job model and store
    file/      # persistent artifact access
    workdir/   # temporary work directories
    net/       # validation of user-provided URLs
    logging/   # logging setup
  capabilities/  # one implementation package per family
  api/           # FastAPI routers grouped by domain and family
```

The directory name of a capability is its canonical family identifier.

## Startup Flow

```text
application startup
  -> register every capability
      -> register ModelSpec entries
      -> register CapabilitySpec entries
  -> mount FastAPI routers
  -> warm up configured models within the memory budget
  -> accept requests
```

Warmup is optional. Other models load lazily on their first acquisition.
Unactivated warmup targets are skipped with a warning, without stopping startup.

## Settings and User Directories

`core/app` owns the application-wide `AppContext`. User-directory resolution is
delegated to the shared `kiarina-utils-app` package, and resolves in this order:
explicit setting, XDG environment variable, then `platformdirs`.

| Purpose | Setting (`kiapi.core.app`) | Environment fallback | platformdirs |
|---|---|---|---|
| cache | `user_cache_dir` | `XDG_CACHE_HOME/kiapi` | `user_cache_dir` |
| config | `user_config_dir` | `XDG_CONFIG_HOME/kiapi` | `user_config_dir` |
| data | `user_data_dir` | `XDG_DATA_HOME/kiapi` | `user_data_dir` |

Settings are configured under the `kiapi.core.app` section of the user
`settings.yaml`. Configured paths expand `~` for the current user.

## Related Concepts

- [Model Lifecycle](../model-lifecycle/)
- [Jobs and Files](../jobs-and-files/)
- [API](../api/)
- [Architecture overview](../../../ARCHITECTURE.md)
