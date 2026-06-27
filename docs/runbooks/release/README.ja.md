# Release

[English](README.md) | **日本語**

## Prepare

ルートの `CHANGELOG.md` と、変更した各パッケージの `CHANGELOG.md` の
`Unreleased` セクションにリリースノートを追加します。

次に、リリースを準備します。

```bash
mise run release:bump-version <version>
mise run ci --no-setup
```

変更内容を確認します。未リリースの変更があるパッケージだけが bump・公開されます。

## Publish

準備した変更を commit し、共有バージョンの tag を作成して push します。

```bash
git add VERSION CHANGELOG.md packages/*/pyproject.toml packages/*/CHANGELOG.md uv.lock
git commit -m "chore(release): prepare v<version>"
git tag v<version>
git push origin main --tags
```

tag により release workflow が起動し、GitHub Release の作成と、対象パッケージの
PyPI への公開が行われます。

## Verify

`Release PyPI` workflow の成功を確認し、GitHub Release と PyPI 上の公開パッケージを
確認します。
