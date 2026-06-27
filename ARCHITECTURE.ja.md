# kiapi Architecture

[English](ARCHITECTURE.md) | **日本語**

kiapi は、ローカル推論サーバー、relay transport、cross-platform proxy で構成される
uv workspace です。この文書はアーキテクチャ全体の地図であり、詳しい設計資料は
[`docs/concepts`](docs/concepts/) 以下に置きます。

## Design Principles

- ソースコードは
  [Crystal Architecture](https://github.com/kiarina/crystal-architecture)
  に従います。
- 設定管理には
  [Pydantic Settings Manager](https://github.com/kiarina/pydantic-settings-manager)
  を使用します。
- 全推論を単一 worker で直列化し、メモリ会計と MLX の thread affinity を予測可能に
  保ちます。
- すべての capability で、モデル、subprocess 型 capability、ジョブ、ファイルに共通の
  lifecycle abstraction を使用します。
- `kiapi-relay` は platform-independent とし、`kiapi-proxy` は MLX に依存しません。

## Concepts

| Concept | Description |
|---|---|
| [Application](docs/concepts/application/README.ja.md) | workspace 構成、アプリケーション起動、設定、ユーザーディレクトリ |
| [Model Lifecycle](docs/concepts/model-lifecycle/README.ja.md) | setup resource、model registry、memory budget、TTL、subprocess isolation |
| [Jobs and Files](docs/concepts/jobs-and-files/README.ja.md) | 処理フロー、worker の直列化、進捗、ファイル、response negotiation |
| [Relay](docs/concepts/relay/README.ja.md) | local transport または GCP transport によるリモートリクエスト配送 |
| [API](docs/concepts/api/README.ja.md) | endpoint 編成、モデル発見、2 層の OpenAPI documentation |

## Documentation Types

- [`docs/concepts`](docs/concepts/) はシステムの設計を説明します。
- [`docs/runbooks`](docs/runbooks/) は運用手順と障害対応手順を収めます。
- [`docs/playbooks`](docs/playbooks/) は反復可能な開発 workflow を収めます。
