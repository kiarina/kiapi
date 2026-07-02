# AGENTS.md

このリポジトリで作業するエージェント向けのガイドラインです。

## リポジトリ構成

このリポジトリは uv workspace で、複数パッケージを `packages/` 以下に持ちます。

- `packages/kiapi` … 推論 API サーバー本体（Apple Silicon / MLX 専用）。
- `packages/kiapi-relay` … relay トランスポート共有パッケージ（プラットフォーム非依存）。`kiapi` と `kiapi-proxy` の両方が依存します。
- `packages/kiapi-proxy` … relay 経由で kiapi に中継する Proxy サーバー（Linux/Windows/Mac で動作、`kiapi`/MLX 非依存）。

ワークスペース全体で単一のバージョンを共有し、ルートの `VERSION` ファイルで一元管理します。`bump-version` は CHANGELOG に未リリースの変更があるパッケージを自動検出し、それらだけを新バージョンへ bump・ビルド・PyPI 公開します（変更のないパッケージは据え置き）。リリースタグは `v<version>` 形式の単一タグで、これが GitHub Release と PyPI 公開を起動します。CHANGELOG はプロジェクト全体を記すルートの `CHANGELOG.md` と、各 `packages/<package>/CHANGELOG.md` の両方を持ちます。ルートの `pyproject.toml` は workspace 設定と共有の lint/test 設定のみを持ちます。

## 作業前に読むもの

あらゆるタスクを開始する前に、下記を必ず把握してください。

- `README.ja.md`
- `ARCHITECTURE.ja.md`
- `docs/concepts/`
- `mise.toml`
- `pyproject.toml` とルート、および対象 `packages/<package>/pyproject.toml`
- `.mise/tasks`
- `Makefile`
- `.github/workflows/`

コードの設計・追加・編集を行う場合、下記も先に把握してください。

- https://github.com/kiarina/crystal-architecture
- https://github.com/kiarina/pydantic-settings-manager

プラグイン機能やシングルトンの実装を行う場合、下記を把握してください。
- https://github.com/kiarina/kiarina-python/tree/main/packages/kiarina-utils-common

Google 認証が必要な機能を実装する場合、下記を把握してください。
- https://github.com/kiarina/kiarina-python/tree/main/packages/kiarina-lib-google

## ドキュメント作成時の注意点

- シンプルで、わかりやすく、簡潔に書きます。

## README の運用

- 常に `README.md` と `README.ja.md` の両方を作成します。
- `README.md` と `README.ja.md` は、言語違いの完全なミラーとして維持してください。
- README の各ファイルには、言語切り替えのためのリンクを必ず設置してください。
- 対応箇所を見出しで追いやすくするため、`README.ja.md` の `#`, `##`, `###`, `####` などの見出しは `README.md` と同じ英語に必ず一致させてください。

## ドキュメントの配置

リポジトリ全体や複数のパッケージにまたがるドキュメントは、内容に応じて
`docs/concepts`、`docs/playbooks`、`docs/runbooks` のいずれかに配置します。

```text
docs/{concepts|playbooks|runbooks}/{わかりやすい-slug}/
  README.md
  README.ja.md
```

- `concepts` には、設計思想、アーキテクチャ、主要な仕組みの説明を置きます。
- `playbooks` には、開発や保守で繰り返し実施する作業手順を置きます。
- `runbooks` には、運用、監視、障害対応の手順を置きます。
- directory の slug には、内容を端的に表す英語の kebab-case を使用します。

特定の capability に閉じた説明は、共通の `docs/` ではなく、その family の実装と
同じ directory に配置します。

```text
packages/kiapi/src/kiapi/capabilities/{family}/
  README.md
  README.ja.md
```

特定の relay implementation に閉じた説明も、その implementation と同じ directory
に配置します。

```text
packages/kiapi-relay/src/kiapi_relay/impl/{relay_name}/
  README.md
  README.ja.md
```

## commit message と Pull Request タイトルの書き方

- commit message も、英語で `type(scope): subject` の Conventional Commits 形式で記述してください。
- Pull Request タイトルは、英語で `type(scope): subject` の Conventional Commits 形式で記述してください。
- scope には、family やサブパッケージ名を指定してください。
- scope が複数ある場合は、カンマ区切りで指定してください。
- scope は省略可能ですが、できるだけ明示してください。

## CHANGELOG の運用

- 依存パッケージの更新、機能追加・変更、デプロイパイプラインに関わる変更を行った場合は、`CHANGELOG.md` の `Unreleased` セクションに追記してください。
- 変更したパッケージの `packages/<package>/CHANGELOG.md` と、ルートの `CHANGELOG.md` の両方に追記してください。ルート側はパッケージ名（例: `**kiapi-relay**: ...`）を接頭辞に付け、リポジトリ全体に関わる変更は接頭辞なしで記載します。リリースノートはルートの `CHANGELOG.md` から生成されます。
- ドキュメントのみの更新、フォーマット・スタイルのみの変更、コメントや内部整理など利用者向けの挙動に影響しない変更は、`CHANGELOG.md` に追記しなくて構いません。

## 変更後の確認

コードを変更した場合は、`make` を実行して format と lint、ドキュメントの再生成を行ってください。

```bash
make
```

## テスト方針

kiapi のテストは、実行速度の観点から下記を明確に分離します。

- CPU のみで完結する小さなロジックのテスト
- GPU を使用する重い機能テスト・回帰テスト

### 単体テスト

- **フレームワーク**: `pytest` を使用します。
- **配置場所**: 各パッケージの `packages/<package>/tests/` ディレクトリ以下に配置します。
- **構造**: そのパッケージの `src/<package>/` ディレクトリの構造をそのままミラーリングします。
  - 例: `packages/kiapi/src/kiapi/api/chat/router.py` のテストは `packages/kiapi/tests/api/chat/test_router.py` に配置します。
- **命名規則**:
  - 各ディレクトリには `__init__.py` を配置し、同名のテストファイル（例: `test_common.py`）が衝突しないようにします。
  - テストコードはクラス（`unittest.TestCase`）ではなく、関数（`def test_...():`）ベースで記述します。
- **制約**: GPU を使う処理（モデルのロードや推論実行など）は、`packages/*/tests/` 以下には含めないでください。
- **実行方法**:

```bash
make test
```

### 機能テスト・回帰テスト

- **配置場所**: `scripts/capabilities/` の `verify_*.py`（capability 検証）と `scripts/relay/verify_{local,gcp}.py`（relay トランスポート検証）を使用します。
- **用途**: 実際のモデルを GPU にロードし、生成・推論のフロー全体が正常に動作することを確認します。
- **ドライバ**: `mise run verify`（実体は `scripts/verify.py`）が、検証対象と relay の選択、kiapi / kiapi-proxy の起動・停止、成果物の出力先切り替えまでを行います。成果物の出力先は `KIAPI_VERIFY_DIR`（既定 `.verify`）で指定でき、ドライバは対象ごとに `.verify/kiapi` / `.verify/kiapi-proxy` を渡します。
- **実行方法**:

```bash
make verify              # 対象・family・relay を対話選択して検証
make verify-fast         # 対話選択 + 各スクリプトを軽量実行（--fast）
make verify-kiapi        # kiapi 直に対する capability 検証（relay 不要）
make verify-kiapi-relay  # relay トランスポートの検証（既定 relay: local）
make verify-kiapi-proxy  # kiapi-proxy 経由の capability 検証（既定 relay: local）

# 個別 capability やオプション指定は mise へ直接:
mise run verify --kiapi --family embedding --fast
mise run verify --kiapi-proxy --family chat --relay gcp
```
