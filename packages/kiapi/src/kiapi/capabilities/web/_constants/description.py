DESCRIPTION = """Web search + single-page fetch for LLM agents.

Use this family when an agent needs current web information or needs to read the
contents of a specific HTML page. Search returns structured JSON results; fetch
renders one page and returns Markdown by default, or PDF when requested.

## When To Use
- Use search when you need discovery: recent facts, unknown URLs, multiple
  candidate sources, or comparison across sources.
- Use fetch when you already have a URL and need the page body in agent-friendly
  Markdown or as a rendered PDF artifact.
- Search and fetch are separate steps. Search result snippets are useful for
  triage, but fetch is better when the exact page content matters.

## Search Tips
- Search results are live and may change between calls.
- SearXNG inline operators are useful for agents: `site:`, `!wp`, `!images`,
  `:ja`, and engine/category bangs can be placed directly in `query`.
- Use `categories`, `engines`, `language`, `time_range`, and `safesearch` to
  narrow the search when the task has a clear domain.
- Use `max_results` to keep responses small. It truncates one returned page of
  SearXNG results; it does not aggregate multiple pages.

## Fetch Tips
- Fetch is for HTML pages only. It intentionally rejects binary resources such
  as images, videos, audio files, archives, and PDFs instead of returning their
  raw bytes.
- Markdown output is best for reading and summarization. PDF output is useful
  when layout, pagination, or visual preservation matters.
- Successful fetches are also stored in the Files API. Use the returned
  `X-Kiapi-File-Id` when the artifact needs to be referenced later.

## Common Failures
- `not_html`: the URL points to a non-HTML resource.
- `empty_content`: the page loaded but produced no extractable content.
- `unsupported_accept`: fetch was called with an Accept header that allows
  neither Markdown nor PDF.
"""
