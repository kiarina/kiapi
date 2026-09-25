import { useRef, useState } from "react";

import { uploadFile, type FileRecord } from "../api";
import { Icon } from "../components/Icon";
import { Thumb, mediaKind } from "../components/ui";
import { sortedFiles, useData } from "../data";
import { bytes } from "../format";

export type Accept = "image" | "audio" | "video" | "any";

// Which files a FileRef field expects, from its name.
export function acceptFor(field: string): Accept {
  if (/image/.test(field)) return "image";
  if (field === "audio" || field === "source") return "audio";
  return "any";
}

const MIME: Record<Accept, string> = {
  image: "image/*",
  audio: "audio/*",
  video: "video/*",
  any: "",
};

function matches(file: FileRecord, accept: Accept): boolean {
  return accept === "any" || mediaKind(file.content_type) === accept;
}

export function FilePicker({
  accept,
  multiple,
  onPick,
  onClose,
}: {
  accept: Accept;
  multiple: boolean;
  onPick: (ids: string[]) => void;
  onClose: () => void;
}) {
  const { files } = useData();
  const [selected, setSelected] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string>();
  const input = useRef<HTMLInputElement>(null);
  const list = sortedFiles(files.data?.data).filter((f) => matches(f, accept));

  const toggle = (id: string) => {
    if (!multiple) {
      onPick([id]);
      return;
    }
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  };

  const upload = async (picked: FileList | null) => {
    if (!picked?.length) return;
    setUploading(true);
    setError(undefined);
    try {
      const recs = [];
      for (const f of Array.from(picked)) recs.push(await uploadFile(f, f.name));
      files.reload();
      onPick(recs.map((r) => r.file_id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="overlay" onClick={onClose}>
      <div className="card picker" role="dialog" aria-label="Choose a file" onClick={(e) => e.stopPropagation()}>
        <div className="card-head">
          <h2 className="card-title">Choose {multiple ? "files" : "a file"}</h2>
          <input
            ref={input}
            type="file"
            accept={MIME[accept]}
            multiple={multiple}
            hidden
            onChange={(e) => void upload(e.target.files)}
          />
          <button type="button" className="btn small" onClick={() => input.current?.click()} disabled={uploading}>
            <Icon name="upload" size={14} />
            {uploading ? "Uploading…" : "Upload from this device"}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
        <div className="picker-grid">
          {list.length === 0 && <div className="empty">No matching files yet. Upload one.</div>}
          {list.map((f) => (
            <button
              key={f.file_id}
              type="button"
              className={`tile-media picker-item${selected.includes(f.file_id) ? " on" : ""}`}
              onClick={() => toggle(f.file_id)}
            >
              <Thumb file={f} />
              <span className="cap">
                <b>{f.filename}</b>
                <span>{bytes(f.size)}</span>
              </span>
            </button>
          ))}
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button type="button" className="btn small" onClick={onClose}>
            Cancel
          </button>
          {multiple && (
            <button type="button" className="btn small primary" disabled={!selected.length} onClick={() => onPick(selected)}>
              Use {selected.length || ""} selected
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
