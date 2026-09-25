# Web UI Development

How to change, check and ship the web UI in `web/`. The design is described in
[Web UI](../concepts/web-ui.md).

## Develop

Node and pnpm come from `mise.toml`; `make init` installs the dependencies.

```sh
make dev       # kiapi on 127.0.0.1:8000
make web-dev   # Vite dev server that proxies /v1, /health and /openapi.json to it
```

Point the dev server at another kiapi with `KIAPI_URL=http://127.0.0.1:8500 mise run web:dev`.

To check against the real server instead, run `mise run web:build`. A running
kiapi picks up a new build without a restart, because `/` reads `index.html`
on every request. Changes to the Python side still need a restart.

## Check

```sh
mise run web:build   # type check (tsc) and build
make                 # Python format, lint and generated docs
make test
```

Then look at the result in a browser, in both themes and at a phone width
(375px). Also confirm that no page scrolls sideways at that width:
`document.documentElement.scrollWidth` should equal the viewport width.

## A second kiapi for checks

kiapi allows one instance per user, through a lock file in the user cache
directory. To check a change next to a running server, give the second instance
its own cache directory and keep the Hugging Face cache where the models are:

```sh
XDG_CACHE_HOME=/tmp/kiapi-cache HF_HOME=~/.cache/huggingface uv run kiapi run --port 8600
```

With no `warmup_models`, it loads nothing until a request needs a model. It
shares the settings and the file store with the running server.

## Pitfalls

- Write `useEffect` bodies as blocks. An expression body returns its value, and
  React calls a returned value as the cleanup, which crashed the chat when
  `scrollIntoView` returned something.
- Keep class names unique across components. The floating assistant once used
  `.assistant`, which also matched chat's `.bubble.assistant` and pinned chat
  bubbles to the screen.
- Scroll containers that follow new content should follow only while the
  reader is at the bottom (`useStickToBottom`). Scrolling on every streamed
  piece makes the page shake and fights the reader.
- Popovers inside scrolling panels are positioned against their field, not the
  "?" button, so they stay inside the panel.
- `uv build` builds the wheel from the sdist. Anything gitignored that the
  wheel needs, such as `src/kiapi/api/ui/static`, must be listed in the sdist
  `artifacts` as well.

## Screenshots for public pages

The README shows `docs/images/web-ui/<page>-<theme>.webp` (2880x2000, light and
dark) through absolute `raw.githubusercontent.com` URLs, because PyPI does not
show relative images. They only appear after they are pushed to `main`.

kiapi is public, so the shots must not show a host name, your own files, or
outputs of models that forbid commercial use. To retake them:

1. Start a clean instance on the README's port, with an empty file store:

   ```sh
   XDG_CACHE_HOME=/tmp/kiapi-shots/cache HF_HOME=~/.cache/huggingface \
   KIAPI_FILES_ROOT=/tmp/kiapi-shots/files uv run kiapi run --port 8000
   ```

2. Generate the pictures with models whose licenses allow commercial use, such
   as Z-Image `turbo` and ERNIE-Image `turbo`. Not Qwen Image `image-2.1`,
   FLUX.2 `klein-9b` / `klein-base-9b`, Ideogram 4, or AudioGen.
3. Capture with Chrome driven by puppeteer-core at 1440x1000 and a device scale
   factor of 2. Switch themes by emulating `prefers-color-scheme`, hide the
   floating assistant button except in its own shot, and wait until every
   sidebar family name has loaded before capturing.
4. For the Overview, start one generation first and capture both themes while
   it runs. Each extra run adds a file and a job; delete them with
   `DELETE /v1/files/{id}` and `DELETE /v1/jobs/{id}` so the gallery keeps six
   pictures.
5. Convert to WebP (quality about 86; each image stays under 250 KB) and stop
   the instance.
