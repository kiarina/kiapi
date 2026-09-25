# kiapi の全 family を使える Web UI を `/` で提供する

## 背景

kiapi は LLM エージェント向けで、人には何ができるか分かりにくく、すぐ使いにくい。エージェントが読む
`openapi.json` を元データにして、人が全 family を試せる UI を kiapi 自身が配る。

段階 1（読み取り）と段階 2（実行、chat、質問チャット）は 2026-09-26 に実装した。経緯と実測は `HISTORY.md`、
設計の正典は `docs/concepts/web-ui.md`、開発手順と落とし穴は `docs/playbooks/web-ui-development.md`。

## やること

### 次: README で見せて、0.8.0 としてリリースする（ユーザーと合意、2026-09-26）

- 撮影用に、**商用可の model**（Z-Image turbo、Qwen Image の `image`（Apache-2.0）、ERNIE など）で見栄えのする
  生成物を作る。非商用の model（Qwen Image 2.1、FLUX.2 klein 9B、Ideogram 4）の出力と、みぃねこ関連は画面に映さない
- `localhost` で開いて撮る（サイドバーとアドレスバーにホスト名を出さない）
  - README の冒頭: Playground で生成結果が出ている画面。ライトとダークを `<picture>` で出し分ける
  - 「Web UI」節: Overview、Models（コマンド案内）、質問チャットがフォームを埋める場面の 3 枚
  - できれば、質問チャットがフォームを埋めて光る 10 秒ほどの GIF
- 画像はリポジトリに置き、README からは絶対 URL で参照する（PyPI は相対パスの画像を出さない）
- README の画像は `main` 上の絶対 URL なので、push してからでないと GitHub で確かめられない。先に README と画像を push し、
  リリースは実行直前にユーザーへ確認する
- 2026-09-26: 撮影と README の更新を済ませた（`docs/images/web-ui/*.webp`、2880×2000、ライト・ダーク各 4 枚）。
  撮影は、`KIAPI_FILES_ROOT` と `XDG_CACHE_HOME` を一時ディレクトリにした 2 つ目の kiapi を :8000 で起動し、
  Z-Image turbo と ERNIE-Image turbo だけで作った 6 枚を入れて、puppeteer-core（インストール済みの Chrome）で撮った。
  テーマは `prefers-color-scheme` のエミュレートで切り替える（localStorage を事前に書くと reload のたびに上書きされる）。
  GIF は見送った。残りは 0.8.0 のリリース

### その後（必要になったら）

- 非商用バッジ: `ModelSpec` にライセンスの情報が無い。`license` と商用可否を ModelSpec に足し、`/v1/setup` で返して
  Models・Guide・Playground のモデル選択に出す
- 出力例の見本を GitHub Pages に置き、自分の生成物が無い family の Guide に出す
- ファイルと family の対応: 今はファイル名の接頭辞（`qwen_…`、Z-Image だけ `image_…`）で推測している。生成時に
  `meta.family` を書くと確実になる
- family ごとの工夫（サイズのプリセット、音声の波形など）: 汎用フォームで一通り使えるので、使って欲しくなったものから足す
- 実行中ジョブの中断: kiapi に中断の API が無い（`DELETE /v1/jobs/{id}` は実行中を止めない）ので UI にも無い
- ltx2 の `enhance_prompt` と「Write with chat」の使い分けは未検討

## 完了条件

- `kiapi run` だけで `/` に UI が出て、全 family をフォームから実行し、成果物をその場で確認できる（達成）
- 各 family で何ができるか（用途、model、ライセンス、出力例）が UI だけで分かる（ライセンスと見本が未達）
- 全モデルのセットアップ状態と、足りないものを入れる CLI コマンドが UI で分かる（達成）
- ライトとダーク、デスクトップとスマートフォンで崩れない（達成）
- PyPI から入れた kiapi でも UI が配られる（0.8.0 のリリースで達成）

## 申し送り

- UI の変更は、稼働中の kiapi には `mise run web:build` だけで反映される（再起動不要）。Python 側の変更は再起動が要る
- 質問チャットの最初の回答は 30〜60 秒かかる（model の load と文書の prefill）。同じページの 2 問目からは速い
- `/v1/setup` は 1 回 3〜5 秒。UI は Models を開いたときと Refresh のときだけ取る
