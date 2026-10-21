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
