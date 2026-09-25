import { useEffect, useState } from "react";
import Markdown from "react-markdown";

import type { FileRecord, OpenApiDoc, OpenApiOperation, SchemaRef, SetupModel } from "../api";
import { Command, ErrorBox, Loading, PageHead, Thumb } from "../components/ui";
import { ChatPlayground } from "../playground/ChatPlayground";
import { Playground } from "../playground/Playground";
import { sortedFiles, useData } from "../data";
import { displayTitle, familyHref, loadSpec, specBase } from "../families";
import { firstParagraph, gb } from "../format";

// Generated files are named after their family, except Z-Image, which predates the convention.
const FILE_PREFIXES: Record<string, string[]> = { zimage: ["image_", "zimage_"] };

function familyFiles(family: string, files: FileRecord[]): FileRecord[] {
  const prefixes = FILE_PREFIXES[family] ?? [`${family}_`];
  return files.filter(
    (f) => prefixes.some((p) => f.filename.startsWith(p)) && !f.content_type.startsWith("application/"),
  );
}

export function Family({ domain, family, tab }: { domain: string; family: string; tab: string }) {
  const { setup, files } = useData();
  const [doc, setDoc] = useState<OpenApiDoc>();
  const [error, setError] = useState<Error>();

  useEffect(() => {
    setDoc(undefined);
    setError(undefined);
    loadSpec(domain, family).then(setDoc, setError);
  }, [domain, family]);

  const models = (setup.data?.data ?? []).filter((m) => m.family === family);
  const outputs = familyFiles(family, sortedFiles(files.data?.data)).slice(0, 8);
  const title = displayTitle(doc, family);

  return (
    <>
      <PageHead
        eyebrow={domain}
        title={title}
        sub={doc && <span>{firstParagraph(doc.info.description)}</span>}
        actions={
          <span className="chips">
            <a className="btn small" href={`${specBase(domain, family)}/docs`}>
              Swagger UI
            </a>
            <a className="btn small" href={`${specBase(domain, family)}/openapi.json`}>
              OpenAPI JSON
            </a>
          </span>
        }
      />
      <nav className="tabs" aria-label="Family sections">
        <a className={`tab${tab === "playground" ? " on" : ""}`} href={familyHref(domain, family)}>
          Playground
        </a>
        <a className={`tab${tab === "guide" ? " on" : ""}`} href={familyHref(domain, family, "guide")}>
          Guide
        </a>
        <a className={`tab${tab === "api" ? " on" : ""}`} href={familyHref(domain, family, "api")}>
          API
        </a>
      </nav>

      {error && <ErrorBox error={error} />}
      {!doc && !error && <Loading />}
      {doc && tab === "playground" &&
        (family === "chat" ? (
          <ChatPlayground models={models} />
        ) : (
          <Playground key={family} doc={doc} family={family} models={models} />
        ))}
      {doc && tab === "guide" && <Guide doc={doc} models={models} outputs={outputs} />}
      {doc && tab === "api" && <Api doc={doc} />}
    </>
  );
}

function Guide({ doc, models, outputs }: { doc: OpenApiDoc; models: SetupModel[]; outputs: FileRecord[] }) {
  return (
    <div className="grid-aside">
      <div style={{ display: "flex", flexDirection: "column", gap: 24, minWidth: 0 }}>
        {outputs.length > 0 && (
          <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <h2 className="section-title">Your outputs</h2>
            <div className="gallery">
              {outputs.map((f) => (
                <a key={f.file_id} className="tile-media" href={`#/files/${f.file_id}`}>
                  <Thumb file={f} />
                  <span className="cap">
                    <span>{String(f.meta.model ?? f.filename)}</span>
                  </span>
                </a>
              ))}
            </div>
          </section>
        )}
        <article className="card prose">
          <Markdown>{doc.info.description ?? ""}</Markdown>
        </article>
      </div>

      <aside style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <section className="card">
          <h2 className="card-title">Models</h2>
          {models.length === 0 && <div className="muted small">Loading setup state…</div>}
          <div className="rows">
            {models.map((m) => (
              <div key={m.name} className="row" style={{ flexDirection: "column", alignItems: "stretch", gap: 6, padding: "10px 0" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="mono" style={{ fontWeight: 500 }}>
                    {m.name}
                  </span>
                  {m.default && <span className="badge outline">default</span>}
                  <span style={{ flex: 1 }} />
                  <span className="mono small muted">{m.size_gb ? gb(m.size_gb) : ""}</span>
                  {m.status === "missing" ? (
                    <span className="badge muted">Not set up</span>
                  ) : (
                    <span className="badge ok">Ready</span>
                  )}
                </div>
                {m.resources
                  .filter((r) => !r.ready)
                  .map((r) => (
                    <Command key={r.label} text={r.activate_command} />
                  ))}
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h2 className="card-title">Endpoints</h2>
          <div className="rows">
            {operations(doc).map(({ method, path, op }) => (
              <div key={`${method} ${path}`} className="row" style={{ flexDirection: "column", alignItems: "stretch", gap: 2, padding: "8px 0" }}>
                <div style={{ display: "flex", gap: 8 }} className="mono small">
                  <span className={`method ${method}`}>{method.toUpperCase()}</span>
                  <span style={{ overflowWrap: "anywhere" }}>{path}</span>
                </div>
                <div className="small muted" style={{ paddingLeft: 48 }}>
                  {opSummary(op)}
                </div>
              </div>
            ))}
          </div>
        </section>
      </aside>
    </div>
  );
}

function operations(doc: OpenApiDoc) {
  return Object.entries(doc.paths).flatMap(([path, methods]) =>
    Object.entries(methods)
      .filter(([method]) => ["get", "post", "put", "patch", "delete"].includes(method))
      .map(([method, op]) => ({ method, path, op })),
  );
}

// FastAPI derives `summary` from the handler name, so the docstring's first line reads better.
function opSummary(op: OpenApiOperation): string {
  return firstParagraph(op.description).split(/(?<=\.)\s/)[0] || op.summary || "";
}

function resolve(doc: OpenApiDoc, schema: SchemaRef | undefined): SchemaRef | undefined {
  if (!schema?.$ref) return schema;
  const name = schema.$ref.split("/").pop()!;
  return doc.components?.schemas?.[name];
}

function typeLabel(doc: OpenApiDoc, s: SchemaRef | undefined): string {
  if (!s) return "";
  if (s.$ref) return s.$ref.split("/").pop()!;
  if (s.enum) return s.enum.map((v) => JSON.stringify(v)).join(" | ");
  const union = s.anyOf ?? s.oneOf;
  if (union) {
    return union
      .filter((u) => u.type !== "null")
      .map((u) => typeLabel(doc, u))
      .join(" | ");
  }
  if (s.type === "array") return `${typeLabel(doc, s.items)}[]`;
  return s.type ?? "";
}

function RequestFields({ doc, op }: { doc: OpenApiDoc; op: OpenApiOperation }) {
  const content = op.requestBody?.content;
  const body = content ? Object.values(content)[0]?.schema : undefined;
  const schema = resolve(doc, body);
  const props = Object.entries(schema?.properties ?? {});
  if (props.length === 0) return null;
  const required = new Set(schema?.required ?? []);
  const cols = "200px 180px minmax(0, 1fr)";
  return (
    <div className="table fields">
      <div className="table-head hide-sm" style={{ gridTemplateColumns: cols }}>
        <span>Field</span>
        <span>Type</span>
        <span>Description</span>
      </div>
      {props.map(([name, prop]) => (
        <div key={name} className="table-row" style={{ gridTemplateColumns: cols }}>
          <span className="mono small" style={{ overflowWrap: "anywhere" }}>
            {name}
            {required.has(name) && <span style={{ color: "var(--fail)" }}> *</span>}
          </span>
          <span className="mono small muted push" style={{ overflowWrap: "anywhere" }}>
            {typeLabel(doc, prop)}
            {prop.default !== undefined && prop.default !== null && (
              <span style={{ display: "block" }}>= {JSON.stringify(prop.default)}</span>
            )}
          </span>
          <span className="desc wide">{prop.description ?? resolve(doc, prop)?.description ?? ""}</span>
        </div>
      ))}
    </div>
  );
}

function Api({ doc }: { doc: OpenApiDoc }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      {operations(doc).map(({ method, path, op }) => (
        <section key={`${method} ${path}`} className="op">
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <span className={`method ${method}`}>{method.toUpperCase()}</span>
            <code style={{ fontSize: 14 }}>{path}</code>

          </div>
          {op.description && (
            <div className="prose" style={{ fontSize: 13.5 }}>
              <Markdown>{op.description}</Markdown>
            </div>
          )}
          <RequestFields doc={doc} op={op} />
        </section>
      ))}
    </div>
  );
}
