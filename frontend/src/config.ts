/**
 * Runtime configuration, read once from Vite's environment and the URL.
 *
 * | Variable              | Meaning                                    | Default               |
 * |-----------------------|--------------------------------------------|-----------------------|
 * | VITE_API_URL          | Backend address                            | http://localhost:8000 |
 * | VITE_SHOW_MODE_CHOICE | Sing opens into spoken / singing accuracy  | off (spoken)          |
 * | VITE_SHOW_COACH       | "Ask why" on the coach bubble              | off                   |
 *
 * Owner: A. Spec: docs/tasks/frontend.md, "Configuration".
 */

const flag = (v: string | undefined) => ["1", "true", "on", "yes"].includes((v ?? "").trim().toLowerCase());

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
export const SHOW_MODE_CHOICE = flag(import.meta.env.VITE_SHOW_MODE_CHOICE);
export const SHOW_COACH = flag(import.meta.env.VITE_SHOW_COACH);
