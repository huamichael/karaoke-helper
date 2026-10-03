/**
 * Vite config for the frontend dev server and build.
 *
 * Port 5173 is fixed (strictPort) because the backend's CORS allows only
 * http://localhost:5173. Docker passes --host 0.0.0.0 on the command line.
 *
 * Owner: A. Spec: docs/tasks/frontend.md.
 */
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true },
  preview: { port: 5173, strictPort: true },
});
