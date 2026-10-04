/**
 * Runtime configuration, read once from Vite's environment and the URL.
 *
 * | Variable            | Meaning                                         | Default               |
 * |---------------------|-------------------------------------------------|-----------------------|
 * | VITE_API_URL        | Backend address                                 | http://localhost:8000 |
 * | VITE_SINGING_READY  | Singing accuracy can be chosen and sung         | off ("not ready yet") |
 * | VITE_SHOW_COACH     | "Ask why" on the coach bubble                   | off                   |
 *
 * Sing always opens into Spoken accuracy and Singing accuracy. VITE_SHOW_MODE_CHOICE
 * (docs/tasks/frontend.md, compose.yaml) no longer hides the choice.
 *
 * Owner: A. Spec: docs/tasks/frontend.md, "Configuration".
 */

const flag = (v: string | undefined) => ["1", "true", "on", "yes"].includes((v ?? "").trim().toLowerCase());

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

// TODO(backend): singing accuracy waits for the backend's CTC and rhythm layers (ENABLE_CTC=1,
// ENABLE_RHYTHM=1 after checkpoint B, docs/tasks/backend-ctc-rhythm.md). Until then choosing it says
// "not ready yet"; once they are on, set VITE_SINGING_READY=1 (or flip this default) to let it start.
export const SINGING_READY = flag(import.meta.env.VITE_SINGING_READY);
export const SHOW_COACH = flag(import.meta.env.VITE_SHOW_COACH);
