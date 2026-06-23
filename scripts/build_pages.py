"""Build static GitHub Pages assets for kiapi OpenAPI docs."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from html import escape
from pathlib import Path

from kiapi.api._helpers.build_openapi import build_openapi
from kiapi.cli import register_all_capabilities
from kiapi.core.capability import CapabilitySpec, capability_spec_registry

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
PAGES_BASE_URL = "https://kiarina.github.io/kiapi"
REDOC_JS_URL = "https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"
SWAGGER_UI_CSS_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
SWAGGER_UI_JS_URL = (
    "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"
)


@dataclass(frozen=True)
class PageDoc:
    title: str
    summary: str
    openapi_path: str
    swagger_ui_path: str
    redoc_path: str


def main() -> None:
    register_all_capabilities()

    from kiapi.api.app import COMMON_OPENAPI_PATHS, app

    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir(parents=True)
    (PUBLIC / ".nojekyll").write_text("", encoding="utf-8")

    specs = _capability_specs()
    root_schema = build_openapi(
        app,
        title="kiapi Common API",
        description=_root_pages_description(specs),
        path_prefixes=COMMON_OPENAPI_PATHS,
    )
    _write_json(PUBLIC / "openapi.json", root_schema)
    _write_redoc(
        PUBLIC / "redoc.html",
        title="kiapi Common API",
        openapi_url="./openapi.json",
    )
    _write_swagger_ui(
        PUBLIC / "docs.html",
        title="kiapi Common API",
        openapi_url="./openapi.json",
    )

    docs = [
        PageDoc(
            title="kiapi Common API",
            summary="Common endpoints and links to every capability.",
            openapi_path="openapi.json",
            swagger_ui_path="docs.html",
            redoc_path="redoc.html",
        )
    ]

    for spec in specs:
        out_dir = PUBLIC / spec.openapi_path.removeprefix("/").removesuffix(
            "/openapi.json"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        schema = build_openapi(
            app,
            title=spec.title,
            description=spec.description,
            path_prefixes=spec.path_prefixes,
            include_paths=spec.include_paths,
            capability=spec,
        )
        _write_json(out_dir / "openapi.json", schema)
        _write_redoc(
            out_dir / "redoc.html",
            title=spec.title,
            openapi_url="./openapi.json",
        )
        _write_swagger_ui(
            out_dir / "docs.html",
            title=spec.title,
            openapi_url="./openapi.json",
        )
        docs.append(
            PageDoc(
                title=spec.title,
                summary=spec.summary,
                openapi_path=f"{_relative_pages_path(spec.openapi_path)}openapi.json",
                swagger_ui_path=f"{_relative_pages_path(spec.openapi_path)}docs.html",
                redoc_path=f"{_relative_pages_path(spec.openapi_path)}redoc.html",
            )
        )

    _write_index(PUBLIC / "index.html", docs)


def _capability_specs() -> list[CapabilitySpec]:
    order = {
        "chat": 0,
        "embedding": 1,
        "image": 2,
        "audio": 3,
        "video": 4,
        "web": 5,
    }
    return sorted(
        capability_spec_registry.list_specs(),
        key=lambda spec: (order.get(spec.domain, 99), spec.domain, spec.name),
    )


def _root_pages_description(specs: list[CapabilitySpec]) -> str:
    lines = [
        "Common kiapi endpoints.",
        "",
        "Static capability docs:",
    ]
    for spec in specs:
        base = _relative_pages_path(spec.openapi_path)
        lines.append(
            f"- **{spec.title}** - {spec.summary} "
            f"[Swagger UI]({base}docs.html), "
            f"[ReDoc]({base}redoc.html), "
            f"[OpenAPI JSON]({base}openapi.json)"
        )
    return "\n".join(lines)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_redoc(path: Path, *, title: str, openapi_url: str) -> None:
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} - ReDoc</title>
</head>
<body>
  <redoc spec-url="{escape(openapi_url)}"></redoc>
  <script src="{REDOC_JS_URL}"></script>
</body>
</html>
""",
        encoding="utf-8",
    )


def _write_swagger_ui(path: Path, *, title: str, openapi_url: str) -> None:
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} - Swagger UI</title>
  <link rel="stylesheet" href="{SWAGGER_UI_CSS_URL}">
  <style>
    body {{
      margin: 0;
    }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="{SWAGGER_UI_JS_URL}"></script>
  <script>
    window.onload = () => {{
      window.ui = SwaggerUIBundle({{
        url: "{escape(openapi_url)}",
        dom_id: "#swagger-ui",
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
        ],
        layout: "BaseLayout",
      }});
    }};
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def _write_index(path: Path, docs: list[PageDoc]) -> None:
    rows = "\n".join(
        "        <tr>"
        f"<td>{escape(doc.title)}</td>"
        f"<td>{escape(doc.summary)}</td>"
        f'<td><a href="{escape(doc.swagger_ui_path)}">Swagger UI</a></td>'
        f'<td><a href="{escape(doc.redoc_path)}">ReDoc</a></td>'
        f'<td><a href="{escape(doc.openapi_path)}">OpenAPI JSON</a></td>'
        "</tr>"
        for doc in docs
    )
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>kiapi API Docs</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body {{
      margin: 0;
      padding: 40px;
      line-height: 1.5;
    }}
    main {{
      max-width: 1040px;
      margin: 0 auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 24px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid color-mix(in srgb, currentColor 18%, transparent);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      font-weight: 650;
    }}
    a {{
      color: #0969da;
    }}
  </style>
</head>
<body>
  <main>
    <h1>kiapi API Docs</h1>
    <p>Static OpenAPI, Swagger UI, and ReDoc pages for kiapi.</p>
    <table>
      <thead>
        <tr>
          <th>Document</th>
          <th>Summary</th>
          <th>Swagger UI</th>
          <th>ReDoc</th>
          <th>OpenAPI JSON</th>
        </tr>
      </thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )


def _relative_pages_path(runtime_openapi_path: str) -> str:
    return runtime_openapi_path.removeprefix("/").removesuffix("openapi.json")


if __name__ == "__main__":
    main()
