/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    // Recharts alone is about 550 kB. It sits in its own chunk so the app code stays small.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: { manualChunks: { charts: ["recharts"] } },
    },
  },
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
