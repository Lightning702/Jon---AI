import { useEffect, useState } from "react";
import { BASE } from "./api";

export type Stufe = "standard" | "premium" | "admin" | "entwickler";

export interface PremiumFeature {
  key: string;
  name: string;
  beschreibung: string;
  frei: boolean;
  kontingent: number;
  verbraucht: number;
}

export interface PremiumStatus {
  stufe: Stufe;
  name: string;
  geraet: string;
  gueltig_bis: number;
  inhaber: string;
  abo: boolean;
  hinweis: string;
  token: string;
  offen: boolean;
  codes: boolean;
  team: boolean;
  haupt: boolean;
  flags: Record<string, boolean>;
  beta: boolean;
  ungelesen: number;
  plaene: { key: string; name: string; preis: string; zeitraum: string; hinweis?: string }[];
  features: PremiumFeature[];
}

export type CodeArt = "entwickler" | "premium" | "admin";

export interface CodeGeraet {
  geraet: string;
  kurz: string;
  seit: number;
  version?: string;
  system?: string;
  zuletzt?: number;
  ablauf?: number;
}

export interface EntwicklerCode {
  id: string;
  name: string;
  art: CodeArt;
  tage: number;
  erstellt: number;
  zuletzt: number;
  geraete: number;
  geraete_liste: CodeGeraet[];
  max_geraete: number;
  gesperrt: boolean;
  ende: string;
}

export interface TeamNachricht {
  id: string;
  zeit: number;
  von: { id: string; name: string; rolle: string };
  an: string;
  art: "idee" | "fehler" | "nachricht" | "rundschreiben";
  text: string;
  antwort_auf: string;
  status?: string;
  stimmen: number;
  meine_stimme: boolean;
  gelesen: boolean;
  von_mir: boolean;
  anhang: null | { system: string; log: string; bild: boolean };
}

export interface TeamStand {
  nachrichten: TeamNachricht[];
  ungelesen: number;
  ich: { id: string; name: string; rolle: string; haupt: boolean };
  mitglieder: { id: string; name: string; rolle: string }[];
  status: Record<string, string>;
}

export function teamAnfrage<T>(aktion: string, body: unknown = {}): Promise<T> {
  return premiumAnfrage<T>("/premium/team/" + aktion, body);
}

export interface PremiumAnlass {
  feature: string;
  text: string;
}

let stand: PremiumStatus | null = null;
const hoerer = new Set<(wert: PremiumStatus | null) => void>();

function verteilen(wert: PremiumStatus | null) {
  stand = wert;
  hoerer.forEach(h => h(wert));
}

export async function premiumAnfrage<T>(pfad: string, body?: unknown): Promise<T> {
  const antwort = await fetch(BASE + pfad, { method: body === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(60000) });
  const daten = await antwort.json().catch(() => ({}));
  if (!antwort.ok) {
    const detail = typeof daten.detail === "string" ? daten.detail : Array.isArray(daten.detail) ? "Bitte prüfe deine Eingabe." : "";
    throw new Error(detail || `Jon antwortet mit Fehler ${antwort.status}.`);
  }
  if (daten && typeof daten === "object" && "stufe" in daten) verteilen(daten as PremiumStatus);
  return daten as T;
}

export async function premiumLaden(): Promise<PremiumStatus | null> {
  try {
    return await premiumAnfrage<PremiumStatus>("/premium");
  } catch {
    return stand;
  }
}

export function usePremium(): PremiumStatus | null {
  const [wert, setWert] = useState<PremiumStatus | null>(stand);
  useEffect(() => {
    hoerer.add(setWert);
    if (!stand) void premiumLaden();
    return () => {hoerer.delete(setWert);};
  }, []);
  return wert;
}

export const istPremium = (wert: PremiumStatus | null) => wert?.stufe === "premium" || wert?.stufe === "admin" || wert?.stufe === "entwickler";

export function premiumOeffnen(feature = "", text = "") {
  window.dispatchEvent(new CustomEvent<PremiumAnlass>("jon-premium", { detail: { feature, text } }));
}

export function premiumPruefen(antwort: Response) {
  if (antwort.status !== 402) return;
  void antwort.clone().json().then(daten => {
    if (daten && typeof daten.premium === "string") premiumOeffnen(daten.premium, typeof daten.detail === "string" ? daten.detail : "");
  }).catch(() => {});
}
