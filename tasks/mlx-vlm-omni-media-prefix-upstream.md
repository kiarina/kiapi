# Omni media prefix再利用の上流取り込みを追う

## 状態（2026-09-20）

- PR: https://github.com/Blaizzy/mlx-vlm/pull/2311 （CI成功、review待ち）
- fork branch: `codex/omni-media-prefix-reuse`、実装commit `98300012`。
- 親PR #2309に依存する。現在のpinは`pyproject.toml` / `uv.lock`を正典とする。
- 実装・検証完了記録はHISTORY 2026-09-20、仕様はchat README。

## 次の作業

- review指摘へ対応し、親PRの変更があれば整合させる。検証済みcommitをkiapiへpinする。
- 両PRが公式releaseに含まれたら、Qwen側の`mlx-vlm-image-prefix-upstream.md`と合わせて
  source overrideを外す。複数audio、prefix capability marker、新引数が存在することを確認する。
- chat full verify、Omni画像追加・旧画像差し替え、native probeの追加mediaのみencodeと
  audio/FPS変更の再計算を再検証する。公式版移行時はdeepstackの既存追跡taskも確認する。
- Native interleaved audio/videoとbatchは今回未対応であり、無条件にAPCを有効化しない。
