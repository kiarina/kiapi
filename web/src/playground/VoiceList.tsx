import { useEffect, useState } from "react";

import { apiFetch, type ListEnvelope } from "../api";
import { Icon } from "../components/Icon";
import { CopyButton, ErrorBox } from "../components/ui";
import { ago, duration } from "../format";
import { useApi, useFileSrc, useNow } from "../hooks";
import { useToken } from "../session";

interface Voice {
  id: string;
  name: string | null;
  transcript: string | null;
  duration_s: number;
  created_at: number;
}

const VOICES = "/v1/audio/voices";

// Registered speech voices: listen, rename, fix the transcript, use, delete.
export function VoiceList({ version, onUse }: { version: number; onUse: (voiceId: string) => void }) {
  const voices = useApi<ListEnvelope<Voice>>(VOICES);
  const now = useNow(60_000);

  useEffect(() => {
    if (version > 0) voices.reload();
  }, [version]);

  const list = [...(voices.data?.data ?? [])].reverse();
  return (
    <section className="card voice-list">
      <div className="card-head">
        <h2 className="card-title">
          Registered voices <span className="muted small">{voices.data ? list.length : ""}</span>
        </h2>
        <button type="button" className="icon-btn" aria-label="Reload voices" onClick={voices.reload}>
          <Icon name="refresh" size={15} />
        </button>
      </div>
      {voices.error && <ErrorBox error={voices.error} />}
      {voices.data && list.length === 0 && (
        <div className="empty">No voices yet. Register one with the Voices form.</div>
      )}
      <div className="rows">
        {list.map((v) => (
          <VoiceRow key={v.id} voice={v} now={now} onUse={onUse} onChange={voices.reload} />
        ))}
      </div>
    </section>
  );
}

function VoiceRow({
  voice,
  now,
  onUse,
  onChange,
}: {
  voice: Voice;
  now: number;
  onUse: (voiceId: string) => void;
  onChange: () => void;
}) {
  const [listening, setListening] = useState(false);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(voice.name ?? "");
  const [transcript, setTranscript] = useState(voice.transcript ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error>();

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(undefined);
    try {
      await action();
      onChange();
      return true;
    } catch (e) {
      setError(e as Error);
      return false;
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    const ok = await run(() =>
      apiFetch(`${VOICES}/${voice.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, transcript }),
      }),
    );
    if (ok) setEditing(false);
  };

  const remove = () => {
    if (!window.confirm(`Delete the voice "${voice.name ?? voice.id}"? This cannot be undone.`)) return;
    void run(() => apiFetch(`${VOICES}/${voice.id}`, { method: "DELETE" }));
  };

  const startEdit = () => {
    setName(voice.name ?? "");
    setTranscript(voice.transcript ?? "");
    setEditing(true);
  };

  return (
    <div className="row voice-row">
      <div className="voice-head">
        <span className="voice-name">{voice.name ?? <span className="muted">Unnamed</span>}</span>
        <span className="mono small muted">
          {duration(voice.duration_s)} · {ago(voice.created_at, now)}
        </span>
        <span className="mono small muted voice-id">{voice.id}</span>
      </div>

      {editing ? (
        <div className="voice-edit">
          <label className="field">
            <span className="field-label">Name</span>
            <input className="input" value={name} maxLength={200} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Transcript</span>
            <textarea
              className="input textarea"
              rows={3}
              value={transcript}
              maxLength={2000}
              onChange={(e) => setTranscript(e.target.value)}
            />
          </label>
        </div>
      ) : (
        <p className={`voice-transcript${voice.transcript ? "" : " muted"}`}>
          {voice.transcript ?? "No transcript: cloned from the speaker embedding only."}
        </p>
      )}

      {listening && <VoiceAudio voiceId={voice.id} />}
      {error && <ErrorBox error={error} />}

      <div className="pg-actions">
        {editing ? (
          <>
            <button type="button" className="btn small primary" disabled={busy} onClick={() => void save()}>
              Save
            </button>
            <button type="button" className="btn small" disabled={busy} onClick={() => setEditing(false)}>
              Cancel
            </button>
          </>
        ) : (
          <>
            <button type="button" className="btn small primary" onClick={() => onUse(voice.id)}>
              <Icon name="play" size={13} />
              Use in Speech
            </button>
            <button type="button" className={`btn small${listening ? " on" : ""}`} onClick={() => setListening((x) => !x)}>
              <Icon name="audio" size={14} />
              {listening ? "Hide reference" : "Listen"}
            </button>
            <CopyButton text={voice.id} label="Copy id" />
            <button type="button" className="btn small" onClick={startEdit}>
              Edit
            </button>
            <button type="button" className="btn small voice-delete" disabled={busy} onClick={remove}>
              <Icon name="x" size={13} />
              Delete
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function VoiceAudio({ voiceId }: { voiceId: string }) {
  const token = useToken();
  const src = useFileSrc(`${VOICES}/${voiceId}/audio`, token);
  if (!src) return <div className="small muted">Loading the reference…</div>;
  return <audio className="voice-audio" src={src} controls autoPlay />;
}
