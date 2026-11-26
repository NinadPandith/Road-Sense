/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_SUPABASE_URL?: string
  readonly VITE_SUPABASE_ANON_KEY?: string
  readonly VITE_PILOT_AREA_NAME?: string
  readonly VITE_MAP_CENTER?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
