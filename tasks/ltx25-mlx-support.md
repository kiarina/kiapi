# LTX-2.5 を MLX 経由で取り込む

## 目的

kiapi の `ltx2` family を LTX-2.5 に更新し、Apple Silicon 上で新しい distilled pipeline を
利用できるようにする。

## 現在の引き継ぎ（2026-09-15）

この節が現在状態と次の作業順の正典。下の「実行計画」と「進捗」は調査・判断の経緯を残したものなので、
着手時はまずこの節を使う。

### 現在状態

- upstream PR: [Blaizzy/mlx-video#52](https://github.com/Blaizzy/mlx-video/pull/52)
  `feat(ltx2): add LTX-2.5 distilled generation support`
- PR は open / mergeable、status check なし。`main` 向け、head は
  `kiarina:ltx-2.5-local-port`
- `mlx-video` checkout: `~/src/github.com/Blaizzy/mlx-video`
- 作業 branch: `ltx-2.5-local-port`。fork の同名 branch を追跡し、working tree は clean
- kiapi はまだ LTX-2.5 を取り込んでいない。production pin は
  `87db56a51758fefb748a359b90a5283bb8ba4837` のまま
- kiapi capability の技術知見は `src/kiapi/capabilities/ltx2/README.md` の
  「LTX-2.5 upstream development status」に反映済み

### PR #52 の commit 構成

| Commit | 内容 |
|---|---|
| `a956b3a` | split checkpoint、Gemma 4 Unified encode、22B Transformer、conv VAE、T2V / I2V |
| `b73e6a8` | 必要 component だけの download、README、model-path tests |
| `73d919b` | LTX-2.5 ancestral Euler と sampler tests |
| `3ca6fef` | generated audio、A2V、A2V + I2V、audio VAE / vocoder、mux frame truncation 修正 |
| `c8000e1` | DurationHead と `num_frames` 自動予測 |
| `7d8b2f0` | 別 Gemma 4 E2B-it による T2V / I2V prompt enhancement |
| `fae541a` | prompt-driven Multishot の検証済み example と制約の文書化 |
| `5f008b8` | conv VAE限定DFR、generated keyframe slots、IC-LoRA detailing、tests / docs |
| `1e071c7` | READMEに記載済みの`mlx_video.generate` CLI aliasをproject scriptsへ追加 |
| `dc33a96` | DiffVAE向け3D neighborhood attention Metal kernel prototypeと数値tests |
| `aa18e5a` | LTX head dim 64向けSIMD-group Metal kernel最適化 |
| `ef28627` | DiffVAEのabsolute RoPE、NA block、SwiGLU、linear pixel shuffle layers |
| `e634684` | keyframeなし5-stage DiffVAE decoder、strict loader、CLI統合 |
| `4775630` | DiffVAE stage 4 / 5のhalo付きspatial tiling |
| `5001b17` | DFR keyframe dual-stream joint-attention Metal kernelとdecoder統合 |
| `f9a458a` | DFR keyframe-aware DiffVAE spatial tiling |
| `d29c248` | plain / keyframe-aware DiffVAE temporal tiling |

各機能は同じ PR branch へ独立 commit で追加する。maintainer から要求された場合だけ、commit 境界を
使って後から PR を分ける。新しい PR を先に増やさない。

### ローカル resource と成果物

- LTX-2.5 split weights: `~/src/github.com/Blaizzy/mlx-video/models/LTX-2.5/`
  （safetensors は checkout の ignore 対象）
- Prompt enhancer: `~/.cache/kiarina/ltx25/gemma-4-e2b-it-bf16/`
- DFR detailing IC-LoRA:
  `~/src/github.com/Blaizzy/mlx-video/models/LTX-2.5-detailing-lora/`
- 動画、WAV、contact sheet、ffprobe JSON:
  `~/src/github.com/kiarina/kiapi/.verify/ltx25-mlx-video/`
- 代表成果物:
  - `ltx25-t2v-768x512-121.mp4`
  - `ltx25-i2v-768x512-121-final.mp4`
  - `ltx25-audio-768x512-121.mp4`
  - `ltx25-a2v-768x512-121.mp4`
  - `ltx25-auto-duration.mp4`
  - `ltx25-enhance-auto.mp4`
  - `ltx25-multishot-direct-768x512-241.mp4`
  - `ltx2-multishot-direct-768x512-241.mp4`
  - `ltx25-dfr-fixed-768x512-121.mp4`
  - `ltx25-dfr-baseline-768x512-121.mp4`
  - `ltx25-dfr-fixed-768x512-121-comparison.png`
  - `ltx25-dfr-audio-auto.mp4`
  - `ltx25-dfr-audio-auto.wav`
  - `ltx2-dfr-regression-256-25.mp4`
  - `ltx25-diffvae-256-25.mp4`
  - `ltx25-diffvae-768x512-121.mp4`
  - `ltx25-diffvae-768x512-121-comparison.png`
  - `ltx25-diffvae-tiled2-eval-768x512-121.mp4`
  - `ltx25-dfr-diffvae-keyframes-768x512-121.mp4`
  - `ltx25-dfr-diffvae-keyframes-tiled2-768x512-121.mp4`
  - `ltx25-dfr-diffvae-keyframes-768x512-121-comparison.png`
  - `ltx25-diffvae-temporal2-768x512-121.mp4`
  - `ltx25-dfr-diffvae-keyframes-temporal2-768x512-121.mp4`
  - `ltx25-dfr-diffvae-audio-auto-tiled2.mp4`
  - `ltx25-diffvae-i2v-256-25.mp4`
  - `ltx25-diffvae-a2v-256-25.mp4`

### 検証状態と既知の問題

- LTX-2.5 T2V / I2V / generated audio / A2V / A2V + I2V / auto-duration /
  T2V enhancement / I2V enhancement は実 checkpoint で end-to-end 完走
- 関連 tests は 55 passed。fresh Python 3.12 install / CLI import も成功
- 旧 LTX-2 は変更後も生成でき、`num_frames` 省略時の 33-frame default を維持
- 同一 prompt / seed / 768x512 / 241 frames / generated audio で Multishot を新旧比較した。
  LTX-2.5 は中景、close-up、暖色の店先へのwide shotを描き分け、人物と衣装も維持した。
  旧LTX-2も画角変更と人物維持はできたが、3-shot指示と店へ入る展開への追従は弱かった
- conv VAE限定DFRは実checkpointで256x256 / 25 framesと768x512 / 121 framesを完走。
  代表設定は179.6秒・41.25 GB、同一prompt / seedの通常distilledは103.4秒・37.81 GB。
  DFRは毛並み、輪郭、草の微細構造と時間方向の被写体形状が改善した
- DFR + generated audio + auto-durationも完走。4.88秒→113 framesを予測し、内部121-frame
  canvasからMP4を正確に113 frames / 4.708秒へtrim。WAVも4.708秒、mux後AACは4.693秒。
  video/audioはfiniteで、静止・灰色・無音出力ではない
- 旧LTX-2 distilledは変更後も256x256 / 25 framesを23.6秒・36.73 GBで生成した
- fresh Python 3.12 installでDFR importとCLI optionsを確認。READMEで使っていた
  `mlx_video.generate`がproject scriptに無かったためaliasを追加し、実起動を確認した
- keyframeなしDiffVAEは396-tensor checkpointをstrict loadし、256x256 / 25 framesと
  768x512 / 121 framesをend-to-end decode。代表設定は全体149.2秒・51.33 GB、Conv VAEは
  103.4秒・37.81 GB。出力は121 frames / finite / 時間変化あり
- DiffVAE 2x2 spatial tilingは代表設定を216.9秒・37.81 GBで完走。tilingなしの51.33 GBから
  13.52 GB削減し、生成Transformerのpeakを超えない。full/tiled MP4差は平均2.67/255で、
  tile境界の局所誤差peakなし
- DFR generated keyframesを全5 stagesでjoint decode。代表設定はtilingなし241.1秒・49.71 GB、
  2x2 spatial tilesは331.0秒・41.25 GB。どちらも121 frames / finite。tiledは8.46 GB削減し、
  full/tiled差3.23/255、seam誤差集中なし
- temporal 2 tilesはplain DiffVAEで185.4秒・46.21 GB、keyframe-aware DFRで292.4秒・46.24 GB。
  fullとの差は各1.42/255、2.16/255で、frame seamに破綻なし
- DFR + DiffVAE + keyframes + 2x2 spatial tiles + generated audio + auto-durationは328.1秒・
  41.25 GBで完走。内部121 framesから113 frames / 4.708秒へtrimし、WAVも同duration
- DiffVAE I2V / A2Vは256x256 / 25 framesで完走。LTX-2.5 tests 40 passed、fresh Python
  3.12 install / CLI、旧LTX-2 Conv VAE regressionも成功
- upstream 全 pytest は今回差分と無関係な既存問題で green にならない:
  `tests/test_generate_dev.py` が削除済み `mlx_video.generate_dev` を import、
  `test_wan_tiling.py` が古い `causal_temporal` argument を使用、torch optional test は
  torch 未導入環境で失敗
- PR #52 への本文更新・maintainer返信など外部へ送る文章は、送信前に日本語訳でユーザーへ
  提示し承認を取る。issue #51 はユーザーしか返信していないため、細かな進捗を逐次追記しない

### 次の作業順

1. **DiffVAE完成内容をPR本文へ反映する。** 全追記の日本語訳をユーザーへ提示し、承認後に
   commits、対応範囲、implementation、実測、制約をPR #52へまとめて追記する
2. **upstream reviewへ対応する。** maintainerから分割や変更を求められた場合のみcommit境界を
   使って再構成する。Issue #51へ細かな進捗は追記しない
3. upstream実装が固まってからkiapi統合へ進む。`mlx-video` pin、split resources、API、memory
   headroom、progress ETA、disk sizeを更新し、full verifyと旧LTX-2回帰を通す

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

### 2026-09-15: upstream PR 作成

ユーザーが日本語訳で issue 返信と PR 本文を確認・承認した後に実行。

- public fork `kiarina/mlx-video` を作成し、branch `ltx-2.5-local-port` を push
- upstream PR [Blaizzy/mlx-video#52](https://github.com/Blaizzy/mlx-video/pull/52)
  `feat(ltx2): add LTX-2.5 distilled T2V and I2V support` を作成
- issue [Blaizzy/mlx-video#51](https://github.com/Blaizzy/mlx-video/issues/51) へ実装範囲、
  121-frame 実測、test 結果、PR URL を返信
- PR は open / mergeable。調査時点で status check の登録はない

次の一手: maintainer review を待ち、質問・変更要求・CI 結果が来たら対応する。
返信テキストは今回と同じく、送信前に日本語訳でユーザー確認を取る。

### 2026-09-15: Audio / A2V stacked PR 候補を実装

PR #52 の先端から local branch `ltx-2.5-audio` を作り、local commit `6fb1208`
(`feat(ltx2): add LTX-2.5 audio support`) で次を実装した。

- LTX-2.5 split audio checkpoint を必要 component allowlist へ追加
- metadata から audio VAE encoder / decoder と BigVGAN + BWE vocoder の config を復元
- PyTorch Conv1d / Conv2d / ConvTranspose1d weights を MLX layout へ変換
- T2V + generated audio、A2V、A2V + I2V を split checkpoint で有効化
- 既存 mux の `-shortest` が音声の端数差で 25-frame 動画を 21 frames へ
  切り詰める不具合を発見。`apad` で音声を動画長まで補完し、全 frame を保持

検証:

- split audio encoder / decoder / vocoder の strict load と個別 forward 成功。vocoder は
  48 kHz stereo で finite waveform を生成
- 256x256 / 25 frames で generated audio、A2V、A2V + I2V の 3 経路が完走
- 768x512 / 121 frames: generated audio は 118.1 秒・37.81 GB、A2V は
  106.4 秒・37.81 GB
- generated audio は H.264 121 frames + AAC 48 kHz stereo 5.035 秒、A2V は
  H.264 121 frames + AAC 16 kHz stereo 4.992 秒
- 音声の NaN / Inf は 0。generated audio は peak -0.58 dB / RMS -10.69 dB、
  A2V は peak -6.14 dB / RMS -20.77 dB
- 関連 tests 49 passed、fresh Python 3.12 install / import 成功

成果物は引き続きサーバー機の
`~/src/github.com/kiarina/kiapi/.verify/ltx25-mlx-video/` に保存。local branch は clean で、
fork へはまだ push していない。

次は、本家 `main` 向けに `Depends on #52` と明記した stacked PR と、issue #51 への
経緯追記を作成する。本文は送信前に日本語訳でユーザー確認を取る。

### 2026-09-15: Audio stacked PR 作成

ユーザーが日本語訳で PR 本文と issue 追記を確認・承認した後に実行。

- fork branch `kiarina:ltx-2.5-audio` を push
- 本家 `main` 向けの stacked PR
  [Blaizzy/mlx-video#53](https://github.com/Blaizzy/mlx-video/pull/53)
  `feat(ltx2): add LTX-2.5 audio generation and A2V support` を作成
- PR 本文に `Depends on #52` と、#52 を先に merge する必要があることを明記
- issue [Blaizzy/mlx-video#51](https://github.com/Blaizzy/mlx-video/issues/51) へ audio の
  対応範囲、実測、stacked PR URL を追記
- PR #53 は open / mergeable。調査時点で status check の登録はない

次の一手: #52 / #53 の maintainer review を待ちながら、次の独立機能を別 branch で
進める。返信や次の PR 本文は引き続き送信前に日本語訳で確認を取る。

### 2026-09-15: PR #52 へ統合

ユーザーと、基本機能を過度に細分化せず commit 単位でレビューできる 1 PR に
まとめる方針に変更した。日本語訳で更新文と close コメントを確認・承認後に実行。

- Audio commit を PR #52 branch へ cherry-pick し、`3ca6fef` として push
- PR #52 を `feat(ltx2): add LTX-2.5 distilled generation support` へ改題し、
  4 commits の review guide、T2V / I2V / Audio / A2V の全範囲、実測、未対応範囲を記載
- PR #52 は 4 commits / 19 files、open / mergeable、status check なし
- PR #53 に「Audio を #52 の commit `3ca6fef` へ統合した」と記録して close
- issue #51 へ、#52 が Audio / A2V を含む正典 PR になったことを追記

次の一手: Duration predictor と Gemma 4 prompt enhancement はそれぞれ独立 commit として
PR #52 branch へ追加する。その後の Diffusion video VAE、DFR、multishot も同 branch へ
機能別 commit で追加し、PR 本文の commit guide でレビュー境界を示す。

### 2026-09-15: Duration predictor を追加

PR #52 branch の独立 commit `c8000e1`
(`feat(ltx2): add LTX-2.5 duration prediction`) で次を実装・push した。

- 3.8 MB の split duration-head checkpoint を必要 component allowlist へ追加
- video 4096-dim / audio 2048-dim connector outputs の projection、modality embedding、
  4-head cross-attention pooler、MLP からなる MLX `DurationHead`
- PyTorch `MultiheadAttention.in_proj_weight` layout をそのまま strict load し、
  MLX で Q / K / V に分解して実行
- 予測秒を 1〜20 秒に clamp し、causal VAE の `8k+1` frame grid へ snap
- LTX-2.5 は `num_frames` 省略時に自動予測。`--auto-duration MIN MAX` で範囲を指定
- LTX-2 / 2.3 は従来どおり省略時 33 frames で後方互換を維持

検証:

- 実 checkpoint を strict load。zero connector tokens で video-only 2.47 秒、audio-only 2.38 秒、
  video + audio 2.42 秒を finite 出力
- 実 prompt で `A quick blink.` は 4.72 秒→113 frames、長い旅行シーンは
  5.28 秒→121 frames
- `num_frames` 省略の end-to-end で 256x256 / 113 frames / 24 fps / 4.708 秒の
  H.264 MP4 を 29.0 秒・37.03 GB で生成
- LTX-2 の `num_frames` 省略回帰は 33 frames で完走
- 関連 tests 54 passed

PR #52 は新 commit を含むが、PR 本文はまだ更新していない。更新文は日本語訳で
ユーザー確認後に送信する。

### 2026-09-15: Gemma 4 prompt enhancement を追加

PR #52 branch の独立 commit `7d8b2f0`
(`feat(ltx2): add Gemma 4 prompt enhancement`) で実装・push した。

実装前の probe で、LTX-2.5 の 12B Gemma 4 Unified text-encoder checkpoint は encode 専用で、
そのまま autoregressive generation すると無意味な反復出力になることを確認。公式
PyTorch 実装も Gemma 4 Unified encode root では別の generative instruct checkpoint を必須と
していたため、その設計に合わせた。

- 既定で `mlx-community/gemma-4-e2b-it-bf16` を別ロードし、
  `--prompt-enhancer-repo` で差し替え可能
- LTX-2.5 公式の Gemma 4 T2V / I2V system prompts を追加
- T2V はユーザーの短い prompt のみ、I2V は実際の reference image も Gemma 4 へ入力
- Gemma 4 E2B-it は greedy generation で caption のみ返し、その caption を 12B
  Unified encoder と DurationHead へ渡す
- 古い LTX-2 / 2.3 の Gemma 3 enhancement 経路は変更しない

検証:

- T2V `a cat walking through grass` を、framing、camera motion、lighting、soundscape を
  含む英語 caption へ展開
- I2V は `miineko.png` の magenta pixel-art cat、黒背景、白い耳、黒い目を
  正しく読み取った caption を生成
- enhancement + auto-duration end-to-end は、展開 caption から 2.55 秒→57 frames を
  予測し、256x256 MP4 を 26.8 秒・36.97 GB で生成
- I2V enhancement + 25-frame generation は 32.3 秒・37.08 GB で完走
- 関連 tests 55 passed

PR #52 本文は Duration / Prompt enhancement の 2 commits をまとめて追記する。
更新文と issue #51 の進捗追記は送信前に日本語訳でユーザー確認を取る。

ユーザー確認で、issue #51 は現時点でユーザーしか返信していないため、
この進捗は追記せず PR 本文だけを更新すると決定。日本語訳で追記内容を
承認後、PR #52 本文に次を反映した。

- commit guide を `c8000e1` / `7d8b2f0` まで拡張
- 対応範囲、実装説明、検証結果へ Duration / Prompt enhancement を追加
- 未対応から Duration / Prompt enhancement を削除
- 別 Gemma 4 E2B-it checkpoint を使う理由と既定 repo を追記
- test 表記を 55 passed へ更新
- PR #52 は 6 commits / 24 files、open / mergeable、status check なし

issue #51 は更新していない。

### PR の分割方針

2026-09-15 にユーザーと再検討し、LTX-2.5 対応は原則として PR #52 の同一 branch へ
機能別 commit で積み上げると決定した。checkpoint path、loader、pipeline、検証が共有される
ため、先行して複数 PR へ分けると、相互依存の説明、rebase、正典の判別がかえって
複雑になる。

- 機能単位で commit を分ける
- PR 本文の commit guide で各機能のレビュー境界を明示する
- maintainer から PR の分割を要求された場合に限り、commit 境界を使って後から分ける
- 独立 PR を先に増やさない

### 2026-09-15: Diffusion video VAE の実装境界

LTX-2.5 の `ltx-2.5-video-vae-bf16.safetensors` を取得し、公式 `DiffusionVideoDecoder`、
checkpoint config、396 tensors を解析した。encoder は既存 conv VAE とほぼ共通だが、
decoder は 5-stage の 3D neighborhood-attention backbone で、最終段に 11x11x11 の局所 attention を
8 blocks 持つ。

768x512 / 121 frames の latent から段階的に展開すると、最終段は
`113x64x96 = 694,272` query positions、1 query あたり `11^3 = 1,331` neighbors になり、
1 block あたり約 9.24 億 neighborhood pairs。head / channel 内積と 8 blocks を含めると、
素朴な MLX gather + SDPA 実装は巨大な一時 tensor と数十億〜数兆規模の演算になる。

公式実装も CUDA では NATTEN fused kernel を production path とし、無い環境の
eager implementation は compatibility-only と明記する。Apple Silicon 向けに同等の実用性を
得るには、`mx.fast.metal_kernel` 等による 3D neighborhood attention 専用 Metal kernel、
query tiling、online softmax、boundary window shift、RoPE の統合が必要。これは他の追加機能と
比べて独立した GPU-kernel 開発になる。

現時点で PR #52 branch は clean で、DiffVAE の未完成コードは追加していない。
次はユーザーと、(1) 専用 Metal kernel 開発として続行、(2) 先に DFR / multishot を
conv VAE 経路で実装し DiffVAE を後回し、の優先順を決める。

### 2026-09-15: Multishot 新旧比較と対応方針

同じ3-shot prompt、seed `314159`、768x512、241 frames、24 fps、generated audioで
LTX-2.5と旧LTX-2 distilledを比較した。

- LTX-2.5: 3分39.1秒、peak 39.55 GB。中景からclose-up、暖色の店先へのwide shotという
  構成を描き分け、銀髪、黄色いraincoat、赤いscarf、顔の同一性を維持した
- 旧LTX-2: 3分16.3秒、peak 39.07 GB。人物と衣装は維持したが、長い連続的な画角変化と
  終盤のcutに寄り、指定した3-shot構成と店へ入る展開への追従は弱かった
- `Hard cut`を指定しても、LTX-2.5を含めて滑らかな遷移になる場合がある。shot長とcut位置は
  frame単位では保証されない

Multishotは専用checkpointや追加の推論経路を必要とせず、通常のT2V promptで新旧とも機能する。
このため独自の構造化APIは追加せず、検証済みprompt example、同一性を保つ書き方、制約を
`mlx-video` READMEへ追加した。commit `fae541a` をPR #52と同じbranchへpush済み。
日本語案をユーザーが承認後、PR #52本文のcommit guide、対応範囲、実装説明、検証結果を更新し、
未対応欄からMultishotを削除した。Issue #51は更新していない。次の実装はconv VAE限定DFR。

### 2026-09-15: conv VAE限定DFR

公式LTX-2 repositoryのcommit `a95ab856bf29407b6b066ede0abe1846050db56c` を基準に、
temporal upscalingとDiffVAE decodeを除いた最初のDFR vertical sliceを実装した。

- 24 / 32-frame segment gridとcanvas padding
- single-pixel-frame RoPE positionを持つgenerated keyframe slots
- 第1段階でvideo / audio / slotをrectified-flow ancestral Eulerで同時denoise
- videoとslotを既存latent spatial upscalerでx2
- detailing IC-LoRA metadataの`reference_downscale_factor=2`を読み、低解像度videoを
  clean reference tokensとして第2段階へ連結
- 480 LoRA pairsを既定strength 0.5でmergeし、3-step spatial detailing
- padded canvasを要求frame数へtrim。generated audioも要求durationへtrim
- CLI `--pipeline dfr`、`--detailing-lora`、`--detailing-lora-strength`

detailing adapterは327.3 MB、rank 32。別gated repo
`Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler`から取得する。

初回実装では一般的なsigma-space ancestral Eulerを誤って使い、出力が黄緑へ強く飽和した。
既存LTX-2.5経路で検証済みのrectified-flow ancestral Eulerへ統一すると解消した。この式は
通常のEuler ancestralと置換可能ではない。

検証はDFR関連を含むselected suite 22 passed。実checkpoint E2Eは256x256 / 25 framesと
768x512 / 121 framesで完走した。代表設定のDFRは179.6秒・41.25 GB、通常distilledは
103.4秒・37.81 GB。DFRは毛並み、輪郭、草の細部と被写体形状の時間的一貫性が改善した。

commit `5f008b8` をPR #52 branchへpush済み。初期対応はT2Vと任意のgenerated audio。
I2V、A2V、streaming、temporal upscaling、DiffVAE decodeは未対応。日本語案をユーザーが
承認後、PR #52本文のcommit guide、対応範囲、実装説明、実測、制約、別gated adapterを
更新した。PRはopen / mergeable。Issue #51は更新していない。

### 2026-09-15: DFR残検証

generated audio、auto-duration、内部canvas paddingを1回のE2E生成で検証した。promptから
4.88秒 / 113 framesを予測し、DFRは内部canvasを121 framesへpadding。conv VAE decode後に
MP4を113 frames / 4.708秒へtrimし、WAVも48 kHz stereo / 4.708秒へtrimした。mux後AACは
4.693秒で、映像を短縮していない。decoded video / audioはfinite、video std 56.93、
audio std 89.12 / peak 1871で、静止、灰色、無音ではない。生成は187.5秒・41.25 GB。

通常LTX-2.5 distilledは同じDFR実装後の代表比較で103.4秒・37.81 GB、旧LTX-2 distilledは
256x256 / 25 framesを23.6秒・36.73 GBで完走した。selected suiteは22 passedを再確認。
fresh Python 3.12環境へinstallし、DFR module importとCLI optionsを確認した。

fresh install検証で、model README全体が使う`uv run mlx_video.generate`に対応するproject scriptが
無い既存不整合を発見した。既存の`mlx_video.ltx_2.generate`を維持しつつ同じentry pointへのaliasを
追加し、実際に`--help`が起動することを確認。commit `1e071c7`をPR branchへpush済み。

日本語案をユーザーが承認後、DFR generated audio / padding / trim、旧LTX-2 regression、fresh
install、CLI aliasをPR #52本文へ追記した。PRは9 commits、open / mergeable、checkなし、
review required。Issue #51は更新していない。DFR残検証は完了。

### 2026-09-15: DiffVAE Metal kernel prototype

NATTEN PR #312（commit `943e14a204141a1a2eb3300dcb77d0dd6ea1cccf`、open / reviewなし）の
Metal MPS backendを調査した。PRはNA1D / 2D / 3D、FP32 / FP16 / BF16、forward / backward、
GQA、causal、stride、dilation、additional KVを含む約6,221 linesで、Metal / Objective-C++が
4,039 lines、testsが1,358 lines。PyTorch ATen / MPS wrapperは直接使えないが、window geometry、
KV bounding box、threadgroup K/V tile、online softmaxはMLX kernelへ移植可能。

最初の正解基準として`mx.fast.metal_kernel`によるinference-only NA3Dを実装した。BTHWHD layout、
FP32 / FP16 / BF16、odd 3D window、NATTEN互換のboundary shift、float32 accumulatorを持ち、
attention score tensorをmaterializeしない。各threadが1 query / headを処理し、2-passでmaximumと
softmax/value accumulationを行う単純版。小型eager MLX referenceも追加した。

- FP32 / BF16の3x3x3 boundary testはeager referenceと一致
- LTX実条件の11x11x11 / head dim 64はfiniteで完走
- warm 11x11x11 grid / 1 head / dim 64: 4.0〜4.6 ms、peak 1.67 MiB
- warm 16x16x16 grid / 16 heads / dim 64: 20.8 ms、peak 80.0 MiB
- DiffVAE / DFR / VAE selected tests 12 passed

実decoder最終gridへの外挿では1 block数秒になり得るため、この版は正解referenceであり最終性能では
ない。次はPR #312のSIMD group分担とthreadgroup K/V tileを移植する。通常NA3Dはほぼ対応するが、
LTX keyframe decodeはqueryごとに近いkeyframe planesを選ぶため、PRのglobal additional KVを
そのまま使えず、通常decode確立後に専用拡張する。commit `dc33a96`をPR #52 branchへpush済み。

続いてLTXのhead dim 64に特化したSIMD版を追加した。1 query / headを32-lane SIMD groupへ割り当て、
各laneが2 channelsを担当し、`simd_sum`でQK dot productを求める。近傍ごとのthreadgroup barrierは
不要で、online softmax stateは各laneで同じ値を更新する。ほかのhead dimは正解版へfallbackする。

- BF16 / head dim 64を3x3x3 boundaryでeager referenceと比較し一致
- 11x11x11 / 1 head / dim 64: median 0.83 ms（単純版約4.0 ms、約4.9倍）
- 16x16x16 / 16 heads / dim 64: median 12.75 ms（単純版20.8 ms、約1.6倍）
- DiffVAE / DFR / VAE selected tests 13 passed

commit `aa18e5a`をPR #52 branchへpush済み。次はこのkernelを使うkeyframeなし5-stage decoderの
class / checkpoint loaderを移植し、実際のstage shape上で追加最適化の要否を判断する。

### 2026-09-15: keyframeなしDiffVAE decoder

公式checkpoint metadataどおり、stage channels `2048/1024/512/512/256`、depths `4/6/4/2/8`、
kernels `3x7x7 / 3x7x7 / 3x5x5 / 3x5x5 / 11x11x11`、4段のcausal linear pixel shuffle、
stage-5 one-step x0 diffusionを実装した。absolute 3-axis RoPEはhead dim 64を`16/24/24`に分割。
Q/K/Vはpeakを抑えるためcheckpointのfused qkvを3つのLinearへsplit loadする。

396-tensor safetensorsからencoder keysを除外し、decoder fused qkvをsplit、per-channel statisticsの
hyphen keysをMLX namesへ変換してstrict loadした。parameter leavesは408。小型zero latent
`1x128x1x7x7`は`1x3x1x224x224`へ0.60秒・2.31 GBでdecodeし、finite。

CLIに`--video-decoder conv|diffusion`を追加し、remote使用時だけdiffusion VAE checkpointを
追加downloadする。Conv VAEを既定のまま維持。実生成latentで次を確認した。

- 256x256 / 25 frames: end-to-end成功、正しいframe count、Conv VAEと同じ内容・動きを復元
- 768x512 / 121 frames: tilingなしでend-to-end成功、149.2秒・51.33 GB
- 同条件Conv VAE: 103.4秒・37.81 GB。DiffVAE追加costは約45.8秒・13.52 GB
- MP4は121 frames / 5.042秒、finite、pixel std 51.91、mean frame delta 20.53
- DiffVAE / DFR / VAE / config / model-path selected tests 24 passed

commit `ef28627`（共通layers）と`e634684`（decoder / loader / CLI / docs）をPR #52 branchへpush。
現時点はkeyframeなし・tilingなし。次はtiling、その後DFR generated keyframesのjoint decode。

### 2026-09-15: DiffVAE spatial tiling

公式と同様にstage 1〜3はfull volumeで一度だけ処理し、stage 4 / 5をspatial tileへ分割した。
stage-4 2 blocks / 5x5 windowとstage-5 8 blocks / 11x11 windowの受容野から、stage-4入力で
片側24 cellsのhaloを算出。各tileを独立decodeし、haloを除いたcoreを連結する。

最初の実測はMLX lazy graphをtile loop後まで保持したため、276.5秒・75.24 GBと悪化した。
共有stage-4入力をloop前に`mx.eval`し、各tileも逐次eval / cache clearする修正後は、2x2 tilesで
216.9秒・37.81 GB。tilingなし149.2秒・51.33 GBに対し、67.7秒遅い代わりに13.52 GB削減した。
peakは生成Transformerと同値で、DiffVAE decodeが追加peakを作らない。

小型fixtureではfull / tiled latent outputが数値一致。実MP4は同shapeの121 framesで、圧縮後の
full / tiled平均絶対差2.67/255、p99 11、max 58。縦横tile seam位置に誤差集中はない。
selected tests 25 passed。CLI `--diffusion-vae-spatial-tiles`を追加し、既定1でtilingなしを維持。
commit `4775630`をPR #52 branchへpush済み。PR本文はDiffVAE完成まで更新しない。

### 2026-09-15: DFR keyframe-aware DiffVAE

generated keyframe planesをdecoderの全5 stagesへ通すdual-stream経路を実装した。video queryは
clamp-and-mask 3D local windowに加え、時刻距離が近い2 keyframe planesのspatial windowを見る。
keyframe queryは自身のplaneのspatial windowと、近い2 video framesを見る。すべて1つのonline
softmaxで処理するhead-dim-64専用Metal kernel。keyframe時刻は残りtemporal strideに合わせて
stageごとに`8/8/4/2/1`へ変換し、absolute RoPEへ渡す。

joint kernelはランダムFP32入力でNumPy全列挙referenceと一致。uniform-value invariant、nearest-slot
tie-break、両stream finiteもtest。deterministic blocks、causal pixel shuffle、stage-5 diffusion blocksは
video/keyframe間で同じQKV / norm / attention / MLP weightsを共有する。

DFRが生成した5 slot latents（121 frames時は24/48/72/96/120）をgenerate pipelineからdecoderへ渡し、
256x256 / 25 framesと768x512 / 121 framesをE2E完走。代表設定は241.1秒・49.71 GB、
Conv VAE DFRは179.6秒・41.25 GB。MP4は121 frames / 5.042秒、finite、pixel std 43.46、
mean frame delta 17.74。commit `5001b17`をpush。

さらにspatial tileごとに全keyframe planesをvideoと同じ24-cell haloでcropし、共有noise fieldから
対応領域を渡すkeyframe-aware 2x2 tilingを実装。小型fixtureはfullと数値一致。代表設定は
331.0秒・41.25 GBで、untiledから8.46 GB削減。full/tiled MP4平均差3.23/255、p99 14、max 57。
縦横seam近傍の差は全体平均以下。selected tests 30 passed。commit `f9a458a`をpush。
PR本文は未更新。次はtemporal tilingと最終回帰。

### 2026-09-15: DiffVAE temporal tilingと最終回帰

stage-4入力上で片側22 cellsのtemporal haloを使い、先頭tileだけcausal pixel shuffleのleading
frameをdrop、後続tileは保持するtemporal tilingを実装した。global pixel frameへ再配置してcoreを
連結し、keyframe timesもstage-4 / stage-5のtile originでrebaseする。spatial / temporal tilesの
同時指定は未対応として明示的に拒否する。

- plain temporal 2 tiles: 185.4秒・46.21 GB。untiled 149.2秒・51.33 GBから5.12 GB削減
- keyframe-aware DFR temporal 2 tiles: 292.4秒・46.24 GB。untiled 241.1秒・49.71 GBから3.47 GB削減
- full/tiled MP4平均差はplain 1.42/255、keyframe 2.16/255。temporal seam付近は差が増えるが
  global frame max以下で、視認上の境界破綻なし。両方121 frames
- commit `d29c248`をPR #52 branchへpush

最終複合回帰としてDFR + generated keyframes + DiffVAE + 2x2 spatial tiles + generated audio +
auto-durationを実行。4.88秒→113 frames予測、内部121-frame canvasからMP4 / WAVを113 frames /
4.708秒へtrim、AACは4.693秒。video/audio finite、video std 54.34、mean frame delta 13.79、
audio std 89.12 / peak 1871。328.1秒・41.25 GB。

追加回帰はDiffVAE I2V 256x256 / 25 frames（23.1秒・37.08 GB）、A2V 25 frames + 16 kHz
stereo AAC（16.4秒・36.94 GB）、旧LTX-2 Conv VAE 25 frames（24.2秒・36.73 GB）が完走。
`tests/test_ltx25_*.py`は40 passed。fresh Python 3.12 install、DiffVAE import、documented CLI alias、
video decoder / spatial / temporal optionsを確認。working tree clean。

DiffVAEの実装と回帰は完了。PR本文はまだ更新していない。ユーザーへ日本語追記案を提示し、
承認後にのみ外部更新する。
