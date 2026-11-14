import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Inicie Bd - Troc.AI/api.py para encaminhar as chamadas /api ao backend Python.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:3001" } },
});
