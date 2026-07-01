# Application

[English](README.md) | **日本語**

この concept は workspace の境界、`kiapi` のソース構成、アプリケーション起動を
説明します。

## Workspace

このリポジトリは 3 package からなる uv workspace です。

```text
packages/
  kiapi/        # Apple Silicon / MLX 推論 API server
  kiapi-relay/  # platform-independent な relay transport
  kiapi-proxy/  # relay 経由の cross-platform HTTP proxy
```

`kiapi` と `kiapi-proxy` はどちらも `kiapi-relay` に依存します。`kiapi-proxy` は
`kiapi` に依存しないため、MLX なしで install、実行できます。

## Source Layout

main package は capability-independent な土台、capability 実装、HTTP boundary を
分離します。

```text
kiapi/
  core/
    app/       # AppContext
    model/     # model registry
    setup/     # resource activation
    memory/    # memory budget と TTL eviction
    worker/    # single-flight executor と queue
    job/       # job model と store
    file/      # 永続 artifact へのアクセス
    workdir/   # 一時 work directory
    net/       # user-provided URL の検証
    logging/   # logging setup
  capabilities/  # family ごとの実装 package
  api/           # domain と family で編成した FastAPI router
```

capability の directory 名を canonical family identifier とします。

## Startup Flow

```text
application startup
  -> すべての capability を register
      -> ModelSpec entry を register
      -> CapabilitySpec entry を register
  -> FastAPI router を mount
  -> memory budget 内で設定済みモデルを warmup
  -> request の受付を開始
```

warmup は任意です。それ以外のモデルは最初の acquire 時に lazy load します。
activate されていない warmup target は warning を出して skip し、起動は継続します。

## Settings and User Directories

`core/app` がアプリケーション全体の `AppContext` を所有します。user directory の
解決と single-instance lock は共有パッケージ `kiarina-utils-app` が提供し、
`kiarina.utils.app` として直接利用します。app identity は CLI entry と ASGI
factory で `kiarina.utils.app.configure("kiapi", "kiarina")` を呼んで設定します。
directory は明示設定、XDG environment variable、`platformdirs` の順で解決します。

| Purpose | Setting (`kiarina.utils.app`) | Environment fallback | platformdirs |
|---|---|---|---|
| cache | `user_cache_dir` | `XDG_CACHE_HOME/kiapi` | `user_cache_dir` |
| config | `user_config_dir` | `XDG_CONFIG_HOME/kiapi` | `user_config_dir` |
| data | `user_data_dir` | `XDG_DATA_HOME/kiapi` | `user_data_dir` |

設定は user の `settings.yaml` の `kiarina.utils.app` セクションで行い、上書き用の
environment variable は `KIARINA_UTILS_APP_` prefix を使います。設定した path の
`~` は現在の user に対して展開します。

## Related Concepts

- [Model Lifecycle](../model-lifecycle/README.ja.md)
- [Jobs and Files](../jobs-and-files/README.ja.md)
- [API](../api/README.ja.md)
- [Architecture overview](../../../ARCHITECTURE.ja.md)
