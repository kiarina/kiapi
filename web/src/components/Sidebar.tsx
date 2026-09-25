import { useMemo } from "react";

import { useData } from "../data";
import { displayTitle, familyHref, groupFamilies, useSpecs } from "../families";
import type { Theme } from "../session";
import { Icon } from "./Icon";

interface Props {
  route: string[];
  open: boolean;
  theme: Theme;
  onToggleTheme: () => void;
  onOpenToken: () => void;
}

export function Sidebar({ route, open, theme, onToggleTheme, onOpenToken }: Props) {
  const { health, setup, jobs, files } = useData();
  const groups = useMemo(() => groupFamilies(setup.data?.data ?? []), [setup.data]);
  const specs = useSpecs(useMemo(() => groups.flatMap((g) => g.families), [groups]));

  const section = route[0] ?? "";
  const activeFamily = section === "f" ? route[2] : undefined;
  const active = (key: string) => (section === key ? " active" : "");
  const busy = (jobs.data?.data ?? []).filter((j) => j.status === "running" || j.status === "queued");
  const runningTypes = new Set(busy.map((j) => j.type));
  const summary = setup.data?.summary;
  const warm = health.data?.warm;

  return (
    <nav className={`sidebar${open ? " open" : ""}`} aria-label="Main">
      <a className="brand" href="#/">
        <span className="brand-mark">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 2.5v11" />
            <path d="M12 3 6.5 8.2 12 13" />
          </svg>
        </span>
        kiapi
      </a>

      <div className="server-pill" title={health.error ? health.error.message : undefined}>
        <span className={`dot ${health.error ? "fail" : warm ? "ok ring" : "warn ring pulse"}`} />
        <span className="host">{window.location.host}</span>
        <span className="small" style={{ color: health.error ? "var(--fail)" : warm ? "var(--ok-text)" : "var(--text-3)", fontWeight: 500 }}>
          {health.error ? "offline" : warm ? "warm" : "warming"}
        </span>
      </div>

      <div className="nav">
        <a className={`nav-item${section === "" ? " active" : ""}`} href="#/">
          <Icon name="overview" />
          <span className="grow">Overview</span>
        </a>
        <a className={`nav-item${active("models")}`} href="#/models">
          <Icon name="models" />
          <span className="grow">Models</span>
          {summary && (
            <span className="nav-meta">
              {summary.models_ready}/{summary.models_total}
            </span>
          )}
        </a>
        <a className={`nav-item${active("jobs")}`} href="#/jobs">
          <Icon name="jobs" />
          <span className="grow">Jobs</span>
          {busy.length > 0 && <span className="nav-badge">{busy.length}</span>}
        </a>
        <a className={`nav-item${active("files")}`} href="#/files">
          <Icon name="files" />
          <span className="grow">Files</span>
          {files.data && <span className="nav-meta">{files.data.data.length}</span>}
        </a>
      </div>

      <div className="divider" />

      <div className="nav-groups">
        {groups.map((g) => (
          <div key={g.domain} className="nav">
            <div className="nav-group-label">{g.domain}</div>
            {g.families.map((f) => {
              const ready = f.models.filter((m) => m.status !== "missing").length;
              const dot = runningTypes.has(f.family) ? "dot run pulse" : ready < f.models.length ? "dot warn" : "dot";
              return (
                <a
                  key={f.family}
                  className={`nav-item small${activeFamily === f.family ? " active" : ""}`}
                  href={familyHref(f.domain, f.family)}
                >
                  <span className={dot} style={{ width: 6, height: 6 }} />
                  <span className="grow">{displayTitle(specs[f.family], f.family)}</span>
                  <span className="nav-meta">
                    {ready < f.models.length ? `${ready}/${f.models.length}` : f.models.length}
                  </span>
                </a>
              );
            })}
          </div>
        ))}
        {setup.loading && !setup.data && <div className="nav-group-label">Loading families…</div>}
      </div>

      <div className="sidebar-foot">
        <a className="nav-item small" href="/docs" style={{ flex: 1 }}>
          <Icon name="book" size={15} />
          <span className="grow">API reference</span>
        </a>
        <button type="button" className="icon-btn" aria-label="Access token" onClick={onOpenToken}>
          <Icon name="key" />
        </button>
        <button
          type="button"
          className="icon-btn"
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          onClick={onToggleTheme}
        >
          <Icon name={theme === "dark" ? "sun" : "moon"} />
        </button>
      </div>
    </nav>
  );
}
