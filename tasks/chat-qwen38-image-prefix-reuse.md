# Qwen3.8 の画像追加で既存prefixを再利用する

## 方針（2026-09-19 ユーザー合意）

- Qwen3.8の画像付き履歴へ新しい画像を追加しても、変更のないprefixをAPCから再利用する。
- mlx-vlm本体のforkで実装・実機検証し、成立した変更をcommit固定でkiapiへ取り込む。上流へPRを出す。
- 困難な点が判明したら根拠を報告する。今回はOmniやaudio/videoの追加へ広げない。

## 完了条件

- text→image、image→image、複数image追加で既存prefixのhitとTTFT改善を確認する。
- cold/warmの回答とlogitsを比較し、位置・特徴の対応を検証する。
- 古い画像の変更、順序変更、同じpathの内容変更、画像途中の境界で誤hitしない。
- upstream regression test、kiapi unit test / chat full verifyを通す。
- fork commitを固定参照し、上流PRと残す制約・fallbackを記録する。

## 進捗

- kiapiは本番と分離したdetached worktree、mlx-vlmは上流main `e79b0e04`から
  `codex/qwen38-image-prefix-reuse`を作って調査開始。既存のstereo修正branchは保全した。
- upstreamはversion 0.7.1のままAPC coordinator等が更新されている。依存requirementsに差分はない。
- mlx-vlmにopt-in `apc_image_prefix=True`を実装。画像pixel/grid/spanをprefix単位でhashし、
  既存checkpointの範囲指定lookupを使う。cache保存形式は変更しない。
- 初回実機検証: image→imageは2,994 tokens中2,897を再利用し、11.78 s→0.55 s。
  旧画像はencodeせず追加画像だけをencodeした。text→image、2画像同時追加も成功した。
- 同じpathの旧画像差し替え、過去画像の順序変更は旧画像以後を再計算し、前段text 2,048 tokensのみ再利用。
- cold/warmの色の応答順は一致し、first-token KLは0.0005未満。量子化モデルなのでbit一致は保証しない。
- 明示position/rope、cached_image_features等のopaque overrideはAPCを無効化し、別の入力状態の混用を防いだ。
- upstreamのcache/generate/新規tests 451件、Qwen3.5系model contract 2件が通過。独立reviewで指摘を修正済み。
- upstream PR: https://github.com/Blaizzy/mlx-vlm/pull/2309
  fork commit: `3c5bd17c5cff3ad45d80273b366e86ad7df4ed96`。
- kiapiはtool.uv.sourcesでcommitを固定。PyPI配布の既存mlx-vlm 0.7.1では新引数を検出できないため、
  Qwen3.8も従来のwhole-request media invalidationへ安全に戻る。
- fork baseにはOmni C/Hの上流修正が入っていた。Cはno-op、Hはexpanded deepstack representationを検出してskip。
  公式0.7.1との互換性は残し、CPU testは両layoutのsemantic結果を検証する。
- kiapi CPU test 339件通過。chat full verify中。API経由の画像追加と旧画像変更も検証caseへ追加した。
- full verifyの新しい画像変更caseで「青へ差し替えたのにRed, green」と答えたが、cached_tokens=0。
  manager.clear後の同一requestも同じ結果で、cache誤利用ではなかった。
  履歴中に旧回答Red.を残していた検証入力の矛盾を除き、変形aspect ratioも含めて再検証する。
- upstream PR #2309のCI（pre-commit / Python tests）は成功した。
- kiapiの通常chat全caseは完了。stream全caseは検証入力の矛盾を除いて再実行し、3 modelすべて通過。
  API image-prefix caseはappend cached=2,499、変更した旧画像はcached=0で正しい順序の色を返した。
- 最終Qwen3.8 matrixも通過。45画像/2,991 tokens、画像がcheckpointを跨ぐcase、追加media、
  旧画像内容変更、clear/reloadを確認。release後のMLX active memoryは1,056 bytes。
- makeとCPU test 339件が通過。公式PyPI 0.7.1環境でもchat CPU test 54件を通し、fallback互換を確認。
- 次の一手: mainへ統合・push、停止中にuv sync --inexact --frozenでpinned engineを反映、サービス再起動と本番API検証。
  その後、このtaskをHISTORYへ移し、上流PR追従だけ別taskへ残す。
