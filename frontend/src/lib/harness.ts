import { BASE } from "./api";

export interface HarnessTask {
  id: string;
  goal: string;
  root: string;
  source: string;
  status: string;
  step: number;
  steps: string[];
  summary: string;
  specialists?: { role: string; question: string; status: string; result?: string; error?: string }[];
  pending: null | { id: string; notice: string; args: { command: string; cwd: string; timeout: number } };
  changes: { path: string; diff: string }[];
  checks: { command: string; output: string; ok: boolean; exit_code: number; revision: number }[];
  log?: { time: number; type: string; tool: string; message: string }[];
}

export const finished = new Set(["done", "needs_review", "failed", "cancelled", "interrupted"]);
export const taskLabels: Record<string, string> = { planning: "Plant", working: "Arbeitet", verifying: "Prüft", waiting_approval: "Freigabe nötig", cancelling: "Stoppt", cancelled: "Gestoppt", interrupted: "Unterbrochen", done: "Abgeschlossen", needs_review: "Prüfung offen", failed: "Fehlgeschlagen" };

export async function harnessRequest<T>(path: string, body?: unknown, method?: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(BASE + path, { method: method || (body === undefined ? "GET" : "POST"), headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body), signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(20000)]) : AbortSignal.timeout(20000) });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = typeof data.detail === "string" ? data.detail : "";
    throw new Error(detail || (response.status === 401 ? "Verbindung zu Jon nicht autorisiert. Bitte die App neu öffnen." : response.status === 404 ? "Diese Funktion ist im laufenden Backend noch nicht verfügbar. Jon aus dem aktualisierten Projekt neu starten." : `Jon antwortet mit Fehler ${response.status}.`));
  }
  return response.json();
}
