import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // Relative base so the built bundle works from any subdirectory — GitHub
  // Pages, an internal file server, or straight off disk. The hub has no
  // backend, so there is no origin to be absolute about.
  base: "./",
  server: { port: 5173 },
});
