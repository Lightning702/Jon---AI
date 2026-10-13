export interface WerkstattFarben {
  primary: string;
  secondary: string;
  accent: string;
  dark: string;
  light: string;
  muted: string;
  soft: string;
}

export interface WerkstattFolie {
  layout: string;
  titel?: string;
  untertitel?: string;
  text?: string;
  punkte?: string[];
  items?: { titel: string; text: string; punkte: string[] }[];
  tabelle?: string[][];
  bild?: string;
  notizen?: string;
  quelle?: string;
  diagramm?: { art: string; kategorien: string[]; werte: number[] };
}

export interface PptxAktion {
  art: string;
  titel: string;
  folie?: number;
  element?: number;
  nach?: number;
  alt?: string;
  neu?: string;
  text?: string;
  position?: string;
  farbe?: string;
  folie_inhalt?: WerkstattFolie;
}

export interface DocxAktion {
  art: string;
  titel: string;
  nr?: number;
  nach?: number;
  zeile?: number;
  spalte?: number;
  stil?: string;
  alt?: string;
  neu?: string;
  text?: string;
  tabelle?: string[][];
}

export interface DokumentBlock {
  typ: string;
  text: string;
}

export type WerkstattDaten =
  | { art: "folien"; titel: string; untertitel?: string; theme: string; farben: WerkstattFarben; folien: WerkstattFolie[]; anzahl: number; pfad?: string }
  | { art: "folien_aenderung"; pfad: string; aktionen: PptxAktion[]; farben: WerkstattFarben }
  | { art: "dokument_aenderung"; pfad: string; aktionen: DocxAktion[] }
  | { art: "dokument"; titel: string; format: string; pfad: string; bloecke: DokumentBlock[] }
  | { art: "tabelle"; titel: string; format: string; pfad: string; zeilen: string[][] }
  | { art: "code"; pfad: string; sprache: string; inhalt: string; anhaengen?: boolean }
  | { art: "diff"; pfad: string; sprache: string; alt: string; neu: string }
  | { art: "terminal"; befehl: string; shell: string; pruefung?: boolean };

export interface WerkstattErgebnis {
  ok: boolean;
  fehler?: string;
  pfad?: string;
  office?: boolean;
  folien?: number;
  hinweise?: string[];
  exit_code?: number | null;
  ausgabe?: string;
  diff?: string;
}

export interface RenderZustand {
  status: "fertig" | "laeuft" | "fehler" | "nicht_moeglich" | "offen";
  seiten?: number;
  version?: string;
  fehler?: string;
}

export interface RenderQuelle {
  starten: (pfad: string) => Promise<RenderZustand | undefined>;
  stand: (pfad: string) => Promise<RenderZustand>;
  seite: (pfad: string, nr: number, version: string) => string;
}

export interface WerkzeugSchritt {
  id?: string;
  name: string;
  done: boolean;
  ok?: boolean;
  args?: Record<string, unknown>;
  summary?: string;
  werkstatt?: WerkstattDaten;
  ergebnis?: WerkstattErgebnis;
  live?: boolean;
}

export interface WerkzeugEreignis {
  name?: string;
  status?: "running" | "done";
  ok?: boolean;
  args?: Record<string, unknown>;
  summary?: string;
  werkstatt?: WerkstattDaten;
  werkstatt_ergebnis?: WerkstattErgebnis;
}

let zaehler = 0;

export function schrittAnwenden<T extends WerkzeugSchritt>(tools: T[] | undefined, evt: WerkzeugEreignis): T[] {
  const liste = [...(tools ?? [])];
  const name = evt.name ?? "tool";
  if (evt.status === "running") {
    zaehler += 1;
    liste.push({ id: `w${Date.now().toString(36)}${zaehler}`, name, done: false, args: evt.args, summary: evt.summary, werkstatt: evt.werkstatt, live: true } as T);
    return liste;
  }
  let index = -1;
  for (let i = liste.length - 1; i >= 0; i--) {
    if (liste[i].name === name && !liste[i].done) {
      index = i;
      break;
    }
  }
  if (index < 0) index = liste.map((t) => t.name).lastIndexOf(name);
  if (index >= 0) liste[index] = { ...liste[index], done: true, ok: evt.ok, ergebnis: evt.werkstatt_ergebnis ?? liste[index].ergebnis };
  return liste;
}

export function dateiname(pfad: string | undefined): string {
  return String(pfad || "").split(/[\\/]/).filter(Boolean).at(-1) || "";
}
