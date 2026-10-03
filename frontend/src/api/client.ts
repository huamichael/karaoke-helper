/**
 * API client.
 *
 * Typed wrappers for the three calls the app makes: list songs, get one song, and
 * submit a recording for grading (multipart POST /api/v1/attempts).
 *
 * The type names below are aliases of the generated types in ./types.ts; nothing
 * here describes a shape by hand.
 *
 * Owner: A. Spec: docs/contracts/api.md.
 */
import { API_URL } from "../config";
import type { components } from "./types";

type Schemas = components["schemas"];
export type SongSummary = Schemas["SongSummary"];
export type Song = Schemas["Song"];
export type Line = Schemas["Line"];
export type Syllable = Schemas["LyricSyllable"];
export type Word = Schemas["Word"];
export type AttemptResult = Schemas["AttemptResult"];
export type WordResult = Schemas["WordResult"];
export type SyllableResult = Schemas["SyllableResult"];
export type Part = Schemas["Part"];
export type Scores = Schemas["Scores"];
export type NextStep = AttemptResult["next_step"];
export type Status = WordResult["status"];
export type Mode = NonNullable<AttemptResult["mode"]>;

/** Grading takes a few seconds; give up after this long. */
export const ATTEMPT_TIMEOUT_MS = 20_000;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number | null,
  ) {
    super(message);
  }
}

/** Track and word clips come back as paths on the backend ("/media/..."). */
export function mediaUrl(url: string): string {
  return /^(https?:|blob:|data:)/.test(url) ? url : `${API_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = 10_000): Promise<T> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  const outer = init.signal;
  outer?.addEventListener("abort", () => ctl.abort(), { once: true });
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, signal: ctl.signal });
  } catch (e) {
    if (outer?.aborted) throw new ApiError("Cancelled.", "cancelled", null);
    if (ctl.signal.aborted) throw new ApiError("The grader took too long to answer.", "timeout", null);
    throw new ApiError(`We couldn't reach the backend at ${API_URL}.`, "network", null);
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as Schemas["ErrorBody"] | null;
    throw new ApiError(body?.error.message ?? `Request failed (${res.status}).`, body?.error.code ?? "http_error", res.status);
  }
  return (await res.json()) as T;
}

export const listSongs = (signal?: AbortSignal) => request<SongSummary[]>("/api/v1/songs", { signal });

export const getSong = (id: string, signal?: AbortSignal) =>
  request<Song>(`/api/v1/songs/${encodeURIComponent(id)}`, { signal });

export type AttemptTarget =
  | { target: "line"; songId: string; lineIndex: number; mode: Mode }
  | { target: "word"; songId: string; lineIndex: number; wordIndex: number };

function fileName(blob: Blob): string {
  if (blob.type.includes("mp4")) return "attempt.mp4";
  if (blob.type.includes("wav")) return "attempt.wav";
  if (blob.type.includes("ogg")) return "attempt.ogg";
  return "attempt.webm";
}

export function submitAttempt(audio: Blob, t: AttemptTarget, signal?: AbortSignal): Promise<AttemptResult> {
  const form = new FormData();
  form.append("audio", audio, fileName(audio));
  form.append("song_id", t.songId);
  form.append("line_index", String(t.lineIndex));
  form.append("target", t.target);
  if (t.target === "line") form.append("mode", t.mode);
  else form.append("word_index", String(t.wordIndex));
  return request<AttemptResult>("/api/v1/attempts", { method: "POST", body: form, signal }, ATTEMPT_TIMEOUT_MS);
}
