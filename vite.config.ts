import { defineConfig, loadEnv } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'

function normalizeBackendUrl(raw: string | undefined) {
  if (!raw) {
    return 'http://localhost:8000'
  }

  const trimmed = raw.trim()

  if (!trimmed) {
    return 'http://localhost:8000'
  }

  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed
  }

  return `http://${trimmed}`
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = normalizeBackendUrl(env.BACKEND_URL)

  return {
    envPrefix: ['VITE_', 'BACKEND_'],
    plugins: [react(), babel({ presets: [reactCompilerPreset()] })],
    server: {
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
  }
})
