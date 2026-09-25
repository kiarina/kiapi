# mflux#741 がリリースされたら Qwen-Image-2.1 の pin を上流へ戻す

## 背景

2026-09-25 に qwen family へ `image-2.1`（`Qwen/Qwen-Image-2.1`）を足した。mflux 0.20.0 には 2.1 の
txt2img / img2img（`QwenImage21`）しかなく、編集・RGBA 出力・複数参照は上流 PR
[mflux-community/mflux#741](https://github.com/mflux-community/mflux/pull/741)（dreampuf、OPEN）にある。

- fork: [kiarina/mflux](https://github.com/kiarina/mflux) の `qwen-image-2.1-edit` branch。
  PR head `144a6becfb587bcaa0139758131faf0a7930ae18`（`v.0.20.0` + PR の 2 commit）をそのまま置いている。
  kiapi の pin を到達可能に保つための branch なので force-push しない
- 作業 checkout は `~/src/github.com/kiarina/mflux`（`origin` = fork、`upstream` = mflux-community/mflux）
- kiapi は `pyproject.toml` の `[tool.uv.sources]` と `uv.lock` で固定している。公開 wheel の依存は
  `mflux>=0.20.0` のままで、公式 mflux では `mflux.models.qwen21.reference` が無いので
  `register.py` が `image-2.1` を登録しない
- kiapi は 2.1 の `QwenImage21Edit`（vision tower 付き）だけを使い、生成も編集も 1 つの常駐モデルで行う。
  txt2img 専用の `QwenImage21` は checkpoint の layout が違い、両方を載せると重みが二重になるので使っていない
  （そのため 2.1 では strength 方式の img2img を受け付けない）

## 上流 PR の状態（2026-09-25 確認）

- CI の `tests` だけ失敗。member の fxd0h のコメントでは、CI 仮想 Metal の MPS OOM と float32 の atol（1e-4 に対し 1.23e-4）で、
  実装の誤りではないという見立て。block-causal attention・prefix cache・参照 latent の差し込みは誰も diffusers と突き合わせていない
- 作者自身の報告: 1024² の一部の編集（雪景色化・2 体合成）は指示に従わず、公式 diffusers でも同様に失敗する
- **踏んだ落とし穴（軽微、2026-09-25 に PR へ共有済み）**: `mflux.models.qwen21.variants.edit.qwen_image_21_edit` を最初に import すると
  循環 import で失敗する（その module が `reference.latent_creator` を import → `reference/__init__.py` が読み込み途中の同じ module から
  `QwenImage21Edit` を取り出そうとする）。2026-09-25 に kiapi と無関係の新しい venv でも再現した。PR の CLI・README・テストはすべて
  `mflux.models.qwen21.reference` 経由なので文書どおりの使い方では起きないが、mflux の他の model は variant の module を直接 import
  するのが慣例なので、その書き方だと踏む。kiapi は `reference` 経由で import している。ユーザーの承認を得て、再現・原因・
  `reference/__init__.py` の再 export を遅延させる直し方を PR にコメントした
  （https://github.com/mflux-community/mflux/pull/741#issuecomment-5832506872）。返信が来たら内容を確かめ、返事が要るなら
  日本語訳でユーザーの承認を取ってから返す。直ったら kiapi の import を variant の module へ戻すかは、戻すときに判断する

## やること

- #741 がマージされて PyPI にリリースされたら、`[tool.uv.sources]` の mflux 行を外して `mflux>=<その版>` にし、
  import 先（`mflux.models.qwen21.reference.QwenImage21Edit`）と `generate_image` の引数
  （`image_paths`、`output_resolution`、`use_kv_cache`）が変わっていないか確かめる
- 戻したら qwen の full verify（`mise run verify --kiapi --family qwen`、image-2.1 は [9]〜[12]）と、
  mflux を使う他の family（zimage / flux2 / ernie / ideogram4 / seedvr2）の full verify を通す
- 戻したら fork の `qwen-image-2.1-edit` branch を消してよいか判断する（旧 kiapi を install し直す可能性が無くなってから）
- レビューで PR が rebase・分割されたら、fork の branch は動かさず、検証した新しい commit を別 branch に置いて pin を更新する

## 申し送り

- 実測（サーバー機 Mac Studio M4 Max 128GB、q8、直接呼び出し）: 常駐 16.6 GiB、load 時の peak 31.5 GiB、
  1024² の 40 steps で txt2img 210 s、参照 1 枚の編集 246 s（peak 29.6 GiB）。bf16 は 5.0 s/step（q8 は 5.4）で
  速さはほぼ同じなのに 13 GiB 多いので、既定は q8。上流の M5 Max bf16 の 78 s より約 2.7 倍遅い
- 2048² 以上のメモリは未計測。`peak_headroom_gb=15.0` は 1024² の実測からの見積もり
- 2.1 は LoRA 非対応（mflux が未実装）。`/edit` の mask・丸印による部分編集は、参照画像に描き込めば model が読むはずだが未検証
