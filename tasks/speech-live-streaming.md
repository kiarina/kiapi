# Qwen3-TTS live input/output

完了条件: 双方向APIを通話クライアントから使え、GPU回帰を通してmainへ統合する。

## 状態

- `/v1/audio/speech/stream` WebSocket、独立した `speech/live`、声参照promptの4件LRUを実装。
- 既存HTTP用patchの元prompt builderを保存しliveから使う。日本語の末尾pre-tokenを保留する。
- mlx-audio 0.6.1へ更新。0.6.0と0.6.1のQwen3-TTS modelソースは同一。既存のprompt/penalty/decoder patchを維持。
- CPU全465件pass、make（format/lint/mypy/API docs）pass。lock変更はmlx-audioのみ。
- CPU検証後、統合担当がspeechとtranscriptionsのfull GPU verifyを直列実施する。
- 上流PRは未作成。独立packageを抽出できるが、kiapi互換hookは上流化時に不要。

## 申し送り

- CLI script `scripts/capabilities/verify_speech_live.py` は稼働中の検証サーバーと登録済みvoiceを指定して実行する。
- `mise run verify --kiapi --family transcriptions` をfullで実行。speechは上記scriptでHTTP回帰とWebSocket成功/cancel/切断を確認する。
- 音声の自然さ・声の似方は成果物を実際に試聴する。

## 自己監査

- queued cancelは受信側から即座にjob/sourceを止め、workerは未実行jobをskip。futureを待たずsocketを終え、完了時例外を回収する。
- socket書込が詰まっていても受信側finallyがcancelを通知し、bounded queueのputは100ms周期でキャンセルを検知する。CPU回帰でworker解放を確認。
- ready前の入力はUnicode sourceに保持し、tokenizerはworkerだけでbind。
- HTTP/liveは同じsingle workerで直列。liveは元prepareのみ使い、pending primeを前後でclearしdecoderの状態をfinallyでreset。
- voiceは各発話で再resolveし、参照ファイルを毎回hash。変更は新key、削除は失敗となり旧cacheを使わない。cacheはpayload所有で4件上限。

## 利用上の制約

- live thunkはテキスト待機中もsingle workerを保持し、chat等は後ろへ並ぶ。同じkiapiへのchat/tool委譲結果を待ってから続きを送る構成は相互待ちになり、30秒idle上限まで進まない可能性がある。
- 今回resumable-workerは実装しない。1接続1返答、返答終了時に必ずtext.done、割り込み時は即cancel、ターンを跨いで接続を保持しない。
- session.createdはqueuedも含む受理、readyはモデル・声の準備完了（入力prefix待ちは残り得る）。UI側でこの違いを示す。
