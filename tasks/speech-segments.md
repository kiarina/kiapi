# Cached short spans for calls

完了条件: protocol2 segmentsを全参照cache/1socket/中断を保って配備し、SGの1秒初期bufferと実利用する。

- v2 start generation:segmentsを任意指定、ready echoで旧serverを検出。省略時は従来token mode。
- lab canonicalの句読点>=8/14字、CJK24字/Latin6語、doneで最終tail。Latin/CJKのscriptを受信textから判定し、設定jaでも英語を語境界で区切る。小数点・数字内区切りは保留/非境界。
- 各spanは同じfull prepared refをforkし、同一utteranceへPCMを連結。speaker抽出/ref prefillを繰り返さない。
- inner closed sourceでもoutercancelをpoll/GPU frame/code predictor/decoder前に検査し、outer waitにもcallbackを100ms以内に反映。
- make成功、CPU全479件pass。M4 isolated29bf8d1で同一socket日本語3spans/cancel後/次turnのPCMhash完全一致（各167040samples、warm0.202秒）。全参照WAV/transcript hashはlabと一致。
- 同socketの英語captionもlanguage jaのまま2spansで成功（184320samples）。ASR英語全文一致、日本語は先頭「うん、」省略・残り一致。試聴は未実施、ASRの省略と実音声の読み落としは未分離。
- 省略時token modeのPCMは従来d428bd…b38aと完全一致、HTTP/v1/cancel/disconnectもpass。
- rootの6turn SG E2Eを待機中。終了後main統合・配備・task完了・一時server/worktree除去まで行う。
