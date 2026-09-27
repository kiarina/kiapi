# mlx-vlm #2309・#2311（prefix 再利用）のレビューかリリース

- 待っているもの: 上流 PR [Blaizzy/mlx-vlm#2309](https://github.com/Blaizzy/mlx-vlm/pull/2309)（Qwen3.5 / Qwen3.8-Flash-Next の
  画像 prefix 再利用）と [#2311](https://github.com/Blaizzy/mlx-vlm/pull/2311)（Omni の media prefix 再利用。#2309 に依存）の
  レビュー指摘、または両方のマージと公式リリース。2026-09-28 時点で両方 OPEN、レビューなし（最終更新 2026-09-24）。
  最新の 0.7.3 には入っていない
- 確かめ方: `gh pr view 2309 -R Blaizzy/mlx-vlm --json state,mergedAt,reviews,comments`（2311 も同じ）。
  マージ後は `gh release list -R Blaizzy/mlx-vlm` と、fork の checkout（`~/src/github.com/kiarina/mlx-vlm`、`upstream` remote）で
  `git fetch upstream --tags && git tag --contains <merge commit>`
- 確かめる目安: 2026-10-05
- 満たされたら:
  - 指摘が来たら、fork で修正・test して検証済み commit へ kiapi の pin を更新するタスクを起こす。fork の branch は
    `codex/qwen38-image-prefix-reuse`（#2309、先頭 `f54ccb9a`）と `codex/omni-media-prefix-reuse`（#2311、先頭 `6581ba8c` = 今の pin）。
    force-push しない
  - 両方が公式リリースに入ったら、`tool.uv.sources` の mlx-vlm 行を外すタスクを起こす。新引数・複数 audio・prefix capability marker が
    あることを確かめ、chat の full verify、Qwen3.8 の画像追加・旧画像変更・text-only、Omni の画像追加・旧画像差し替え、
    native probe（追加 media だけ encode、audio / FPS 変更で再計算）を再検証する。#2309 は single-request の qwen3_5 / qwen4_exp
    限定、native interleaved audio/video と batch は未対応なので、APC を無条件に広げない
- 経緯: `HISTORY.md` の 2026-09-19・2026-09-20・2026-09-24（実装と実測）と 2026-09-28。仕様は chat の README
