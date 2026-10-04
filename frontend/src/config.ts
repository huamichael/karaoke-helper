/**
 * Runtime configuration, read once from Vite's environment and the URL.
 *
 * | Variable            | Meaning                                         | Default               |
 * |---------------------|-------------------------------------------------|-----------------------|
 * | VITE_API_URL        | Backend address                                 | http://localhost:8000 |
 * | VITE_SHOW_COACH     | "Ask why" on the coach bubble                   | off                   |
 *
 * Sing always opens into Practice mode and Karaoke mode. VITE_SHOW_MODE_CHOICE
 * (compose.yaml) and VITE_SINGING_READY are no longer read.
 *
 * Owner: A. Spec: docs/tasks/frontend.md, "Configuration".
 */

const flag = (v: string | undefined) => ["1", "true", "on", "yes"].includes((v ?? "").trim().toLowerCase());

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export const SHOW_COACH = flag(import.meta.env.VITE_SHOW_COACH);
