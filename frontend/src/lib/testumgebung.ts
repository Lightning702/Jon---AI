import { BASE } from "./api";
import { fehlerText } from "./version";

export interface Umgebung {
  id: string;
  name: string;
  modus: "maschine" | "ordner";
  erstellt: number;
  dateien: number;
  groesse: number;
  zustand: "bereit" | "richtet_ein" | "docker_aus" | string;
  pfad: string;
}

export interface DockerStand {
  installiert: boolean;
  laeuft: boolean;
}

export interface Lauf {
  befehl?: string;
  exit?: number | null;
  ausgabe?: string;
  dauer?: number;
  abgebrochen?: boolean;
  datei?: string;
  vorschau?: string;
  umgebung?: string;
}

export const AUSFUEHRBAR = new Set(["python", "py", "javascript", "js", "node", "php", "bash", "sh", "shell", "powershell", "ps1"]);
export const VORSCHAUBAR = new Set(["html", "htm", "svg"]);

const WURZEL = BASE.replace(/\/api$/, "");

async function anfrage<T>(pfad: string, optionen?: RequestInit): Promise<T> {
  const antwort = await fetch(`${BASE}/testumgebung${pfad}`, optionen);
  const daten = await antwort.json().catch(() => ({}));
  if (!antwort.ok) throw new Error(fehlerText(antwort.status, daten.detail));
  return daten as T;
}

function json(methode: string, koerper: unknown): RequestInit {
  return { method: methode, headers: { "Content-Type": "application/json" }, body: JSON.stringify(koerper) };
}

export const testumgebung = {
  liste: () => anfrage<{ umgebungen: Umgebung[]; docker: DockerStand }>(""),
  neu: (name: string, maschine?: boolean) => anfrage<Umgebung>("", json("POST", { name, maschine })),
  loeschen: (id: string) => anfrage<{ ok: boolean }>(`/${id}`, { method: "DELETE" }),
  zuruecksetzen: (id: string) => anfrage<Umgebung>(`/${id}/zuruecksetzen`, { method: "POST" }),
  beschreiben: (id: string) => anfrage<Umgebung>(`/${id}`),
  dateien: (id: string) => anfrage<{ id: string; dateien: { pfad: string; groesse: number }[] }>(`/${id}/dateien`),
  lesen: (id: string, pfad: string) => anfrage<{ pfad: string; inhalt: string }>(`/${id}/datei?pfad=${encodeURIComponent(pfad)}`),
  schreiben: (id: string, pfad: string, inhalt: string) => anfrage<{ ok: boolean; pfad: string }>(`/${id}/datei`, json("PUT", { pfad, inhalt })),
  ausfuehren: (id: string, befehl: string) => anfrage<Lauf>(`/${id}/ausfuehren`, json("POST", { befehl })),
  code: (id: string, sprache: string, code: string, dateiname = "") => anfrage<Lauf>(`/${id}/code`, json("POST", { sprache, code, dateiname })),
  dockerStarten: () => anfrage<{ ok: boolean; text: string }>("/docker/starten", { method: "POST" }),
};

export function vorschauAdresse(pfad: string): string {
  return pfad.startsWith("http") ? pfad : `${WURZEL}${pfad}`;
}

export function testumgebungOeffnen(id = "standard", datei = ""): void {
  window.dispatchEvent(new CustomEvent("jon:testumgebung", { detail: { id, datei } }));
}

export function dateinameFuer(sprache: string, code: string): string {
  const art = sprache.toLowerCase();
  const titel = /<title>([^<]{1,60})<\/title>/i.exec(code)?.[1];
  const basis = (titel || "").normalize("NFKD").replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-").toLowerCase().slice(0, 40);
  const endung: Record<string, string> = { html: "html", htm: "html", svg: "svg", python: "py", py: "py", javascript: "js", js: "js", node: "js", php: "php", bash: "sh", sh: "sh", shell: "sh", powershell: "ps1", ps1: "ps1", css: "css", json: "json", typescript: "ts", ts: "ts" };
  const ende = endung[art] || "txt";
  if (art === "html" || art === "htm") return `${basis || "index"}.html`;
  return `${basis || (ende === "py" ? "main" : ende === "php" ? "index" : "main")}.${ende}`;
}
