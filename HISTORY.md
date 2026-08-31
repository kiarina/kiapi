# HISTORY

完了した作業、実測値、過去の意思決定の記録です。
作業日と作業 PC 名を含めて、新しいものを上に追記します。

## 2026-09-01 — relay watch ハングの修正と Tailscale 直結の開始

作業 PC: macbook-pro-m1-max（mac-studio-m4-max へは SSH で操作）

- 2026-08-31、mac-studio-m4-max の kiapi で RTDB SSE watch が無言のネットワーク断
  （18:53〜20:13 の DNS 断）で永久ハングし、proxy → kiapi が不通になった。
  heartbeat は watch と独立に生き残るため liveness からは検知できず、
  RTDB の `nodes/{node_id}/requests` に通知が 10 件滞留していた。kiapi 再起動で復旧
- 原因は共有 httpx クライアントの `read=None`。`0447ebc` で watch ストリームに
  読み取りタイムアウト（`watch_read_timeout_s`、既定 90 秒）を追加して修正し、
  mac-studio へデプロイ
- 実測: `/health` は relay 経由 1.1〜1.7 秒、Tailscale serve 直結 33ms
- relay 経由は応答を全量バッファするため chat streaming が逐次配信にならないことを
  `RelayRunner._dispatch` で確認
- これらを受けて relay 廃止の検討を開始（`tasks/remove-relay.md`）。
  mac-studio-m4-max で `tailscale serve --bg --https=8500 8500` を開始し、
  kiari / spirits-garden の日常利用を直結へ切り替えて併用評価中
