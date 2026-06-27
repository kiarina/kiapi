"""End-to-end verification for kiapi's web capability (search + fetch).

search (POST /v1/web/search): a basic query, result truncation via max_results,
SearXNG inline operators (site:), validation errors, and help discovery.
fetch (GET /v1/web/fetch): markdown render, PDF via Accept, the not_html guard
for a binary URL (with content_type in the error), and 406 on a bad Accept.
Unlike the GPU verifiers this uses no local ML model. It does require Docker:
kiapi starts SearXNG and Crawl4AI as resident subprocess models on demand.

Usage:
    # start the server:
    #   KIAPI_PORT=8000 uv run kiapi
    uv run python scripts/capabilities/verify_web.py

Env:
    KIAPI_BASE_URL   server base URL (default http://127.0.0.1:8000)
"""

import os
import sys

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
SEARCH_URL = f"{BASE_URL}/v1/web/search"
FETCH_URL = f"{BASE_URL}/v1/web/fetch"


def _ok(msg: str) -> None:
    print(f"  OK: {msg}")


def main() -> int:
    with httpx.Client(timeout=30.0) as client:
        # 1. basic search
        r = client.post(SEARCH_URL, json={"query": "apple", "max_results": 5})
        r.raise_for_status()
        data = r.json()
        assert data["query"], "missing query in response"
        assert isinstance(data["results"], list), "results must be a list"
        assert len(data["results"]) <= 5, "max_results not honoured"
        for key in ("answers", "infoboxes", "suggestions", "unresponsive_engines"):
            assert key in data, f"missing {key} block"
        _ok(f"basic search returned {len(data['results'])} results (<=5)")

        # 2. results are passed through verbatim (have url/title)
        if data["results"]:
            first = data["results"][0]
            assert "url" in first and "title" in first, "result dict not passed through"
            _ok(f"first result: {first.get('title')!r} <{first.get('url')}>")

        # 3. SearXNG inline operator (site:) passes through query verbatim
        r = client.post(
            SEARCH_URL, json={"query": "site:github.com searxng", "max_results": 3}
        )
        r.raise_for_status()
        _ok(f"site: operator query returned {len(r.json()['results'])} results")

        # 4. validation error: empty query → 422
        r = client.post(SEARCH_URL, json={"query": ""})
        assert r.status_code == 422, (
            f"expected 422 for empty query, got {r.status_code}"
        )
        _ok("empty query rejected with 422")

        # 5. capability discovery via OpenAPI
        r = client.get(f"{BASE_URL}/v1/web/openapi.json")
        r.raise_for_status()
        doc = r.json()
        assert doc.get("x-kiapi-capability") == "web", "openapi capability mismatch"
        assert "/v1/web/search" in doc["paths"], "search path missing from openapi"
        assert "/v1/web/fetch" in doc["paths"], "fetch path missing from openapi"
        _ok("web openapi.json served (search + fetch)")

        # --- fetch ---------------------------------------------------------
        # 6. markdown render (default Accept) → raw text/markdown body
        r = client.get(FETCH_URL, params={"url": "https://gifuquest.blazeworks.jp"})
        r.raise_for_status()
        assert r.headers["content-type"].startswith("text/markdown"), (
            f"expected text/markdown, got {r.headers.get('content-type')}"
        )
        assert r.text.strip(), "markdown body is empty"
        assert "岐阜クエスト" in r.text, "expected page text in markdown"
        _ok(f"fetch markdown returned {len(r.text)} chars")

        # 7. PDF via Accept: application/pdf → raw PDF bytes
        r = client.get(
            FETCH_URL,
            params={"url": "https://gifuquest.blazeworks.jp"},
            headers={"Accept": "application/pdf"},
        )
        r.raise_for_status()
        assert r.headers["content-type"].startswith("application/pdf"), (
            f"expected application/pdf, got {r.headers.get('content-type')}"
        )
        assert r.content[:5] == b"%PDF-", "response is not a PDF"
        _ok(f"fetch PDF returned {len(r.content)} bytes")

        # 8. non-HTML URL → 422 not_html, with the upstream content_type echoed
        r = client.get(
            FETCH_URL,
            params={"url": "https://www-media.blazeworks.jp/content/icon/miineko.png"},
        )
        assert r.status_code == 422, f"expected 422 for binary URL, got {r.status_code}"
        detail = r.json()["detail"]
        assert detail["error"] == "not_html", f"expected not_html, got {detail}"
        assert detail.get("content_type"), "content_type missing from not_html error"
        _ok(f"binary URL rejected: not_html ({detail['content_type']})")

        # 9. unacceptable Accept → 406 unsupported_accept
        r = client.get(
            FETCH_URL,
            params={"url": "https://gifuquest.blazeworks.jp"},
            headers={"Accept": "application/json"},
        )
        assert r.status_code == 406, f"expected 406, got {r.status_code}"
        assert r.json()["detail"]["error"] == "unsupported_accept"
        _ok("Accept: application/json rejected with 406")

        # 10. non-http scheme → 422 request validation
        r = client.get(FETCH_URL, params={"url": "ftp://example.com/file"})
        assert r.status_code == 422, f"expected 422 for bad scheme, got {r.status_code}"
        _ok("non-http(s) url rejected with 422")

    print("\nweb verification completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
