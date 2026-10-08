import {BookOpen, CalendarCheck, Code2, FileSearch, Globe, Languages, Lightbulb, ListChecks, Palette, PenLine, Search, Sigma, SquareTerminal, FlaskConical, type LucideIcon} from "lucide-react";

export type Anfrage = (pfad: string, body?: unknown, method?: string) => Promise<any>;

export type TeilStatus = "queued" | "working" | "done" | "failed" | "cancelled" | "interrupted";

export interface Teil {
  titel: string;
  auftrag?: string;
  rolle: string;
  rolle_name?: string;
  status: string;
  ergebnis?: string;
  fehler?: string;
  dauer?: number;
  begonnen?: number;
}

export interface Pruefung {
  ok: boolean;
  probleme: string[];
  korrektur: string;
}

export interface Lauf {
  id: string;
  aufgabe: string;
  source?: string;
  status: string;
  antwort?: string;
  datei?: string;
  fehler?: string;
  hinweis?: string;
  teile?: Teil[];
  pruefung?: Pruefung | null;
  created_at?: number;
  updated_at?: number;
  dauer?: number;
  vollstaendig?: boolean;
  model?: string;
}

export interface Spezialist {
  role: string;
  profil?: string;
  question: string;
  status: string;
  result?: string;
  error?: string;
  dauer?: number;
  begonnen?: number;
}

export interface HarnessAuftrag {
  id: string;
  thread?: string;
  goal: string;
  root: string;
  source: string;
  status: string;
  step: number;
  steps: string[];
  summary: string;
  companion?: boolean;
  model?: string;
  provider?: string;
  specialists?: Spezialist[];
  pending: null | {id: string; notice: string; args: {command: string; cwd: string; timeout: number}};
  changes: {path: string; diff: string}[];
  checks: {command: string; output: string; ok: boolean; exit_code: number; revision: number}[];
  log?: {time: number; type: string; tool: string; message: string; pfad?: string; plus?: number; minus?: number; ok?: boolean; ausgabe?: string}[];
  plan_schritt?: number;
  created_at?: number;
  updated_at?: number;
  modus?: "code" | "allgemein";
  kompaktierungen?: number;
  modellaufrufe?: number;
  kontext?: {zeichen: number; budget: number; schaetzung_tokens: number};
  aktives_modell?: string;
  fortschritt?: {nummer: number; text: string; zustand: "erledigt" | "aktiv" | "offen"}[];
}

export type KernPhase = "ruhe" | "bereit" | "denken" | "verteilen" | "pruefen" | "sammeln" | "warten" | "fertig" | "offen" | "fehler";

export interface Knoten {
  id: string;
  titel: string;
  rolle: string;
  status: string;
}

export const ENDE = new Set(["done", "needs_review", "failed", "cancelled", "interrupted"]);

export const ROLLEN: Record<string, {name: string; farbe: string; icon: LucideIcon}> = {
  general: {name: "Fachanalyse", farbe: "#e5c889", icon: Lightbulb},
  latin: {name: "Latein", farbe: "#c7a6ff", icon: Languages},
  learning: {name: "Lernen & Mathe", farbe: "#79d0ff", icon: Sigma},
  coding: {name: "Programmierung", farbe: "#7fe0a4", icon: Code2},
  research: {name: "Recherche", farbe: "#ffad74", icon: Globe},
  planning: {name: "Planung", farbe: "#f59ccd", icon: CalendarCheck},
  writing: {name: "Schreiben", farbe: "#9fb2ff", icon: PenLine},
  design: {name: "Gestaltung", farbe: "#ffd36a", icon: Palette},
};

export const rolle = (key?: string) => ROLLEN[key || ""] || ROLLEN.general;

export const LAUF_TEXT: Record<string, string> = {
  planning: "Jon verteilt die Aufgabe",
  working: "Die Fachagenten arbeiten",
  verifying: "Gegenprüfung läuft",
  summarizing: "Jon fasst zusammen",
  done: "Fertig und gegengeprüft",
  needs_review: "Fertig mit offenen Punkten",
  failed: "Fehlgeschlagen",
  cancelled: "Gestoppt",
  interrupted: "Unterbrochen",
};

export const TEIL_TEXT: Record<string, string> = {
  queued: "Wartet",
  working: "Arbeitet",
  done: "Fertig",
  failed: "Fehler",
  cancelled: "Gestoppt",
  interrupted: "Unterbrochen",
};

export const HARNESS_TEXT: Record<string, string> = {
  planning: "Plant den Auftrag",
  working: "Arbeitet im Projekt",
  verifying: "Prüft die Änderungen",
  compacting: "Verdichtet den bisherigen Verlauf und arbeitet dann weiter",
  waiting_for_tool: "Ein Jon-Werkzeug läuft",
  evaluating: "Wertet das Ergebnis aus",
  paused: "Pausiert",
  waiting_approval: "Wartet auf deine Freigabe",
  cancelling: "Stoppt",
  done: "Fertig und geprüft",
  needs_review: "Fertig, bitte ansehen",
  failed: "Fehlgeschlagen",
  cancelled: "Gestoppt",
  interrupted: "Unterbrochen",
};

export const QUELLE_TEXT: Record<string, string> = {
  app: "",
  minijon: "über MiniJon",
  handy: "vom Handy",
  telegram: "aus Telegram",
  terminal: "aus dem Terminal",
  agenten: "",
};

export function quelle(source?: string): string {
  if (!source) return "";
  if (source.startsWith("telegram")) return QUELLE_TEXT.telegram;
  return QUELLE_TEXT[source] ?? "";
}

export function laufPhase(status: string): KernPhase {
  if (status === "planning") return "denken";
  if (status === "working") return "verteilen";
  if (status === "verifying") return "pruefen";
  if (status === "summarizing") return "sammeln";
  if (status === "done") return "fertig";
  if (status === "needs_review") return "offen";
  if (status === "failed" || status === "interrupted" || status === "cancelled") return "fehler";
  return "ruhe";
}

export function harnessPhase(status: string): KernPhase {
  if (status === "planning") return "denken";
  if (status === "working" || status === "cancelling") return "verteilen";
  if (status === "verifying") return "pruefen";
  if (status === "waiting_approval") return "warten";
  if (status === "done") return "fertig";
  if (status === "needs_review") return "offen";
  if (ENDE.has(status)) return "fehler";
  return "ruhe";
}

export const LAUF_STUFEN = [
  {key: "planning", label: "Verteilen"},
  {key: "working", label: "Arbeiten"},
  {key: "verifying", label: "Gegenprüfen"},
  {key: "summarizing", label: "Bündeln"},
  {key: "ende", label: "Fertig"},
];

export function laufStufe(status: string): number {
  const index = LAUF_STUFEN.findIndex(stufe => stufe.key === status);
  if (index >= 0) return index;
  return ENDE.has(status) ? LAUF_STUFEN.length - 1 : 0;
}

export const WERKZEUG_ICON: Record<string, LucideIcon> = {
  plan: ListChecks,
  list: BookOpen,
  read: FileSearch,
  search: Search,
  delegate: Lightbulb,
  edit: PenLine,
  create: Code2,
  command: SquareTerminal,
  verify: FlaskConical,
  running_command: SquareTerminal,
};

export const WERKZEUG_TEXT: Record<string, string> = {
  plan: "plant",
  list: "sieht sich um",
  read: "liest",
  search: "sucht",
  delegate: "fragt einen Fachagenten",
  edit: "ändert",
  create: "legt an",
  command: "führt aus",
  verify: "testet",
  running_command: "führt aus",
};

export function dauerText(sekunden: number): string {
  const wert = Math.max(0, Math.round(sekunden));
  if (wert < 60) return `${wert}s`;
  return `${Math.floor(wert / 60)}m ${String(wert % 60).padStart(2, "0")}s`;
}

export function diffZahlen(diff: string) {
  let plus = 0;
  let minus = 0;
  for (const zeile of diff.split("\n")) {
    if (zeile.startsWith("+") && !zeile.startsWith("+++")) plus++;
    if (zeile.startsWith("-") && !zeile.startsWith("---")) minus++;
  }
  return {plus, minus};
}

export function fehlerText(e: unknown, ersatz = "Jon ist gerade nicht erreichbar."): string {
  return e instanceof Error && e.message ? e.message : ersatz;
}
