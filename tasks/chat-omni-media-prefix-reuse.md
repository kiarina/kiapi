# Omni の追加メディアでも既存prefixを再利用する

## 方針（2026-09-20 ユーザー合意）

- Qwen3.8で成立したprefix単位のメディア識別を、Omniへ画像→音声→動画の順で広げる。
- mlx-vlm forkで実装し、cold/hitの意味・logits・追加分のencode・誤利用防止を実機で検証する。
- 検証済みfork commitをkiapiへpinして取り込む。困難な点が判明したら根拠を報告する。
- 既存Qwen3.8対応とprefill chunk既定2048を維持する。disk / continuous batchingは広げない。

## 進捗

- prefill chunkの並行作業は完了済み（kiapi `8b89f23`）。mainはcleanで同期済み。
- kiapiは別のdetached worktree、mlx-vlmは既存Qwen画像対応`3c5bd17c`から
  `codex/omni-media-prefix-reuse`を用意。既存上流PR #2309はOPEN、変更せず保全する。
- 画像の実装を進めながら、音声・動画のtensor配置と前処理制約を読み取り調査する。

## 完了条件

- 各対応modalityで追加時のcache hit・速度改善・追加分のみencodeを実測。
- 内容変更、並べ替え、設定変更、media途中の境界、長いpromptで誤hitしない。
- モデル解放、再ロード、text-only、既存Qwen3.8、chat full verifyが通る。
- 対応できない組み合わせは理由とfallbackを明記し、未検証のまま有効にしない。

## 実装と検証

- 画像prefixの方式を共通化し、Omniはdense KVでもprefill checkpointを使う。
  suffixのdeepstackをfull-prompt座標へprefix paddingし、RoPEを保持する。
- 音声は複数clipを個別に特徴抽出・encodeする。padding前にmel長を確定し、長いclip追加でも旧clipを不変にした。
  MLXの負数整数除算により100-frame単位の長さが1ずれる問題と、clip長でchunk maskを作る問題を修正した。
- Native実機2回ずつでimage/audio/video/mixed/音声付きvideo（別demux audio）の追加が全てhit。
  cold/hitで色・合言葉の順序が一致し、追加mediaだけをencodeした。旧音声を同じpath・同じ長さで差し替えると
  旧audioは再encodeされ、前段text 2,048 tokensだけを再利用した。FPS変更も同様にvideo以後を再計算した。
- 画像の初期probeにQwen3.8用enable_thinking=Falseを流用するとOmniへ不適切な空think prefillが入った。
  Omniではこの指定をしない。量子化MoEのcold/hit logitsはprefill/encode batch形状で変わるため、
  小型float32モデルでfull/restore/chunked suffixのlogits一致を別途検証した。
- upstream cache/generate/prefix tests 467件、Qwen3.5系/Omni model contracts 3件、kiapi CPU 340件は通過。
  音声mask優先順位、flat waveform list、odd sample count等の独立review指摘も修正済み。
- Native interleaved use_audio_in_video=TrueはAPC対象外。kiapiの既存demux方式は対応する。

- 中断中にchat full verifyと上流PR #2311のCIが完了。APIの曖昧な質問でUnderstood.だけを返すcaseは、
  manager.clear後の同一requestでも同じ応答だった。質問を具体化し、実際の直前応答を履歴へ入れ、
  cache hitだけでなく内容のanchorも確認するようAPI検証を強化する。

- 具体化したAPI検証はimage/audio/video/audiovisual/mixed全件成功。旧promptの末尾1token以外を再利用し、内容も確認した。
- Omniの異なる画像追加（赤→緑）は2,448tokensを再利用、旧画像差し替え（青）はcached=0で再計算し、色の応答も成功。
- 最終makeとCPU340件も成功。上流forkは98300012、PR #2311はCI成功。残りはmainへの取り込み・稼働環境反映・完了記録。
