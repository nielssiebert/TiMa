/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_APP_TITLE?: string
	readonly VITE_APP_PROFILE?: 'local' | 'production'
	readonly VITE_API_BASE_URL?: string
	readonly VITE_OVERVIEW_REFRESH_DEFAULT_MS?: string
	readonly VITE_OVERVIEW_REFRESH_EXECUTION_EVENTS_MS?: string
	readonly VITE_OVERVIEW_REFRESH_SEQUENCES_MS?: string
}

interface ImportMeta {
	readonly env: ImportMetaEnv
}
