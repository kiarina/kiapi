# mlx-video#52 がマージされたら LTX-2.5 の pin を上流へ戻す

## 背景

kiapi は 2026-09-15 に `ltx-2.5-distilled` を既定モデルとして取り込んだ。LTX-2.5 対応は上流
PR [Blaizzy/mlx-video#52](https://github.com/Blaizzy/mlx-video/pull/52) でレビュー中のため、
`src/kiapi/capabilities/ltx2/_helpers/register.py` の `MLX_VIDEO_SPEC` は fork の
`kiapi/ltx-2.5` branch の `cbb2c10f2a25305b0bf09169ab6b865ab86e3332` を指している。
これは PR head `d29c248` に、prompt enhancement の system prompt（`prompts/*.txt`）を wheel に
含める `package-data` の修正を 1 commit 足したもの。git / wheel install では prompt が入らず
`enhance_prompt` が `FileNotFoundError` になっていた（editable install の開発中は顕在化しない。
旧 pin の Gemma 3 prompt も同じく入っていなかった既存の不具合）。

`kiapi/ltx-2.5` は kiapi の pin を到達可能に保つためだけの branch。PR branch
（`ltx-2.5-local-port`）はレビューで rebase や分割がありうるので pin に使わない。
`kiapi/ltx-2.5` は force-push しない。

## やること

- `cbb2c10`（packaging 修正）は 2026-09-16 に PR branch `ltx-2.5-local-port` へも push 済み
  （ユーザー承認。PR 本文・コメントは更新していない）。今は PR head と `kiapi/ltx-2.5` が同じ commit
- #52 のレビューに対応する。mlx-video の作業 checkout は `~/src/github.com/Blaizzy/mlx-video`、
  PR 本文や maintainer への返信は送信前に日本語訳でユーザーの承認を取る
- レビューで kiapi が使う API（`generate_video` の引数、`PipelineType.DFR`、`LTX25_MODEL_REPO`、
  必要ファイル名）が変わったら、`_models/ltx25.py` と `register.py` の `LTX25_FILES` を追従させる
- マージされたら `MLX_VIDEO_SPEC` を `Blaizzy/mlx-video` の merge 後 commit へ戻し、
  `kiapi activate --family ltx2` で入れ替えて ltx2 の full verify（13 ケース）を通す
- 戻したら fork の `kiapi/ltx-2.5` branch を消してよいか判断する（旧 kiapi を install し直す
  可能性が無くなってから）

## 申し送り

- `verify_attrs` の `LTX25_MODEL_REPO` は、旧 pin の mlx-video が入った環境を未準備と判定させて
  `kiapi activate` に入れ替えさせるためのもの。上流へ戻すときも、kiapi が新しく依存する属性が
  あれば同じ方法で足す（`PythonPackageResource` は spec の変化では再 install しない）
- サーバー機の HF cache は、mlx-video 開発時の local dir から APFS clone で作った。
  `kiapi activate` は download せずに通る
