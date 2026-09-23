# chat に Qwen3.8-Flash-Next を追加する

## 背景

Qwen3.8-Flash-Next（125B MoE + 51B n-gram 埋め込み表、6B active、`model_type: qwen4_exp`）は、
公式の比較で Qwen3.8-27B を全般に上回り、特にエージェント系（DeepSWE 1.1 58.7 vs 42.2）で差が大きい。
入力は text / image / video、thinking 切り替え、context 262K（1M まで拡張可）で、機能面は 27B とほぼ同じ。

mlx-vlm は #2032（2026-08-26 merge）で `qwen4_exp` に対応済み。**現在 pin している fork
（base `e79b0e04`、2026-09-18）にも `mlx_vlm/models/qwen4_exp` が入っているので、mlx-vlm の更新は前提ではない。**

## 候補の重み（2026-09-24 時点、容量は HF の合計）

- `mlx-community/Qwen3.8-Flash-Next-4bit` — 111.5 GB。128 GB のサーバー機では他モデルと共存できず、長い context の余地も小さい
- `sh0wie/Qwen3.8-Flash-Next-REAP-288-MLX-4bit` — 73.5 GB。expert を 512→288 に pruning。
  model card 上は M4 Max で常駐 68 GB（n-gram 表を NVMe から streaming すると 39 GB）、stock mlx-vlm で約 28 tok/s。
  REAP の校正は agentic-coding の通信のみで、公開評価は HumanEval（93.9→91.5）だけ。日本語・知識・vision は未評価

どちらを既定にするかは、labs での劣化評価（agent リポジトリの tasks が追跡）の結果で決める。

## やること

- fork の pin のまま `qwen4_exp` の重みが load・生成できるか、text / image / video で確かめる
- `qwen3_5` handler を流用できるか調べる（chat template、Hermes/XML の tool call、thinking の切り替え）。
  できなければ `_models/` に handler を足す
- `ModelSpec` を登録し、`weight_gb` と `peak_headroom_gb` を実測で決める。
  16 GiB の APC と共存できるか、できないなら APC 上限をモデルごとに持たせるか判断する
- APC: text の prefix 再利用は上流の APC 再設計（#1960）と QSA cache 再利用（#2126）で `qwen4_exp` も対象のはず。
  kiapi 経由で `cached_tokens` が出ることを実測する
- 画像追加時の prefix 再利用（fork の `apc_image_prefix`、#2309）は `qwen3_5` 専用。
  `qwen4_exp` へ広げるかは、対応を終えてから別タスクにする（この task の前提にしない）
- n-gram 表の NVMe streaming（oMLX 等）は stock mlx-vlm では使えない。使うなら別途検討する
- chat の full verify を通す。alias をどこへ向けるか（`qwen3.8` / `vlm` を移すか）を決める

## 完了条件

- 選んだ重みが kiapi の chat で text / image / tool call まで動き、full verify が通る
- サーバー機でのピークメモリ、prefill / decode の速度、APC の hit を HISTORY に記録している
