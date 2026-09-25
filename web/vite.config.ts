import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// `pnpm dev` proxies API calls to a running kiapi (default: `make dev`).
const target = process.env.KIAPI_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../src/kiapi/api/ui/static",
    emptyOutDir: true,
    assetsDir: "_ui",
  },
  server: {
    proxy: {
      "/v1": target,
      "/health": target,
      "/openapi.json": target,
    },
  },
});
