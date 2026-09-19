# Qwen3.8 の cold prefill chunk サイズを測定する

## 範囲

- 2026-09-19 の依頼。chunk サイズだけを変更し、モデル・量子化・engine pin・APC 方針を維持する。
- base `5b5ab85`、mlx-vlm fork `3c5bd17` の画像 prefix APC を含めて比較する。
- サーバー機と同じ環境なので detached worktree と専用 venv を使用し、本番を停止して直列計測する。

## 計画と現在の状態

- 512 / 1024 / 2048 / 4096 / 8192 を比較。モデルロードを除外、APC を各 cold 試行前に clear。
- text 長文の TTFT・prompt throughput・MLX peak memory を反復計測し、候補を絞る。
- 画像入力、画像追加時の prefix hit、旧画像変更時の invalidation を確認する。
- 効果が再現した値だけ採用。差がなければ既定値を維持し、実測結果を記録する。
- 画像 APC の checkpoint は chunk より優先するため、実際に処理した chunk 長も観測する。

## 途中結果・環境競合

- 4K（4,114 tokens）は5サイズ各2回で16.0〜16.3秒。大きいchunkの速度上昇なし。
- 16K（16,402 tokens）の1回目は512=67.004、1024=66.779、2048=66.742、4096=67.398、8192=69.041秒。
- 16K逆順の2回目途中でUnreal Editorが起動しCPU約100%を消費。2048=69.170秒へ変動した。
  この時点以降の測定は不採用。エージェント自身の計測プロセスをSIGINTで停止し、本番を再起動した。
- ユーザーへUnreal作業終了のタイミングを確認中。GPUが空いたら16Kの比較をやり直す。
- 生データはworktreeの`.verify/prefill/sweep.json`。追加したscriptは計測中にmetadataと画像検証を拡張したため、
  初回結果のmetadataにはscript hash等がない。モデルとengine・chunk指定・text生成条件は同じ。

## 再開手順

- 本番health正常・queue_len=0を確認済み。通常の2048を維持し、productionコード・設定は未変更。
- 生データを`docs/playbooks/chat-prefill-benchmark/2026-09-19-initial-sweep.json`へ保全。
- `scripts/capabilities/measure_chat_prefill.py`と`docs/playbooks/chat-prefill-benchmark.md`を追加。
  `make`とCPU tests 339件は成功。`--image-checks`は準備済みだがGPUではまだ未実行。
- Unreal作業終了の回答と実プロセスの停止を確認する。サービスを停止し、隔離環境で
  `--steps 128 256 2048 --tokens 4096 --repeats 2`を比較する。改善候補があれば16Kへ進む。
- 16Kは512 / 1024 / 2048 / 4096 / 8192の5サイズ比較を安定した環境で完了する。
  本番APC budgetは16 GiB。初回比較は4 GiBで統一しており、変更する場合は別表にする。
- `--steps 512 2048 8192 --image-checks --repeats 2`で画像APCを確認。
- 新しいscriptのJSONにengine pin、script hash、arguments、実chunk長が記録される。
- 性能差が再現しなければ既定値は維持し、結果をHISTORYへ記録してtaskを完了する。
- 作業終了・失敗・中断のいずれでも本番serviceを再開し、health正常を確認する。
