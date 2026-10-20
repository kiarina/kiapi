# OpenAI 互換の音声合成（`/v1/audio/speech`）を Qwen3-TTS の声のクローンで足す

完了条件: kiapi が `POST /v1/audio/speech`（OpenAI 互換、PCM のストリーミング）と声の登録（`/v1/audio/voices`）を持ち、
登録した参照の声で Qwen3-TTS 1.7B Base（MLX bf16）が話す。サーバー機で動かして、最初の音の速さを確かめる。

## 背景

- Spirits Garden の試作の body は、話す声（TTS）を差し替えられるようにする（OS の声が既定、OpenAI 互換の HTTP を口にする）。
  その差し替え先として、参照の声をまねて話す Qwen3-TTS を kiapi で出す（オーナー、2026-10-21）
- 調べた結果は labs `2026/10/20/japanese-zero-shot-tts-compare`: MLX bf16（mlx-audio 0.6.0）が、聞いて PyTorch 版と同じ質で、
  実時間の約 0.5 倍の時間で生成でき、ストリーミングの最初の音は約 0.4 秒（MacBook Pro M1 Max）
- mlx-audio 0.6.0 のままだと質が落ち、ストリーミングの話し始めが崩れる。lab の worker の 2 つの直しを持ち込む（下）
- 推論は他と同じく 1 本の worker で順番に処理する（オーナー、2026-10-21）。他の推論が長いときは待つ。body は待ちが長いと OS の声に戻す想定

## 約束

- `POST /v1/audio/speech`: `{model?, input, voice, response_format?, stream_format?, speed?, instructions?, language?, seed?}`
  - `voice` は登録した声の id（OpenAI の既定の声の名前は無い）
  - `response_format`: `pcm`（既定。24 kHz・16 bit・mono・little endian の生の PCM を、生成しながら返す）か `wav`（全部できてから）
  - `stream_format` は `audio` だけ。`speed` は 1 だけ、`instructions` は空だけ（Base は扱えない。それ以外は 422）
  - `language`（拡張）: `ja`・`japanese` など。省略は auto
  - 接続が切れたら生成をやめる（チャンクの間で確かめる）
- `POST /v1/audio/voices`: `{audio, name?, transcript?}`。`audio` は Files API の id・URL・data URL。24 kHz mono にし、1〜30 秒
  （長ければ先頭 30 秒）。`transcript` が無いと話者の埋め込みだけでまねる（質は下がる）
- `GET /v1/audio/voices`・`GET /v1/audio/voices/{id}`・`DELETE /v1/audio/voices/{id}`
- 声はユーザーのデータのフォルダ（`speech/voices/<id>/`）に残る（再起動しても使える）

## mlx-audio 0.6.0 への直し（lab で確かめたもの）

1. 声のクローンの生成の設定を qwen-tts 0.1.1 に合わせる: 繰り返しの罰則は 1.05 を生成したすべての符号に（mlx-audio は 1.5 以上を直近 64 個に）、
   プロンプトは文を参照の符号に重ねる並べ方（qwen-tts の `non_streaming_mode=False`）
2. ストリーミングの復号器を、参照の符号の末尾 12 個（約 1 秒）で温めてから流す（mlx-audio は文脈なしで復号して話し始めが崩れる）

どちらも mlx-audio の内部を差し替えるので、mlx-audio は 0.6.0 に固定する。上げるときは lab の比べ方で確かめ直す。

## 進み具合

- 2026-10-21: 実装した（`capabilities/speech`・`api/audio/speech`、単体テスト、`kiapi check` の項目、README・CHANGELOG）。
  mlx-audio を 0.6.0 に固定した（0.5.9 は mlx-vlm の推移的な依存として入っていた）。lint・mypy・全テスト（429）が通る
- 開発機（MacBook Pro M1 Max）でローカルに動かして確かめた（参照 6.6 秒と文字起こし、日本語 3.6〜10.9 秒の文）:
  読み込んだ後の最初の PCM は 0.37〜0.38 秒、生成時間は音声の 0.52〜0.56 倍。最初の 1 回は読み込みを含めて約 10 秒。
  `wav` は 6.6 秒の文で 3.7 秒。途中で接続を切ると、次の頼みの最初の音は 0.60 秒（切った生成はすぐ止まった）。
  常駐 約 4.9 GB、通しのピーク 13 GB。whisper.cpp で文字にすると、昔話の文の頭（「昔々」）だけ崩れて聞こえた（1 回の観測）
- 注意: lockfile は古い uv（0.10）で作ると形式が変わる。mise で uv を最新にしてから `uv lock` する

## 残り

- サーバー機へ入れる（PyPI への公開とサービスの更新。オーナーの確認を取ってから）。入れたら `kiapi activate --family speech` と `kiapi check`、最初の音の速さを測る
- mlx-audio 0.6.0 で mlx-vlm（chat）の音声の入力が動くか、サーバー機で確かめる（0.5.9 から上がった）
- Web UI の speech の画面（`tasks/web-ui.md` の流れで足すか決める）
