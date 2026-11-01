import { useSyncExternalStore } from "react";
import { BASE, saveUserSettings } from "./api";
import { withToken } from "./token";
import { iconZeichnen } from "./designIcon";

export type HintergrundArt = "farbe" | "bild" | "video" | "live";
export type LiveArt = "aurora" | "sterne" | "wellen" | "partikel" | "nebel" | "herzen";
export type Anpassung = "cover" | "contain" | "fill";

export interface Design {
  akzent: string;
  text: string;
  flaeche: string;
  flaecheDeckkraft: number;
  rand: string;
  randDeckkraft: number;
  leiste: string;
  leisteDeckkraft: number;
  nutzerBlase: string;
  nutzerBlase2: string;
  nutzerText: string;
  jonBlase: string;
  jonBlaseDeckkraft: number;
  jonText: string;
  eingabe: string;
  eingabeDeckkraft: number;
  senden: string;
  senden2: string;
  sendenText: string;
  helligkeit: number;
  kontrast: number;
  saettigung: number;
  farbton: number;
  rundung: number;
  glas: number;
  schrift: string;
  groesse: number;
  hintergrund: string;
  leuchten: string;
  hintergrundArt: HintergrundArt;
  quelle: string;
  live: LiveArt;
  anpassung: Anpassung;
  bildHelligkeit: number;
  bildUnschaerfe: number;
  abdunkeln: number;
  tempo: number;
  herzen: boolean;
  widmung: boolean;
  widmungText: string;
}

export type DesignFeld = keyof Design;

export const STANDARD: Design = {
  akzent: "#d4af37",
  text: "#ffffff",
  flaeche: "#ffffff",
  flaecheDeckkraft: 5,
  rand: "#ffffff",
  randDeckkraft: 10,
  leiste: "#000000",
  leisteDeckkraft: 40,
  nutzerBlase: "",
  nutzerBlase2: "",
  nutzerText: "#000000",
  jonBlase: "",
  jonBlaseDeckkraft: 5,
  jonText: "",
  eingabe: "",
  eingabeDeckkraft: 5,
  senden: "",
  senden2: "",
  sendenText: "#000000",
  helligkeit: 100,
  kontrast: 100,
  saettigung: 100,
  farbton: 0,
  rundung: 100,
  glas: 100,
  schrift: "standard",
  groesse: 100,
  hintergrund: "#050506",
  leuchten: "#14141c",
  hintergrundArt: "farbe",
  quelle: "",
  live: "aurora",
  anpassung: "cover",
  bildHelligkeit: 100,
  bildUnschaerfe: 0,
  abdunkeln: 35,
  tempo: 100,
  herzen: false,
  widmung: false,
  widmungText: "",
};

export const GRENZEN: Partial<Record<DesignFeld, [number, number]>> = {
  flaecheDeckkraft: [0, 100],
  randDeckkraft: [0, 100],
  leisteDeckkraft: [0, 100],
  jonBlaseDeckkraft: [0, 100],
  eingabeDeckkraft: [0, 100],
  helligkeit: [40, 160],
  kontrast: [50, 150],
  saettigung: [0, 200],
  farbton: [-180, 180],
  rundung: [0, 250],
  glas: [0, 200],
  groesse: [70, 150],
  bildHelligkeit: [20, 160],
  bildUnschaerfe: [0, 40],
  abdunkeln: [0, 90],
  tempo: [25, 300],
};

const FARBEN = new Set<DesignFeld>([
  "akzent", "text", "flaeche", "rand", "leiste", "nutzerBlase", "nutzerBlase2", "nutzerText",
  "jonBlase", "jonText", "eingabe", "senden", "senden2", "sendenText", "hintergrund", "leuchten",
]);

export const AUTOMATISCH = new Set<DesignFeld>(["nutzerBlase", "nutzerBlase2", "jonBlase", "jonText", "eingabe", "senden", "senden2"]);

export const SCHRIFTEN: { wert: string; name: string; familie: string }[] = [
  { wert: "standard", name: "Standard", familie: 'Inter, "Segoe UI"' },
  { wert: "system", name: "System", familie: 'system-ui, "Segoe UI"' },
  { wert: "rund", name: "Rund", familie: '"Segoe UI Variable Display", Nunito, Quicksand, "Varela Round", "Segoe UI"' },
  { wert: "serif", name: "Serifen", familie: 'Georgia, Cambria, "Times New Roman", serif' },
  { wert: "mono", name: "Mono", familie: '"Cascadia Code", "JetBrains Mono", Consolas, monospace' },
  { wert: "hand", name: "Handschrift", familie: '"Segoe Print", "Comic Sans MS", "Bradley Hand", cursive' },
];

const AUSWAHL: Partial<Record<DesignFeld, readonly string[]>> = {
  hintergrundArt: ["farbe", "bild", "video", "live"],
  live: ["aurora", "sterne", "wellen", "partikel", "nebel", "herzen"],
  anpassung: ["cover", "contain", "fill"],
  schrift: SCHRIFTEN.map((s) => s.wert),
};

const SCHLUESSEL = "jon_design";
const HEX = /^#[0-9a-f]{6}$/i;
const STANDARD_HELL = "#f5d67b";
const STANDARD_DUNKEL = "#9a7b1f";
export const WIDMUNG_LAENGE = 80;

export function normalisieren(roh: unknown): Design {
  const ergebnis: Record<string, unknown> = { ...STANDARD };
  if (!roh || typeof roh !== "object") return ergebnis as unknown as Design;
  const quelle = roh as Record<string, unknown>;
  for (const feld of Object.keys(STANDARD) as DesignFeld[]) {
    const wert = quelle[feld];
    const vorlage = STANDARD[feld];
    if (typeof vorlage === "boolean") {
      if (typeof wert === "boolean") ergebnis[feld] = wert;
    } else if (typeof vorlage === "number") {
      if (typeof wert !== "number" || !Number.isFinite(wert)) continue;
      const [min, max] = GRENZEN[feld] ?? [-Infinity, Infinity];
      ergebnis[feld] = Math.min(max, Math.max(min, wert));
    } else if (typeof wert === "string") {
      if (FARBEN.has(feld)) {
        if (HEX.test(wert)) ergebnis[feld] = wert.toLowerCase();
        else if (wert === "" && AUTOMATISCH.has(feld)) ergebnis[feld] = "";
      } else if (AUSWAHL[feld]) {
        if (AUSWAHL[feld]?.includes(wert)) ergebnis[feld] = wert;
      } else if (feld === "widmungText") {
        ergebnis[feld] = wert.slice(0, WIDMUNG_LAENGE);
      } else if (wert.length <= 2048) {
        ergebnis[feld] = wert.trim();
      }
    }
  }
  return ergebnis as unknown as Design;
}

function teile(hex: string): [number, number, number] {
  const zahl = parseInt(hex.slice(1), 16);
  return [(zahl >> 16) & 255, (zahl >> 8) & 255, zahl & 255];
}

function alsHex(werte: number[]): string {
  return "#" + werte.map((w) => Math.round(Math.min(255, Math.max(0, w))).toString(16).padStart(2, "0")).join("");
}

export function mischen(hex: string, ziel: string, anteil: number): string {
  const a = teile(hex);
  const b = teile(ziel);
  return alsHex(a.map((w, i) => w + (b[i] - w) * anteil));
}

function rgb(hex: string): string {
  return teile(hex).join(" ");
}

export function akzentHell(d: Design): string {
  return d.akzent === STANDARD.akzent ? STANDARD_HELL : mischen(d.akzent, "#ffffff", 0.38);
}

export function akzentDunkel(d: Design): string {
  return d.akzent === STANDARD.akzent ? STANDARD_DUNKEL : mischen(d.akzent, "#000000", 0.3);
}

export function wirksam(d: Design, feld: DesignFeld): string {
  const wert = d[feld];
  if (typeof wert === "string" && wert) return wert;
  switch (feld) {
    case "nutzerBlase":
    case "senden":
      return akzentHell(d);
    case "nutzerBlase2":
    case "senden2":
      return akzentDunkel(d);
    case "jonBlase":
    case "eingabe":
      return d.flaeche;
    case "jonText":
      return d.text;
    default:
      return String(STANDARD[feld]);
  }
}

export function lesen(): Design {
  try {
    const roh = localStorage.getItem(SCHLUESSEL);
    return normalisieren(roh ? JSON.parse(roh) : null);
  } catch {
    return { ...STANDARD };
  }
}

const zoomBruecke = (window as unknown as { jon?: { setZoom?: (faktor: number) => void; setAppIcon?: (png: string) => Promise<unknown> } }).jon;

export function zoomMoeglich(): boolean {
  return typeof zoomBruecke?.setZoom === "function";
}

export function anwenden(d: Design): void {
  const wurzel = document.documentElement;
  const stil = wurzel.style;
  const setzen = (name: string, wert: string) => stil.setProperty(name, wert);
  const auto = (feld: DesignFeld, ersatz: string) => {
    const wert = d[feld];
    return typeof wert === "string" && wert ? rgb(wert) : ersatz;
  };
  setzen("--gold-rgb", rgb(d.akzent));
  setzen("--gold-light-rgb", rgb(akzentHell(d)));
  setzen("--gold-dark-rgb", rgb(akzentDunkel(d)));
  setzen("--gold-sanft-rgb", d.akzent === STANDARD.akzent ? "229 200 137" : rgb(mischen(d.akzent, "#ffffff", 0.45)));
  setzen("--gold-hauch-rgb", d.akzent === STANDARD.akzent ? "255 241 201" : rgb(mischen(d.akzent, "#ffffff", 0.8)));
  setzen("--weiss-rgb", rgb(d.text));
  setzen("--hg-basis-rgb", rgb(d.hintergrund));
  setzen("--hg-leuchten-rgb", rgb(d.leuchten));
  setzen("--hg-tiefe-rgb", d.hintergrund === STANDARD.hintergrund ? "0 0 0" : rgb(mischen(d.hintergrund, "#000000", 0.55)));
  setzen("--flaeche-rgb", rgb(d.flaeche));
  setzen("--flaeche-a", String(d.flaecheDeckkraft / 100));
  setzen("--rand-rgb", rgb(d.rand));
  setzen("--rand-a", String(d.randDeckkraft / 100));
  setzen("--leiste-rgb", rgb(d.leiste));
  setzen("--leiste-a", String(d.leisteDeckkraft / 100));
  setzen("--nb1-rgb", auto("nutzerBlase", "var(--gold-light-rgb)"));
  setzen("--nb2-rgb", auto("nutzerBlase2", "var(--gold-dark-rgb)"));
  setzen("--nb-text-rgb", rgb(d.nutzerText));
  setzen("--jb-rgb", auto("jonBlase", "var(--flaeche-rgb)"));
  setzen("--jb-a", String(d.jonBlaseDeckkraft / 100));
  setzen("--jb-text-rgb", auto("jonText", "var(--weiss-rgb)"));
  setzen("--eingabe-rgb", auto("eingabe", "var(--flaeche-rgb)"));
  setzen("--eingabe-a", String(d.eingabeDeckkraft / 100));
  setzen("--senden1-rgb", auto("senden", "var(--gold-light-rgb)"));
  setzen("--senden2-rgb", auto("senden2", "var(--gold-dark-rgb)"));
  setzen("--senden-text-rgb", rgb(d.sendenText));
  setzen("--jd-rund", String(d.rundung / 100));
  setzen("--jd-glas", String(d.glas / 100));
  setzen("--jd-schrift", (SCHRIFTEN.find((s) => s.wert === d.schrift) ?? SCHRIFTEN[0]).familie);
  const filter = [
    d.helligkeit !== 100 ? `brightness(${d.helligkeit / 100})` : "",
    d.kontrast !== 100 ? `contrast(${d.kontrast / 100})` : "",
    d.saettigung !== 100 ? `saturate(${d.saettigung / 100})` : "",
    d.farbton !== 0 ? `hue-rotate(${d.farbton}deg)` : "",
  ].filter(Boolean);
  if (filter.length) setzen("--jd-filter", filter.join(" "));
  else stil.removeProperty("--jd-filter");
  wurzel.classList.toggle("jd-filter", filter.length > 0);
  wurzel.classList.toggle("jd-wallpaper", d.hintergrundArt !== "farbe");
  wurzel.classList.toggle("jd-herzen", d.herzen);
  if (zoomMoeglich()) zoomBruecke?.setZoom?.(d.groesse / 100);
}

let aktuell: Design = lesen();
const hoerer = new Set<() => void>();
let speicherTimer = 0;
let offen = false;

function melden(): void {
  hoerer.forEach((hoeren) => hoeren());
}

export function designHolen(): Design {
  return aktuell;
}

function merken(d: Design): void {
  try {
    localStorage.setItem(SCHLUESSEL, JSON.stringify(d));
  } catch {
    return;
  }
}

let iconTimer = 0;
let iconStand = "";

function iconPlanen(verzoegerung = 1200): void {
  if (typeof zoomBruecke?.setAppIcon !== "function") return;
  window.clearTimeout(iconTimer);
  iconTimer = window.setTimeout(() => {
    const d = aktuell;
    const stand = `${d.akzent}|${d.herzen}`;
    if (stand === iconStand) return;
    iconStand = stand;
    void zoomBruecke?.setAppIcon?.(iconZeichnen(d))?.catch(() => undefined);
  }, verzoegerung);
}

export function designSetzen(neu: Design, sichern = true): void {
  aktuell = normalisieren(neu);
  merken(aktuell);
  anwenden(aktuell);
  if (aktuell.herzen) geheimOeffnen();
  melden();
  iconPlanen();
  if (!sichern) return;
  window.clearTimeout(speicherTimer);
  offen = true;
  speicherTimer = window.setTimeout(() => sichernJetzt(false), 500);
}

function sichernJetzt(beimSchliessen: boolean): void {
  if (!offen) return;
  offen = false;
  window.clearTimeout(speicherTimer);
  const daten = { design: aktuell as unknown as Record<string, unknown> };
  if (!beimSchliessen) {
    void saveUserSettings(daten).catch(() => undefined);
    return;
  }
  void fetch(`${BASE}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(daten),
    keepalive: true,
  }).catch(() => undefined);
}

export function designAendern(teil: Partial<Design>): void {
  designSetzen({ ...aktuell, ...teil });
}

export function vomServer(roh: unknown, liste?: unknown): void {
  if (Array.isArray(liste) && liste.length) {
    const neueListe = eigeneNormalisieren(liste);
    if (JSON.stringify(neueListe) !== JSON.stringify(eigene)) {
      eigene = neueListe;
      eigeneMerken();
      if (eigene.some((e) => e.werte.herzen)) geheimOeffnen();
      melden();
    }
  }
  if (!roh || typeof roh !== "object" || !Object.keys(roh as object).length) return;
  const neu = normalisieren(roh);
  if (JSON.stringify(neu) === JSON.stringify(aktuell)) return;
  designSetzen(neu, false);
}

function abonnieren(hoeren: () => void): () => void {
  hoerer.add(hoeren);
  return () => hoerer.delete(hoeren);
}

export function useDesign(): Design {
  return useSyncExternalStore(abonnieren, designHolen);
}

export function designStarten(): void {
  anwenden(aktuell);
  iconPlanen(4000);
  window.addEventListener("pagehide", () => sichernJetzt(true));
  window.addEventListener("storage", (ereignis) => {
    if (ereignis.key === LISTE) {
      eigene = eigeneLesen();
      melden();
      return;
    }
    if (ereignis.key !== SCHLUESSEL) return;
    aktuell = lesen();
    anwenden(aktuell);
    melden();
  });
}

export const HINTERGRUND_FELDER: DesignFeld[] = [
  "hintergrundArt", "quelle", "live", "anpassung", "bildHelligkeit", "bildUnschaerfe", "abdunkeln", "tempo",
];

export interface Vorlage {
  name: string;
  beschreibung: string;
  werte: Partial<Design>;
}

export const VORLAGEN: Vorlage[] = [
  { name: "Schwarz-Gold", beschreibung: "Jons Standard", werte: {} },
  { name: "Mitternacht", beschreibung: "Tiefes Blau", werte: { akzent: "#5b8cff", hintergrund: "#04060d", leuchten: "#101b38", text: "#eef3ff" } },
  { name: "Smaragd", beschreibung: "Ruhiges Grün", werte: { akzent: "#34d399", hintergrund: "#030807", leuchten: "#0b231b", text: "#effdf7" } },
  { name: "Rosé", beschreibung: "Warm und weich", werte: { akzent: "#f472b6", hintergrund: "#0a0508", leuchten: "#2a1121", text: "#fff1f7", rundung: 140 } },
  { name: "Glut", beschreibung: "Orange wie Feuer", werte: { akzent: "#fb923c", hintergrund: "#0a0603", leuchten: "#2c1607", text: "#fff7ed" } },
  { name: "Graphit", beschreibung: "Schlicht und kantig", werte: { akzent: "#e4e4e7", hintergrund: "#0b0b0c", leuchten: "#1c1c20", rundung: 45, flaecheDeckkraft: 6, sendenText: "#0b0b0c" } },
  { name: "Polarlicht", beschreibung: "Live-Hintergrund", werte: { akzent: "#22d3ee", hintergrund: "#02070a", leuchten: "#062430", text: "#ecfeff", hintergrundArt: "live", live: "aurora", abdunkeln: 20 } },
  { name: "Sternennacht", beschreibung: "Live-Hintergrund", werte: { akzent: "#c7d2fe", hintergrund: "#000000", leuchten: "#0b1020", text: "#f8fafc", hintergrundArt: "live", live: "sterne", abdunkeln: 0 } },
  { name: "Ozean", beschreibung: "Live-Hintergrund", werte: { akzent: "#38bdf8", hintergrund: "#020a12", leuchten: "#08243a", text: "#f0f9ff", hintergrundArt: "live", live: "wellen", abdunkeln: 10 } },
  { name: "Lila Nebel", beschreibung: "Live-Hintergrund", werte: { akzent: "#a78bfa", hintergrund: "#07050d", leuchten: "#1b1430", text: "#f5f3ff", hintergrundArt: "live", live: "nebel", abdunkeln: 25 } },
  { name: "Netz", beschreibung: "Live-Hintergrund", werte: { akzent: "#f59e0b", hintergrund: "#050505", leuchten: "#1a1305", hintergrundArt: "live", live: "partikel", abdunkeln: 0 } },
];

const BLEIBT: DesignFeld[] = ["groesse", "widmung", "widmungText"];

export const ANNA: Vorlage = {
  name: "Anna \u2764\uFE0F",
  beschreibung: "Rosarot mit Herzen und Rosen",
  werte: {
    akzent: "#ff4d8d",
    text: "#fff0f6",
    flaeche: "#ffd1e3",
    flaecheDeckkraft: 7,
    rand: "#ff9ec4",
    randDeckkraft: 18,
    leiste: "#2a0716",
    leisteDeckkraft: 55,
    nutzerBlase: "#ff8fb8",
    nutzerBlase2: "#e0245e",
    nutzerText: "#ffffff",
    jonBlase: "#ffb3cf",
    jonBlaseDeckkraft: 9,
    senden: "#ff6fa5",
    senden2: "#d6164f",
    sendenText: "#ffffff",
    rundung: 150,
    hintergrund: "#16040c",
    leuchten: "#4a0d2b",
    hintergrundArt: "live",
    live: "herzen",
    abdunkeln: 8,
    herzen: true,
    widmung: true,
    widmungText: "Ich liebe dich Anna \u2764\uFE0F",
  },
};

export function vorlageAnwenden(vorlage: Vorlage): void {
  const behalten: Partial<Design> = {};
  if (!vorlage.werte.hintergrundArt) {
    for (const feld of HINTERGRUND_FELDER) (behalten as Record<string, unknown>)[feld] = aktuell[feld];
  }
  for (const feld of BLEIBT) (behalten as Record<string, unknown>)[feld] = aktuell[feld];
  designSetzen({ ...STANDARD, ...behalten, ...vorlage.werte });
}

export function vorlageAktiv(vorlage: Vorlage, d: Design): boolean {
  const soll = { ...STANDARD, ...vorlage.werte };
  const felder = Object.keys(STANDARD).filter((f) => !HINTERGRUND_FELDER.includes(f as DesignFeld) && !BLEIBT.includes(f as DesignFeld)) as DesignFeld[];
  const passt = felder.every((f) => soll[f] === d[f]);
  if (!passt) return false;
  if (!vorlage.werte.hintergrundArt) return true;
  return d.hintergrundArt === soll.hintergrundArt && d.live === soll.live;
}

const GEHEIM = "jon_design_geheim";
const LISTE = "jon_designs";
const MAX_EIGENE = 40;

export interface EigenesDesign {
  id: string;
  name: string;
  werte: Design;
  zeit: number;
}

function geheimLesen(): boolean {
  try {
    return localStorage.getItem(GEHEIM) === "1";
  } catch {
    return false;
  }
}

let geheim = geheimLesen() || aktuell.herzen;

export function geheimOeffnen(): void {
  if (geheim) return;
  geheim = true;
  melden();
  try {
    localStorage.setItem(GEHEIM, "1");
  } catch {
    return;
  }
}

export function useGeheim(): boolean {
  return useSyncExternalStore(abonnieren, () => geheim);
}

function eigeneNormalisieren(roh: unknown): EigenesDesign[] {
  if (!Array.isArray(roh)) return [];
  const ergebnis: EigenesDesign[] = [];
  for (const eintrag of roh) {
    if (!eintrag || typeof eintrag !== "object") continue;
    const e = eintrag as Record<string, unknown>;
    const name = typeof e.name === "string" ? e.name.trim().slice(0, 40) : "";
    const id = typeof e.id === "string" && /^[a-z0-9-]{4,40}$/.test(e.id) ? e.id : "";
    if (!name || !id || ergebnis.some((x) => x.id === id)) continue;
    ergebnis.push({ id, name, werte: normalisieren(e.werte), zeit: typeof e.zeit === "number" ? e.zeit : 0 });
    if (ergebnis.length >= MAX_EIGENE) break;
  }
  return ergebnis;
}

function eigeneLesen(): EigenesDesign[] {
  try {
    return eigeneNormalisieren(JSON.parse(localStorage.getItem(LISTE) || "[]"));
  } catch {
    return [];
  }
}

let eigene: EigenesDesign[] = eigeneLesen();

function eigeneMerken(): void {
  try {
    localStorage.setItem(LISTE, JSON.stringify(eigene));
  } catch {
    return;
  }
}

function eigeneSichern(): void {
  eigeneMerken();
  melden();
  void saveUserSettings({ design_liste: eigene as unknown as Record<string, unknown>[] }).catch(() => undefined);
}

export function useEigene(): EigenesDesign[] {
  return useSyncExternalStore(abonnieren, () => eigene);
}

export function eigenesSpeichern(name: string): EigenesDesign | null {
  const sauber = name.trim().slice(0, 40);
  if (!sauber) return null;
  const vorhanden = eigene.find((e) => e.name.toLowerCase() === sauber.toLowerCase());
  const eintrag: EigenesDesign = {
    id: vorhanden?.id ?? `d-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
    name: sauber,
    werte: { ...aktuell },
    zeit: Date.now(),
  };
  eigene = [eintrag, ...eigene.filter((e) => e.id !== eintrag.id)].slice(0, MAX_EIGENE);
  eigeneSichern();
  return eintrag;
}

export function eigenesLoeschen(id: string): void {
  eigene = eigene.filter((e) => e.id !== id);
  eigeneSichern();
}

export function eigenesAnwenden(eintrag: EigenesDesign): void {
  designSetzen({ ...eintrag.werte, groesse: aktuell.groesse });
}

export function eigenesAktiv(eintrag: EigenesDesign, d: Design): boolean {
  return (Object.keys(STANDARD) as DesignFeld[]).every((f) => f === "groesse" || eintrag.werte[f] === d[f]);
}

export interface HintergrundDatei {
  name: string;
  art: "bild" | "video";
  groesse: number;
  zeit: number;
}

export function hintergrundUrl(quelle: string): string {
  if (!quelle) return "";
  if (/^https?:\/\//i.test(quelle)) return quelle;
  return withToken(`${BASE}/design/hintergruende/${encodeURIComponent(quelle)}`);
}

async function fehlerText(antwort: Response, ersatz: string): Promise<string> {
  const daten = await antwort.json().catch(() => ({}));
  return daten && daten.detail ? String(daten.detail) : ersatz;
}

export async function hintergruendeLaden(): Promise<HintergrundDatei[]> {
  const antwort = await fetch(`${BASE}/design/hintergruende`);
  if (!antwort.ok) {
    if (antwort.status === 404) throw new Error("Starte Jon einmal neu, dann kannst du eigene Bilder und Videos hochladen.");
    throw new Error(await fehlerText(antwort, "Die Hintergründe ließen sich nicht laden."));
  }
  const daten = await antwort.json();
  return Array.isArray(daten.eintraege) ? daten.eintraege : [];
}

export async function hintergrundHochladen(datei: File): Promise<HintergrundDatei> {
  const antwort = await fetch(`${BASE}/design/hintergruende?name=${encodeURIComponent(datei.name)}`, {
    method: "POST",
    body: datei,
    headers: { "Content-Type": "application/octet-stream" },
  });
  if (!antwort.ok) throw new Error(await fehlerText(antwort, `Hochladen ging nicht (HTTP ${antwort.status}).`));
  return antwort.json();
}

export async function hintergrundLoeschen(name: string): Promise<void> {
  const antwort = await fetch(`${BASE}/design/hintergruende/${encodeURIComponent(name)}`, { method: "DELETE" });
  if (!antwort.ok && antwort.status !== 404) throw new Error(await fehlerText(antwort, "Löschen ging nicht."));
}
