import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { JonDatei, dateiInhaltUrl, dateiOeffnen } from "../lib/api";

const TEXTARTIG = /^(text\/|application\/(json|yaml|xml|javascript|x-sh|sql))/;

const CODE_ENDUNGEN = new Set([
  "py", "js", "ts", "tsx", "jsx", "html", "css", "json", "yaml", "yml", "xml",
  "sql", "c", "cpp", "h", "hpp", "java", "rs", "go", "dart", "sh", "ps1", "bat",
  "ini", "toml", "env", "log", "csv",
]);

const NICHT_ANZEIGBAR: Record<string, string> = {
  dokument: "Word- und OpenDocument-Dateien kann Jon nicht selbst darstellen.",
  tabelle: "Tabellen zeigt Jon nicht selbst an.",
  praesentation: "Präsentationen zeigt Jon nicht selbst an.",
  "3d": "3D-Dateien zeigt Jon nicht selbst an.",
  archiv: "Archive lassen sich hier nicht öffnen.",
};

function endung(name: string): string {
  const teil = name.split(".").pop()?.toLowerCase();
  return teil && teil !== name.toLowerCase() ? teil : "";
}

function istText(datei: JonDatei): boolean {
  if (TEXTARTIG.test(datei.mimeType)) return true;
  return CODE_ENDUNGEN.has(endung(datei.name));
}

export default function DateiAnsicht({
  datei,
  onClose,
}: {
  datei: JonDatei;
  onClose: () => void;
}) {
  const [text, setText] = useState<string | null>(null);
  const [fehler, setFehler] = useState("");
  const [laedt, setLaedt] = useState(false);
  const [meldung, setMeldung] = useState("");

  const url = dateiInhaltUrl(datei.path);
  const art = datei.kind;
  const textartig = istText(datei);

  useEffect(() => {
    const beiTaste = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", beiTaste);
    return () => window.removeEventListener("keydown", beiTaste);
  }, [onClose]);

  useEffect(() => {
    if (!textartig) return;
    let abgebrochen = false;
    setLaedt(true);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.text();
      })
      .then((t) => {
        if (!abgebrochen) setText(t.slice(0, 400_000));
      })
      .catch(() => {
        if (!abgebrochen) setFehler("Die Datei ließ sich nicht lesen.");
      })
      .finally(() => {
        if (!abgebrochen) setLaedt(false);
      });
    return () => {
      abgebrochen = true;
    };
  }, [url, textartig]);

  const extern = async (ordner: boolean) => {
    setMeldung("");
    const ergebnis = await dateiOeffnen(datei.path, ordner);
    if (ergebnis?.error) setMeldung(ergebnis.error);
  };

  const inhalt = () => {
    if (art === "bild") {
      return (
        <img
          src={url}
          alt={datei.name}
          className="max-w-full max-h-full object-contain mx-auto"
        />
      );
    }
    if (art === "video") {
      return <video src={url} controls className="max-w-full max-h-full mx-auto" />;
    }
    if (art === "audio") {
      return (
        <div className="flex items-center justify-center h-full">
          <audio src={url} controls className="w-full max-w-lg" />
        </div>
      );
    }
    if (endung(datei.name) === "pdf") {
      return <iframe src={url} title={datei.name} className="w-full h-full border-0" />;
    }
    if (endung(datei.name) === "svg") {
      return (
        <img src={url} alt={datei.name} className="max-w-full max-h-full mx-auto" />
      );
    }
    if (textartig) {
      if (laedt) return <div className="text-white/50">wird geladen …</div>;
      if (fehler) return <div className="text-red-300/85">{fehler}</div>;
      return (
        <pre className="text-[12.5px] leading-relaxed whitespace-pre-wrap break-words font-mono text-white/85">
          {text}
        </pre>
      );
    }
    return (
      <div className="flex flex-col items-center justify-center h-full text-center gap-3">
        <span className="text-[46px]">📄</span>
        <div className="text-white/70 max-w-sm">
          {NICHT_ANZEIGBAR[art] ?? "Diesen Dateityp zeigt Jon nicht selbst an."}
        </div>
        <div className="text-[11px] text-white/40">
          Öffne sie im passenden Programm oder lade sie herunter.
        </div>
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.97, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        onClick={(e) => e.stopPropagation()}
        className="glass rounded-2xl border border-gold/25 w-[92%] max-w-4xl h-[86vh] flex flex-col overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-label={`Datei ${datei.name}`}
      >
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/10">
          <span className="text-[15px]">📄</span>
          <div className="min-w-0 flex-1">
            <div className="text-[13px] font-medium truncate">{datei.name}</div>
            <div className="text-[10.5px] text-white/40 truncate" title={datei.folder}>
              {datei.sizeText} · {datei.folder}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[12px] px-3 py-1 rounded-lg border border-white/15 text-white/70 hover:bg-white/5"
          >
            Schließen
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4 bg-black/25">{inhalt()}</div>

        <div className="flex flex-wrap items-center gap-2 px-4 py-2.5 border-t border-white/10">
          <button
            onClick={() => void extern(false)}
            className="text-[11.5px] px-3 py-1.5 rounded-lg bg-gold/80 text-black font-semibold"
          >
            Im Programm öffnen
          </button>
          <button
            onClick={() => void extern(true)}
            className="text-[11.5px] px-3 py-1.5 rounded-lg border border-gold/30 text-gold/85 hover:bg-gold/10"
          >
            Im Ordner öffnen
          </button>
          <a
            href={url}
            download={datei.name}
            className="text-[11.5px] px-3 py-1.5 rounded-lg border border-white/15 text-white/70 hover:bg-white/5"
          >
            Herunterladen
          </a>
          {meldung && (
            <span className="text-[11px] text-red-300/85 flex-1">{meldung}</span>
          )}
        </div>
      </motion.div>
    </div>
  );
}
