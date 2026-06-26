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
