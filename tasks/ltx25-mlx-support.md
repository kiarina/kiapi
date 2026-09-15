# LTX-2.5 を MLX 経由で取り込む

## 目的

kiapi の `ltx2` family を LTX-2.5 に更新し、Apple Silicon 上で新しい distilled pipeline を
利用できるようにする。

## 2026-09-15 調査

### 現在の kiapi

- `prince-canuma/LTX-2-distilled`（LTX-2 / 19B 世代）を使用する
- `Blaizzy/mlx-video` の commit `87db56a51758fefb748a359b90a5283bb8ba4837` を固定している
  （調査時点の upstream `main` と同一）
- `PipelineType.DISTILLED` の二段構成を呼び、T2V / I2V / first+last frame / A2V /
  audio-video joint generation を公開している
- モデル snapshot は約 101 GB、実行時の一時 headroom は 40 GB としている

### LTX-2.5 の主な差分

- Transformer は 22B。distilled は固定 8-step schedule、CFG=1
- Gemma 3 12B + 別 projection ではなく、LTX 用に調整された Gemma 4 12B + projection の
  専用 checkpoint が必須
- 従来の convolutional video VAE に加えて、新しい diffusion video decoder が標準の高品質経路
- 一枚の統合 checkpoint ではなく、Transformer、text encoder、video/audio VAE、latent spatial
  upscaler などを個別ファイルで渡す構成。公式 distilled quick start 一式は約 66 GiB
- native multishot、Diffusion Fidelity Rendering（DFR）、prompt enhancer、任意の duration predictor、
  改良された distilled model を追加
- 公式 distilled の代表設定は 960x544、121 frames、24 fps。frame 数は `8k+1`、縦横は 32 の倍数
- ライセンスは 2026-08-11 以降の LTX-2.x Community License。年間売上 1,000 万 USD 未満の
  entity は条件内で商用・production 利用可、それ以上は paid commercial license が必要

### 取り込み可否

現時点では **kiapi の設定や model repo の差し替えだけでは取り込めない**。

`mlx-video` の `main` は調査時点で kiapi の pin と同じ commit で、LTX-2 / LTX-2.3 の
Gemma 3 text encoder、従来 Transformer / VAE / upscaler を実装している。LTX-2.5 の Gemma 4、
checkpoint-driven architecture、diffusion video decoder、分割 checkpoint loader は未実装。
upstream issue `Blaizzy/mlx-video#51` は open、assignee・関連 PR ともになし。

公式 PyTorch / Diffusers 実装を kiapi に直接足す案は Apple Silicon 向け MLX capability という
現在の実装方針から外れ、66 GiB の bf16 一式と新 decoder の peak memory / runtime も未測定なため、
通常の model upgrade としては採用しない。MLX port 自体を kiapi 内で所有するより、まず
`mlx-video` upstream で共通実装にする。

## 実行計画

外部への提案を先に行わず、ローカル実装と実測で実現可能性を確定してから
issue / PR を行う。

### Phase 1: 比較基準と変換仕様を固める

- `mlx-video` の最新 `main` を独立したローカル checkout で保持する
- 現行 LTX-2 distilled の 97-frame T2V / I2V を一度実行し、生成時間、peak memory、
  出力とログを baseline として保存する
- LTX-2.5 の split checkpoint の metadata / tensor key / shape を取得し、公式 PyTorch 実装と
  現行 MLX class の対応表を作る
- Gemma 4 が `mlx-vlm` の再利用で足りるか、`mlx-video` 内の専用実装が必要かを
  小さな loader probe で判定する

完了条件: 必要 component、tensor 対応、未実装 operator の一覧があり、最小ポートの
範囲を確定できる。

### Phase 2: 重みを読まない単体実装

- checkpoint-driven 22B config と split checkpoint path resolver
- Gemma 4 tokenizer / text encoder / projection
- 2.5 Transformer、RoPE、distilled sigma schedule、latent spatial upscaler
- synthetic tensor と小型 fixture で shape、key conversion、forward を検証する
- 旧 LTX-2 / 2.3 の現行 test をすべて通し、後方互換を保つ

完了条件: 巨大 checkpoint に依存せず、新旧 config と変換ロジックを test で
再現できる。

### Phase 3: 段階的な実 checkpoint ロード

- まず各 component を個別に load し、weight key と dtype / shape の完全一致を確認する
- Gemma 4 の prompt encoding が完走することを確認する
- Transformer の 1 step forward を小解像度・短い sequence で通す
- convolutional video VAE で latent decode を通す

停止条件: Metal 非対応 operator や統合 memory 不足が解消できない場合は、無理に
全 pipeline へ進まず、再現コードと代替案を記録する。

### Phase 4: 最小 end-to-end 生成

- convolutional VAE と distilled pipeline で 256x256 / 9-frame T2V を通す
- 同条件の I2V を通し、input image の conditioning が効いていることを確認する
- NaN / Inf、灰色 frame、frame count、fps、MP4 mux を自動検査する

完了条件: Apple Silicon で視認可能な T2V / I2V MP4 が生成され、同じ seed で
再現できる。

### Phase 5: 代表設定で実測する

- 新旧を比較できる代表設定 768x512 / 121 frames / 24 fps で T2V と I2V を実行する
- wall time、peak process RSS、MLX active / peak memory、初回と二回目の差、出力サイズを測る
- 同じ意図の prompt で現行 LTX-2 と並べ、prompt adherence、motion、人物・文字、
  temporal consistency を視認比較する
- 出力見本、実行コマンド、環境、commit、実測値を保存する

完了条件: upstream maintainer が再現できる実装と、効果・コストを判断できる
実測資料が揃う。

### Phase 6: upstream への送信と PR

- 実装と実測が成功してから issue #51 に、対応範囲、非対応範囲、測定値、
  出力見本、PR 予定を書く
- maintainer のフィードバックを取り込み、fork へ push して PR を開く
- 最初の PR は distilled T2V / I2V + conv VAE に保ち、audio、diffusion VAE、
  duration head、DFR / multishot は follow-up とする

issue コメント、fork の公開 push、PR 作成は第三者への送信・公開なので、
実行直前にユーザーの確認を取る。

### Phase 7: kiapi へ取り込む

- upstream の対応 commit を固定し、kiapi の model resources を split checkpoint に対応させる
- kiapi の T2V / I2V full verify と旧 LTX-2 の regression test を通す
- 実測値から memory headroom、進捗 ETA、disk size を更新する
- 旧モデル併存か既定移行かを決める

## upstream PR の進め方

`mlx-video` への PR は可能。MIT license で特別な contribution 手順はなく、
LTX-2 実装も `mlx_video/models/ltx_2/` にまとまっている。ただし、一度に DFR や
multishot まで入れず、最初の PR は次の縦切りにする。

- LTX-2 / 2.3 の後方互換を保つ
- 2.5 split checkpoint の loader と checkpoint-driven config
- Gemma 4 12B + projection の MLX 実装・重み変換
- 22B distilled Transformer と固定 sigma schedule
- まず convolutional video VAE を使う distilled T2V / I2V
- 小型 tensor / config / conversion の単体テストと、Apple Silicon での 121-frame
  end-to-end 生成結果

この最小 PR の後、audio、diffusion VAE、duration head、DFR / multishot の順に分ける。
`mlx-video` の現行 LTX テストは scheduler / RoPE / VAE の一部に限られるため、
新 loader と Gemma 4 のテストは PR 側で追加する。

まず Phase 1〜5 を外部へ送信せず進め、動作と実測値を得てから Phase 6 に進む。

## 再確認先

- `https://huggingface.co/Lightricks/LTX-2.5`
- `https://github.com/Lightricks/LTX-2/releases/tag/v1.2.0`
- `https://github.com/Blaizzy/mlx-video/issues/51`

## 進捗

### 2026-09-15: Phase 1 開始

- サーバー機に `Blaizzy/mlx-video` の最新 `main`
  (`87db56a51758fefb748a359b90a5283bb8ba4837`) を clone し、ローカル branch
  `ltx-2.5-local-port` を作成。外部へは push していない
- kiapi の現行 LTX-2 full verify は 6/6 成功。256x256 baseline は T2V 25 frames
  29.4 秒、I2V 17 frames 26.5 秒、async T2V 17 frames 26.1 秒
- LTX-2.5 の最小 distilled + conv VAE 一式は、Transformer 42.02 GB、Gemma 4 text
  encoder 26.26 GB、conv video VAE 1.45 GB、spatial upscaler 1.00 GB、audio を除いて
  合計約 70.7 GB（10 進 GB）と確認
- Hugging Face へは `kiarina` で認証済みだが、`Lightricks/LTX-2.5` の利用条件が
  未承諾のため download は `Access denied. This repository requires approval.` で停止

次の一手: ユーザーが Hugging Face で LTX-2.x Community License に承諾した後、
component ごとの download と Phase 3 以降を進める。承諾待ちの間も、公式コードに
基づく Phase 2 の実装は進められる。

### 2026-09-15: Phase 1〜5 完了（前回のユーザ向け一覧の手順 6 まで）

ユーザーが Hugging Face の利用条件を承諾し、LTX-2.5 の必要な split weights を
サーバー機に取得した。`Blaizzy/mlx-video` の local branch `ltx-2.5-local-port` で
既存の `mlx_video.models.ltx_2` 設計を維持したまま実装し、local commit `a956b3a`
(`feat(ltx2): add initial LTX-2.5 distilled support`) を作成。外部へは push していない。

実装範囲:

- LTX-2.5 split checkpoint の自動検出と component path 解決
- `mlx-vlm>=0.7.1` の Gemma 4 Unified 実装を再利用する text encoder adapter
- checkpoint 内の tokenizer / config / text projection の読み込み
- checkpoint-driven Transformer config、独立した FF bias / gated attention / cross-attention
  AdaLN、keyframe absolute-position embedding
- LTX-2.5 の 22B Transformer を 4,349 tensors すべて strict load
- split conv video VAE encoder / decoder と 2.5 spatial upscaler
- LTX-2.5 が必要とする stage-1 ancestral Euler、条件付き frame の保護
- 旧 LTX-2 / 2.3 の従来レイアウトと deterministic sampler は維持

検証:

- Gemma 4: 1024 tokens から video `(1, 1024, 4096)` / audio `(1, 1024, 2048)` の
  finite embeddings を生成、peak 30.73 GB
- conv VAE: 9-frame 32x32 へ decode して finite、upscaler も 72 weights を load
- 256x256 / 9-frame: T2V 18.4 秒・36.92 GB、I2V 24.7 秒・37.08 GB。MP4 は
  H.264 / 24 fps / 9 frames で、画像・動画とも視認確認済み
- 768x512 / 121-frame T2V の同一 prompt / seed 比較:
  LTX-2.5 は 108.7 秒・37.81 GB、LTX-2 は 96.9 秒・37.48 GB。2.5 は約 12% 遅い
- 768x512 / 121-frame I2V の同一 input / prompt / seed 比較:
  LTX-2.5 は 120.8 秒・39.54 GB、LTX-2 は 101.7 秒・39.35 GB。2.5 は約 19% 遅い
- 全出力は 121 frames が揃い、最小 frame standard deviation は 48.49 以上、
  adjacent-frame mean absolute difference は 3.47〜10.37 で、灰色画像・静止画・NaN はない
- 視認上、2.5 は T2V の波と反射が細かく、色が自然で、時間的な一貫性も良好。
  I2V も input 構図を保ったまま 121 frames 完走
- 追加・関連 unit tests は 43 passed。全体は `test_generate_dev.py` の削除済み
  module import、`test_wan_tiling.py` の古い argument、optional torch 未導入の既存 3 問題があり、
  今回変更と無関係に upstream `main` の test suite 全体は元から green ではない。

注記: 公式の Diffusers 例の `960x544` は stage 1 解像度で、x2 後は `1920x1088`。
`mlx-video` の現行二段 API は最終出力解像度を受け取るため、新旧の公平な比較に
`768x512` を使った。従来計画の `960x544` 出力という記述はこの理由で訂正する。

成果物はサーバー機の
`~/src/github.com/kiarina/kiapi/.verify/ltx25-mlx-video/` に MP4、contact sheet、ffprobe JSON を保存。

次の一手: local commit のレビューと PR 向け整理を行う。issue コメント、fork への
push、PR 作成はまだ行わない。

### 2026-09-15: PR 向け整理とライセンス再評価

local commit `b73e6a8` を追加し、LTX-2.5 の必要な 4 component だけを
Hugging Face から取得する allowlist、未対応の audio / dev pipeline の明示的エラー、
利用手順、model path の単体テスを追加。関連 test は 45 passed。

公開前のレビューで一度、LTX-2.5 の LTX-2.x Community License と
`mlx-video` の MIT license が両立するかを blocker 候補とした。新ライセンスは次を定める。

- 1.5: LTX-2.x の architecture に基づく derivative model architecture も Derivative
- 3.2: Derivative は同 Agreement の条件のみで配布し、完全な Agreement を同梱
- 3.3: 変更ファイルに目立つ変更告知を記載
- 3.6: 追加 license は許容するが Agreement と競合できず、Agreement が優先

ただし、これは LTX-2.5 で初めて入った条項ではない。LTX-2 / 2.3 に適用される
旧 `LICENSE-2` も、Derivative の定義に derivative model architecture を含み、同 Agreement
での配布、全文同梱、変更告知を要求している。`mlx-video` はその旧ライセンス下の
LTX-2 / 2.3 inference implementation を既に MIT repository で配布している。

したがって、**2.5 対応だけを新規ライセンス blocker とする先の判断は撤回する**。
適用文書は LTX-2.5 から `LICENSE-2_x` に変わるが、inference port の取り扱いは
`mlx-video` の既存方針に従う。PR では LTX-2.5 のモデルカードとライセンスを
明示するが、Lightricks への事前照会を必須条件にしない。

### 2026-09-15: PR 候補の最終ローカル検証

- local commit `73d919b` を追加し、LTX-2.5 ancestral Euler step を単独関数にして
  seed 再現性と最終 denoise step を単体テスト化
- 関連 test は 47 passed
- 新しい Python 3.12 venv で local package を一から install し、`mlx-vlm 0.7.1`、
  CLI `--help`、LTX-2.5 component allowlist の import を確認
- upstream `main` は依然 `87db56a`。issue #51 に返信と assignee はなく、LTX-2.5 の
  競合 PR もない
- local branch は clean。未公開 commits は `a956b3a`, `b73e6a8`, `73d919b`
- upstream 全 test suite は既存の `tests/test_generate_dev.py` が削除済み module
  `mlx_video.generate_dev` を import するため collection で停止する。今回差分では触らない

次は、ユーザー確認用に issue #51 の返信文と PR 本文を日本語訳で提示する。
ユーザーが承認するまで issue 返信、fork / push、PR 作成は行わない。
