import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The built UI ships inside the Python package so `pip install whorl` serves
// it with no Node toolchain. `base: "./"` keeps asset paths relative.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../whorl/web",
    emptyOutDir: true,
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:8010" },
  },
});
