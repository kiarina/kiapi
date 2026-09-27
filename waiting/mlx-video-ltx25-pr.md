# mlx-video#52（LTX-2.5 対応）のレビューかマージ

- 待っているもの: 上流 PR [Blaizzy/mlx-video#52](https://github.com/Blaizzy/mlx-video/pull/52) のレビュー指摘、またはマージ。
  2026-09-28 時点で OPEN、レビュー・コメントなし（最終更新 2026-09-15）
- 確かめ方: `gh pr view 52 -R Blaizzy/mlx-video --json state,mergedAt,reviews,comments`
- 確かめる目安: 2026-10-05
- 満たされたら:
  - 指摘が来たら、対応するタスクを起こす。作業 checkout は `~/src/github.com/Blaizzy/mlx-video`。PR 本文や maintainer への
    返信は、送信前に日本語訳で kiarina の承認を取る。kiapi が使う API（`generate_video` の引数、`PipelineType.DFR`、
    `LTX25_MODEL_REPO`、必要ファイル名）が変わったら `_models/ltx25.py` と `register.py` の `LTX25_FILES` を追従させる
  - マージされたら、`src/kiapi/capabilities/ltx2/_helpers/register.py` の `MLX_VIDEO_SPEC` を `Blaizzy/mlx-video` の
    merge 後 commit へ戻すタスクを起こす。`kiapi activate --family ltx2` で入れ替えて ltx2 の full verify（13 ケース）を通す。
    kiapi が新しく依存する属性があれば `verify_attrs` に足す（`PythonPackageResource` は spec の変化では再 install しない）
  - 今の pin は fork の `kiapi/ltx-2.5` branch の `cbb2c10`（PR head と同じ。prompt の `package-data` 修正を含む）。
    この branch は force-push しない。消すのは旧 kiapi を入れ直す可能性が無くなってから
- 経緯: `HISTORY.md` の 2026-09-15〜16（LTX-2.5 の追加）と 2026-09-28（waiting への切り出し）
