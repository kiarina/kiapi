# AGENTS.md

このリポジトリで作業するエージェント向けのガイドラインです。

## リポジトリ構成

このリポジトリは uv workspace で、パッケージを `packages/` 以下に持ちます。

- `packages/kiapi` … 推論 API サーバー本体（Apple Silicon / MLX 専用）。

ワークスペース全体で単一のバージョンを共有し、ルートの `VERSION` ファイルで一元管理します。`bump-version` は CHANGELOG に未リリースの変更があるパッケージを自動検出し、それらだけを新バージョンへ bump・ビルド・PyPI 公開します（変更のないパッケージは据え置き）。リリースタグは `v<version>` 形式の単一タグで、これが GitHub Release と PyPI 公開を起動します。CHANGELOG はプロジェクト全体を記すルートの `CHANGELOG.md` と、各 `packages/<package>/CHANGELOG.md` の両方を持ちます。ルートの `pyproject.toml` は workspace 設定と共有の lint/test 設定のみを持ちます。

## 作業前に読むもの

あらゆるタスクを開始する前に、下記を必ず把握してください。

- 下の「タスク一覧」と、着手するタスクの `tasks/` ファイル
- `README.md`
- `ARCHITECTURE.md`
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

## タスク管理

- `tasks/` — 未完了タスク。1 タスク 1 ファイルで、背景・やること・進捗・申し送りを
  そのファイルに直接記載する
- `HISTORY.md` — 完了した作業、実測値、過去の意思決定
- 仕様・設計・手順の正典は従来どおり `docs/` と各 README

運用ルール:

- タスクに着手したら、進捗・未検証の懸念・踏んだ落とし穴・次の一手を該当の
  `tasks/` ファイルへ直接追記する
- 新しいタスク（今すぐ着手しない将来候補も含む）は `tasks/` にファイルを作り、
  下の「タスク一覧」へ 1 行追記する
- **タスクが完了したら、実測値・意思決定を `HISTORY.md` へ、再利用する知見を該当する
  `docs/` へ移した上で、タスクファイルを削除し、「タスク一覧」から行を消す。**
  削除したファイルの全文は git 履歴で辿れるため、転記は要点だけで良い
- `HISTORY.md` に記録するときは、作業日を含める
- 公開リポジトリなので、PC 名・ホスト名・アカウント名など、ローカル環境にしか意味の
  ない呼称は `tasks/` にも `HISTORY.md` にも書かない。運用中のマシンを指す必要が
  あるときは「サーバー機」「開発機」のような役割で書き、どのマシンかは agent
  リポジトリ（`~/src/github.com/kiarina/agent`）の runbook が持つ
- `tasks/` と `HISTORY.md` は作業指示・作業記録なので日本語で構わない
  （「ドキュメントの運用」の英語正典の対象外）

## テキストの方針

すべてのテキストは、シンプルで、明確で、簡潔にしてください。

- ドキュメントは、この方針に沿って簡潔に書いてください。
- コメントは、コードから読み取れない事情がある場合にのみ書いてください。
- `__init__.py` の `__all__` と遅延 import のマッピングでは、import 元ごとにグループコメントを残してください。 (必要なら ruff の例外を設定してください)
- コードをグループ化する区切りコメント（`# ---...` とグループ名）は残してください。
- docstring は、原則として下記にのみ書いてください。
  - 公開する設定クラスやスキーマクラスの説明
  - 公開するグローバル変数や型の説明
- 名前から役割を推測できる場合は、docstring を書かないでください。
- フィールドには docstring を書かないでください。Pydantic の公開クラスでは、フィールドに `title` と `description` を設定してください。

## ドキュメントの運用

- ルート・各パッケージ・各実装の README、`ARCHITECTURE.md`、`docs/` 以下の技術文書は英語で記述してください。
- `README.ja.md` など、言語別の README は作成しません。言語切り替えのリンクも置きません。
- ユーザーとの相談と、`AGENTS.md`、`CLAUDE.md` の作業指示は日本語で構いません。
- リポジトリの利用者や開発者が現在の仕様・手順として読む文書は、英語を正典とします。

## ドキュメントの配置

リポジトリ全体や複数のパッケージにまたがるドキュメントは、内容に応じて
`docs/concepts`、`docs/playbooks`、`docs/runbooks` のいずれかに配置します。

```text
docs/{concepts|playbooks|runbooks}/{わかりやすい-slug}.md
```

- `concepts` には、設計思想、アーキテクチャ、主要な仕組みの説明を置きます。
- `playbooks` には、開発や保守で繰り返し実施する作業手順を置きます。
- `runbooks` には、運用、監視、障害対応の手順を置きます。
- slug には、内容を端的に表す英語の kebab-case を使用します。
- 一つの主題が複数の文書に分かれる場合だけ、slug の directory を作ってその下に置きます。

特定の capability に閉じた説明は、共通の `docs/` ではなく、その family の実装と
同じ directory に配置します。

```text
packages/kiapi/src/kiapi/capabilities/{family}/
  README.md
```

## commit message と Pull Request タイトルの書き方

- commit message も、英語で `type(scope): subject` の Conventional Commits 形式で記述してください。
- Pull Request タイトルは、英語で `type(scope): subject` の Conventional Commits 形式で記述してください。
- scope には、family やサブパッケージ名を指定してください。
- scope が複数ある場合は、カンマ区切りで指定してください。
- scope は省略可能ですが、できるだけ明示してください。

## CHANGELOG の運用

- 依存パッケージの更新、機能追加・変更、デプロイパイプラインに関わる変更を行った場合は、`CHANGELOG.md` の `Unreleased` セクションに追記してください。
- 変更したパッケージの `packages/<package>/CHANGELOG.md` と、ルートの `CHANGELOG.md` の両方に追記してください。ルート側はパッケージ名（例: `**kiapi**: ...`）を接頭辞に付け、リポジトリ全体に関わる変更は接頭辞なしで記載します。リリースノートはルートの `CHANGELOG.md` から生成されます。
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

- **配置場所**: `scripts/capabilities/` の `verify_*.py`（capability 検証）を使用します。
- **用途**: 実際のモデルを GPU にロードし、生成・推論のフロー全体が正常に動作することを確認します。
- **ドライバ**: `mise run verify`（実体は `scripts/verify.py`）が、family の選択と kiapi の起動・停止、成果物の出力先切り替えまでを行います。成果物の出力先は `KIAPI_VERIFY_DIR`（既定 `.verify`）で指定でき、ドライバは `.verify/kiapi` を渡します。
- **実行方法**:

```bash
make verify        # family を対話選択して検証
make verify-fast   # 対話選択 + 各スクリプトを軽量実行（--fast）
make verify-kiapi  # 全 capability を非対話で検証

# 個別 capability やオプション指定は mise へ直接:
mise run verify --kiapi --family embedding --fast
```

## タスク一覧

各タスクの内容は `tasks/` のファイルだけに書き、ここはポインタ（1 ファイル 1 行）に保ちます。
ファイルの追加・削除のたびにこの一覧を更新してください。

（なし）
