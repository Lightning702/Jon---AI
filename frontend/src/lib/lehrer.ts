import { BASE } from "./api";
import { fehlerText } from "./version";

export interface KursKurz {
  id: string;
  titel: string;
  fach: string;
  ziel: string;
  termin: string;
  status: "baut" | "bereit" | "fehler" | string;
  fortschritt: number;
  schritt: string;
  fehler: string;
  lektionen: number;
  beherrschung: number;
  faellig: number;
  dateien: number;
  zuletzt: number;
  serie: number;
}

export interface Lektion {
  nr: number;
  titel: string;
  ziele: string[];
  inhalt: string;
  beispiele: string[];
  begriffe: string[];
  beherrschung: number;
  bereit: boolean;
  aufgaben: number;
}

export interface Kurs extends KursKurz {
  zusammenfassung: string;
  niveau: string;
  dateiliste: { name: string; zeichen: number }[];
  lektionsliste: Lektion[];
  chat: { rolle: "du" | "lehrer"; text: string; zeit: number }[];
  empfehlung: string;
}

export interface Aufgabe {
  id: string;
  lektion: number;
  art: "auswahl" | "frei" | "lueckentext" | "wahr_falsch";
  frage: string;
  optionen: string[];
  schwierigkeit: number;
  stufe: number;
}

export interface Bewertung {
  richtig: boolean;
  teilweise: boolean;
  feedback: string;
  loesung: string;
  erklaerung: string;
  beherrschung: number;
  naechste_wiederholung: number;
  serie: number;
}

async function abrufen<T>(pfad: string, optionen?: RequestInit): Promise<T> {
  const antwort = await fetch(`${BASE}/lehrer${pfad}`, optionen);
  const daten = await antwort.json().catch(() => ({}));
  if (!antwort.ok) throw new Error(fehlerText(antwort.status, daten.detail));
  return daten as T;
}

function senden<T>(pfad: string, koerper: unknown): Promise<T> {
  return abrufen<T>(pfad, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(koerper) });
}

export const lehrer = {
  kurse: () => abrufen<{ kurse: KursKurz[] }>("/kurse").then((d) => d.kurse),
  kurs: (id: string) => abrufen<Kurs>(`/kurse/${id}`),
  neu: (daten: { fach: string; ziel: string; niveau: string; termin: string; dateien: string[] }) => senden<KursKurz>("/kurse", daten),
  entfernen: (id: string) => abrufen<{ ok: boolean }>(`/kurse/${id}`, { method: "DELETE" }),
  neuBauen: (id: string) => senden<KursKurz>(`/kurse/${id}/neu-bauen`, {}),
  aufgabe: (id: string, lektion?: number) => abrufen<{ aufgabe: Aufgabe; grund: string }>(`/kurse/${id}/aufgabe${lektion ? `?lektion=${lektion}` : ""}`),
  antworten: (id: string, aufgabe: string, antwort: string) => senden<Bewertung>(`/kurse/${id}/antwort`, { aufgabe, antwort }),
  fragen: (id: string, text: string, lektion?: number) => senden<{ antwort: string }>(`/kurse/${id}/frage`, { text, lektion }),
  erklaeren: (id: string, lektion: number, art: string) => senden<{ text: string }>(`/kurse/${id}/erklaeren`, { lektion, art }),
  probetest: (id: string, anzahl = 10) => abrufen<{ aufgaben: Aufgabe[]; minuten: number }>(`/kurse/${id}/probetest?anzahl=${anzahl}`),
};
