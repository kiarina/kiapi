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

## 次の一手

1. `Blaizzy/mlx-video#51` に実装または PR が付いたら再確認する
2. upstream が止まったままで、自前 port を優先するとユーザーが決めた場合は、`mlx-video` 側へ
   Gemma 4、22B config、split checkpoint loader、2.5 upscaler、まず軽い convolutional VAE decoder
   の順で実装する。diffusion decoder と DFR は別段階にする
3. 対応 commit ができたら、kiapi の git pin と model resources を更新する。LTX-2.5 は複数ファイル
   なので、従来の単一 `HfSnapshotResource` / `model_repo` 前提も見直す
4. サーバー機で T2V、I2V、A2V、audio generation を full verify し、ディスク量、peak memory、
   121-frame 生成時間、旧 LTX-2 との画質を実測する
5. 実測後に既定モデルの移行、旧モデル併存、API へ multishot / auto-duration / prompt enhancement /
   DFR をどこまで公開するか決める

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

着手前に issue #51 へ「最初は distilled T2V / I2V + conv VAE」という範囲を書き、
maintainer の期待と合わせる。第三者への送信になるため、issue へのコメントと
PR 公開は実行直前にユーザーの確認を取る。

## 再確認先

- `https://huggingface.co/Lightricks/LTX-2.5`
- `https://github.com/Lightricks/LTX-2/releases/tag/v1.2.0`
- `https://github.com/Blaizzy/mlx-video/issues/51`
