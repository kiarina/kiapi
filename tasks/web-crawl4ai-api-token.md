# crawl4ai の新しい image で web.fetch が ready にならない件を直す

## 背景

2026-11-09、サーバー機で `unclecode/crawl4ai:latest` を pull し直したところ（未使用 image の掃除で消えていた）、`GET /v1/web/fetch` が
`crawl4ai backend did not become ready within 60.0s: Server disconnected without sending a response.` で 503 になった。
本番の main でも同じ。

コンテナのログ（`/tmp/kiapi/logs/web/kiapi-web-crawl4ai-*.log`）の entrypoint は次を出す:

- `no CRAWL4AI_API_TOKEN set; binding loopback only (127.0.0.1:11235)`
- published ports (`-p 11235:11235`) では届かず、host からの接続はリセットされる
- 届かせるには `CRAWL4AI_API_TOKEN` を渡す（custom の `config.yml` で `security.jwt_enabled` を有効にしたなら `CRAWL4AI_JWT_ENABLED=true`）

gunicorn 自体は `Application startup complete` まで進んでおり、kiapi の `/health` の probe だけが届かない。

## やること

- crawl4ai の新しい版の変更（token が要るようになった版、`/health` と `/md` などの API に token が要るか）を上流で確かめる
- `src/kiapi/capabilities/web/_models/crawl4ai.py` と `WebBackendProcess` で、起動ごとの token を生成して `-e CRAWL4AI_API_TOKEN=...` で渡し、
  kiapi からの呼び出しに付ける。代わりに動いていた版の tag に pin する案も比べる（`latest` は再 pull で壊れうる）
- `mise run verify --kiapi --family web` を通す（SearXNG の search は 2026-11-09 に通っている）
