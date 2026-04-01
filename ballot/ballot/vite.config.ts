import { defineConfig } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
  base: "/static/ballot/",
  build: {
    outDir: path.resolve(__dirname, '../static/ballot/'),
    emptyOutDir: false,
    manifest: "manifest.json",
  },
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] }),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    cors: {
      origin: "*", // Allow all origins in dev to bypass the proxy CORS issues
      methods: "GET,OPTIONS",
      allowedHeaders: "Content-Type,Authorization",
    },
  }
})
