import { version as OBERFLAECHE } from "../../package.json";

export const OBERFLAECHE_VERSION = OBERFLAECHE;

export const NEUSTART_HINWEIS = "Diese Funktion kennt dein laufendes Jon-Backend noch nicht. Starte Jon einmal neu, dann geht sie.";

function teile(text: string): number[] {
  return String(text || "").split(".").map((t) => parseInt(t, 10) || 0);
}

export function aelterAls(links: string, rechts: string): boolean {
  const a = teile(links);
  const b = teile(rechts);
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    if ((a[i] ?? 0) !== (b[i] ?? 0)) return (a[i] ?? 0) < (b[i] ?? 0);
  }
  return false;
}

export function backendVeraltet(backend: string): boolean {
  return !!backend && aelterAls(backend, OBERFLAECHE_VERSION);
}

export function fehlerText(status: number, detail: unknown): string {
  const text = typeof detail === "string" ? detail : "";
  if (status === 404 && (!text || text === "Not Found")) return NEUSTART_HINWEIS;
  return text || `Jon antwortet mit Fehler ${status}.`;
}
