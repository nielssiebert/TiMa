import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

function resolveBasePath(configured: string | undefined): string {
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
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    base: resolveBasePath(env.VITE_PUBLIC_BASE_PATH),
    plugins: [
      vue(),
      vueDevTools(),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
    },
  }
})
