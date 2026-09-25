import { createContext, useContext, type ReactNode } from "react";

import type { FileRecord, Health, Job, ListEnvelope, Setup } from "./api";
import { useApi, type Remote } from "./hooks";

interface Data {
  health: Remote<Health>;
  setup: Remote<Setup>;
  jobs: Remote<ListEnvelope<Job>>;
  files: Remote<ListEnvelope<FileRecord>>;
}

const DataContext = createContext<Data | null>(null);

// Shared server state, polled once for every page.
export function DataProvider({ children }: { children: ReactNode }) {
  const value: Data = {
    health: useApi<Health>("/health", 3000),
    // Setup checks run local commands, so it is fetched on demand only.
    setup: useApi<Setup>("/v1/setup"),
    jobs: useApi<ListEnvelope<Job>>("/v1/jobs", 2000),
    files: useApi<ListEnvelope<FileRecord>>("/v1/files", 10000),
  };
  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useData(): Data {
  const data = useContext(DataContext);
  if (!data) throw new Error("useData outside DataProvider");
  return data;
}

export function sortedJobs(jobs: Job[] | undefined): Job[] {
  return [...(jobs ?? [])].sort((a, b) => b.created_at - a.created_at);
}

export function sortedFiles(files: FileRecord[] | undefined): FileRecord[] {
  return [...(files ?? [])].sort((a, b) => b.created_at - a.created_at);
}
