import { useState, type ReactNode } from "react";
import Markdown from "react-markdown";

import type { SetupModel } from "../api";
import { Icon } from "../components/Icon";
import { Thumb } from "../components/ui";
import { useData } from "../data";
import { shortId } from "../format";
import { FilePicker, acceptFor } from "./FilePicker";
import type { Field } from "./schema";

export interface FieldContext {
  models: SetupModel[];
  onWrite?: (field: Field) => void;
}

// A "?" that shows the field's full description on hover, focus, or tap.
export function Hint({ label, text }: { label: string; text: string }) {
  if (!text) return null;
  return (
    <span className="hint">
      <button type="button" className="hint-btn" aria-label={`About ${label}`}>
        ?
      </button>
      <span role="tooltip" className="hint-pop prose">
        <Markdown>{text}</Markdown>
      </span>
    </span>
  );
}

function Frame({ field, children, aside, flash }: { field: Field; children: ReactNode; aside?: ReactNode; flash?: boolean }) {
  return (
    <div className={`field${flash ? " flash" : ""}`}>
      <div className="field-head">
        <label className="field-label" htmlFor={`f-${field.name}`}>
          {field.label}
          {field.required && <span className="req"> *</span>}
        </label>
        <Hint label={field.label} text={field.description} />
        <span style={{ flex: 1 }} />
        {aside}
      </div>
      {children}
    </div>
  );
}

function FileChip({ id, onRemove }: { id: string; onRemove: () => void }) {
  const { files } = useData();
  const rec = files.data?.data.find((f) => f.file_id === id);
  return (
    <span className="file-chip">
      {rec ? <Thumb file={rec} /> : <span className="thumb" />}
      <span className="mono small">{rec?.filename ?? shortId(id)}</span>
      <button type="button" className="icon-btn" aria-label="Remove file" onClick={onRemove}>
        <Icon name="x" size={13} />
      </button>
    </span>
  );
}

function FilesInput({ field, value, onChange }: { field: Field; value: string[]; onChange: (v: string[]) => void }) {
  const [open, setOpen] = useState(false);
  const multiple = field.kind === "files";
  return (
    <>
      <div className="file-list">
        {value.map((id) => (
          <FileChip key={id} id={id} onRemove={() => onChange(value.filter((x) => x !== id))} />
        ))}
        {(multiple || value.length === 0) && (
          <button type="button" id={`f-${field.name}`} className="file-add" onClick={() => setOpen(true)}>
            <Icon name="plus" size={16} />
            {multiple && value.length > 0 ? "Add" : "Choose file"}
          </button>
        )}
      </div>
      {open && (
        <FilePicker
          accept={acceptFor(field.name)}
          multiple={multiple}
          onClose={() => setOpen(false)}
          onPick={(ids) => {
            onChange(multiple ? [...value, ...ids.filter((id) => !value.includes(id))] : ids.slice(0, 1));
            setOpen(false);
          }}
        />
      )}
    </>
  );
}

interface Lora {
  file: string;
  scale: number;
}

function LorasInput({ field, value, onChange }: { field: Field; value: Lora[]; onChange: (v: Lora[]) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {value.map((l, i) => (
          <div key={l.file} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <FileChip id={l.file} onRemove={() => onChange(value.filter((_, j) => j !== i))} />
            <label className="small muted" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              scale
              <input
                className="input mono"
                style={{ width: 72, height: 32 }}
                type="number"
                step="0.05"
                value={l.scale}
                onChange={(e) => onChange(value.map((x, j) => (j === i ? { ...x, scale: Number(e.target.value) } : x)))}
              />
            </label>
          </div>
        ))}
        {value.length < 4 && (
          <button type="button" id={`f-${field.name}`} className="file-add" onClick={() => setOpen(true)}>
            <Icon name="plus" size={16} />
            Add LoRA
          </button>
        )}
      </div>
      {open && (
        <FilePicker
          accept="any"
          multiple={false}
          onClose={() => setOpen(false)}
          onPick={(ids) => {
            onChange([...value, { file: ids[0], scale: 1 }]);
            setOpen(false);
          }}
        />
      )}
    </>
  );
}

function TagsInput({ field, value, onChange }: { field: Field; value: string[]; onChange: (v: string[]) => void }) {
  const [draft, setDraft] = useState("");
  if (field.options && (field.name === "categories" || field.name === "engines")) {
    return (
      <div className="chips">
        {value.map((item) => (
          <button key={item} type="button" className="chip on" onClick={() => onChange(value.filter((x) => x !== item))}>
            {item} ×
          </button>
        ))}
        <select
          id={`f-${field.name}`}
          className="input"
          aria-label={`Add ${field.label.toLowerCase()}`}
          style={{ width: "100%" }}
          value=""
          disabled={field.options.length === 0}
          onChange={(e) => onChange([...value, e.target.value])}
        >
          <option value="">{field.options.length ? `Choose ${field.label.toLowerCase()}…` : "Loading choices…"}</option>
          {field.options.filter((option) => !value.includes(option)).map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </div>
    );
  }
  if (field.options) {
    return (
      <div className="chips">
        {field.options.map((o) => (
          <button
            key={o}
            type="button"
            className={`chip${value.includes(o) ? " on" : ""}`}
            aria-pressed={value.includes(o)}
            onClick={() => onChange(value.includes(o) ? value.filter((x) => x !== o) : [...value, o])}
          >
            {o}
          </button>
        ))}
      </div>
    );
  }
  const add = () => {
    const parts = draft.split(",").map((s) => s.trim()).filter(Boolean);
    if (parts.length) onChange([...value, ...parts.filter((p) => !value.includes(p))]);
    setDraft("");
  };
  return (
    <div className="chips">
      {value.map((t) => (
        <button key={t} type="button" className="chip on" onClick={() => onChange(value.filter((x) => x !== t))}>
          {t} ×
        </button>
      ))}
      <input
        id={`f-${field.name}`}
        className="input"
        style={{ width: 180, height: 32 }}
        placeholder="Type and press Enter"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            add();
          }
        }}
        onBlur={add}
      />
    </div>
  );
}

function ModelInput({ value, onChange, ctx }: { value: string; onChange: (v: string) => void; ctx: FieldContext }) {
  const fallback = ctx.models.find((m) => m.default)?.name;
  return (
    <div className="model-options" role="radiogroup" aria-label="Model">
      {ctx.models.map((m) => {
        const on = (value || fallback) === m.name;
        return (
          <label key={m.name} className={`model-option${on ? " on" : ""}${m.status === "missing" ? " off" : ""}`}>
            <input
              type="radio"
              name="model"
              aria-label={m.name}
              checked={on}
              onChange={() => onChange(m.default ? "" : m.name)}
            />
            <span className="mono">{m.name}</span>
            {m.default && <span className="badge outline">default</span>}
            {m.status === "missing" && <span className="badge muted">not set up</span>}
          </label>
        );
      })}
    </div>
  );
}

export function FieldInput({
  field,
  value,
  onChange,
  ctx,
  flash,
}: {
  field: Field;
  value: unknown;
  onChange: (v: unknown) => void;
  ctx: FieldContext;
  flash?: boolean;
}) {
  const id = `f-${field.name}`;
  const placeholder = field.required
    ? ""
    : field.defaultValue !== undefined && field.defaultValue !== null
      ? String(field.defaultValue)
      : "auto";

  switch (field.kind) {
    case "model":
      if (ctx.models.length === 0) break;
      return (
        <Frame field={field} flash={flash}>
          <ModelInput value={String(value ?? "")} onChange={onChange} ctx={ctx} />
        </Frame>
      );
    case "prompt":
      return (
        <Frame
          flash={flash}
          field={field}
          aside={
            ctx.onWrite && (
              <button type="button" className="write-btn" onClick={() => ctx.onWrite?.(field)}>
                <Icon name="sparkle" size={14} />
                Write with chat
              </button>
            )
          }
        >
          <textarea
            id={id}
            className="input textarea"
            rows={field.name === "lyrics" ? 8 : field.name === "prompt" ? 5 : 3}
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
          />
        </Frame>
      );
    case "integer":
    case "number":
      return (
        <Frame
          flash={flash}
          field={field}
          aside={
            field.name === "seed" && (
              <button
                type="button"
                className="icon-btn"
                aria-label="Random seed"
                onClick={() => onChange(String(Math.floor(Math.random() * 2 ** 31)))}
              >
                <Icon name="dice" size={14} />
              </button>
            )
          }
        >
          <input
            id={id}
            className="input mono"
            type="number"
            inputMode={field.kind === "integer" ? "numeric" : "decimal"}
            step={field.kind === "integer" ? 1 : "any"}
            min={field.minimum}
            max={field.maximum}
            placeholder={placeholder}
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
          />
        </Frame>
      );
    case "enum":
      return (
        <Frame field={field} flash={flash}>
          <select id={id} className="input" value={String(value ?? "")} onChange={(e) => onChange(e.target.value)}>
            <option value="">{placeholder === "auto" ? "Default" : `Default (${placeholder})`}</option>
            {field.options?.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        </Frame>
      );
    case "boolean": {
      const state = value === undefined || value === "" ? "default" : value ? "on" : "off";
      return (
        <Frame field={field} flash={flash}>
          <div className="seg" role="radiogroup" aria-label={field.label} title={field.description}>
            {(["default", "on", "off"] as const).map((s) => (
              <button
                key={s}
                type="button"
                className={state === s ? "on" : ""}
                aria-pressed={state === s}
                onClick={() => onChange(s === "default" ? undefined : s === "on")}
              >
                {s === "default" ? `Default${field.defaultValue !== undefined ? ` (${field.defaultValue ? "on" : "off"})` : ""}` : s === "on" ? "On" : "Off"}
              </button>
            ))}
          </div>
        </Frame>
      );
    }
    case "file":
    case "files":
      return (
        <Frame field={field} flash={flash}>
          <FilesInput
            field={field}
            value={field.kind === "file" ? (value ? [String(value)] : []) : ((value as string[]) ?? [])}
            onChange={(ids) => onChange(field.kind === "file" ? ids[0] : ids)}
          />
        </Frame>
      );
    case "loras":
      return (
        <Frame field={field} flash={flash}>
          <LorasInput field={field} value={(value as Lora[]) ?? []} onChange={onChange} />
        </Frame>
      );
    case "tags":
      return (
        <Frame field={field} flash={flash}>
          <TagsInput field={field} value={(value as string[]) ?? []} onChange={onChange} />
        </Frame>
      );
    case "json":
      return (
        <Frame field={field} flash={flash}>
          <textarea
            id={id}
            className="input textarea mono"
            rows={4}
            placeholder="JSON"
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
          />
        </Frame>
      );
  }
  return (
    <Frame field={field} flash={flash}>
      <input
        id={id}
        className="input"
        placeholder={placeholder}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    </Frame>
  );
}
