<!-- Language: [English](README.md) | **日本語** -->

# kiapi workspace

[English](README.md) | [日本語](README.ja.md)

このリポジトリは、kiapi ファミリーのパッケージを束ねる [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/) です。

## Packages

| Package | 説明 | 動作環境 |
| --- | --- | --- |
| [`kiapi`](packages/kiapi/README.ja.md) | Apple Silicon (MLX) 上の LLM エージェント向け統合ローカル推論 API サーバー。chat / embedding / image / music / sound-effect / video に対応。 | Apple Silicon (macOS) |
| [`kiapi-relay`](packages/kiapi-relay/README.ja.md) | relay 経由で kiapi に到達するための共有トランスポート(リクエスト/レスポンスのスキーマとクライアント)。 | 全プラットフォーム |
| [`kiapi-proxy`](packages/kiapi-proxy/README.ja.md) | HTTP リクエストを relay 経由で kiapi に転送し、結果(JSON・ファイル・chat の event-stream)を返す Proxy サーバー。 | Linux / Windows / macOS |

`kiapi` は十分な性能を持つ Apple Silicon を必要とします。`kiapi-proxy` を使うと
任意のプラットフォームのクライアントから relay 経由でリモートの kiapi に到達できます。
重い MLX 依存を含めないよう、`kiapi-proxy` は別パッケージとして公開します。

## Development

```bash
# 全ワークスペースパッケージと開発ツールをインストール
uv sync --all-groups --all-extras

# format / lint / 設定テンプレート・API ドキュメント生成
make

# 全パッケージのユニットテストを実行
make test
```

各パッケージは独立してバージョン管理・リリースします。各パッケージの
`CHANGELOG.md` と [Releasing](#releasing) を参照してください。

## Releasing

リリースはパッケージ単位で、`<package>-v<version>` 形式のタグを push して実行します。

```bash
make bump-version PKG=kiapi VERSION=0.2.1
# 差分を確認してから:
git add packages/kiapi/pyproject.toml packages/kiapi/CHANGELOG.md uv.lock
git commit -m "chore(release): prepare kiapi-v0.2.1"
git tag kiapi-v0.2.1 && git push origin main --tags
```

## License

MIT
