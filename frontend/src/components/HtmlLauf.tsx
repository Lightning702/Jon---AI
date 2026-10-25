import { useEffect, useMemo, useRef, useState } from "react";
import { SquareTerminal, Trash2 } from "lucide-react";
import { LAUF_SANDBOX, laufSeite } from "../lib/htmlLauf";
import "./code-block.css";

type Meldung = { art: string; text: string };

export default function HtmlLauf({ code, sprache = "html", takt = 0, className = "" }: { code: string; sprache?: string; takt?: number; className?: string }) {
  const kennung = useMemo(() => Math.random().toString(36).slice(2, 12), []);
  const rahmen = useRef<HTMLIFrameElement>(null);
  const puffer = useRef<Meldung[]>([]);
  const zeit = useRef(0);
  const [meldungen, setMeldungen] = useState<Meldung[]>([]);
  const [konsole, setKonsole] = useState(false);
  const dokument = useMemo(() => laufSeite(code, sprache, kennung), [code, sprache, kennung]);

  useEffect(() => {
    puffer.current = [];
    setMeldungen([]);
  }, [dokument, takt]);

  useEffect(() => {
    const leeren = () => {
      zeit.current = 0;
      const neu = puffer.current;
      puffer.current = [];
      if (!neu.length) return;
      setMeldungen((alt) => [...alt, ...neu].slice(-200));
      if (neu.some((m) => m.art === "error")) setKonsole(true);
    };
    const an = (e: MessageEvent) => {
      if (!rahmen.current || e.source !== rahmen.current.contentWindow) return;
      const daten = e.data as { jonLauf?: string; art?: string; text?: string } | null;
      if (!daten || daten.jonLauf !== kennung) return;
      puffer.current.push({ art: String(daten.art || "log"), text: String(daten.text ?? "") });
      if (puffer.current.length > 200) puffer.current = puffer.current.slice(-200);
      if (!zeit.current) zeit.current = window.setTimeout(leeren, 120);
    };
    window.addEventListener("message", an);
    return () => {
      window.removeEventListener("message", an);
      window.clearTimeout(zeit.current);
      zeit.current = 0;
    };
  }, [kennung]);

  const fehler = meldungen.filter((m) => m.art === "error").length;

  return (
    <div className={`hl ${className}`}>
      <iframe key={takt} ref={rahmen} title="Laufende Seite" sandbox={LAUF_SANDBOX} srcDoc={dokument} />
      <div className="hl-leiste">
        <button type="button" onClick={() => setKonsole((k) => !k)} aria-expanded={konsole}>
          <SquareTerminal size={12} />
          Konsole{meldungen.length ? ` · ${meldungen.length}` : ""}
          {fehler > 0 && <span className="hl-zahl">{fehler} Fehler</span>}
        </button>
        {konsole && meldungen.length > 0 && (
          <button type="button" onClick={() => setMeldungen([])} title="Konsole leeren">
            <Trash2 size={12} />
          </button>
        )}
      </div>
      {konsole && (
        <div className="hl-konsole" role="log">
          {meldungen.length ? meldungen.map((m, i) => <div key={i} className={`hl-z hl-${m.art}`}>{m.text}</div>) : <div className="hl-z hl-leer">Noch keine Ausgabe. console.log und Fehler deiner Seite erscheinen hier.</div>}
        </div>
      )}
    </div>
  );
}
