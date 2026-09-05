# HISTORY

完了した作業、実測値、過去の意思決定の記録です。
作業日を含めて、新しいものを上に追記します。

## 2026-09-05 — 依存・Actions・Dependabot 設定の定期保守

- open alert 0 件・CI success の状態から、lockfile を `uv lock --upgrade` で更新。
  torch 2.13→2.14、torchvision 0.28→0.29、huggingface-hub 1.29→1.30、
  tokenizers 0.23.1→0.23.2、anyio 4.14.2→4.15.0、ruff 0.16.5→0.16.6 ほか計 10 件。
  `mlx-vlm==0.6.3` は chat のパッチ前提の意図的 pin なので据え置き
- torch は kiapi 本体から直接 import せず、transformers の Qwen processor 用に
  入れているだけなので、unit test では上げても差が出ない。開発機（Apple Silicon）で
  torch / torchvision / torchaudio の実 import と MPS 利用可否、`torchaudio.functional.resample`、
  `torchvision.transforms.v2.Resize` の実行まで確認した。torchaudio は 2.11.0 のまま
  torch 2.14 と共存する。**実モデル推論での検証は未実施**
- GitHub Actions を現行 major へ更新（checkout v6/v4→v7、configure-pages v5→v6、
  upload-pages-artifact v3→v5、deploy-pages v4→v5、upload-artifact v4→v7、
  download-artifact v4→v8）。落とし穴として、upload-pages-artifact は v4 以降
  dotfile を既定で除外するため、`public/.nojekyll` が黙って落ちる。
  `include-hidden-files: true` を明示して回避し、deploy 後に公開 URL の
  `.nojekyll` が 200 で返ることを確認した
- `.github/dependabot.yml` が陳腐化していた。npm ecosystem の記述は v0.6.0 で
  削除した root の `package.json` を指しており、どの manifest にも一致しない
  設定が残っていた。`uv` と `github-actions` の 2 ecosystem に置き換え、
  pin の理由が同じ `mlx-vlm` を ignore に入れた。push 後、両 ecosystem の
  Dependabot run が success で PR 0 件（＝現時点で追従漏れなし）を確認
- `packages/kiapi/pyproject.toml` の mlx-vlm コメントが存在しない
  `docs/mlx-vlm.md` を指していたので、実体の
  `src/kiapi/capabilities/chat/README.md` へ修正
- 検証は開発機で `mise run ci`（lint + mypy 571 files + 276 tests + config/pages
  再生成 + build）を通し、生成物に差分が出ないことを確認。push 後の CI も success

## 2026-09-01 — relay を廃止して Tailscale 直結へ一本化（v0.6.0）

- ユーザー判断で併用評価（開始 2026-09-01）を短縮し、relay 廃止を決定。
  スモーク確認は省略（直結は日常利用中、git で戻せるためリスク許容）
- `packages/kiapi-relay` / `packages/kiapi-proxy`、relay runner の組み込み、
  `kiapi run --relay`、`/health` の `relay` フィールド、`relay-gcp` extra、
  `scripts/relay/`、`docs/concepts/relay.md` を削除（154 ファイル、約 7,300 行削減）。
  release パイプラインは `packages/*/` を動的検出するため削除に自動追従した
- 破壊的変更として v0.6.0 をリリース（CI / Release PyPI とも成功）。
  PyPI の `kiapi-relay` / `kiapi-proxy` には deprecation の最終リリースを
  出さない判断（実利用者が本人のみ。既存リリースは残置、以後更新しない）
- サーバー機へデプロイ時の落とし穴 2 件:
  - 削除済みパッケージの `__pycache__` 残骸が workspace glob `packages/*` に
    マッチして `uv run` が失敗。残骸ディレクトリの削除で解消
  - `tailscale serve --https=8500` が Tailscale IP の 8500 を掴むため、
    kiapi の `host: 0.0.0.0` bind が再起動時に EADDRINUSE で失敗
    （初回は kiapi が先に bind していたため共存できていた）。
    `host: 127.0.0.1` へ変更して解消。serve は 127.0.0.1 へ proxy するので
    tailnet 経由のアクセスは変わらず、tailnet 外への露出もなくなった
- サーバー機の `~/.config/kiapi/settings.yaml` から relay / google セクションを
  除去（backup: `settings.yaml.pre-relay-removal`）。lock 外の mlx-video は保全
- 開発機の kiapi-proxy launchd service は、editable install の実体が
  削除済みで CLI が使えないため、`launchctl bootout` + plist 削除で手動
  uninstall。`~/.config/kiapi-proxy/` も削除
- GCP の後始末（ユーザー承認済み）: GCS bucket `kiarina-kiapi`（relay セッション
  残骸 約 105KB のみ）を削除、Firebase RTDB インスタンス `kiarina-kiapi`
  （asia-southeast1）を disable → 削除。ADC は relay 専用ではないため残置
- relay を復活させる場合は git 履歴（v0.5.3 以前）と、当時の GCP 構築手順
  （`packages/kiapi-relay/.mise/tasks/gcp/setup`、削除済み）を参照

## 2026-09-01 — relay watch ハングの修正と Tailscale 直結の開始

- 2026-08-31、サーバー機の kiapi で RTDB SSE watch が無言のネットワーク断
  （18:53〜20:13 の DNS 断）で永久ハングし、proxy → kiapi が不通になった。
  heartbeat は watch と独立に生き残るため liveness からは検知できず、
  RTDB の `nodes/{node_id}/requests` に通知が 10 件滞留していた。kiapi 再起動で復旧
- 原因は共有 httpx クライアントの `read=None`。`0447ebc` で watch ストリームに
  読み取りタイムアウト（`watch_read_timeout_s`、既定 90 秒）を追加して修正し、
  サーバー機へデプロイ
- 実測: `/health` は relay 経由 1.1〜1.7 秒、Tailscale serve 直結 33ms
- relay 経由は応答を全量バッファするため chat streaming が逐次配信にならないことを
  `RelayRunner._dispatch` で確認
- これらを受けて relay 廃止の検討を開始（`tasks/remove-relay.md`）。
  サーバー機で `tailscale serve --bg --https=8500 8500` を開始し、
  kiari / spirits-garden の日常利用を直結へ切り替えて併用評価中
