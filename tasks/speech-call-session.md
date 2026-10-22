# 通話全体の speech protocol 2

完了条件: 参照を通話開始時に準備し、1 socketで複数返答・cancel後の次返答を汚染なく生成して配備する。

- full reference text EOS + codec EOS + fresh role/language/speaker prefix を独立 `speech/live` に実装。
- talker KV/decoder streaming state をモデル所有の2件LRUに保持し、返答ごとに独立fork。socketはCPU参照snapshotのみ所有。
- protocol:2 / utterance IDs / ID付きPCM / cancel ack / late旧ID fence。既存HTTP・v1維持。
- 初期準備jobはready後にworkerを解放し、utterance.startだけでもworkerを取らず、初回text.appendで生成jobを入れる。
- make成功、CPU全473件pass。compiled decoder wrapperの実moduleへ状態を戻す回帰、blocked socket＋64fragment後cancelのworker解放も追加。
- M4 isolated GPU: 完全一致参照c03e2da1…/256283samplesを全量使用。1socket turn1/3(cancel後)/4は各113280samples、PCM SHA256 d428bd8a…b38aで完全一致、最初PCM0.204秒。legacy HTTP/v1 verifyもpass。
- 同じ出力1本を既存Qwen3-ASRで確認し、target全文一致・参照tailの混入なし。この原稿1件の診断であり自然さの主観評価ではない。
- root SG device-free E2Eもpass（3turn1socket、80ms/charで最初PCM2322ms < textdone3678ms、mic割込28ms/cancelack14ms）。本番統合・配備へ進む。
