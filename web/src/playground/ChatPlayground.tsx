import { useLayoutEffect, useMemo, useRef, useState } from "react";
import Markdown from "react-markdown";

import type { OpenApiDoc, SetupModel } from "../api";
import { Icon } from "../components/Icon";
import { useStickToBottom } from "../hooks";
import {
  attachmentPart,
  completeChat,
  DEFAULT_CHAT_MODEL,
  streamChat,
  type ChatMessage,
  type ChatResult,
  type ContentPart,
  type ToolCall,
  type Usage,
} from "./chat";
import { FieldInput, Hint } from "./fields";
import { buildPayload, operationsOf, type Values } from "./schema";

interface Attachment {
  name: string;
  part: ContentPart;
  preview?: string;
}

type Turn =
  | { role: "user"; text: string; attachments: Attachment[] }
  | {
      role: "assistant";
      text: string;
      toolCalls: ToolCall[];
      finishReason?: string | null;
      usage?: Usage;
      seconds?: number;
      pending?: boolean;
    }
  | { role: "tool"; toolCallId: string; name: string; text: string };

const EXAMPLE_TOOLS = JSON.stringify(
  [
    {
      type: "function",
      function: {
        name: "get_weather",
        description: "Get the current weather for a city.",
        parameters: {
          type: "object",
          properties: { city: { type: "string", description: "City name" } },
          required: ["city"],
        },
      },
    },
  ],
  null,
  2,
);

// Handled by the conversation itself rather than the parameter panel.
const OWN_FIELDS = new Set(["messages", "model"]);

function toMessages(system: string, turns: Turn[]): ChatMessage[] {
  const out: ChatMessage[] = system.trim() ? [{ role: "system", content: system.trim() }] : [];
  for (const t of turns) {
    if (t.role === "user") {
      out.push({
        role: "user",
        content: t.attachments.length ? [...t.attachments.map((a) => a.part), { type: "text", text: t.text }] : t.text,
      });
    } else if (t.role === "assistant") {
      if (t.pending) continue;
      out.push({
        role: "assistant",
        content: t.text || (t.toolCalls.length ? null : ""),
        ...(t.toolCalls.length ? { tool_calls: t.toolCalls } : {}),
      });
    } else {
      out.push({ role: "tool", tool_call_id: t.toolCallId, content: t.text });
    }
  }
  return out;
}

// Sizes the chat to the rest of the viewport so its log scrolls on its own.
function useFillViewport(ref: React.RefObject<HTMLElement | null>) {
  const [height, setHeight] = useState<number>();
  useLayoutEffect(() => {
    const update = () => {
      const top = (ref.current?.getBoundingClientRect().top ?? 0) + window.scrollY;
      setHeight(Math.max(420, window.innerHeight - top - 24));
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [ref]);
  return height;
}

function prettyArgs(args: string): string {
  try {
    return JSON.stringify(JSON.parse(args), null, 2);
  } catch {
    return args;
  }
}

export function ChatPlayground({ doc, models }: { doc: OpenApiDoc; models: SetupModel[] }) {
  const op = useMemo(() => operationsOf(doc).find((o) => o.path.endsWith("/completions")), [doc]);
  const fields = (op?.fields ?? []).filter((f) => !OWN_FIELDS.has(f.name));
  const [model, setModel] = useState(
    models.some((m) => m.name === DEFAULT_CHAT_MODEL) ? DEFAULT_CHAT_MODEL : models[0]?.name ?? DEFAULT_CHAT_MODEL,
  );
  const [system, setSystem] = useState("");
  const [params, setParams] = useState<Values>({});
  const [stream, setStream] = useState(true);
  const [panelOpen, setPanelOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<Attachment[]>([]);
  const [toolResults, setToolResults] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const abort = useRef<AbortController | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const root = useRef<HTMLDivElement>(null);
  const log = useRef<HTMLDivElement>(null);
  const height = useFillViewport(root);
  useStickToBottom(log, turns);

  const extra = useMemo(() => {
    if (!op) return {};
    const body = buildPayload({ ...op, fields }, params);
    delete body.stream;
    delete body.stream_options;
    return body;
  }, [op, fields, params]);

  const run = async (history: Turn[]) => {
    setTurns([...history, { role: "assistant", text: "", toolCalls: [], pending: true }]);
    setBusy(true);
    setError(undefined);
    abort.current = new AbortController();
    const body = { ...extra, model, messages: toMessages(system, history) };
    const update = (patch: Partial<Extract<Turn, { role: "assistant" }>>) =>
      setTurns((ts) => {
        const next = [...ts];
        const last = next[next.length - 1];
        if (last?.role === "assistant") next[next.length - 1] = { ...last, ...patch };
        return next;
      });
    try {
      let text = "";
      const result: ChatResult = stream
        ? await streamChat(
            body,
            {
              onText: (d) => {
                text += d;
                update({ text });
              },
              onToolCalls: (calls) => update({ toolCalls: calls }),
            },
            abort.current.signal,
          )
        : await completeChat(body);
      update({ ...result, pending: false });
    } catch (e) {
      update({ pending: false });
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const send = () => {
    const text = draft.trim();
    if ((!text && pending.length === 0) || busy) return;
    setDraft("");
    setPending([]);
    void run([...turns, { role: "user", text, attachments: pending }]);
  };

  const last = turns[turns.length - 1];
  const openCalls = last?.role === "assistant" && !last.pending ? last.toolCalls : [];
  const sendToolResults = () => {
    const results: Turn[] = openCalls.map((c) => ({
      role: "tool",
      toolCallId: c.id,
      name: c.function.name,
      text: toolResults[c.id] ?? "",
    }));
    setToolResults({});
    void run([...turns, ...results]);
  };

  const attach = async (files: FileList | null) => {
    if (!files) return;
    const added = await Promise.all(
      Array.from(files).map(async (f) => ({
        name: f.name,
        part: await attachmentPart(f),
        preview: f.type.startsWith("image/") ? URL.createObjectURL(f) : undefined,
      })),
    );
    setPending((p) => [...p, ...added]);
  };

  const setCount = Object.values(params).filter((v) => v !== undefined && v !== "").length;

  return (
    <div className={`chat-shell${panelOpen ? " with-panel" : ""}`} ref={root} style={{ height }}>
      <div className="chat">
        <div className="chat-bar">
          <select className="input" style={{ width: "auto", height: 34 }} aria-label="Chat model" value={model} onChange={(e) => setModel(e.target.value)}>
            {models.map((m) => (
              <option key={m.name} value={m.name} disabled={m.status === "missing"}>
                {m.name}
                {m.status === "missing" ? " (not set up)" : ""}
              </option>
            ))}
          </select>
          <input
            className="input"
            style={{ flex: 1, minWidth: 160, height: 34 }}
            placeholder="System prompt (optional)"
            value={system}
            onChange={(e) => setSystem(e.target.value)}
          />
          <button type="button" className={`btn small${panelOpen ? " on" : ""}`} aria-expanded={panelOpen} onClick={() => setPanelOpen((o) => !o)}>
            Parameters{setCount ? ` · ${setCount}` : ""}
          </button>
          <button type="button" className="btn small" onClick={() => setTurns([])} disabled={busy || turns.length === 0}>
            New chat
          </button>
        </div>

        <div className="chat-log" ref={log} aria-live="polite">
          {turns.length === 0 && (
            <div className="empty">
              Only <span className="mono">qwen3-omni</span> accepts audio and video; the Qwen3.8 models take text and
              images. Add tools under Parameters to try tool calling. The first message loads the model.
            </div>
          )}
          {turns.map((t, i) =>
            t.role === "user" ? (
              <div key={i} className="bubble user">
                {t.attachments.length > 0 && (
                  <div className="bubble-files">
                    {t.attachments.map((a, j) =>
                      a.preview ? <img key={j} src={a.preview} alt={a.name} /> : <span key={j} className="tag mono">{a.name}</span>,
                    )}
                  </div>
                )}
                <div style={{ whiteSpace: "pre-wrap" }}>{t.text}</div>
              </div>
            ) : t.role === "tool" ? (
              <div key={i} className="tool-result">
                <span className="mono small muted">tool result · {t.name}</span>
                <pre>{t.text || "(empty)"}</pre>
              </div>
            ) : (
              <div key={i} className="bubble assistant">
                {t.text && (
                  <div className="prose">
                    <Markdown>{t.text}</Markdown>
                  </div>
                )}
                {t.toolCalls.map((c, j) => (
                  <div key={c.id || j} className="tool-call">
                    <div className="mono small">
                      <Icon name="play" size={12} /> {c.function.name || "…"}
                      <span className="muted"> · {c.id}</span>
                    </div>
                    <pre>{prettyArgs(c.function.arguments)}</pre>
                  </div>
                ))}
                {t.pending && !t.text && t.toolCalls.length === 0 && (
                  <span className="typing" aria-label="Writing">
                    <span />
                    <span />
                    <span />
                  </span>
                )}
                {!t.pending && (t.usage || t.finishReason) && (
                  <div className="turn-meta mono">
                    {t.finishReason && <span>{t.finishReason}</span>}
                    {t.usage && (
                      <span>
                        {t.usage.prompt_tokens} in
                        {t.usage.prompt_tokens_details?.cached_tokens ? ` (${t.usage.prompt_tokens_details.cached_tokens} cached)` : ""} ·{" "}
                        {t.usage.completion_tokens} out
                      </span>
                    )}
                    {t.seconds !== undefined && <span>{t.seconds.toFixed(1)}s</span>}
                  </div>
                )}
              </div>
            ),
          )}
          {openCalls.length > 0 && !busy && (
            <div className="card tool-reply">
              <div className="small" style={{ fontWeight: 500 }}>
                Reply with tool results
              </div>
              {openCalls.map((c) => (
                <label key={c.id} className="field">
                  <span className="field-label mono">{c.function.name}</span>
                  <textarea
                    className="input textarea mono"
                    rows={2}
                    placeholder='{"temperature": 21, "condition": "sunny"}'
                    value={toolResults[c.id] ?? ""}
                    onChange={(e) => setToolResults((r) => ({ ...r, [c.id]: e.target.value }))}
                  />
                </label>
              ))}
              <div>
                <button type="button" className="btn small primary" onClick={sendToolResults}>
                  Send {openCalls.length > 1 ? `${openCalls.length} results` : "result"}
                </button>
              </div>
            </div>
          )}
          {error && <div className="error">{error}</div>}
        </div>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          {pending.length > 0 && (
            <div className="bubble-files">
              {pending.map((a, j) => (
                <button key={j} type="button" className="tag mono" onClick={() => setPending((p) => p.filter((_, k) => k !== j))}>
                  {a.name} ×
                </button>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <input ref={fileInput} type="file" hidden multiple accept="image/*,audio/*,video/*" onChange={(e) => void attach(e.target.files)} />
            <button type="button" className="icon-btn" aria-label="Attach files" onClick={() => fileInput.current?.click()}>
              <Icon name="plus" size={18} />
            </button>
            <textarea
              className="input textarea"
              rows={2}
              placeholder="Message"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            {busy ? (
              <button type="button" className="btn primary" aria-label="Stop" onClick={() => abort.current?.abort()}>
                <Icon name="stop" size={15} />
              </button>
            ) : (
              <button type="submit" className="btn primary" aria-label="Send" disabled={!draft.trim() && pending.length === 0}>
                <Icon name="send" size={15} />
              </button>
            )}
          </div>
        </form>
      </div>

      {panelOpen && (
        <aside className="chat-panel" aria-label="Parameters">
          <div className="card-head">
            <h2 className="card-title">Parameters</h2>
            <button type="button" className="adv-toggle" onClick={() => setParams({})}>
              Reset
            </button>
            <button type="button" className="icon-btn" aria-label="Close parameters" onClick={() => setPanelOpen(false)}>
              <Icon name="x" />
            </button>
          </div>
          <div className="field">
            <div className="field-head">
              <span className="field-label">Stream</span>
              <Hint
                label="Stream"
                text="Stream the answer as it is generated (`stream: true`, with `stream_options.include_usage`). Off waits for the whole `chat.completion` object."
              />
            </div>
            <div className="seg">
              <button type="button" className={stream ? "on" : ""} aria-pressed={stream} onClick={() => setStream(true)}>
                On
              </button>
              <button type="button" className={!stream ? "on" : ""} aria-pressed={!stream} onClick={() => setStream(false)}>
                Off
              </button>
            </div>
          </div>
          {fields
            .filter((f) => f.name !== "stream" && f.name !== "stream_options")
            .map((f) => (
              <div key={f.name}>
                <FieldInput field={f} value={params[f.name]} onChange={(v) => setParams((p) => ({ ...p, [f.name]: v }))} ctx={{ models: [] }} />
                {f.name === "tools" && !params.tools && (
                  <button type="button" className="adv-toggle" style={{ marginTop: 6 }} onClick={() => setParams((p) => ({ ...p, tools: EXAMPLE_TOOLS }))}>
                    Insert an example tool
                  </button>
                )}
                {f.name === "tool_choice" && (
                  <div className="chips" style={{ marginTop: 6 }}>
                    {["auto", "none", "required"].map((c) => (
                      <button key={c} type="button" className={`chip${params.tool_choice === c ? " on" : ""}`} onClick={() => setParams((p) => ({ ...p, tool_choice: c }))}>
                        {c}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          <details className="small">
            <summary className="muted" style={{ cursor: "pointer" }}>
              Request body
            </summary>
            <pre className="json">{JSON.stringify({ model, ...extra, stream, messages: "…" }, null, 2)}</pre>
          </details>
        </aside>
      )}
    </div>
  );
}
