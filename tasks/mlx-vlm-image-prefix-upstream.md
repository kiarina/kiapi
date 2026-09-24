# Qwen3.8 画像prefix再利用の上流取り込みを追う

## 現在の状態（2026-09-24）

- 上流PR: https://github.com/Blaizzy/mlx-vlm/pull/2309 （OPEN、review待ち）。2026-09-24 に Qwen3.8-Flash-Next（`qwen4_exp`）
  対応を同じ PR に足し、title を「reuse Qwen3.5 / Qwen3.8-Flash-Next image prefixes when appending images」に変えた
  （Flash-Next 対応は上流にとって優先度が高く、混ぜたほうがマージされやすいというユーザー判断）
- fork: `kiarina/mlx-vlm`、branch `codex/qwen38-image-prefix-reuse`
- Qwen画像対応commit: `3c5bd17c5cff3ad45d80273b366e86ad7df4ed96`（base `e79b0e04`）、
  Flash-Next対応commit: `f54ccb9a`（Omni branch へは cherry-pick して `6581ba8c`）
- 現在のpinはOmni追補PR #2311も含む。`pyproject.toml` / `uv.lock`を正典とする。
- kiapiの`pyproject.toml`の`tool.uv.sources`と`uv.lock`で固定している。
- 実装・実測の正典はこのrepoのHISTORY 2026-09-19とchat README。
  engineの実装・tests・実機probeはmlx-vlm fork側が所有する。

## 次に行うこと

- review指摘が来たらforkで修正・testし、検証済みcommitにkiapiのpinを更新する。
- #2309とOmni追補#2311の両方が公式releaseに含まれたら、新引数・挙動を確認してuv source overrideを外す。
- Qwen3.8の画像追加・旧画像変更・text-only、Omniを含むchat full verifyを通す。
- #2309単体はsingle-request qwen3_5 / qwen4_exp text/image限定。Omniは#2311の対応範囲を確認し、batchへ無条件に広げない。
- fork baseでC/Hの上流修正を使っているため、公式版へ戻すときは
  `tasks/mlx-vlm-omni-deepstack-upstream.md`と互換patchの状態も合わせて確認する。

Omni側の追跡: [mlx-vlm-omni-media-prefix-upstream.md](mlx-vlm-omni-media-prefix-upstream.md)。
