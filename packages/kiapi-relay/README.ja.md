<!-- Language: [English](README.md) | **日本語** -->

# kiapi-relay

[English](README.md) | [日本語](README.ja.md)

[kiapi](https://github.com/kiarina/kiapi) のための共有 relay トランスポートです。
relay プロトコル、リクエスト/レスポンスのスキーマ、インプロセスのリクエストランナー、
および relay 経由で kiapi インスタンスへリクエストを発行するクライアントを提供します。

このパッケージはプラットフォーム非依存で、`kiapi`(relay ランナーを動かすサーバー側)と
`kiapi-proxy`(HTTP リクエストを relay 経由で転送するクライアント側)の両方から依存されます。

## Installation

```bash
pip install kiapi-relay

# GCP relay バックエンド付き
pip install "kiapi-relay[gcp]"
```

## Backends

| Module | 説明 | Extra |
| --- | --- | --- |
| `kiapi_relay.impl.local` | ローカル開発・検証用のファイルシステムベース relay。 | — |
| `kiapi_relay.impl.gcp` | GCP relay(GCS ペイロード + Firebase Realtime Database 通知)。 | `gcp` |

## Usage

```python
from kiapi_relay import RelayRequest, RelayResponse, relay_registry

# 設定済みの relay を解決し、relay 経由でリクエストを発行する。
relay = relay_registry.get("local")
response: RelayResponse = await relay.request(
    RelayRequest(method="GET", path="/health")
)
```

relay アーキテクチャの詳細は [kiapi のドキュメント](https://kiarina.github.io/kiapi/) を参照してください。

## License

MIT
