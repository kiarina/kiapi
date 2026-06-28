# web

**日本語**

SearXNG と Crawl4AI を kiapi から使うための **web capability** です。

- **search**: SearXNG で Web 検索し、JSON の検索結果を返す。
- **fetch**: Crawl4AI で単一 URL をレンダリングし、Markdown または PDF を返す。

web は、SearXNG / Crawl4AI を **resident subprocess model** として扱います。
初回リクエスト時に `docker run --rm` を foreground subprocess として起動し、
空いている localhost port を割り当て、以降は resident backend として再利用します。
search / fetch も Job として single-flight worker に投入されます。

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/web/search` | Web 検索 | SearXNG の `/search?format=json` を呼び、検索結果を返す。 |
| `GET /v1/web/fetch?url=...` | ページ取得 | Crawl4AI で HTML ページをレンダリングし、Markdown または PDF を返す。 |
| `GET /v1/web/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/web/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/web/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/web/redoc.html)

## Dependencies

| バックエンド | License | Mem | Description |
|---|---|---:|---|
| [SearXNG](https://github.com/searxng/searxng) | AGPL-3.0 | ~0.7 GB | メタ検索エンジン。kiapi が `docker run --rm` subprocess として起動する。 |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | Apache-2.0 | ~2 GB | ブラウザレンダリング + Markdown/PDF 変換。kiapi が `docker run --rm` subprocess として起動する。 |

## Notes

- **resident subprocess model**:
  SearXNG と Crawl4AI は `ModelSpec(family="web")` として登録されます。`load()` は
  foreground の `docker run --rm` subprocess を起動し、`release()` は subprocess を停止します。
- **Job / single-flight**:
  search / fetch はどちらも Job として single-flight worker で実行されます。
- **search の query**:
  `query` は SearXNG へそのまま渡します。`site:`、`!wp`、`!images`、`:ja` などの
  SearXNG インライン演算子をそのまま使えます。
- **search の結果数**:
  SearXNG 自体に `max_results` はないため、kiapi が 1 ページ分の結果を受け取ったあと
  client-side で切り詰めます。既定は `KIAPI_WEB_DEFAULT_MAX_RESULTS=10` です。
- **fetch の対象**:
  `fetch` は HTML ページ専用です。画像、音声、動画、PDF、その他バイナリ URL は
  バイト列として返さず、`not_html` で拒否します。
- **fetch の空コンテンツ保護**:
  HTML として到達できても、レンダリング後に抽出できる本文がない場合は
  `empty_content` を返します。
- **fetch の成果物**:
  fetch の raw body は Files API に保存され、レスポンスヘッダに `X-Kiapi-File-Id` と
  `X-Kiapi-Job-Id` が付きます。
- **主なエラー**:
  validation は 422、`fetch` の `unsupported_accept` は 406、バックエンド到達不能や
  HTTP エラーは 502、timeout は 504 です。
- **非決定性**:
  `search` はライブの検索エンジン結果に依存するため、同じクエリでも結果は変わります。

## Settings

| 変数 | 既定値 | 意味 |
|---|---|---|
| `KIAPI_WEB_SEARCH_IMAGE` | `searxng/searxng:latest` | SearXNG backend の Docker image。 |
| `KIAPI_WEB_FETCH_IMAGE` | `unclecode/crawl4ai:latest` | Crawl4AI backend の Docker image。 |
| `KIAPI_WEB_BACKEND_READY_TIMEOUT_S` | `60.0` | backend subprocess の起動待ち timeout。 |
| `KIAPI_WEB_BACKEND_LOG_DIR` | `/tmp/kiapi/logs/web` | backend subprocess の stdout/stderr log 出力先。 |
| `KIAPI_WEB_TIMEOUT_S` | `10.0` | SearXNG への HTTP timeout。 |
| `KIAPI_WEB_DEFAULT_CATEGORIES` | `null` | `categories` 省略時の既定。`null` は SearXNG に任せる。 |
| `KIAPI_WEB_DEFAULT_ENGINES` | `null` | `engines` 省略時の既定。`null` は SearXNG に任せる。 |
| `KIAPI_WEB_DEFAULT_LANGUAGE` | `null` | `language` 省略時の既定。 |
| `KIAPI_WEB_DEFAULT_SAFESEARCH` | `null` | `safesearch` 省略時の既定。 |
| `KIAPI_WEB_DEFAULT_MAX_RESULTS` | `10` | `max_results` 省略時の client-side 切り詰め数。 |
| `KIAPI_WEB_FETCH_TIMEOUT_S` | `30.0` | Crawl4AI への HTTP timeout。 |
| `KIAPI_WEB_FETCH_MIN_CONTENT_CHARS` | `1` | これ未満の Markdown を `empty_content` とみなす。 |
| `KIAPI_WEB_FETCH_FILTER` | `fit` | Crawl4AI `/md` の filter。`fit` は readability-pruned、`raw` は DOM 全体。 |
| `KIAPI_WEB_FETCH_CACHE` | `0` | Crawl4AI `/md` の cache 指定。 |

## Quickstart

Docker Desktop など、`docker run` が使える状態で kiapi を起動します。SearXNG と
Crawl4AI は初回リクエスト時に自動起動されます。

### search — Web 検索

```bash
jq -n \
'{
  query: "apple",
  max_results: 5
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/web/search \
-H 'Content-Type: application/json' \
--data-binary @- |
jq .
```

カテゴリ、エンジン、言語、新しさで絞り込む:

```bash
jq -n \
'{
  query: "mlx quantization",
  categories: ["it"],
  engines: ["google", "duckduckgo"],
  language: "en",
  time_range: "month",
  max_results: 10
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/web/search \
-H 'Content-Type: application/json' \
--data-binary @- |
jq .
```

SearXNG のインライン演算子を使う:

```bash
jq -n \
'{
  query: "site:github.com kiapi"
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/web/search \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '.results[] | {title, url}'

jq -n \
'{
  query: "!wp :ja Python"
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/web/search \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '.results[] | {title, url}'
```

レスポンスには `query`、`results`、`answers`、`infoboxes`、`suggestions`、
`unresponsive_engines` が含まれます。

### fetch — Markdown 取得

```bash
curl -sS -o page.md \
"http://localhost:${PORT:-8000}/v1/web/fetch?url=https://github.com/kiarina"
```

`Accept: text/markdown` は既定なので省略できます。kiapi が検出した upstream の
content-type は `X-Kiapi-Content-Type` ヘッダで確認できます。

```bash
curl -sS -D - -o page.md \
"http://localhost:${PORT:-8000}/v1/web/fetch?url=https://github.com/kiarina" \
| grep -i x-kiapi
```

### fetch — PDF 取得

```bash
curl -sS -H 'Accept: application/pdf' -o page.pdf \
"http://localhost:${PORT:-8000}/v1/web/fetch?url=https://github.com/kiarina"
```

### fetch — 非 HTML URL の拒否

```bash
curl -sS \
"http://localhost:${PORT:-8000}/v1/web/fetch?url=https://www-media.blazeworks.jp/content/icon/miineko.png" \
| jq .
```

レスポンス例:

```json
{
  "detail": {
    "error": "not_html",
    "message": "Resource is not an HTML page (content-type: image/png).",
    "url": "https://www-media.blazeworks.jp/content/icon/miineko.png",
    "content_type": "image/png"
  }
}
```
