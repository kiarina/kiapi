# Cached short spans for calls

完了条件: protocol2 segmentsを全参照cache/1socket/中断を保って配備し、SGの1秒初期bufferと実利用する。

- v2 start generation:segmentsを任意指定、ready echoで旧serverを検出。省略時は従来token mode。
- lab canonicalの句読点>=8/14字、CJK24字/Latin6語、doneで最終tail。Latin/CJKのscriptを受信textから判定し、設定jaでも英語を語境界で区切る。小数点・数字内区切りは保留/非境界。
- 各spanは同じfull prepared refをforkし、同一utteranceへPCMを連結。speaker抽出/ref prefillを繰り返さない。
- inner closed sourceでもoutercancelをpoll/GPU frame/code predictor/decoder前に検査し、outer waitにもcallbackを100ms以内に反映。
- CPU/make検証中。本番switch前にactive call/GPUを確認し、isolated GPU→SG E2E→本番を直列化する。
