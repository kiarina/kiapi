# relay を廃止して Tailscale 直結へ一本化する

## 背景

relay（GCS + Firebase RTDB）は、直接届かない kiapi へ HTTP を届けるための仕組みだが、
全 PC が Tailscale に乗った現在、reachability は Tailscale が解決している。

- 2026-08-31 に SSE watch が無言のネットワーク断でハングする障害が発生
  （`0447ebc` の read timeout で修正済み）
- レイテンシは relay 経由で `/health` 1.1〜1.7 秒、Tailscale 直結で 33ms
- relay は応答を全量バッファするため、chat の streaming が逐次配信にならない
- 2026-09-01 から mac-studio-m4-max で `tailscale serve --bg --https=8500 8500` を
  立て、kiari / spirits-garden の日常利用を直結
  （`https://mac-studio-m4-max.taile8045d.ts.net:8500/v1`）へ切り替えて併用評価中

評価（1〜2 週間、直結で困る場面がないかの観察）の主管は agent リポジトリの
`~/src/github.com/kiarina/agent/tasks/kiapi-relay-removal-evaluation.md`。
このタスクは評価で廃止が決まった後の kiapi 側の実装を担当する。

## 決定事項（2026-09-01 ユーザー確認済み）

- 評価期間を短縮して廃止を決定。スモーク確認は省略し、そのまま削除へ進む
  （直結は日常利用中で、問題が出ても git で戻せるためリスク許容）
- PyPI の `kiapi-relay` / `kiapi-proxy` へ deprecation 告知の最終リリースは
  **出さない**。既存リリースを残したまま以後更新しない
- GCP リソースの後始末は先送りせず、実機切り替え（Phase 3）と同時に削除する

## やること

- [x] 評価完了と廃止の決定をユーザーと確認してから着手する（2026-09-01）
- [ ] Phase 1: コード削除
  - kiapi 本体から relay 組み込みを除去。対象は `packages/kiapi/src/kiapi/` の
    `cli/run/cli.py`（`--relay`）、`api/app.py`、`api/_helpers/get_relay_runner.py`、
    `api/health/router.py`、`api/health/_views/health_response.py`、
    `cli/config/template/cli.py`、`api/__init__.py`
  - `packages/kiapi-relay` と `packages/kiapi-proxy` を削除し、ルート
    `pyproject.toml` の workspace 依存と ruff `known-first-party` を更新、
    `uv.lock` を再生成
  - `scripts/relay/` を削除、`scripts/verify.py` を kiapi 単体ターゲットへ縮小、
    Makefile の `setup-relay-gcp` / `verify-kiapi-relay` / `verify-kiapi-proxy` と
    dev run の `--relay gcp` を除去
  - `docs/concepts/relay.md` を削除し、`ARCHITECTURE.md` / `README.md` を
    Tailscale serve 直結を正とする内容へ更新
  - `make verify-kiapi` と CI を通す。release パイプラインはパッケージを
    `mise run package:list` で動的検出するため追従するはずだが、`package:list` と
    bump-version がパッケージ減に耐えるか実際に確認する
- [ ] Phase 2: 破壊的変更としてバージョンを上げ、CHANGELOG（ルート + kiapi）へ
      移行手順（Tailscale serve への切り替え）を書いてリリースする
- [ ] Phase 3: 実機切り替えと後始末（同時に実施）
  - mac-studio へ新バージョンをデプロイし、Tailscale 直結で `/health` と
    chat streaming を確認する
  - macbook-pro-m1-max の kiapi-proxy launchd service
    （`io.github.kiarina.kiapi-proxy`）を停止・uninstall し、
    `~/.config/kiapi-proxy/settings.yaml` を整理する
  - クライアント側に macbook の `127.0.0.1:8500`（proxy）を向いた設定が
    残っていないか確認する（kiari / spirits-garden は直結へ切り替え済み）
  - GCS bucket `kiarina-kiapi`、Firebase RTDB `kiarina-kiapi.asia-southeast1`、
    relay 用の Google 認証設定を削除する（`gcp:setup` があるため再構築は可能）

## 申し送り

- Phase 3 完了までは relay / kiapi-proxy を並行稼働させたまま（切り戻しの保険）
- Tailscale serve の管理手順と現在の運用状態は agent リポジトリの
  `docs/runbooks/kiapi-operations.md` を参照。廃止後の runbook 書き換えと
  agent 側タスクの完了処理は agent リポジトリの
  `tasks/kiapi-relay-removal-evaluation.md` が担当
