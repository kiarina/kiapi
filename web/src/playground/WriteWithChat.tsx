import { useRef, useState } from "react";

import type { OpenApiDoc, SetupModel } from "../api";
import { Icon } from "../components/Icon";
import { useData } from "../data";
import { displayTitle } from "../families";
import { DEFAULT_CHAT_MODEL, streamChat } from "./chat";
import type { Field, Operation } from "./schema";

function systemPrompt(doc: OpenApiDoc, family: string, op: Operation, field: Field): string {
  return [
    `You write the \`${field.name}\` value for a request to the ${displayTitle(doc, family)} \`${op.name}\` operation of kiapi, a local generative AI server.`,
    "Follow the guidance below. Reply with only the value to put in the field: no explanation, no surrounding quotes, no Markdown fences.",
    "Write in the language the guidance recommends for this model; otherwise use the language of the idea.",
    "",
    "# Family guide",
    doc.info.description ?? "",
    "",
    "# Operation",
    op.description,
    "",
    `# Field \`${field.name}\``,
    field.description,
  ].join("\n");
}

export function WriteWithChat({
  doc,
  family,
  op,
  field,
  current,
  onUse,
  onClose,
}: {
  doc: OpenApiDoc;
  family: string;
  op: Operation;
  field: Field;
  current: string;
  onUse: (text: string) => void;
  onClose: () => void;
}) {
  const { setup } = useData();
  const chatModels: SetupModel[] = (setup.data?.data ?? []).filter((m) => m.family === "chat");
  const [model, setModel] = useState(DEFAULT_CHAT_MODEL);
  const [idea, setIdea] = useState("");
  const [output, setOutput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const abort = useRef<AbortController | null>(null);

  const write = async () => {
    setBusy(true);
    setError(undefined);
    setOutput("");
    abort.current = new AbortController();
    const ask = [
      idea.trim() ? `Idea: ${idea.trim()}` : "Write a good example value.",
      current.trim() ? `\nCurrent value (improve it and keep what works):\n${current.trim()}` : "",
    ].join("\n");
    try {
      await streamChat(
        {
          model,
          messages: [
            { role: "system", content: systemPrompt(doc, family, op, field) },
            { role: "user", content: ask },
          ],
          temperature: 0.7,
        },
        (d) => setOutput((o) => o + d),
        abort.current.signal,
      );
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const close = () => {
    abort.current?.abort();
    onClose();
  };

  return (
    <div className="overlay" onClick={close}>
      <div className="card write-dialog" role="dialog" aria-label="Write with chat" onClick={(e) => e.stopPropagation()}>
        <div className="card-head">
          <Icon name="sparkle" />
          <h2 className="card-title">Write {field.label.toLowerCase()} with chat</h2>
          <button type="button" className="icon-btn" aria-label="Close" onClick={close}>
            <Icon name="x" />
          </button>
        </div>
        <p className="small muted" style={{ margin: 0 }}>
          A chat model reads this family's guide and writes the value for you.
        </p>
        <label className="field">
          <span className="field-label">What do you want?</span>
          <textarea
            className="input textarea"
            rows={3}
            autoFocus
            placeholder={current ? "Leave empty to polish the current value" : "A cozy cafe at dusk, with its name on the sign"}
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void write();
            }}
          />
        </label>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select className="input" style={{ width: "auto", height: 34 }} value={model} onChange={(e) => setModel(e.target.value)} aria-label="Chat model">
            {(chatModels.length ? chatModels.map((m) => m.name) : [DEFAULT_CHAT_MODEL]).map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          <span style={{ flex: 1 }} />
          {busy ? (
            <button type="button" className="btn small" onClick={() => abort.current?.abort()}>
              <Icon name="stop" size={14} />
              Stop
            </button>
          ) : (
            <button type="button" className="btn small primary" onClick={() => void write()}>
              <Icon name="sparkle" size={14} />
              {output ? "Write again" : "Write"}
            </button>
          )}
        </div>
        {(busy || output) && (
          <div className="write-output">
            {output || <span className="muted">Loading {model} and writing… The first run loads the model.</span>}
          </div>
        )}
        {error && <div className="error">{error}</div>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button type="button" className="btn small" onClick={close}>
            Cancel
          </button>
          <button type="button" className="btn small primary" disabled={!output || busy} onClick={() => onUse(output.trim())}>
            Use this
          </button>
        </div>
      </div>
    </div>
  );
}
