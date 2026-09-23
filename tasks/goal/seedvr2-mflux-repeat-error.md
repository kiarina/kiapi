# seedvr2 の upscale が mflux 0.19.1 + mlx 0.32.2 で失敗する

## 背景

2026-09-15 の `mise run verify --kiapi --fast` で、seedvr2 だけが失敗した
（他の 12 family は通過）。`POST /v1/image/seedvr2/upscale` が 500 を返す。

```text
mflux/models/seedvr2/model/seedvr2_transformer/attention.py, line 121, in _repeat_text_for_windows
    return mx.repeat(txt, mx.array(counts), axis=0).reshape(-1, *txt.shape[2:])
TypeError: repeat(): incompatible function arguments.
    1. repeat(array: array, repeats: int, axis: int | None = None, *, stream: StreamOrDevice = None) -> array
```

- mflux 0.19.1 は `mx.repeat` に配列の `repeats` を渡すが、mlx 0.32.2 の
  `mx.repeat` は `int` しか受け付けない
- mflux 0.19.1 / mlx 0.32.2 は 2026-08-27 の lock 更新（`990cca7`）で入った。
  単一パッケージ構成への移行（2026-09-15）とは無関係
- 上流 main（filipstrand/mflux）では `_repeat_text_for_windows` がインデックス参照
  （`txt[win_to_batch]`）に書き換えられており、修正済み。2026-09-15 時点で PyPI の
  最新は 0.19.1 で、修正はまだリリースされていない。関連 issue / PR は見つからなかった

## やること

- mflux の次のリリースで修正が入ったら lock を上げ、`mise run verify --kiapi --family seedvr2`
  で確認する
- 待てない場合の選択肢: mflux を修正前の版（0.18.x）へ下げる（ただし他の mflux 系
  family と mlx の範囲制約を確認する）か、kiapi 側で該当関数を差し替える

## 申し送り

- 他の mflux 系 family（zimage / flux2 / qwen / ernie / ideogram4）は fast verify を通過
