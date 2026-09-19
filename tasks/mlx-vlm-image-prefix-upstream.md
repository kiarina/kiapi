# Qwen3.8 画像prefix再利用の上流取り込みを追う

## 現在の状態（2026-09-19）

- 上流PR: https://github.com/Blaizzy/mlx-vlm/pull/2309 （OPEN、CI成功、review待ち）
- fork: `kiarina/mlx-vlm`、branch `codex/qwen38-image-prefix-reuse`
- pin: `3c5bd17c5cff3ad45d80273b366e86ad7df4ed96`（base `e79b0e04`）
- kiapiの`pyproject.toml`の`tool.uv.sources`と`uv.lock`で固定している。
- 実装・実測の正典はこのrepoのHISTORY 2026-09-19とchat README。
  engineの実装・tests・実機probeはmlx-vlm fork側が所有する。

## 次に行うこと

- review指摘が来たらforkで修正・testし、検証済みcommitにkiapiのpinを更新する。
- 上流へmergeされ公式releaseに含まれたら、公式版の新引数・挙動を確認し、uv source overrideを外す。
- Qwen3.8の画像追加・旧画像変更・text-only、Omniを含むchat full verifyを通す。
- 初期版はsingle-request qwen3_5 text/image限定。batchやOmniのmedia追加へ無条件に広げない。
- fork baseでC/Hの上流修正を使っているため、公式版へ戻すときは
  `tasks/mlx-vlm-omni-deepstack-upstream.md`と互換patchの状態も合わせて確認する。
