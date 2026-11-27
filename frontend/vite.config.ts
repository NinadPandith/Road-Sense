/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { createReadStream, readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig, type Plugin } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

/** Serve ONNX Runtime Web's WASM files from our own origin at /ort/ (no CDN needed, and the
 * service worker can cache them for Drive mode). */
function onnxRuntimeFiles(): Plugin {
  const dist = fileURLToPath(new URL('./node_modules/onnxruntime-web/dist/', import.meta.url))
  const files = readdirSync(dist).filter((f) => /^ort-wasm-simd-threaded(\.jsep)?\.(mjs|wasm)$/.test(f))
  return {
    name: 'onnxruntime-files',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const name = req.url?.startsWith('/ort/') ? req.url.slice(5).split('?')[0] : ''
        if (!files.includes(name)) return next()
        res.setHeader('Content-Type', name.endsWith('.wasm') ? 'application/wasm' : 'text/javascript')
        createReadStream(dist + name).pipe(res)
      })
    },
    generateBundle() {
      for (const f of files) this.emitFile({ type: 'asset', fileName: `ort/${f}`, source: readFileSync(dist + f) })
    },
  }
}

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    onnxRuntimeFiles(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon.svg'],
      manifest: {
        name: 'RoadSense',
        short_name: 'RoadSense',
        description: 'Report potholes in 30 seconds. RoadSense helps your city find and rank road damage.',
        theme_color: '#0f766e',
        background_color: '#f8fafc',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/models\//, /^\/ort\//],
        globPatterns: ['**/*.{js,css,html,svg,png}'],
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
        runtimeCaching: [
          {
            // The Drive-mode model: download once, then served from the phone.
            urlPattern: ({ url }) => url.pathname.startsWith('/models/'),
            handler: 'CacheFirst',
            options: { cacheName: 'models', expiration: { maxEntries: 4 } },
          },
          {
            urlPattern: ({ url }) => url.hostname.endsWith('tile.openstreetmap.org'),
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'tiles', expiration: { maxEntries: 300, maxAgeSeconds: 7 * 86400 } },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/ort/'),
            handler: 'CacheFirst',
            options: { cacheName: 'onnx-runtime', expiration: { maxEntries: 10 } },
          },
        ],
      },
    }),
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
})
