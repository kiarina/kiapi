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

## やること

- [ ] 評価完了と廃止の決定をユーザーと確認してから着手する
- [ ] 削除範囲を設計する
  - `packages/kiapi-relay` と `packages/kiapi-proxy` の削除
    （workspace 構成、`bump-version`、CI・リリースパイプラインへの影響を確認）
  - kiapi 本体から relay runner の組み込み、`--relay` オプション、
    `/health` の relay 表示を除去
  - `scripts/relay/verify_{local,gcp}.py` と mise verify の relay 系タスクを整理
  - `docs/concepts/relay.md`、`ARCHITECTURE.md`、`README.md` を更新
- [ ] 破壊的変更としてバージョンを上げ、CHANGELOG（ルート + 各パッケージ）へ
      移行手順（Tailscale serve への切り替え）を書く
- [ ] PyPI 配布済みの `kiapi-relay` / `kiapi-proxy` の扱いを決める
      （最終リリースで deprecation を告知するか）
- [ ] 後始末を検討する: GCS bucket `kiarina-kiapi`、Firebase RTDB インスタンス、
      relay 用の Google 認証設定、macbook-pro-m1-max の kiapi-proxy launchd service
      （`io.github.kiarina.kiapi-proxy`）の uninstall

## 申し送り

- 評価期間中は relay / kiapi-proxy を並行稼働させたまま（切り戻しの保険）
- Tailscale serve の管理手順と現在の運用状態は agent リポジトリの
  `docs/runbooks/kiapi-operations.md` を参照
