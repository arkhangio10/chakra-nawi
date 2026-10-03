import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import basicSsl from '@vitejs/plugin-basic-ssl';
import { VitePWA } from 'vite-plugin-pwa';
import { copyFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';

const require = createRequire(import.meta.url);

// Hilos de WebAssembly: exigen aislamiento de origen cruzado (COOP + COEP).
const AISLAMIENTO = {
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Embedder-Policy': 'require-corp',
};

/** Copia el runtime WASM de onnxruntime-web a public/ort/: se sirve desde el propio dominio y entra al precache. */
function copiarOrt(): Plugin {
  return {
    name: 'copiar-ort',
    buildStart() {
      const dist = dirname(require.resolve('onnxruntime-web/ort-wasm-simd-threaded.wasm'));
      const destino = resolve(import.meta.dirname, 'public/ort');
      mkdirSync(destino, { recursive: true });
      for (const f of ['ort-wasm-simd-threaded.wasm', 'ort-wasm-simd-threaded.mjs']) copyFileSync(resolve(dist, f), resolve(destino, f));
    },
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [
    copiarOrt(),
    react(),
    ...(mode === 'lan' ? [basicSsl()] : []),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icono.svg'],
      manifest: {
        name: 'Chakra Ñawi',
        short_name: 'Chakra Ñawi',
        description: 'Triaje de la chacra de café, sin internet.',
        lang: 'es-PE',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#f4f1e8',
        theme_color: '#1f5135',
        icons: [
          { src: 'icono-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icono-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icono-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Todo lo que necesita el triaje offline: app, runtime WASM, modelo, audios, fichas.
        globPatterns: ['**/*.{js,css,html,svg,png,woff2,json,onnx,wasm,mjs,opus}'],
        // El límite por defecto (2 MiB) deja fuera el modelo y el WASM.
        maximumFileSizeToCacheInBytes: 40 * 1024 * 1024,
        // onnxruntime-web se carga desde /ort/; la copia que Vite emite en /assets/ no se precachea (14 MB duplicados).
        globIgnores: ['assets/ort-wasm*'],
        navigateFallback: 'index.html',
      },
    }),
  ],
  server: {
    headers: AISLAMIENTO,
    fs: { allow: [resolve(import.meta.dirname, '../..')] },
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, '') } },
  },
  preview: {
    headers: AISLAMIENTO,
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, '') } },
  },
  test: {
    environment: 'jsdom',
  },
}));
