# Qwen3-Omni と multimodal chat に APC を広げる

## 背景

2026-09-19にQwen3.6 / Qwen3.8のtext-only requestへmemory-only Automatic Prefix Cachingを導入した。
Qwen3-OmniとQwen3.6 / Qwen3.8の画像入力は、安全性を個別検証するまで明示的に対象外にしている。
text-onlyの実測と設計判断は`HISTORY.md`を参照。

## やること

- Qwen3-Omniのtext-onlyでcold/warm parity、partial hit、TTFT、memoryを確認する
- image、audio、video、image + videoを一つずつ有効にする
- mediaがprefix内とsuffix側にある場合を分け、内容hash、path、`fps`、`use_audio_in_video`の変更で誤hitしないことを確認する
- 2048 tokensを越えるvisual promptでpatch C / HとAPC cache layoutの組み合わせを確認する
- disk tierはmemory APCに対する追加効果、平文metadata、容量上限、破損時fallbackを評価してから採否を決める
- 各段階でserverの生存、cold/warm response semantics、chat full verifyを確認する

## 完了条件

- 対応すると決めた各modalityでcache hitとTTFT改善を実測し、cold/warmで意味的な回帰がない
- 同じpathで内容変更、異なるpathで同じ内容、media option変更で誤hitしない
- model eviction / restartでstale cacheやmemory leakがない
- 未対応で残すmodalityやdisk tierは、理由と設定上の除外が明確になっている
