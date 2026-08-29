import { BASE } from "./api";
import { withToken } from "./token";

export type ResearchStatus =
  | "planung"
  | "laeuft"
  | "pausiert"
  | "fertig"
  | "abgebrochen"
  | "unterbrochen"
  | "fehler";

export interface ResearchLogEntry {
  ts: number;
  kind: string;
  icon: string;
  title: string;
  detail: string;
}

export interface ResearchSource {
  url: string;
  title: string;
  domain: string;
  status: string;
  chars: number;
  subtopic: string;
  summary: string;
  reason: string;
  fetched_at: number;
}

export interface ResearchSubtopic {
  id: string;
  title: string;
  question: string;
  importance: number;
  status: string;
  file: string;
  sources: string[];
  findings: string;
  conflicts: string[];
  confidence: string;
}

export interface ResearchTask {
  id: string;
  thema: string;
  slug: string;
  titel: string;
  zusammenfassung: string;
  minuten: number;
  tiefe: string;
  provider: string;
  model: string;
  status: ResearchStatus;
  phase: string;
  erstellt_at: number;
  gestartet_at: number;
  beendet_at: number;
  verbraucht_s: number;
  verbleibend_s: number;
  fortschritt: number;
  aktuelles_thema: string;
  unterthemen: ResearchSubtopic[];
  quellen: ResearchSource[];
  protokoll: ResearchLogEntry[];
  dateien: string[];
  skill: string;
  fehler: string;
  ordner: string;
}

export interface ResearchSummary {
  id: string;
  thema: string;
  titel: string;
  slug: string;
  status: ResearchStatus;
  minuten: number;
  verbraucht_s: number;
  fortschritt: number;
  quellen: number;
  dateien: number;
  skill: string;
  erstellt_at: number;
  beendet_at: number;
  unterthemen: number;
}

export const ACTIVE_STATES: ResearchStatus[] = ["planung", "laeuft", "pausiert"];

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export function listResearch(): Promise<{
  aufgaben: ResearchSummary[];
  aktiv: ResearchTask[];
}> {
  return json(`${BASE}/research/tasks`);
}

export function startResearch(
  topic: string,
  minutes = 0,
  depth: "schnell" | "normal" | "tief" = "normal"
): Promise<ResearchTask> {
  return json(`${BASE}/research/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, minutes, depth }),
  });
}

export function getResearch(id: string): Promise<ResearchTask> {
  return json(`${BASE}/research/tasks/${id}`);
}

export function controlResearch(
  id: string,
  action: "pause" | "resume" | "stop" | "resume_task"
): Promise<ResearchTask> {
  return json(`${BASE}/research/tasks/${id}/control`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
}

export function deleteResearch(id: string): Promise<{ deleted: boolean }> {
  return json(`${BASE}/research/tasks/${id}`, { method: "DELETE" });
}

export function researchFiles(
  id: string
): Promise<{ dateien: { name: string; chars: number; geaendert: string }[] }> {
  return json(`${BASE}/research/tasks/${id}/files`);
}

export function researchFile(
  id: string,
  name: string
): Promise<{ name: string; inhalt: string }> {
  return json(`${BASE}/research/tasks/${id}/files/${encodeURIComponent(name)}`);
}

export function watchResearch(
  id: string,
  onUpdate: (task: ResearchTask) => void
): () => void {
  const source = new EventSource(
    withToken(`${BASE}/research/tasks/${id}/stream`)
  );
  source.onmessage = (event) => {
    try {
      onUpdate(JSON.parse(event.data) as ResearchTask);
    } catch {
      return;
    }
  };
  source.onerror = () => source.close();
  return () => source.close();
}

export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = total % 60;
  return [hours, minutes, rest]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}

export function formatSpan(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${String(minutes % 60).padStart(2, "0")}m`;
}

export const STATUS_LABELS: Record<ResearchStatus, string> = {
  planung: "Plant",
  laeuft: "Läuft",
  pausiert: "Pausiert",
  fertig: "Abgeschlossen",
  abgebrochen: "Abgebrochen",
  unterbrochen: "Unterbrochen",
  fehler: "Fehler",
};
