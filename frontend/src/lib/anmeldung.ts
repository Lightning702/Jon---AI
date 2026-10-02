import { BASE } from "./api";

export const SUPPORT_URL = "https://felworks-impressum.netlify.app/support";

export interface AnmeldeStand {
  eingerichtet: boolean;
  gesperrt_sekunden: number;
  support: string;
  mindestens: { benutzername: number; passwort: number };
}

export type AnmeldeAntwort =
  | { ok: true }
  | {
      ok: false;
      status: number;
      text: string;
      versucheUebrig?: number;
      sekunden?: number;
    };

export class StandFehler extends Error {
  constructor(public status: number) {
    super(`status ${status}`);
  }
}

let aktuell = "";

export function angemeldeterName(): string {
  return aktuell;
}

export async function anmeldeStand(): Promise<AnmeldeStand> {
  const res = await fetch(`${BASE}/anmeldung`);
  if (!res.ok) throw new StandFehler(res.status);
  return res.json();
}

async function senden(pfad: string, daten: Record<string, string>): Promise<AnmeldeAntwort> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/anmeldung/${pfad}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(daten),
    });
  } catch {
    return { ok: false, status: 0, text: "Jon ist gerade nicht erreichbar." };
  }
  const inhalt = await res.json().catch(() => ({}));
  if (res.ok) return { ok: true };
  return {
    ok: false,
    status: res.status,
    text: String(inhalt.detail || "Das hat nicht geklappt."),
    versucheUebrig:
      typeof inhalt.versuche_uebrig === "number" ? inhalt.versuche_uebrig : undefined,
    sekunden: typeof inhalt.sekunden === "number" ? inhalt.sekunden : undefined,
  };
}

export async function zugangEinrichten(
  benutzername: string,
  passwort: string
): Promise<AnmeldeAntwort> {
  const antwort = await senden("einrichten", { benutzername, passwort });
  if (antwort.ok) aktuell = benutzername.trim();
  return antwort;
}

export async function anmelden(
  benutzername: string,
  passwort: string
): Promise<AnmeldeAntwort> {
  const antwort = await senden("pruefen", { benutzername, passwort });
  if (antwort.ok) aktuell = benutzername.trim();
  return antwort;
}

export async function zugangAendern(daten: {
  benutzername: string;
  passwort: string;
  neuer_benutzername: string;
  neues_passwort: string;
}): Promise<AnmeldeAntwort> {
  const antwort = await senden("aendern", daten);
  if (antwort.ok && daten.neuer_benutzername.trim()) {
    aktuell = daten.neuer_benutzername.trim();
  }
  return antwort;
}
