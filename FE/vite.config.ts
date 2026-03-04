import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

function resolveBasePath(): string {
  const configured = process.env.VITE_PUBLIC_BASE_PATH
  if (!configured) {
    return '/'
  }
  const trimmed = configured.trim()
  if (!trimmed || trimmed === '/') {
    return '/'
  }
  const prefixed = trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  return prefixed.endsWith('/') ? prefixed : `${prefixed}/`
}

// https://vite.dev/config/
export default defineConfig({
  base: resolveBasePath(),
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
