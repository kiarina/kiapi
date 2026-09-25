import { useMemo, useState } from "react";

import type { SetupModel } from "../api";
import { Icon } from "../components/Icon";
import { Command, ErrorBox, Loading, PageHead } from "../components/ui";
import { useData } from "../data";
import { familyHref, groupFamilies } from "../families";
import { gb } from "../format";

type Filter = "all" | "ready" | "missing";

const COLUMNS = "160px 190px minmax(0, 1fr) 80px 110px";

export function Models() {
  const { setup } = useData();
  const [filter, setFilter] = useState<Filter>("all");
  const [openDomains, setOpenDomains] = useState<Record<string, boolean>>({});
  const models = setup.data?.data ?? [];
  const groups = useMemo(() => groupFamilies(models), [models]);
  const summary = setup.data?.summary;
  const missingCount = models.filter((m) => m.status === "missing").length;

  const visible = (m: SetupModel) =>
    filter === "all" || (filter === "missing" ? m.status === "missing" : m.status !== "missing");

  // Domains with something to set up start expanded.
  const isOpen = (domain: string, list: SetupModel[]) =>
    openDomains[domain] ?? (filter !== "all" || list.some((m) => m.status === "missing"));

  return (
    <>
      <PageHead
        title="Models"
        sub={
          summary ? (
            <span>
              {summary.models_ready} of {summary.models_total} models ready · {gb(summary.installed_gb)} of{" "}
              {gb(summary.total_gb)} installed. Setup runs in your terminal: copy a command, run it, then refresh.
            </span>
          ) : (
            <span>Setup runs in your terminal: copy a command, run it, then refresh.</span>
          )
        }
        actions={
          <>
            <Command text="kiapi check --all" />
            <button type="button" className="btn" onClick={setup.reload} disabled={setup.loading}>
              <Icon name="refresh" size={15} />
              {setup.loading ? "Checking…" : "Refresh"}
            </button>
          </>
        }
      />

      <div className="chips" role="group" aria-label="Filter models">
        {(
          [
            ["all", `All ${models.length}`],
            ["ready", `Ready ${models.length - missingCount}`],
            ["missing", `Not set up ${missingCount}`],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={`chip${filter === key ? " on" : ""}`}
            aria-pressed={filter === key}
            onClick={() => setFilter(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {setup.error && <ErrorBox error={setup.error} />}
      {!setup.data && setup.loading && <Loading label="Checking model resources. This can take a few seconds." />}

      {setup.data && (
        <div className="table">
          <div className="table-head hide-sm" style={{ gridTemplateColumns: COLUMNS }}>
            <span>Family</span>
            <span>Model</span>
            <span>Resources</span>
            <span className="num">Size</span>
            <span style={{ textAlign: "right" }}>Status</span>
          </div>
          {groups.map((g) => {
            const list = g.families.flatMap((f) => f.models).filter(visible);
            if (list.length === 0) return null;
            const open = isOpen(g.domain, list);
            const ready = list.filter((m) => m.status !== "missing").length;
            return (
              <div key={g.domain}>
                <button
                  type="button"
                  className={`group-head${open ? " open" : ""}`}
                  aria-expanded={open}
                  onClick={() => setOpenDomains((s) => ({ ...s, [g.domain]: !open }))}
                >
                  <Icon name={open ? "chevronDown" : "chevronRight"} size={14} />
                  <span className="label">{g.domain}</span>
                  <span className="grow">
                    <span className="hide-sm">{g.families.map((f) => f.family).join(", ")} · </span>
                    {ready} of {list.length} ready · {gb(list.reduce((n, m) => n + m.size_gb, 0))}
                  </span>
                  {ready === list.length ? (
                    <span className="badge ok">
                      <span className="dot ok" style={{ width: 6, height: 6 }} />
                      All ready
                    </span>
                  ) : (
                    <span className="badge muted">{list.length - ready} not set up</span>
                  )}
                </button>
                {open &&
                  g.families.map((f) =>
                    f.models.filter(visible).map((m, i) => (
                      <div key={`${m.family}/${m.name}`} className="table-row" style={{ gridTemplateColumns: COLUMNS }}>
                        <span style={{ fontWeight: 500 }}>
                          {i === 0 && <a href={familyHref(f.domain, f.family)} style={{ color: "var(--text)" }}>{f.family}</a>}
                        </span>
                        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span className="mono" style={{ fontSize: 12.5 }}>
                            {m.name}
                          </span>
                          {m.default && <span className="badge outline">default</span>}
                        </span>
                        <span className="wide" style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
                          {m.resources.length === 0 && <span className="muted small">No setup needed</span>}
                          {m.resources.map((r) =>
                            r.ready ? (
                              <span key={r.label} className="mono small muted" title={r.detail} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                {r.label}
                              </span>
                            ) : (
                              <Command key={r.label} text={r.activate_command} />
                            ),
                          )}
                        </span>
                        <span className="num push">{m.size_gb ? gb(m.size_gb) : "—"}</span>
                        <span className="end">
                          {m.status === "missing" ? (
                            <span className="badge muted">Not set up</span>
                          ) : (
                            <span className="badge ok">
                              <span className="dot ok" style={{ width: 6, height: 6 }} />
                              Ready
                            </span>
                          )}
                        </span>
                      </div>
                    )),
                  )}
              </div>
            );
          })}
        </div>
      )}

      <div className="small muted" style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
        Set up a whole family with <code className="inline-code">kiapi activate --family &lt;family&gt;</code>. Remove with{" "}
        <code className="inline-code">kiapi deactivate</code> and the same options.
      </div>
    </>
  );
}
