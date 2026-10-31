# OpenAI 互換の embedding を PyPI へリリースする

完了条件: `POST /v1/embeddings` を含む版が PyPI と GitHub Release に出ている。

## 背景

2026-10-31 に `POST /v1/embedding` を消して `POST /v1/embeddings` に置き換えた（`aa70070`）。サーバー機へは配備済みで、検証の結果は `HISTORY.md` の同じ日。
PyPI の 0.8.0 はまだ古い API のまま。

## やること

- `CHANGELOG.md` の `Unreleased` の Breaking の項目を確かめて、`docs/runbooks/release.md` の手順で版を上げる。互換性を壊す変更なので、0.9.0 が候補
- 公開はオーナーに確かめてから行う

## 申し送り

- 速度の実測は Mac Studio の `qwen3-embedding-8b` だけ。VL モデルは測っていない
- VL の `usage` は画像を数えない
- `scripts/capabilities/verify_embedding.py` は OpenAI SDK を使わない。`openai` が kiapi の依存に無いため。SDK の確認は `uv run --with openai` で手で行った
