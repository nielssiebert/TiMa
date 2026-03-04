export type AppProfile = 'local' | 'production'

interface AppConfig {
  appTitle: string
  profile: AppProfile
  apiBaseUrl: string
  overviewRefreshMs: {
    default: number
    byApiPath: Record<string, number>
  }
}

function resolveProfile(): AppProfile {
  return import.meta.env.VITE_APP_PROFILE === 'production' ? 'production' : 'local'
}

function parsePositiveInt(value: string | undefined, fallback: number): number {
  if (!value) {
    return fallback
  }
  const parsed = Number.parseInt(value, 10)
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback
  }
  return parsed
}

export const appConfig: AppConfig = {
  appTitle: import.meta.env.VITE_APP_TITLE ?? 'Letrain',
  profile: resolveProfile(),
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api',
  overviewRefreshMs: {
    default: parsePositiveInt(import.meta.env.VITE_OVERVIEW_REFRESH_DEFAULT_MS, 5000),
    byApiPath: {
      '/execution-events': parsePositiveInt(import.meta.env.VITE_OVERVIEW_REFRESH_EXECUTION_EVENTS_MS, 1000),
      '/sequences': parsePositiveInt(import.meta.env.VITE_OVERVIEW_REFRESH_SEQUENCES_MS, 2000),
    },
  },
}
