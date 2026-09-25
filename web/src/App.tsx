import { useEffect, useState } from "react";

import { setToken } from "./api";
import { Icon } from "./components/Icon";
import { Sidebar } from "./components/Sidebar";
import { DataProvider } from "./data";
import { useRoute } from "./hooks";
import { Family } from "./pages/Family";
import { FileDetail, Files } from "./pages/Files";
import { JobDetail, Jobs } from "./pages/Jobs";
import { Models } from "./pages/Models";
import { Overview } from "./pages/Overview";
import { applyTheme, initialTheme, useToken, type Theme } from "./session";

function Page({ route }: { route: string[] }) {
  const [section, a, b, c] = route;
  switch (section) {
    case undefined:
      return <Overview />;
    case "models":
      return <Models />;
    case "jobs":
      return a ? <JobDetail id={a} /> : <Jobs />;
    case "files":
      return a ? <FileDetail id={a} /> : <Files />;
    case "f":
      if (a && b) return <Family domain={a} family={b} tab={c === "api" || c === "guide" ? c : "playground"} />;
      break;
  }
  return <div className="card empty">Page not found. <a href="#/">Go to overview</a></div>;
}

function TokenDialog({ onClose }: { onClose: () => void }) {
  const current = useToken();
  const [value, setValue] = useState(current);
  return (
    <div className="overlay" onClick={onClose}>
      <form
        className="card dialog"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          setToken(value.trim());
          onClose();
          window.location.reload();
        }}
      >
        <h2 className="card-title">Access token</h2>
        <p className="small muted" style={{ margin: 0 }}>
          Needed only when the server sets <code className="inline-code">auth_token</code>. It is kept in this
          browser and sent as a Bearer token.
        </p>
        <label className="small" style={{ display: "flex", flexDirection: "column", gap: 6, fontWeight: 500 }}>
          Token
          <input
            className="input mono"
            type="password"
            autoComplete="off"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
          />
        </label>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button type="button" className="btn small" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn small primary">
            Save
          </button>
        </div>
      </form>
    </div>
  );
}

export function App() {
  const route = useRoute();
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [menuOpen, setMenuOpen] = useState(false);
  const [tokenOpen, setTokenOpen] = useState(false);

  useEffect(() => {
    applyTheme(theme, false);
  }, [theme]);
  useEffect(() => {
    const open = () => setTokenOpen(true);
    window.addEventListener("kiapi:unauthorized", open);
    return () => window.removeEventListener("kiapi:unauthorized", open);
  }, []);
  useEffect(() => {
    window.scrollTo(0, 0);
    setMenuOpen(false);
  }, [route.join("/")]);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    applyTheme(next, true);
    setTheme(next);
  };

  return (
    <DataProvider>
      <div className="topbar">
        <button type="button" className="icon-btn menu-button" aria-label="Open menu" onClick={() => setMenuOpen(true)}>
          <Icon name="menu" size={18} />
        </button>
        <a href="#/" style={{ color: "var(--text)", fontWeight: 600, fontSize: 16 }}>
          kiapi
        </a>
      </div>
      <div className="shell">
        <Sidebar
          route={route}
          open={menuOpen}
          theme={theme}
          onToggleTheme={toggleTheme}
          onOpenToken={() => setTokenOpen(true)}
        />
        {menuOpen && <div className="overlay" style={{ zIndex: 25 }} onClick={() => setMenuOpen(false)} />}
        <main className="main">
          <Page route={route} />
        </main>
      </div>
      {tokenOpen && <TokenDialog onClose={() => setTokenOpen(false)} />}
    </DataProvider>
  );
}
