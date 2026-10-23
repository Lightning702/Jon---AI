import { useMemo, useState } from "react";
import { Box, Check, Copy, Eye, EyeOff, Loader2, Maximize2, Play, RotateCw, Save } from "lucide-react";
import { AUSFUEHRBAR, dateinameFuer, Lauf, testumgebung, testumgebungOeffnen, vorschauAdresse, VORSCHAUBAR } from "../lib/testumgebung";
import "./code-block.css";

const NAMEN: Record<string, string> = { html: "HTML", htm: "HTML", svg: "SVG", python: "Python", py: "Python", javascript: "JavaScript", js: "JavaScript", node: "Node.js", php: "PHP", bash: "Bash", sh: "Shell", shell: "Shell", powershell: "PowerShell", ps1: "PowerShell", css: "CSS", json: "JSON", typescript: "TypeScript", ts: "TypeScript", tsx: "TSX", jsx: "JSX", sql: "SQL", java: "Java", cpp: "C++", c: "C", csharp: "C#", cs: "C#", go: "Go", rust: "Rust", yaml: "YAML", xml: "XML", markdown: "Markdown", md: "Markdown" };

function seite(sprache: string, code: string): string {
  if (sprache === "svg") return `<!doctype html><html><body style="margin:0;display:grid;place-items:center;min-height:100vh;background:#fff">${code}</body></html>`;
  return code;
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
  const [kopiert, setKopiert] = useState(false);
  const [vorschau, setVorschau] = useState(false);
  const [takt, setTakt] = useState(0);
  const [laeuft, setLaeuft] = useState(false);
  const [lauf, setLauf] = useState<Lauf | null>(null);
  const [fehler, setFehler] = useState("");
  const [gespeichert, setGespeichert] = useState("");
  const zeilen = useMemo(() => code.split("\n").length, [code]);
  const name = NAMEN[art] || (art ? art.toUpperCase() : "Code");
  const dateiname = useMemo(() => dateinameFuer(art, code), [art, code]);

  const kopieren = async () => {
    try {
      await navigator.clipboard.writeText(code);
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
      setLauf(await testumgebung.code("standard", art, code, dateiname));
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setLaeuft(false);
    }
  };

  const speichern = async () => {
    setFehler("");
    try {
      const ergebnis = await testumgebung.schreiben("standard", dateiname, code);
      setGespeichert(ergebnis.pfad);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    }
  };

  const groesser = async () => {
    try {
      await testumgebung.schreiben("standard", dateiname, code);
      testumgebungOeffnen("standard", dateiname);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="cb">
      <div className="cb-kopf">
        <span className="cb-sprache">{name}</span>
        <span className="cb-zeilen">{zeilen} {zeilen === 1 ? "Zeile" : "Zeilen"}</span>
        {!fertig && <span className="cb-schreibt"><Loader2 size={11} className="cb-dreh" />Jon schreibt …</span>}
        <div className="cb-knoepfe">
          {kannVorschau && (
            <button type="button" disabled={!fertig} onClick={() => setVorschau((v) => !v)} title="Direkt hier ansehen und ausprobieren">
              {vorschau ? <EyeOff size={13} /> : <Eye size={13} />}
              {vorschau ? "Ausblenden" : "Vorschau"}
            </button>
          )}
          {kannAusfuehren && (
            <button type="button" disabled={!fertig || laeuft} onClick={() => void ausfuehren()} title="In Jons Testumgebung ausführen">
              {laeuft ? <Loader2 size={13} className="cb-dreh" /> : <Play size={13} />}
              Ausführen
            </button>
          )}
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
      <pre className="cb-code">
        <code>{code}</code>
      </pre>
      {vorschau && kannVorschau && fertig && (
        <div className="cb-vorschau">
          <div className="cb-vorschau-leiste">
            <span>Live-Vorschau · läuft abgeschottet</span>
            <button type="button" onClick={() => setTakt((t) => t + 1)} title="Neu laden"><RotateCw size={12} /></button>
            <button type="button" onClick={() => void groesser()} title="Groß in der Testumgebung"><Maximize2 size={12} /></button>
          </div>
          <iframe key={takt} title={`Vorschau ${dateiname}`} sandbox="allow-scripts allow-modals allow-pointer-lock allow-forms allow-popups" srcDoc={seite(art, code)} />
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
