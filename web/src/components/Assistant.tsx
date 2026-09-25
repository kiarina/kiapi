import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";

import { apiJson, type OpenApiDoc } from "../api";
import { useData } from "../data";
import { displayTitle, loadSpec } from "../families";
import { useStickToBottom } from "../hooks";
import { DEFAULT_CHAT_MODEL, streamChat, type ChatMessage } from "../playground/chat";
import { Icon } from "./Icon";

interface Context {
  key: string;
  title: string;
  spec: OpenApiDoc | undefined;
  suggestions: string[];
}

interface Line {
  role: "user" | "assistant";
  text: string;
}

function useContext(route: string[]): Context {
  const [spec, setSpec] = useState<OpenApiDoc>();
  const family = route[0] === "f" && route[1] && route[2] ? { domain: route[1], family: route[2] } : null;
  const key = family ? `${family.domain}/${family.family}` : "root";

  useEffect(() => {
    let alive = true;
    setSpec(undefined);
    const load = family ? loadSpec(family.domain, family.family) : apiJson<OpenApiDoc>("/openapi.json");
    load.then((d) => alive && setSpec(d)).catch(() => undefined);
    return () => {
      alive = false;
    };
    // `key` identifies the family.
  }, [key]);

  if (!family) {
    return {
      key,
      title: "kiapi",
      spec,
      suggestions: ["Which family should I use to make music?", "How do I pass my own image to a family?", "How do I follow a long job?"],
    };
  }
  return {
    key,
    title: displayTitle(spec, family.family),
    spec,
    suggestions: ["What can this family do?", "Which model should I pick?", "Show an example request with curl"],
  };
}

function systemPrompt(ctx: Context): string {
  return [
    `You are the help assistant inside kiapi's web UI. kiapi is a local generative AI API server.`,
    ctx.key === "root"
      ? "The user is on the overview pages. Answer questions about kiapi as a whole from its root OpenAPI document below, which lists every family."
      : `The user is looking at the ${ctx.title} family. Answer from its OpenAPI document below, including the guidance in its descriptions.`,
    "Be concise and practical. When it helps, give an example request as JSON or curl against http://localhost:8500.",
    "Say so when the document does not cover something instead of guessing. Answer in the user's language.",
    "",
    "OpenAPI document:",
    JSON.stringify(ctx.spec),
  ].join("\n");
}

export function Assistant({ route }: { route: string[] }) {
  const [open, setOpen] = useState(false);
  const ctx = useContext(route);
  const { setup } = useData();
  const chatModels = (setup.data?.data ?? []).filter((m) => m.family === "chat" && m.status !== "missing").map((m) => m.name);
  const [model, setModel] = useState(DEFAULT_CHAT_MODEL);
  const [threads, setThreads] = useState<Record<string, Line[]>>({});
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const abort = useRef<AbortController | null>(null);
  const log = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const lines = threads[ctx.key] ?? [];
  useStickToBottom(log, lines);

  useEffect(() => {
    if (open) input.current?.focus();
  }, [open]);

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q || busy || !ctx.spec) return;
    const key = ctx.key;
    const history: Line[] = [...lines, { role: "user", text: q }];
    setThreads((t) => ({ ...t, [key]: [...history, { role: "assistant", text: "" }] }));
    setDraft("");
    setBusy(true);
    setError(undefined);
    abort.current = new AbortController();
    const messages: ChatMessage[] = [
      { role: "system", content: systemPrompt(ctx) },
      ...history.map((l) => ({ role: l.role, content: l.text })),
    ];
    let text = "";
    try {
      await streamChat(
        { model, messages, temperature: 0.3 },
        {
          onText: (d) => {
            text += d;
            setThreads((t) => {
              const cur = [...(t[key] ?? [])];
              cur[cur.length - 1] = { role: "assistant", text };
              return { ...t, [key]: cur };
            });
          },
        },
        abort.current.signal,
      );
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const raised = route[0] === "f" && route[2] === "chat" && (route[3] ?? "playground") === "playground";

  return (
    <>
      {open && (
        <section className="helper" role="dialog" aria-label="Ask about kiapi">
          <header className="helper-head">
            <Icon name="sparkle" />
            <div style={{ flex: 1, minWidth: 0, fontWeight: 600, fontSize: 14, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              Ask about {ctx.title}
            </div>
            <button type="button" className="icon-btn" aria-label="Clear" disabled={busy || !lines.length} onClick={() => setThreads((t) => ({ ...t, [ctx.key]: [] }))}>
              <Icon name="refresh" size={15} />
            </button>
            <button type="button" className="icon-btn" aria-label="Close" onClick={() => setOpen(false)}>
              <Icon name="x" />
            </button>
          </header>
          <div className="helper-log" ref={log} aria-live="polite">
            {lines.length === 0 && (
              <div className="helper-empty">
                <div className="small muted">Ask anything about using {ctx.title}. The first question loads {model}.</div>
                {ctx.suggestions.map((s) => (
                  <button key={s} type="button" className="suggestion" disabled={!ctx.spec} onClick={() => void ask(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}
            {lines.map((l, i) =>
              l.role === "user" ? (
                <div key={i} className="bubble user small-bubble">
                  {l.text}
                </div>
              ) : (
                <div key={i} className="bubble assistant small-bubble">
                  {l.text ? (
                    <div className="prose">
                      <Markdown>{l.text}</Markdown>
                    </div>
                  ) : (
                    <span className="typing" aria-label="Writing">
                      <span />
                      <span />
                      <span />
                    </span>
                  )}
                </div>
              ),
            )}
            {error && <div className="error">{error}</div>}
          </div>
          <div className="helper-foot small muted">
            <span style={{ flex: 1 }}>{ctx.spec ? "Answers from this page's OpenAPI document" : "Loading the document…"}</span>
            <select className="helper-model" aria-label="Chat model" value={model} onChange={(e) => setModel(e.target.value)}>
              {(chatModels.length ? chatModels : [DEFAULT_CHAT_MODEL]).map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <form
            className="helper-input"
            onSubmit={(e) => {
              e.preventDefault();
              void ask(draft);
            }}
          >
            <textarea
              ref={input}
              className="input textarea"
              rows={1}
              placeholder="Ask a question"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  void ask(draft);
                }
              }}
            />
            {busy ? (
              <button type="button" className="btn primary" aria-label="Stop" onClick={() => abort.current?.abort()}>
                <Icon name="stop" size={14} />
              </button>
            ) : (
              <button type="submit" className="btn primary" aria-label="Send" disabled={!draft.trim() || !ctx.spec}>
                <Icon name="send" size={14} />
              </button>
            )}
          </form>
        </section>
      )}
      <button
        type="button"
        className={`fab${raised ? " raised" : ""}${open ? " open" : ""}`}
        aria-label={open ? "Close the assistant" : `Ask about ${ctx.title}`}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name={open ? "x" : "sparkle"} size={22} />
      </button>
    </>
  );
}
