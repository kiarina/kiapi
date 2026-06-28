# web

**English** | [日本語](README.ja.md)

**web capability** for using SearXNG and Crawl4AI from kiapi.

- **search**: Search the web with SearXNG and return JSON search results.
- **fetch**: Render a single URL with Crawl4AI and return Markdown or PDF.

The web treats SearXNG / Crawl4AI as a **resident subprocess model**.
Start `docker run --rm` as foreground subprocess on the first request,
Allocate a free localhost port and reuse it as a resident backend from now on.
search / fetch are also submitted to single-flight workers as Jobs.

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/web/search` | Web search | Call SearXNG's `/search?format=json` and return the search results. |
| `GET /v1/web/fetch?url=...` | Get page | Render an HTML page with Crawl4AI and return Markdown or PDF. |
| `GET /v1/web/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/web/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/web/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/web/redoc.html)

## Dependencies

| Backend | License | Mem | Description |
|---|---|---:|---|
| [SearXNG](https://github.com/searxng/searxng) | AGPL-3.0 | ~0.7 GB | Meta search engine. kiapi starts as `docker run --rm` subprocess. |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | Apache-2.0 | ~2 GB | Browser rendering + Markdown/PDF conversion. kiapi starts as `docker run --rm` subprocess. |

## Notes

- **resident subprocess model**:
  SearXNG and Crawl4AI are registered as `ModelSpec(family="web")`. `load()` is
  `docker run --rm` starts the subprocess in the foreground, and `release()` stops the subprocess.
- **Job/single-flight**:
  Both search/fetch are executed as a single-flight worker as a Job.
- **search query**:
  `query` is passed directly to SearXNG. `site:`, `!wp`, `!images`, `:ja` etc.
  You can use SearXNG inline operators as is.
- **search result count**:
  There is no `max_results` in SearXNG itself, so after kiapi receives one page of results.
  Truncate client-side. Default is `KIAPI_WEB_DEFAULT_MAX_RESULTS=10`.
- **fetch target**:
  `fetch` is only for HTML pages. Images, audio, videos, PDFs, and other binary URLs are
  Do not return it as a byte string and reject it with `not_html`.
- **fetch empty content protection**:
  Even if you can reach it as HTML, there is no body that can be extracted after rendering.
  Returns `empty_content`.
- **fetch artifacts**:
  The raw body of fetch is stored in the Files API, with `X-Kiapi-File-Id` in the response header.
  It will have `X-Kiapi-Job-Id`.
- **Main error**:
  validation is 422, `unsupported_accept` for `fetch` is 406, backend unreachable or
  HTTP error is 502, timeout is 504.
- **Non-determinism**:
  `search` relies on live search engine results, so the results will vary for the same query.

##Settings

| Variable | Default value | Meaning |
|---|---|---|
| `KIAPI_WEB_SEARCH_IMAGE` | `searxng/searxng:latest` | Docker image of SearXNG backend. |
| `KIAPI_WEB_FETCH_IMAGE` | `unclecode/crawl4ai:latest` | Docker image of Crawl4AI backend. |
| `KIAPI_WEB_BACKEND_READY_TIMEOUT_S` | `60.0` | Timeout waiting for backend subprocess to start. |
| `KIAPI_WEB_BACKEND_LOG_DIR` | `/tmp/kiapi/logs/web` | stdout/stderr log output destination of backend subprocess. |
| `KIAPI_WEB_TIMEOUT_S` | `10.0` | HTTP timeout to SearXNG. |
| `KIAPI_WEB_DEFAULT_CATEGORIES` | `null` | `categories` Default if omitted. `null` is left to SearXNG. |
| `KIAPI_WEB_DEFAULT_ENGINES` | `null` | `engines` Default if omitted. `null` is left to SearXNG. |
| `KIAPI_WEB_DEFAULT_LANGUAGE` | `null` | `language` Default if omitted. |
| `KIAPI_WEB_DEFAULT_SAFESEARCH` | `null` | `safesearch` Default when omitted. |
| `KIAPI_WEB_DEFAULT_MAX_RESULTS` | `10` | `max_results` Default client-side truncation number. |
| `KIAPI_WEB_FETCH_TIMEOUT_S` | `30.0` | HTTP timeout to Crawl4AI. |
| `KIAPI_WEB_FETCH_MIN_CONTENT_CHARS` | `1` | Markdown less than this is considered `empty_content`. |
| `KIAPI_WEB_FETCH_FILTER` | `fit` | Crawl4AI `/md` filter. `fit` is readability-pruned, `raw` is the entire DOM. |
| `KIAPI_WEB_FETCH_CACHE` | `0` | Cache specification for Crawl4AI `/md`. |

## Quickstart
Start kiapi in a state where you can use `docker run`, such as Docker Desktop. SearXNG and
Crawl4AI will be automatically started on the first request.

### search — Web search
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
Filter by category, engine, language, newness:
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
Use SearXNG's inline operators:
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
The response includes `query`, `results`, `answers`, `infoboxes`, `suggestions`,
Contains `unresponsive_engines`.

### fetch — Markdown fetch
```bash
curl -sS -o page.md \
"http://localhost:${PORT:-8000}/v1/web/fetch?url=https://github.com/kiarina"
```
`Accept: text/markdown` is the default and can be omitted. upstream detected by kiapi
The content-type can be found in the `X-Kiapi-Content-Type` header.
```bash
curl -sS -D - -o page.md \
"http://localhost:${PORT:-8000}/v1/web/fetch?url=https://github.com/kiarina" \
| grep -i x-kiapi
```
### fetch — Get PDF
```bash
curl -sS -H 'Accept: application/pdf' -o page.pdf \
"http://localhost:${PORT:-8000}/v1/web/fetch?url=https://github.com/kiarina"
```
### fetch — Reject non-HTML URLs
```bash
curl -sS \
"http://localhost:${PORT:-8000}/v1/web/fetch?url=https://www-media.blazeworks.jp/content/icon/miineko.png" \
| jq .
```
Example response:
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
