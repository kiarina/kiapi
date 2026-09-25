import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";

import { apiJson, type OpenApiDoc } from "../api";
import { useData } from "../data";
import { displayTitle, loadSpec } from "../families";
import { useStickToBottom } from "../hooks";
import { DEFAULT_CHAT_MODEL, streamChat, type ChatMessage, type ToolCall } from "../playground/chat";
import { fillTools, toolName, useFormBridge, valuesFromArgs, type FormBridge } from "../playground/formBridge";
import { Icon } from "./Icon";

interface Context {
  key: string;
  title: string;
  spec: OpenApiDoc | undefined;
  suggestions: string[];
}

interface Line {
  // `note` lines are shown to the person only; `tool` lines are sent to the model only.
  role: "user" | "assistant" | "tool" | "note";
  text: string;
  toolCalls?: ToolCall[];
  toolCallId?: string;
}

function toMessages(lines: Line[]): ChatMessage[] {
  const out: ChatMessage[] = [];
  for (const l of lines) {
    if (l.role === "user") out.push({ role: "user", content: l.text });
    else if (l.role === "assistant") {
      out.push({ role: "assistant", content: l.text || (l.toolCalls?.length ? null : ""), ...(l.toolCalls?.length ? { tool_calls: l.toolCalls } : {}) });
    } else if (l.role === "tool") out.push({ role: "tool", tool_call_id: l.toolCallId, content: l.text });
  }
  return out;
}

// Applies each fill_* call to the form; arguments that do not fit are skipped.
function applyCalls(bridge: FormBridge, calls: ToolCall[]): { tool: Line[]; notes: Line[] } {
  const tool: Line[] = [];
  const notes: Line[] = [];
  for (const call of calls) {
    const op = bridge.operations.find((o) => toolName(o) === call.function.name);
    let args: Record<string, unknown> | null = null;
    try {
      const parsed = JSON.parse(call.function.arguments || "{}");
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) args = parsed;
    } catch {
      args = null;
    }
    if (!op || !args) {
      const why = !op ? `unknown tool ${call.function.name}` : "arguments were not a JSON object";
      tool.push({ role: "tool", toolCallId: call.id, text: JSON.stringify({ filled: [], error: why }) });
      notes.push({ role: "note", text: `Could not fill the form: ${why}.` });
      continue;
    }
    const r = valuesFromArgs(op, args, bridge.models);
    if (r.applied.length) bridge.apply(op.name, r.values);
    tool.push({
      role: "tool",
      toolCallId: call.id,
      text: JSON.stringify({ filled: r.applied, skipped: r.skipped, note: "The user reviews the form and submits it." }),
    });
    notes.push({
      role: "note",
      text:
        (r.applied.length ? `Filled ${op.name}: ${r.applied.join(", ")}` : `Nothing filled in ${op.name}`) +
        (r.skipped.length ? ` · skipped: ${r.skipped.join(", ")}` : ""),
    });
  }
  return { tool, notes };
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

function systemPrompt(ctx: Context, bridge: FormBridge | null): string {
  return [
    `You are the help assistant inside kiapi's web UI. kiapi is a local generative AI API server.`,
    ctx.key === "root"
      ? "The user is on the overview pages. Answer questions about kiapi as a whole from its root OpenAPI document below, which lists every family."
      : `The user is looking at the ${ctx.title} family. Answer from its OpenAPI document below, including the guidance in its descriptions.`,
    "Be concise and practical. When it helps, give an example request as JSON or curl against http://localhost:8500.",
    "Say so when the document does not cover something instead of guessing. Answer in the user's language.",
    ...(bridge
      ? [
          `The page shows a form for ${bridge.operations.map((o) => `"${o.name}"`).join(", ")} (currently "${bridge.current}").`,
          "When the user asks you to fill in, set up, or prepare a request, call the matching fill_*_form tool with only the fields to set, following the document's guidance for good values.",
          "The user reviews and submits the form themselves. After filling, briefly say what you set and why.",
        ]
      : []),
    "",
    "OpenAPI document:",
    JSON.stringify(ctx.spec),
  ].join("\n");
}

// On the chat page the button sits above the message console, with the same gap
// above it as the console has below it.
function useLiftAboveComposer(active: boolean): number | undefined {
  const [lift, setLift] = useState<number>();
  useEffect(() => {
    if (!active) {
      setLift(undefined);
      return;
    }
    const update = () => {
      const composer = document.querySelector(".chat .composer");
      if (!composer) return;
      const r = composer.getBoundingClientRect();
      const gap = window.innerHeight - r.bottom;
      setLift(Math.round(window.innerHeight - r.top + gap));
    };
    update();
    const observer = new ResizeObserver(update);
    const composer = document.querySelector(".chat .composer");
    if (composer) observer.observe(composer);
    const timer = window.setInterval(update, 1000);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.clearInterval(timer);
      window.removeEventListener("resize", update);
    };
  }, [active]);
  return lift;
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

  const bridge = useFormBridge();
  const formBridge = bridge && ctx.key.endsWith(`/${bridge.family}`) ? bridge : null;

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q || busy || !ctx.spec) return;
    const key = ctx.key;
    const system: ChatMessage = { role: "system", content: systemPrompt(ctx, formBridge) };
    const tools = formBridge ? fillTools(formBridge) : undefined;
    let thread: Line[] = [...lines, { role: "user", text: q }];
    const show = () => setThreads((t) => ({ ...t, [key]: [...thread] }));
    setDraft("");
    setBusy(true);
    setError(undefined);
    abort.current = new AbortController();
    try {
      // One round may fill the form; the follow-up only explains, so it gets no tools.
      for (const allowTools of tools ? [true, false] : [false]) {
        const reply: Line = { role: "assistant", text: "" };
        thread = [...thread, reply];
        show();
        const result = await streamChat(
          {
            model,
            messages: [system, ...toMessages(thread.slice(0, -1))],
            temperature: 0.3,
            ...(tools ? { tools, tool_choice: allowTools ? "auto" : "none" } : {}),
          },
          {
            onText: (d) => {
              reply.text += d;
              show();
            },
          },
          abort.current.signal,
        );
        reply.toolCalls = result.toolCalls;
        if (!allowTools || !formBridge || result.toolCalls.length === 0) break;
        const { tool, notes } = applyCalls(formBridge, result.toolCalls);
        thread = [...thread, ...tool, ...notes];
        show();
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const raised = route[0] === "f" && route[2] === "chat" && (route[3] ?? "playground") === "playground";
  const lift = useLiftAboveComposer(raised);

  return (
    <>
      {open && (
        <section
          className="helper"
          role="dialog"
          aria-label="Ask about kiapi"
          style={lift === undefined ? undefined : { bottom: lift + 64, height: `min(520px, calc(100vh - ${lift + 96}px))` }}
        >
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
            {lines.map((l, i) => {
              if (l.role === "tool") return null;
              if (l.role === "user") {
                return (
                  <div key={i} className="bubble user small-bubble">
                    {l.text}
                  </div>
                );
              }
              if (l.role === "note") {
                return (
                  <div key={i} className="fill-note">
                    <Icon name="check" size={13} />
                    {l.text}
                  </div>
                );
              }
              const writing = busy && i === lines.length - 1;
              if (!l.text && !writing) return null;
              return (
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
              );
            })}
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
        className={`fab${open ? " open" : ""}`}
        style={lift === undefined ? undefined : { bottom: lift }}
        aria-label={open ? "Close the assistant" : `Ask about ${ctx.title}`}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name={open ? "x" : "sparkle"} size={22} />
      </button>
    </>
  );
}
