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

## labs での評価結果（2026-09-24）

正典: labs `2026/09/24/qwen38-flash-next-reap-eval`。サーバー機、fork と同じ base の upstream mlx-vlm `e79b0e04`、thinking 無効。

| | 日本語 32 問 | needle 32K / 128K / 240K | エージェント 4 題 | load peak |
|---|---:|---|---:|---:|
| Qwen3.8-27B | 30 | 全問正解 / 全問 / 全問 | 4 | 16.1 GB |
| Flash-Next 4bit | 32 | 正解（prefill 256）/ OOM / 未実施 | 4（prefill 256・APC 1 GB） | 111.5 GB |
| REAP-288 | 12（知識 1/16） | 全問正解 / 全問 / 全問 | 3 | 41.5 GB |

- **REAP-288 は日本語の用途に使えない。** 一般知識が言語を問わず崩れ、中国語へ流れる（コード中の「時間」を「时间」に書き換えた）。
  長い context の検索と prefill 速度（約 560〜600 tok/s、27B は 114〜217）は優秀
- **4bit のフル版は、既定の GPU wired limit では 128K まで扱えない**（Metal OOM）。`iogpu.wired_limit_mb` を上げる案は未検証
- 上流の APC は `qwen4_exp` でも turn をまたいで prefix を再利用した（REAP-288 で確認）
- load には `ulimit -n` の引き上げが要る（n-gram 表の shard を全部 mmap するため。既定 256 では `Too many open files`）。
  launchd で動かすなら plist の `SoftResourceLimits` などで上げる

## n-gram 表（PLE）を mmap にした追試（2026-09-24）

正典: labs `2026/09/24/qwen38-flash-next-ple-mmap`。mlx-vlm の `prepare_external_ple_model` で、4bit のフル版に
`ple-store.json` を付けた view を作った（非 PLE の重みは hard link、payload のコピーなし）。

- load peak は 111.5 → **79.5 GB**（PLE の 32.0 GB がちょうど抜けた）。decode は 47.1 → 40.2 tok/s（約 15% 低下、27B の 34.3 よりは速い）
- **既定の設定（prefill 2048、APC 8 GB）で全 suite が通った。** needle 32K / 128K / 240K を全問正解（prefill 530〜580 tok/s、
  peak 83.6 / 89.9 / 96.0 GB）、エージェント 4/4（APC も効いた）、日本語 32/32
- 実行中にスワップは増えなかった
- kiapi へ組み込むなら、この view（`ple-store.json` + `ple_storage` を入れた config）を作る処理を setup に持たせる必要がある。
  hard link なので HF cache と同じ filesystem に置く。240K で 96 GB に達するので、ロード中は他のモデルと共存できない前提で
  `weight_gb` / `peak_headroom_gb` を決める。起動直後の page cache が冷えた状態の decode 速度は未計測

## 次の判断（ユーザーと相談して決める）

- **有力: 4bit のフル版 + PLE の mmap。** 品質を落とさず 128 GB で長い context まで動く。残る懸念は、96 GB を占めて他の family と
  同時に載らないことと、expert の SSD offload（`mlx_vlm/moe_offload.py`）まで重ねるかどうか

- この task を続けるか、保留にするか。続けるなら、どの重みを使うか:
  - 4bit のフル版 + GPU wired limit の引き上げ（システム設定の変更。PLE の mmap で不要になった可能性が高い）
  - より大きい REAP（384 など）や、日本語を含む校正で作った別の pruning を探して評価し直す
  - 3bit 前後の量子化版（ddalcu iQ-MLX 3.3bpw 86.4 GB など）を評価する

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
