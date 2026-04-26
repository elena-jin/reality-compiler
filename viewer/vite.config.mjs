import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const DEFAULT_VIEWER_PORT = 4178;
const resolvedPort = Number.parseInt(
  process.env.VIEWER_PORT || process.env.GUI_PORT || process.env.PORT || "",
  10
);
const viewerPort = Number.isFinite(resolvedPort) ? resolvedPort : DEFAULT_VIEWER_PORT;

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname || ".", "."),
    },
  },
  server: {
    port: viewerPort,
    host: "0.0.0.0",
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
  },
});
