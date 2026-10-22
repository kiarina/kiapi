# 通話全体の speech protocol 2

完了条件: 参照を通話開始時に準備し、1 socketで複数返答・cancel後の次返答を汚染なく生成して配備する。

- full reference text EOS + codec EOS + fresh role/language/speaker prefix を独立 `speech/live` に実装。
- talker KV/decoder streaming state をモデル所有の2件LRUに保持し、返答ごとに独立fork。socketはCPU参照snapshotのみ所有。
- protocol:2 / utterance IDs / ID付きPCM / cancel ack / late旧ID fence。既存HTTP・v1維持。
- 初期準備jobはready後にworkerを解放し、utterance.startだけでもworkerを取らず、初回text.appendで生成jobを入れる。
- CPU/make検証中。M4 isolated GPU→rootのSG E2E→本番配備を直列に行う。
