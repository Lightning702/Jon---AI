import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Box, Check, Code2, Copy, EyeOff, Loader2, Maximize2, Pencil, Play, RotateCw, Save, Undo2 } from "lucide-react";
import { AUSFUEHRBAR, dateinameFuer, Lauf, testumgebung, testumgebungOeffnen, vorschauAdresse, VORSCHAUBAR } from "../lib/testumgebung";
import { useVerzoegert } from "../lib/htmlLauf";
import HtmlLauf from "./HtmlLauf";
import "./code-block.css";

const NAMEN: Record<string, string> = { html: "HTML", htm: "HTML", svg: "SVG", python: "Python", py: "Python", javascript: "JavaScript", js: "JavaScript", node: "Node.js", php: "PHP", bash: "Bash", sh: "Shell", shell: "Shell", powershell: "PowerShell", ps1: "PowerShell", css: "CSS", json: "JSON", typescript: "TypeScript", ts: "TypeScript", tsx: "TSX", jsx: "JSX", sql: "SQL", java: "Java", cpp: "C++", c: "C", csharp: "C#", cs: "C#", go: "Go", rust: "Rust", yaml: "YAML", xml: "XML", markdown: "Markdown", md: "Markdown" };

export function jonCodeOeffnen(pfad: string): void {
  window.dispatchEvent(new CustomEvent("jon-code-oeffnen", { detail: pfad }));
}

export function TestVorschau({ pfad, titel }: { pfad: string; titel?: string }) {
  const [takt, setTakt] = useState(0);
  const teile = pfad.replace(/^\/testumgebung-vorschau\//, "").split("/");
  const umgebung = teile.shift() || "standard";
  const datei = decodeURIComponent(teile.join("/"));
  return (
    <div className="cb cb-karte">
      <div className="cb-kopf">
        <span className="cb-sprache"><Box size={12} /> Testumgebung</span>
        <span className="cb-zeilen">{titel || datei}</span>
        <div className="cb-knoepfe">
          <button type="button" onClick={() => setTakt((t) => t + 1)} title="Neu laden"><RotateCw size={13} />Neu laden</button>
          <button type="button" onClick={() => testumgebungOeffnen(umgebung, datei)} title="Mit Editor und Terminal öffnen"><Maximize2 size={13} />Öffnen</button>
        </div>
      </div>
      <div className="cb-vorschau">
        <iframe key={takt} title={`Vorschau ${datei}`} src={vorschauAdresse(pfad)} sandbox="allow-scripts allow-modals allow-pointer-lock allow-forms allow-popups" />
      </div>
    </div>
  );
}

export default function CodeBlock({ sprache, code, fertig = true }: { sprache: string; code: string; fertig?: boolean }) {
  const art = sprache.toLowerCase();
  const kannVorschau = VORSCHAUBAR.has(art);
  const kannAusfuehren = AUSFUEHRBAR.has(art);
  const [eigen, setEigen] = useState<string | null>(null);
  const [bearbeiten, setBearbeiten] = useState(false);
  const [kopiert, setKopiert] = useState(false);
  const [vorschau, setVorschau] = useState(false);
  const [takt, setTakt] = useState(0);
  const [laeuft, setLaeuft] = useState(false);
  const [lauf, setLauf] = useState<Lauf | null>(null);
  const [fehler, setFehler] = useState("");
  const [gespeichert, setGespeichert] = useState("");
  const feld = useRef<HTMLTextAreaElement>(null);
  const aktuell = eigen ?? code;
  const geaendert = eigen !== null && eigen !== code;
  const vorschauCode = useVerzoegert(aktuell, bearbeiten ? 350 : 0);
  const zeilen = useMemo(() => aktuell.split("\n").length, [aktuell]);
  const name = NAMEN[art] || (art ? art.toUpperCase() : "Code");
  const dateiname = useMemo(() => dateinameFuer(art, aktuell), [art, aktuell]);

  useLayoutEffect(() => {
    const el = feld.current;
    if (!el || !bearbeiten) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight + 2, 416) + "px";
  }, [aktuell, bearbeiten]);

  useEffect(() => {
    if (bearbeiten) feld.current?.focus({ preventScroll: true });
  }, [bearbeiten]);

  useEffect(() => {
    setGespeichert("");
  }, [aktuell]);

  const kopieren = async () => {
    try {
      await navigator.clipboard.writeText(aktuell);
      setKopiert(true);
      setTimeout(() => setKopiert(false), 1600);
    } catch {
      setFehler("Kopieren ging nicht – markiere den Code und drück Strg+C.");
    }
  };

  const ausfuehren = async () => {
    setLaeuft(true);
    setFehler("");
    setLauf(null);
    try {
      setLauf(await testumgebung.code("standard", art, aktuell, dateiname));
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setLaeuft(false);
    }
  };

  const starten = () => {
    if (kannVorschau) {
      setVorschau(true);
      setTakt((t) => t + 1);
    } else if (kannAusfuehren) void ausfuehren();
  };

  const speichern = async () => {
    setFehler("");
    try {
      const ergebnis = await testumgebung.schreiben("standard", dateiname, aktuell);
      setGespeichert(ergebnis.pfad);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    }
  };

  const groesser = async () => {
    try {
      await testumgebung.schreiben("standard", dateiname, aktuell);
      testumgebungOeffnen("standard", dateiname);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    }
  };

  const inJonCode = async () => {
    setFehler("");
    try {
      const ergebnis = await testumgebung.schreiben("standard", dateiname, aktuell);
      const umgebung = await testumgebung.beschreiben("standard");
      const trenner = umgebung.pfad.includes("\\") ? "\\" : "/";
      jonCodeOeffnen(umgebung.pfad.replace(/[\\/]+$/, "") + trenner + ergebnis.pfad.replace(/[\\/]/g, trenner));
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    }
  };

  const tasten = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const el = e.currentTarget;
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      starten();
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      setBearbeiten(false);
      return;
    }
    if (e.key === "Tab" && !e.ctrlKey && !e.altKey && !e.metaKey) {
      e.preventDefault();
      const { selectionStart: a, selectionEnd: b, value } = el;
      if (e.shiftKey) {
        const zeile = value.lastIndexOf("\n", a - 1) + 1;
        const weg = value.slice(zeile, zeile + 2).match(/^ {1,2}/)?.[0].length || 0;
        if (!weg) return;
        setEigen(value.slice(0, zeile) + value.slice(zeile + weg));
        requestAnimationFrame(() => el.setSelectionRange(Math.max(zeile, a - weg), Math.max(zeile, b - weg)));
        return;
      }
      setEigen(value.slice(0, a) + "  " + value.slice(b));
      requestAnimationFrame(() => el.setSelectionRange(a + 2, a + 2));
    }
  };

  return (
    <div className="cb">
      <div className="cb-kopf">
        <span className="cb-sprache">{name}</span>
        <span className="cb-zeilen">{zeilen} {zeilen === 1 ? "Zeile" : "Zeilen"}</span>
        {geaendert && <span className="cb-geaendert">bearbeitet</span>}
        {!fertig && <span className="cb-schreibt"><Loader2 size={11} className="cb-dreh" />Jon schreibt …</span>}
        <div className="cb-knoepfe">
          {kannVorschau && (
            <button type="button" disabled={!fertig} onClick={() => (vorschau ? setVorschau(false) : starten())} title="Direkt hier in Jon ausführen">
              {vorschau ? <EyeOff size={13} /> : <Play size={13} />}
              {vorschau ? "Ausblenden" : "Ausführen"}
            </button>
          )}
          {kannAusfuehren && (
            <button type="button" disabled={!fertig || laeuft} onClick={() => void ausfuehren()} title="In Jons Testumgebung ausführen">
              {laeuft ? <Loader2 size={13} className="cb-dreh" /> : <Play size={13} />}
              Ausführen
            </button>
          )}
          <button type="button" disabled={!fertig} onClick={() => setBearbeiten((b) => !b)} title={bearbeiten ? "Bearbeiten beenden (Esc)" : "Code direkt hier bearbeiten"}>
            {bearbeiten ? <Check size={13} /> : <Pencil size={13} />}
            {bearbeiten ? "Fertig" : "Bearbeiten"}
          </button>
          {geaendert && (
            <button type="button" onClick={() => setEigen(null)} title="Jons ursprünglichen Code wiederherstellen">
              <Undo2 size={13} />
              Zurücksetzen
            </button>
          )}
          <button type="button" disabled={!fertig} onClick={() => void inJonCode()} title="Als Datei in Jon Code öffnen – mit Editor und Live-Vorschau">
            <Code2 size={13} />
            Jon Code
          </button>
          <button type="button" disabled={!fertig} onClick={() => void speichern()} title={`In der Testumgebung als ${dateiname} speichern`}>
            {gespeichert ? <Check size={13} /> : <Save size={13} />}
            {gespeichert ? "Gespeichert" : "Speichern"}
          </button>
          <button type="button" disabled={!fertig} onClick={() => void groesser()} title="In der Testumgebung öffnen – mit Editor, Terminal und großer Vorschau">
            <Box size={13} />
            Testumgebung
          </button>
          <button type="button" onClick={() => void kopieren()} title="Code kopieren">
            {kopiert ? <Check size={13} /> : <Copy size={13} />}
            {kopiert ? "Kopiert" : "Kopieren"}
          </button>
        </div>
      </div>
      {bearbeiten ? (
        <>
          <textarea
            ref={feld}
            value={aktuell}
            onChange={(e) => setEigen(e.target.value)}
            onKeyDown={tasten}
            spellCheck={false}
            autoCapitalize="off"
            autoCorrect="off"
            aria-label={`${name}-Code bearbeiten`}
            className="cb-code cb-edit"
          />
          <div className="cb-tipp">
            {kannVorschau ? "Die Vorschau läuft live mit. " : ""}
            <kbd>Strg</kbd>+<kbd>Enter</kbd> {kannVorschau || kannAusfuehren ? "führt aus" : "–"} · <kbd>Tab</kbd> rückt ein · <kbd>Esc</kbd> beendet
          </div>
        </>
      ) : (
        <pre className="cb-code" onDoubleClick={() => fertig && setBearbeiten(true)}>
          <code>{aktuell}</code>
        </pre>
      )}
      {vorschau && kannVorschau && fertig && (
        <div className="cb-vorschau">
          <div className="cb-vorschau-leiste">
            <span>Läuft direkt in Jon · abgeschottet{bearbeiten ? " · aktualisiert beim Tippen" : ""}</span>
            <button type="button" onClick={() => setTakt((t) => t + 1)} title="Neu starten"><RotateCw size={12} /></button>
            <button type="button" onClick={() => void groesser()} title="Groß in der Testumgebung"><Maximize2 size={12} /></button>
          </div>
          <HtmlLauf code={vorschauCode} sprache={art} takt={takt} />
        </div>
      )}
      {(lauf || fehler || gespeichert) && (
        <div className="cb-ergebnis">
          {gespeichert && !lauf && !fehler && (
            <p className="cb-hinweis">
              Liegt in der Testumgebung als <b>{gespeichert}</b>.{" "}
              <button type="button" onClick={() => testumgebungOeffnen("standard", gespeichert)}>Öffnen</button>
            </p>
          )}
          {fehler && <p className="cb-fehler">{fehler}</p>}
          {lauf && (
            <>
              <div className="cb-status">
                <span className={lauf.exit === 0 ? "ok" : "nok"}>{lauf.abgebrochen ? "Abgebrochen (Zeitlimit)" : lauf.exit === 0 ? "Erfolgreich" : `Exit-Code ${lauf.exit}`}</span>
                {typeof lauf.dauer === "number" && <span>{lauf.dauer.toFixed(1)} s</span>}
                <button type="button" onClick={() => testumgebungOeffnen(lauf.umgebung || "standard", lauf.datei || "")}>Im Terminal weiter</button>
              </div>
              <pre className="cb-ausgabe">{lauf.ausgabe?.trim() || "Keine Ausgabe."}</pre>
              {lauf.vorschau && <iframe className="cb-php" title="Ausgabe als Seite" src={vorschauAdresse(lauf.vorschau)} sandbox="allow-scripts allow-forms" />}
            </>
          )}
        </div>
      )}
    </div>
  );
}
