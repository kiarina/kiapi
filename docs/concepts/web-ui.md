# Web UI

This concept describes the browser UI that kiapi serves at `/`: what it is for,
how it is built and served, and the design system it follows.

## Purpose

kiapi is designed for LLM agents, which read `openapi.json` and call the API.
People need a way to see what kiapi can do and to try it without an agent. The
web UI covers every family with the same information the agents read, so it
stays complete without a second source of truth.

## Serving

- `web/` holds the source: React, Vite, and TypeScript.
- `mise run web:build` builds it into `src/kiapi/api/ui/static`. The output is
  gitignored and listed in the hatch `artifacts` of both the sdist and the
  wheel, because `uv build` makes the wheel from the sdist.
- `GET /` returns `index.html` without caching; assets live under `/_ui` with
  hashed names. A checkout without a build returns a short page that says how
  to build it.
- Pages use hash routes (`/#/models`, `/#/f/<domain>/<family>/<tab>`) so they
  never collide with API paths.
- The UI reads only the public API: `/health`, `/v1/setup`, `/v1/jobs`,
  `/v1/files`, each capability's `openapi.json`, and the capability endpoints.
  It adds no server-side state. With `auth_token` set, it asks for the token
  and sends it as a Bearer token; media are fetched and shown as object URLs.

## Pages

- **Overview**: server, queue, memory and setup totals; running and recent
  jobs; recent files.
- **Models**: every model with its setup state from `GET /v1/setup`. The UI
  never changes the machine's setup; for a missing resource it shows the
  `kiapi activate` command to run in a terminal.
- **Jobs** and **Files**: lists and details with in-place media previews.
- **Family**: Playground, Guide and API tabs for each family.

## Schema-driven forms

The Playground builds its form from the capability `openapi.json`, so a new
family or field needs no UI change.

- Each POST operation (and GET operations with query parameters, such as web
  fetch) becomes a tab. Field kinds come from the JSON schema: text, prompt,
  integer, number, enum, boolean, FileRef, FileRef list, LoRA list, string
  list, and free JSON.
- Only values the person sets are sent, so the server keeps filling
  model-dependent defaults.
- Generation requests are sent with `mode: "async"` and followed as jobs.
- A "?" beside each field shows its full schema description.
- Chat has its own view: every ChatRequest parameter in the left column, the
  conversation in the right, tool calls with a way to reply with results, and
  token usage.

## Chat-assisted features

Both features send kiapi's own documentation to a chat model (default
`qwen3.8-27b`), so a person gets the guidance an agent would read.

- **Write with chat** drafts `prompt`, `negative_prompt` or `lyrics` from the
  family, operation and field descriptions.
- **The floating assistant** answers questions with the current family's
  `openapi.json` (or the root one) as the system prompt. On a Playground it
  also gets one `fill_<operation>_form` tool per operation, built from the
  form fields. Arguments that do not match a field's name, type, range or
  options are skipped and reported back; the form is never submitted.

## Design system

Light and dark themes share type, spacing, radii and layout; only the color
tokens (CSS variables in `web/src/styles/tokens.css`) change. The theme follows
the system setting until the person picks one.

| Role | Light | Dark |
|---|---|---|
| Background | `#F7F6F2` | `#151513` |
| Sidebar | `#EFEEE8` | `#1B1B19` |
| Card | `#FFFFFF` | `#1E1E1B` |
| Input, table header | `#EDEBE4` / `#FAFAF7` | `#262622` / `#232320` |
| Media stage | `#EFEEE8` | `#10100F` |
| Border / control border | `#E4E2DA` / `#DAD8CF` | `#2E2E2A` / `#3A3A35` |
| Text / secondary / muted | `#18181B` / `#52525B` / `#6B6B73` | `#EDECE8` / `#B4B3AC` / `#8F8E87` |
| Primary button | ink `#18181B`, white text | `#EDECE8`, ink text |
| Accent (links, progress) | `#2F54EB` | `#7C9BFF` |
| Ready | `#16A374` | `#3FCF8E` |
| Non-commercial | `#92400E` on `#FEF3C7` | `#F5C66A` on 12% |
| Failed | `#D9480F` | `#FF7A59` |

- Both backgrounds are warm neutrals with no blue cast.
- Dark surfaces are separated by lightness steps and borders, since shadows do
  not show.
- Type: Instrument Serif for page titles, Geist for text, Geist Mono for ids
  and commands, all bundled through Fontsource; Japanese falls back to Hiragino
  Sans.
- Radii: 14px for cards, 8 to 10px for controls. Icons are 1.6px line icons.
- The UI text is English only, so capability descriptions show as written.

## Related Concepts

- [API](api.md)
- [Jobs and Files](jobs-and-files.md)
- [Web UI development](../playbooks/web-ui-development.md)
