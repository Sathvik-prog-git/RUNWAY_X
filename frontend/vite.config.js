import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the FastAPI backend (see backend/main.py, Step 2).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // the backend only accepts requests from http://localhost:5173 — fail loudly instead of switching ports
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
});
