import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon-192.svg", "icon-512.svg"],
      manifest: {
        name: "Mosquera Finance",
        short_name: "Mosquera",
        description: "Finanzas familiares privadas.",
        theme_color: "#07111f",
        background_color: "#07111f",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "icon-192.svg", sizes: "192x192", type: "image/svg+xml", purpose: "any" },
          { src: "icon-512.svg", sizes: "512x512", type: "image/svg+xml", purpose: "any" }
        ]
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg}"],
        navigateFallbackDenylist: [/^\/api(?:\/|$)/],
        runtimeCaching: [
          {
            urlPattern: /\/api(?:\/|$)/,
            handler: "NetworkOnly",
            method: "GET"
          }
        ]
      }
    })
  ],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true
      }
    }
  }
});
