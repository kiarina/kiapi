<!-- Language: [English](README.md) | **日本語** -->

# kiapi-proxy

[English](README.md) | [日本語](README.ja.md)

`kiapi-proxy` は、HTTP リクエストを受け付けて relay 経由で
[kiapi](https://github.com/kiarina/kiapi) インスタンスに転送し、結果を返す Proxy
サーバーです。kiapi のすべてのエンドポイントを中継します。

- JSON レスポンス
- ファイル / バイナリレスポンス
- chat の `text/event-stream` レスポンス(Server-Sent Events として再送出)

kiapi は十分な性能を持つ Apple Silicon Mac でしか動作しませんが、`kiapi-proxy` は
Linux・Windows・計算資源の少ない Mac でも動作します。依存は `kiapi-relay` のみで
(`kiapi` や MLX には依存しません)、重い推論系の依存なしでインストールできます。

## Installation

```bash
pip install kiapi-proxy

# GCP relay バックエンド付き
pip install "kiapi-proxy[gcp]"
```

## Usage

relay を設定し(`KIAPI_RELAY_*` 環境変数で kiapi と共有)、proxy を起動します。

```bash
# ローカルファイルシステム relay 経由で転送
export KIAPI_RELAY_DEFAULT=local
export KIAPI_RELAY_LOCAL_ROOT=/shared/kiapi/relay

kiapi-proxy run --host 0.0.0.0 --port 8080
# relay を明示的に指定する場合:
kiapi-proxy run --relay local
```

あとは kiapi と同じように呼び出せます。

```bash
curl http://localhost:8080/health
curl -X POST http://localhost:8080/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"hello"}],"stream":true}'
```

## Command line interface

`kiapi-proxy` は `kiapi` と同じコマンド構成を持ち、設定ファイルとサービス登録を
独自に備えています。これにより proxy を kiapi とは独立して管理できます。

```bash
kiapi-proxy run       # proxy サーバーを起動
kiapi-proxy check     # サーバーを起動せずに kiapi への relay 接続を確認
kiapi-proxy config    # ユーザー設定ファイルを管理
kiapi-proxy service   # launchd ユーザーサービスを管理(macOS)
```

### Settings file

proxy は kiapi とは別に、独自のユーザー設定ファイルを持ちます。

```bash
kiapi-proxy config init      # 未作成なら作成する
kiapi-proxy config show      # 現在のファイルを表示する
kiapi-proxy config edit      # $EDITOR / $VISUAL で開く
kiapi-proxy config template  # コメント付きの完全なテンプレートを表示する
```

ファイルはユーザー設定ディレクトリ(例:
`~/.config/kiapi-proxy/settings.yaml`)に置かれ、proxy 設定(`kiapi_proxy.api`)と
relay 設定(`kiapi_relay`)を保持します。ここで設定した値は各コマンド実行時に
読み込まれます。環境変数が優先されます。

### Health check

proxy サーバーを起動せずに、relay 経由で稼働中の kiapi ノードへリクエストが
届くかを確認します。

```bash
kiapi-proxy check --relay local
kiapi-proxy check --relay gcp
```

`check` は relay 経由でリクエストを 1 回(既定は `/health`)送り、応答を表示します。
`--path` で別のエンドポイントを、`--timeout` で待ち時間の上限を指定できます。
`--relay` を省略すると、設定済みの proxy/relay の既定値にフォールバックします。

### Service (macOS)

`kiapi-proxy run` を実行する launchd ユーザーエージェント
(`io.github.kiarina.kiapi-proxy`)を、kiapi のサービスとは独立して登録します。

```bash
kiapi-proxy service install
kiapi-proxy service start
kiapi-proxy service status    # relay 経由の /health エンドツーエンド確認を含む
kiapi-proxy service stop
kiapi-proxy service uninstall
```

## Configuration

| 環境変数 | デフォルト | 説明 |
| --- | --- | --- |
| `KIAPI_PROXY_HOST` | `127.0.0.1` | バインドするホスト。 |
| `KIAPI_PROXY_PORT` | `8080` | バインドするポート。 |
| `KIAPI_PROXY_RELAY` | (relay の既定) | 転送に使う relay 指定子。未設定なら `KIAPI_RELAY_DEFAULT` を使用。 |
| `KIAPI_PROXY_REQUEST_TIMEOUT_S` | `1800` | relay 応答を待つ最大時間。 |

relay バックエンドは `kiapi-relay`(`KIAPI_RELAY_*`)で設定します。詳細は
[kiapi-relay のドキュメント](https://github.com/kiarina/kiapi/blob/main/packages/kiapi-relay/README.ja.md)
を参照してください。

## License

MIT
