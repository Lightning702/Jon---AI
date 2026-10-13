import { useEffect, useRef, useState } from "react";
import type { RenderQuelle, RenderZustand } from "../../lib/werkstatt";

export const GESEHEN = new Set<string>();

export function ruhigGewuenscht(): boolean {
  try {
    return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

export function useAblauf(gesamt: number, animieren: boolean, laeuft: boolean, dauer: number): number {
  const [stand, setStand] = useState(() => (animieren ? 0 : gesamt));
  const wert = useRef(animieren ? 0 : gesamt);
  const lauf = useRef(laeuft);
  lauf.current = laeuft;

  useEffect(() => {
    if (wert.current >= gesamt) {
      if (wert.current !== gesamt) {
        wert.current = gesamt;
        setStand(gesamt);
      }
      return;
    }
    let rahmen = 0;
    let zuletzt = performance.now();
    let gemalt = 0;
    const tempo = gesamt / Math.max(400, dauer);
    const schritt = (jetzt: number) => {
      const delta = Math.min(120, jetzt - zuletzt);
      zuletzt = jetzt;
      wert.current = Math.min(gesamt, wert.current + delta * tempo * (lauf.current ? 1 : 4));
      if (jetzt - gemalt > 38 || wert.current >= gesamt) {
        gemalt = jetzt;
        setStand(wert.current >= gesamt ? gesamt : Math.floor(wert.current));
      }
      if (wert.current < gesamt) rahmen = requestAnimationFrame(schritt);
    };
    rahmen = requestAnimationFrame(schritt);
    return () => cancelAnimationFrame(rahmen);
  }, [gesamt, dauer]);

  return Math.min(stand, gesamt);
}

export function useSekunden(aktiv: boolean): number {
  const [sekunden, setSekunden] = useState(0);
  useEffect(() => {
    if (!aktiv) return;
    const start = Date.now();
    const takt = window.setInterval(() => setSekunden(Math.floor((Date.now() - start) / 1000)), 500);
    return () => window.clearInterval(takt);
  }, [aktiv]);
  return sekunden;
}

const ENDE = new Set(["fertig", "fehler", "nicht_moeglich"]);

export function useEchteSeiten(pfad: string | undefined, aktiv: boolean, render?: RenderQuelle): RenderZustand | null {
  const [zustand, setZustand] = useState<RenderZustand | null>(null);
  useEffect(() => {
    if (!pfad || !aktiv || !render) return;
    let aus = false;
    let timer: number | undefined;
    const beginn = Date.now();
    let neuStarten = true;
    const pruefen = async () => {
      try {
        const neu = neuStarten ? await render.starten(pfad) : await render.stand(pfad);
        neuStarten = false;
        if (aus) return;
        if (neu) {
          if (neu.status === "offen") neuStarten = true;
          else setZustand((alt) => (alt && alt.status === neu.status && alt.version === neu.version && alt.seiten === neu.seiten ? alt : neu));
          if (ENDE.has(neu.status)) return;
        }
      } catch {
        if (aus) return;
      }
      if (Date.now() - beginn < 240000) timer = window.setTimeout(() => void pruefen(), 2000);
    };
    void pruefen();
    return () => {
      aus = true;
      window.clearTimeout(timer);
    };
  }, [pfad, aktiv, render]);
  return zustand;
}

export function anteil(rest: number, kosten: number): number {
  if (kosten <= 0) return rest >= 0 ? 1 : 0;
  return Math.max(0, Math.min(1, rest / kosten));
}

export function schnitt(text: string, wert: number): string {
  if (wert >= 1) return text;
  if (wert <= 0) return "";
  return text.slice(0, Math.ceil(text.length * wert));
}

export interface DiffZeile {
  art: " " | "-" | "+";
  text: string;
}

export function zeilenDiff(alt: string, neu: string): DiffZeile[] {
  const a = alt.replace(/\r\n/g, "\n").split("\n");
  const b = neu.replace(/\r\n/g, "\n").split("\n");
  if (!alt) return b.map((text) => ({ art: "+", text }));
  if (a.length * b.length > 250000) return [...a.map((text) => ({ art: "-" as const, text })), ...b.map((text) => ({ art: "+" as const, text }))];
  const n = a.length;
  const m = b.length;
  const tabelle: Uint16Array[] = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      tabelle[i][j] = a[i] === b[j] ? tabelle[i + 1][j + 1] + 1 : Math.max(tabelle[i + 1][j], tabelle[i][j + 1]);
    }
  }
  const ergebnis: DiffZeile[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      ergebnis.push({ art: " ", text: a[i] });
      i++;
      j++;
    } else if (tabelle[i + 1][j] >= tabelle[i][j + 1]) {
      ergebnis.push({ art: "-", text: a[i++] });
    } else {
      ergebnis.push({ art: "+", text: b[j++] });
    }
  }
  while (i < n) ergebnis.push({ art: "-", text: a[i++] });
  while (j < m) ergebnis.push({ art: "+", text: b[j++] });
  return ergebnis;
}

const SCHLUESSEL = new Set(
  (
    "abstract and as assert async await break case catch class const continue def default del do elif else enum except export extends " +
    "false final finally fn for from fun function global go if impl implements import in instanceof interface is lambda let loop match mod " +
    "module mut namespace new nil none None not null object of or override package pass private protected pub public raise readonly return " +
    "self static struct super switch this throw throws trait true True False try type typeof undefined union unsafe use val var void when where " +
    "while with yield int float double bool boolean char string str long short byte unsigned signed auto include define pragma " +
    "SELECT FROM WHERE INSERT INTO VALUES UPDATE SET DELETE CREATE TABLE JOIN LEFT RIGHT INNER ON GROUP BY ORDER LIMIT AND OR NOT " +
    "param begin process end foreach elseif echo fi then done esac local"
  ).split(" ")
);

const HASH = new Set(["python", "bash", "powershell", "yaml", "toml", "ini", "ruby"]);
const SLASH = new Set(["javascript", "typescript", "tsx", "jsx", "java", "kotlin", "c", "cpp", "csharp", "rust", "go", "dart", "swift", "php", "glsl", "css"]);
const STRICH = new Set(["sql", "lua"]);
const AUSZEICHNUNG = new Set(["html", "xml", "markdown"]);
const MUSTER = new Map<string, RegExp>();

function muster(sprache: string): RegExp {
  const vorhanden = MUSTER.get(sprache);
  if (vorhanden) return vorhanden;
  const kommentare = [
    SLASH.has(sprache) && sprache !== "css" ? "\\/\\/.*$" : "",
    SLASH.has(sprache) ? "\\/\\*.*?(?:\\*\\/|$)" : "",
    HASH.has(sprache) ? "#.*$" : "",
    STRICH.has(sprache) ? "--.*$" : "",
    AUSZEICHNUNG.has(sprache) ? "<!--.*?(?:-->|$)" : "",
    sprache === "batch" ? "(?:^\\s*(?:rem|::)\\b.*$)" : "",
  ].filter(Boolean);
  const teile = [
    kommentare.length ? `(${kommentare.join("|")})` : "(\\u0000\\u0001)",
    "(\"(?:\\\\.|[^\"\\\\])*\"?|'(?:\\\\.|[^'\\\\])*'?|`(?:\\\\.|[^`\\\\])*`?)",
    "(\\b\\d[\\d_.]*(?:e[+-]?\\d+)?[a-zA-Z]*\\b|\\b0x[0-9a-fA-F]+\\b)",
    AUSZEICHNUNG.has(sprache) || sprache === "tsx" || sprache === "jsx" ? "(<\\/?[A-Za-z][\\w:.-]*|\\/?>)" : "(\\u0000\\u0002)",
    "([A-Za-z_$@][\\w$]*)",
  ];
  const regex = new RegExp(teile.join("|"), "gm");
  MUSTER.set(sprache, regex);
  return regex;
}

export interface Stueck {
  t: string;
  k?: string;
}

export function faerben(zeile: string, sprache: string): Stueck[] {
  if (sprache === "text" || !zeile) return [{ t: zeile }];
  const regex = muster(sprache);
  regex.lastIndex = 0;
  const stuecke: Stueck[] = [];
  let zuletzt = 0;
  let treffer: RegExpExecArray | null;
  while ((treffer = regex.exec(zeile))) {
    if (treffer[0] === "") {
      regex.lastIndex++;
      continue;
    }
    if (treffer.index > zuletzt) stuecke.push({ t: zeile.slice(zuletzt, treffer.index) });
    const text = treffer[0];
    let klasse: string | undefined;
    if (treffer[1]) klasse = "lw-c";
    else if (treffer[2]) klasse = "lw-s";
    else if (treffer[3]) klasse = "lw-n";
    else if (treffer[4]) klasse = "lw-t";
    else if (treffer[5]) {
      const danach = zeile.slice(regex.lastIndex).trimStart();
      if (SCHLUESSEL.has(text) || (sprache === "sql" && SCHLUESSEL.has(text.toUpperCase()))) klasse = "lw-k";
      else if (text.startsWith("@") || text.startsWith("$")) klasse = "lw-v";
      else if (danach.startsWith("(")) klasse = "lw-f";
      else if (/^[A-Z][a-z0-9]/.test(text)) klasse = "lw-y";
    }
    stuecke.push({ t: text, k: klasse });
    zuletzt = regex.lastIndex;
  }
  if (zuletzt < zeile.length) stuecke.push({ t: zeile.slice(zuletzt) });
  return stuecke;
}
