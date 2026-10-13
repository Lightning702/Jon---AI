import { useEffect, useRef, useState, type ComponentType } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, FileCode2, FileDiff, FileSpreadsheet, FileText, Loader2, Presentation, SquareTerminal } from "lucide-react";
import { dateiname, type RenderQuelle, type WerkstattDaten, type WerkstattErgebnis } from "../../lib/werkstatt";
import { GESEHEN, ruhigGewuenscht } from "./ablauf";
import { CodeAnsicht, DiffAnsicht, TerminalAnsicht } from "./CodeFenster";
import { FolienAenderungAnsicht, FolienAnsicht } from "./FolienBuehne";
import { DokumentAenderungAnsicht, DokumentAnsicht, formatName, TabellenAnsicht } from "./Schreibtisch";
import "./werkstatt.css";

export interface LiveWerkstattProps {
  daten: WerkstattDaten;
  ergebnis?: WerkstattErgebnis;
  laeuft: boolean;
  animieren?: boolean;
  kennung?: string;
  render?: RenderQuelle;
  kompakt?: boolean;
  startOffen?: boolean;
}

const SPRACHNAMEN: Record<string, string> = {
  python: "Python",
  typescript: "TypeScript",
  tsx: "TSX",
  javascript: "JavaScript",
  jsx: "JSX",
  json: "JSON",
  html: "HTML",
  css: "CSS",
  markdown: "Markdown",
  kotlin: "Kotlin",
  java: "Java",
  csharp: "C#",
  cpp: "C++",
  c: "C",
  rust: "Rust",
  go: "Go",
  bash: "Bash",
  powershell: "PowerShell",
  batch: "Batch",
  sql: "SQL",
  yaml: "YAML",
  toml: "TOML",
  xml: "XML",
  glsl: "GLSL",
  text: "Text",
};

function kopfVon(daten: WerkstattDaten): { icon: ComponentType<{ className?: string }>; titel: string; unter: string; pfad?: string } {
  switch (daten.art) {
    case "folien":
      return { icon: Presentation, titel: daten.titel || "Neue Präsentation", unter: `PowerPoint · ${daten.anzahl || daten.folien.length} Folien · Design ${daten.theme}`, pfad: daten.pfad };
    case "folien_aenderung":
      return { icon: Presentation, titel: dateiname(daten.pfad) || "Präsentation", unter: `PowerPoint bearbeiten · ${daten.aktionen.length} ${daten.aktionen.length === 1 ? "Schritt" : "Schritte"}`, pfad: daten.pfad };
    case "dokument":
      return { icon: FileText, titel: daten.titel || dateiname(daten.pfad) || "Dokument", unter: `${formatName(daten.format)} · ${dateiname(daten.pfad)}`, pfad: daten.pfad };
    case "dokument_aenderung":
      return { icon: FileText, titel: dateiname(daten.pfad) || "Dokument", unter: `Word bearbeiten · ${daten.aktionen.length} ${daten.aktionen.length === 1 ? "Schritt" : "Schritte"}`, pfad: daten.pfad };
    case "tabelle":
      return { icon: FileSpreadsheet, titel: daten.titel || dateiname(daten.pfad) || "Tabelle", unter: `${daten.format.toUpperCase()} · ${daten.zeilen.length} Zeilen`, pfad: daten.pfad };
    case "code":
      return { icon: FileCode2, titel: dateiname(daten.pfad) || "Neue Datei", unter: `${daten.anhaengen ? "Anhängen" : "Schreiben"} · ${SPRACHNAMEN[daten.sprache] ?? daten.sprache}`, pfad: daten.pfad };
    case "diff":
      return { icon: FileDiff, titel: dateiname(daten.pfad) || "Datei", unter: `Änderung · ${SPRACHNAMEN[daten.sprache] ?? daten.sprache}`, pfad: daten.pfad };
    case "terminal":
      return { icon: SquareTerminal, titel: daten.pruefung ? "Prüfung" : daten.shell, unter: daten.befehl.split("\n")[0].slice(0, 90) };
  }
}

export default function LiveWerkstatt({ daten, ergebnis, laeuft, animieren: animierenWunsch, kennung, render, kompakt = false, startOffen = true }: LiveWerkstattProps) {
  const [animieren] = useState(() => (animierenWunsch ?? laeuft) && !ruhigGewuenscht() && !(kennung && GESEHEN.has(kennung)));
  const zugeklappt = useRef(false);
  const [offen, setOffen] = useState(startOffen);
  useEffect(() => {
    if (kennung) GESEHEN.add(kennung);
  }, [kennung]);
  const kopf = kopfVon(daten);
  const Icon = kopf.icon;
  const status = laeuft ? "laeuft" : ergebnis && !ergebnis.ok ? "fehler" : "fertig";
  const bewegt = animieren && !zugeklappt.current;
  const gemeinsam = { laeuft, animieren: bewegt, ergebnis, render, kompakt };

  let inhalt = null;
  switch (daten.art) {
    case "folien":
      inhalt = <FolienAnsicht titel={daten.titel} farben={daten.farben} folien={daten.folien} {...gemeinsam} />;
      break;
    case "folien_aenderung":
      inhalt = <FolienAenderungAnsicht pfad={daten.pfad} aktionen={daten.aktionen} farben={daten.farben} {...gemeinsam} />;
      break;
    case "dokument":
      inhalt = <DokumentAnsicht titel={daten.titel} format={daten.format} bloecke={daten.bloecke} {...gemeinsam} />;
      break;
    case "dokument_aenderung":
      inhalt = <DokumentAenderungAnsicht pfad={daten.pfad} aktionen={daten.aktionen} {...gemeinsam} />;
      break;
    case "tabelle":
      inhalt = <TabellenAnsicht zeilen={daten.zeilen} laeuft={laeuft} animieren={bewegt} />;
      break;
    case "code":
      inhalt = <CodeAnsicht inhalt={daten.inhalt} sprache={daten.sprache} anhaengen={daten.anhaengen} laeuft={laeuft} animieren={bewegt} kompakt={kompakt} />;
      break;
    case "diff":
      inhalt = <DiffAnsicht alt={daten.alt} neu={daten.neu} sprache={daten.sprache} laeuft={laeuft} animieren={bewegt} kompakt={kompakt} />;
      break;
    case "terminal":
      inhalt = <TerminalAnsicht befehl={daten.befehl} shell={daten.shell} ergebnis={ergebnis} laeuft={laeuft} animieren={bewegt} kompakt={kompakt} />;
      break;
  }

  return (
    <div className={`lw lw-${status} ${kompakt ? "lw-kompakt" : ""}`}>
      <button
        type="button"
        className="lw-kopf"
        aria-expanded={offen}
        title={kopf.pfad || undefined}
        onClick={() => {
          if (offen) zugeklappt.current = true;
          setOffen((v) => !v);
        }}
      >
        <span className="lw-kopf-icon">
          <Icon />
        </span>
        <span className="lw-kopf-text">
          <strong>{kopf.titel}</strong>
          <small>{kopf.unter}</small>
        </span>
        <span className={`lw-pille ${status}`}>
          {status === "laeuft" ? (
            <>
              <Loader2 className="lw-dreh" />
              Live
            </>
          ) : status === "fehler" ? (
            "Fehler"
          ) : (
            "Fertig"
          )}
        </span>
        <ChevronDown className={`lw-pfeil ${offen ? "offen" : ""}`} />
      </button>
      <AnimatePresence initial={false}>
        {offen && (
          <motion.div className="lw-rumpf" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.24, ease: [0.2, 0.8, 0.2, 1] }}>
            <div className="lw-innen">
              {inhalt}
              {ergebnis && !ergebnis.ok && ergebnis.fehler && <p className="lw-fehler">{ergebnis.fehler}</p>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
