import { memo, useEffect, useMemo, useRef, type ReactElement } from "react";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { WerkstattErgebnis } from "../../lib/werkstatt";
import { faerben, useAblauf, useSekunden, zeilenDiff, type DiffZeile } from "./ablauf";

const FENSTER = 70;
const HOECHSTENS = 1500;

const Zeile = memo(function Zeile({ nummer, text, sprache, zeichen, klasse }: { nummer: number | string; text: string; sprache: string; zeichen?: string; klasse?: string }) {
  const stuecke = useMemo(() => faerben(text, sprache), [text, sprache]);
  return (
    <div className={`lw-c-zeile ${klasse ?? ""}`}>
      <span className="lw-c-nr">{nummer}</span>
      {zeichen !== undefined && <span className="lw-c-zeichen">{zeichen}</span>}
      <code>
        {stuecke.map((s, i) =>
          s.k ? (
            <span key={i} className={s.k}>
              {s.t}
            </span>
          ) : (
            s.t
          )
        )}
        {text === "" && " "}
      </code>
    </div>
  );
});

function useFolgen(aktiv: boolean, abhaengig: unknown) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (aktiv && ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [aktiv, abhaengig]);
  return ref;
}

export function CodeAnsicht({ inhalt, sprache, laeuft, animieren, anhaengen, kompakt }: { inhalt: string; sprache: string; laeuft: boolean; animieren: boolean; anhaengen?: boolean; kompakt?: boolean }) {
  const zeilen = useMemo(() => inhalt.replace(/\r\n/g, "\n").split("\n").slice(0, HOECHSTENS), [inhalt]);
  const grenzen = useMemo(() => {
    let summe = 0;
    return zeilen.map((z) => (summe += z.length + 1));
  }, [zeilen]);
  const gesamt = grenzen.at(-1) ?? 0;
  const p = useAblauf(gesamt, animieren, laeuft, Math.min(10000, Math.max(1400, 900 + gesamt * 3.5)));
  const tippt = p < gesamt;
  let aktuell = zeilen.length - 1;
  if (tippt) aktuell = Math.max(0, grenzen.findIndex((g) => g > p));
  const anfang = tippt ? Math.max(0, aktuell - FENSTER) : 0;
  const teil = tippt ? zeilen[aktuell].slice(0, Math.max(0, p - (grenzen[aktuell - 1] ?? 0))) : "";
  const ref = useFolgen(tippt, aktuell);
  const zeile = tippt ? `${anhaengen ? "Jon hängt an" : "Jon schreibt"} · Zeile ${aktuell + 1} von ${zeilen.length}` : laeuft ? "Jon speichert die Datei …" : `${zeilen.length} Zeilen ${anhaengen ? "angehängt" : "geschrieben"}`;

  return (
    <div className="lw-code">
      <div className="lw-zeile">
        {(tippt || laeuft) && <Loader2 className="lw-dreh" />}
        <span>{zeile}</span>
      </div>
      <div className={`lw-editor ${kompakt ? "kompakt" : ""}`} ref={ref}>
        {anfang > 0 && <div className="lw-c-luecke">{anfang} Zeilen darüber</div>}
        {zeilen.slice(anfang, tippt ? aktuell : zeilen.length).map((z, i) => (
          <Zeile key={anfang + i} nummer={anfang + i + 1} text={z} sprache={sprache} />
        ))}
        {tippt && (
          <div className="lw-c-zeile aktiv">
            <span className="lw-c-nr">{aktuell + 1}</span>
            <code>
              {faerben(teil, sprache).map((s, i) =>
                s.k ? (
                  <span key={i} className={s.k}>
                    {s.t}
                  </span>
                ) : (
                  s.t
                )
              )}
              <i className="lw-caret" />
            </code>
          </div>
        )}
      </div>
    </div>
  );
}

interface DiffEintrag extends DiffZeile {
  alt?: number;
  neu?: number;
}

function nummerieren(zeilen: DiffZeile[]): DiffEintrag[] {
  let a = 0;
  let b = 0;
  return zeilen.map((z) => {
    if (z.art === " ") return { ...z, alt: ++a, neu: ++b };
    if (z.art === "-") return { ...z, alt: ++a };
    return { ...z, neu: ++b };
  });
}

export function DiffAnsicht({ alt, neu, sprache, laeuft, animieren, kompakt }: { alt: string; neu: string; sprache: string; laeuft: boolean; animieren: boolean; kompakt?: boolean }) {
  const eintraege = useMemo(() => nummerieren(zeilenDiff(alt, neu)), [alt, neu]);
  const sichtbar = useMemo(() => {
    const nah = new Set<number>();
    eintraege.forEach((e, i) => {
      if (e.art !== " ") for (let j = Math.max(0, i - 3); j <= Math.min(eintraege.length - 1, i + 3); j++) nah.add(j);
    });
    return eintraege.map((_, i) => nah.has(i) || eintraege.length < 14);
  }, [eintraege]);
  const kosten = useMemo(() => eintraege.map((e) => (e.art === "-" ? 3 : e.art === "+" ? 1 + e.text.length / 1.4 : 0)), [eintraege]);
  const grenzen = useMemo(() => {
    let summe = 0;
    return kosten.map((k) => (summe += k));
  }, [kosten]);
  const gesamt = grenzen.at(-1) ?? 0;
  const p = useAblauf(gesamt, animieren, laeuft, Math.min(9000, Math.max(1200, gesamt * 18)));
  const tippt = p < gesamt;
  const plus = eintraege.filter((e) => e.art === "+").length;
  const minus = eintraege.filter((e) => e.art === "-").length;
  const ref = useFolgen(tippt, Math.floor(p / 8));
  const zeilen: ReactElement[] = [];
  let luecke = 0;
  eintraege.forEach((e, i) => {
    if (!sichtbar[i]) {
      luecke++;
      return;
    }
    if (luecke) {
      zeilen.push(
        <div key={`l${i}`} className="lw-c-luecke">
          {luecke} unveränderte Zeilen
        </div>
      );
      luecke = 0;
    }
    const start = grenzen[i - 1] ?? 0;
    if (e.art === "+" && p <= start) return;
    if (e.art === "+" && p < grenzen[i]) {
      const zeichen = Math.max(0, Math.floor((p - start - 1) * 1.4));
      zeilen.push(
        <div key={i} className="lw-c-zeile plus aktiv">
          <span className="lw-c-nr">{e.neu}</span>
          <span className="lw-c-zeichen">+</span>
          <code>
            {e.text.slice(0, zeichen)}
            <i className="lw-caret" />
          </code>
        </div>
      );
      return;
    }
    const weg = e.art === "-" && p >= grenzen[i];
    zeilen.push(<Zeile key={i} nummer={e.art === "+" ? e.neu ?? "" : e.alt ?? ""} text={e.text} sprache={sprache} zeichen={e.art === " " ? " " : e.art} klasse={e.art === "+" ? "plus" : e.art === "-" ? `minus ${weg ? "weg" : ""}` : ""} />);
  });
  if (luecke) zeilen.push(<div key="ende" className="lw-c-luecke">{luecke} unveränderte Zeilen</div>);
  const zeile = tippt ? "Jon ändert die Datei …" : laeuft ? "Jon speichert …" : "Änderung übernommen";

  return (
    <div className="lw-code">
      <div className="lw-zeile">
        {(tippt || laeuft) && <Loader2 className="lw-dreh" />}
        <span>{zeile}</span>
        <span className="lw-zahlen">
          <b className="plus">+{plus}</b>
          <b className="minus">−{minus}</b>
        </span>
      </div>
      <div className={`lw-editor diff ${kompakt ? "kompakt" : ""}`} ref={ref}>
        {zeilen}
      </div>
    </div>
  );
}

export function TerminalAnsicht({ befehl, shell, ergebnis, laeuft, animieren, kompakt }: { befehl: string; shell: string; ergebnis?: WerkstattErgebnis; laeuft: boolean; animieren: boolean; kompakt?: boolean }) {
  const getippt = useAblauf(befehl.length, animieren, true, Math.min(2600, Math.max(500, befehl.length * 26)));
  const befehlFertig = getippt >= befehl.length;
  const ausgabe = useMemo(() => {
    const teile: { text: string; fehler: boolean }[] = [];
    const normal = (ergebnis?.ausgabe ?? "").replace(/\r\n/g, "\n").trimEnd();
    const fehler = (ergebnis?.fehler ?? "").replace(/\r\n/g, "\n").trimEnd();
    if (normal) for (const text of normal.split("\n")) teile.push({ text, fehler: false });
    if (fehler) for (const text of fehler.split("\n")) teile.push({ text, fehler: true });
    return teile.slice(-400);
  }, [ergebnis?.ausgabe, ergebnis?.fehler]);
  const zeilen = useAblauf(befehlFertig && ergebnis ? ausgabe.length : 0, animieren, false, Math.min(4000, Math.max(500, ausgabe.length * 30)));
  const sekunden = useSekunden(laeuft && befehlFertig);
  const ref = useFolgen(true, zeilen + (befehlFertig ? 1 : 0));
  const prompt = shell === "PowerShell" ? "PS>" : shell === "cmd" ? ">" : "$";
  const ok = ergebnis ? ergebnis.ok : undefined;

  return (
    <div className="lw-code">
      <div className="lw-zeile">
        {laeuft && <Loader2 className="lw-dreh" />}
        <span>{laeuft ? (befehlFertig ? `Befehl läuft · ${sekunden} s` : "Jon tippt den Befehl …") : ok ? "Befehl erfolgreich" : "Befehl mit Fehler beendet"}</span>
        {ergebnis && ergebnis.exit_code !== undefined && ergebnis.exit_code !== null && (
          <span className={`lw-exit ${ok ? "ok" : "fehler"}`}>
            {ok ? <CheckCircle2 /> : <XCircle />}Exit {ergebnis.exit_code}
          </span>
        )}
      </div>
      <div className={`lw-terminal ${kompakt ? "kompakt" : ""}`} ref={ref}>
        <div className="lw-t-befehl">
          <span className="lw-t-prompt">{prompt}</span>
          <span>
            {befehl.slice(0, getippt)}
            {(!befehlFertig || (laeuft && !ergebnis)) && <i className="lw-caret" />}
          </span>
        </div>
        {befehlFertig && laeuft && !ergebnis && <div className="lw-t-warten">läuft …</div>}
        {ausgabe.slice(0, zeilen).map((z, i) => (
          <div key={i} className={`lw-t-zeile ${z.fehler ? "fehler" : ""}`}>
            {z.text || " "}
          </div>
        ))}
        {ergebnis && befehlFertig && !ausgabe.length && <div className="lw-t-warten">Keine Ausgabe</div>}
      </div>
    </div>
  );
}
