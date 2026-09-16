import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { VitePWA } from "vite-plugin-pwa";

// In Docker the API is reachable as http://api:8000; locally as http://localhost:8000.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "icons/*.png", "icons/*.svg"],
      devOptions: { enabled: true },
      workbox: {
        // Authentication and API navigations belong to FastAPI. If Workbox's
        // SPA fallback handled them, an installed PWA would serve index.html
        // instead of letting a login round-trip reach the backend.
        navigateFallbackDenylist: [/^\/auth(?:\/|$)/, /^\/api(?:\/|$)/, /^\/storage(?:\/|$)/],
      },
      manifest: {
        name: "Rodiva",
        short_name: "Rodiva",
        description: "Gestão pessoal e familiar de veículos",
        lang: "pt-PT",
        theme_color: "#B94A22",
        background_color: "#F5F3EF",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icons/pwa-light-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
          { src: "/icons/pwa-light-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
          { src: "/icons/pwa-maskable-light-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
          { src: "/icons/pwa-maskable-light-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    allowedHosts: ["web"],
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
      "/auth": { target: apiTarget, changeOrigin: true },
      "/storage": { target: apiTarget, changeOrigin: true },
    },
  },
  preview: {
    port: 5173,
    allowedHosts: ["web"],
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
      "/auth": { target: apiTarget, changeOrigin: true },
      "/storage": { target: apiTarget, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
