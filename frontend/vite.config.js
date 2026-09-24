import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
      vue(),
      tailwindcss(),
      VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'pwa-192x192.png', 'pwa-512x512.png'],
      workbox: {
        cleanupOutdatedCaches: true
      },
      manifest: {
        name: 'TJSB Tabule',
        short_name: 'TJSB Tabule',
        description: 'Ovládací panel pro sportovní tabuli',
        theme_color: '#4f46e5',
        background_color: '#f3f4f6',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      }
    })
  ],
  server: {
    host: true,
    port: 4173,
    strictPort: true,
    proxy: {
      // Forward all REST HTTP requests to /api to Python
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // Forward all WebSocket requests to /ws to Python as well
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      }
    }
  }
})