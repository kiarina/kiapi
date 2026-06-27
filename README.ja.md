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
# ツール、ワークスペース依存関係、テストアセットをセットアップ
make init

# format / lint / 設定テンプレート・API ドキュメント生成
make

# 全パッケージのユニットテストを実行
make test
```

Makefile は mise task の薄いラッパーです。package の選択や task 固有のオプションは
`mise run <task> --help` で確認できます。たとえば `mise run test kiapi-relay` や
`mise run format --unsafe` を使用します。

ワークスペース全体で単一のバージョンを共有し、ルートの `VERSION` ファイルで管理します。
ルートの `CHANGELOG.md` にプロジェクト全体の変更を記録し、各パッケージも個別の
`CHANGELOG.md` を持ちます。詳細は [Releasing](#releasing) を参照してください。

## Releasing

リリースは単一の共有バージョンと `v<version>` 形式のタグ 1 本で実行します。
`bump-version` は CHANGELOG に未リリースの変更があるパッケージを自動検出し、
それらだけを新バージョンへ bump します（変更のないパッケージは据え置きです）。

```bash
mise run release:bump-version 0.3.0
# 差分を確認してから:
git add VERSION CHANGELOG.md packages/*/pyproject.toml packages/*/CHANGELOG.md uv.lock
git commit -m "chore(release): prepare v0.3.0"
git tag v0.3.0 && git push origin main --tags
```

タグを push するとリリースワークフローが起動し、対象パッケージをビルドして、
ルートの `CHANGELOG.md` から単一の GitHub Release を作成し、成果物を PyPI に公開します。

## License

MIT
