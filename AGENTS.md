# AGENTS.md

このリポジトリで作業するエージェント向けのガイドラインです。

## 作業前に読むもの

あらゆるタスクを開始する前に、下記を必ず把握してください。

- `README.ja.md`
- `ARCHITECTURE.ja.md`
- `pyproject.toml`
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

## README の運用

- 常に `README.md` と `README.ja.md` の両方を作成します。
- `README.md` と `README.ja.md` は、言語違いの完全なミラーとして維持してください。
- README の各ファイルには、言語切り替えのためのリンクを必ず設置してください。
- 対応箇所を見出しで追いやすくするため、`README.ja.md` の `#`, `##`, `###`, `####` などの見出しは `README.md` と同じ英語に必ず一致させてください。

## commit message と Pull Request タイトルの書き方

- commit message も、英語で `type(scope): subject` の Conventional Commits 形式で記述してください。
- Pull Request タイトルは、英語で `type(scope): subject` の Conventional Commits 形式で記述してください。
- scope には、family やサブパッケージ名を指定してください。
- scope が複数ある場合は、カンマ区切りで指定してください。
- scope は省略可能ですが、できるだけ明示してください。

## CHANGELOG の運用

- 依存パッケージの更新、機能追加・変更、デプロイパイプラインに関わる変更を行った場合は、`CHANGELOG.md` の `Unreleased` セクションに追記してください。
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
- **配置場所**: `tests/` ディレクトリ以下に配置します。
- **構造**: `kiapi/` ディレクトリの構造をそのままミラーリングします。
  - 例: `kiapi/api/chat/router.py` のテストは `tests/api/chat/test_router.py` に配置します。
- **命名規則**:
  - 各ディレクトリには `__init__.py` を配置し、同名のテストファイル（例: `test_common.py`）が衝突しないようにします。
  - テストコードはクラス（`unittest.TestCase`）ではなく、関数（`def test_...():`）ベースで記述します。
- **制約**: GPU を使う処理（モデルのロードや推論実行など）は、`tests/` 以下には含めないでください。
- **実行方法**:

```bash
make test
```

### 機能テスト・回帰テスト

- **配置場所**: `scripts/` ディレクトリ以下の `verify_*.py` スクリプトを使用します。
- **用途**: 実際のモデルを GPU にロードし、生成・推論のフロー全体が正常に動作することを確認します。
- **実行方法**:

```bash
make verify  # 全ての capability のテストを実施
make verify-fast  # 全て capability の 1 つのテストのみ実施
make verify-one  # embedding capability のみ実施
make verify-{capability}  # 指定した capability のみ実施
```
