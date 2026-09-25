import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";

import type { SetupModel } from "../api";
import { Icon } from "../components/Icon";
import { attachmentPart, DEFAULT_CHAT_MODEL, streamChat, type ChatMessage, type ContentPart } from "./chat";

interface Turn {
  role: "user" | "assistant";
  text: string;
  attachments: { name: string; part: ContentPart; preview?: string }[];
}

function toMessage(t: Turn): ChatMessage {
  if (t.role === "assistant" || t.attachments.length === 0) return { role: t.role, content: t.text };
  return { role: t.role, content: [...t.attachments.map((a) => a.part), { type: "text", text: t.text }] };
}

export function ChatPlayground({ models }: { models: SetupModel[] }) {
  const [model, setModel] = useState(
    models.some((m) => m.name === DEFAULT_CHAT_MODEL) ? DEFAULT_CHAT_MODEL : models[0]?.name ?? DEFAULT_CHAT_MODEL,
  );
  const [system, setSystem] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<Turn["attachments"]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const abort = useRef<AbortController | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ block: "end" });
  }, [turns]);

  const send = async () => {
    const text = draft.trim();
    if ((!text && pending.length === 0) || busy) return;
    const user: Turn = { role: "user", text, attachments: pending };
    const history = [...turns, user];
    setTurns([...history, { role: "assistant", text: "", attachments: [] }]);
    setDraft("");
    setPending([]);
    setBusy(true);
    setError(undefined);
    abort.current = new AbortController();
    const messages: ChatMessage[] = [
      ...(system.trim() ? [{ role: "system" as const, content: system.trim() }] : []),
      ...history.map(toMessage),
    ];
    try {
      await streamChat(
        { model, messages },
        (d) =>
          setTurns((ts) => {
            const next = [...ts];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, text: last.text + d };
            return next;
          }),
        abort.current.signal,
      );
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setBusy(false);
    }
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

  return (
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
          style={{ flex: 1, minWidth: 180, height: 34 }}
          placeholder="System prompt (optional)"
          value={system}
          onChange={(e) => setSystem(e.target.value)}
        />
        <button type="button" className="btn small" onClick={() => setTurns([])} disabled={busy || turns.length === 0}>
          New chat
        </button>
      </div>

      <div className="chat-log" aria-live="polite">
        {turns.length === 0 && (
          <div className="empty">
            Only <span className="mono">qwen3-omni</span> accepts audio and video; the Qwen3.8 models take text and images.
            The first message loads the model.
          </div>
        )}
        {turns.map((t, i) => (
          <div key={i} className={`bubble ${t.role}`}>
            {t.attachments.length > 0 && (
              <div className="bubble-files">
                {t.attachments.map((a, j) =>
                  a.preview ? <img key={j} src={a.preview} alt={a.name} /> : <span key={j} className="tag mono">{a.name}</span>,
                )}
              </div>
            )}
            {t.role === "assistant" ? (
              t.text ? (
                <div className="prose">
                  <Markdown>{t.text}</Markdown>
                </div>
              ) : (
                <span className="typing" aria-label="Writing">
                  <span />
                  <span />
                  <span />
                </span>
              )
            ) : (
              <div style={{ whiteSpace: "pre-wrap" }}>{t.text}</div>
            )}
          </div>
        ))}
        {error && <div className="error">{error}</div>}
        <div ref={end} />
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
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
                void send();
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
  );
}
