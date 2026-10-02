import {defineConfig} from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({root: "mobile", base: "./", plugins: [react()], build: {outDir: "../mobile-dist", emptyOutDir: true, target: "es2020", chunkSizeWarningLimit: 1200}});
