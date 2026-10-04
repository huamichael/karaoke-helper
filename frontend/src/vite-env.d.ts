/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_SHOW_MODE_CHOICE?: string;
  readonly VITE_SHOW_COACH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
