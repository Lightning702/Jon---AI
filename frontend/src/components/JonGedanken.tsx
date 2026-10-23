import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Brain, ChevronDown } from "lucide-react";
import "./gedanken.css";

function sekundenText(sekunden: number): string {
  if (sekunden < 60) return `${sekunden} s`;
  return `${Math.floor(sekunden / 60)} min ${sekunden % 60} s`;
}

export function useSekunden(aktiv: boolean): number {
  const start = useRef(Date.now());
  const [sekunden, setSekunden] = useState(0);
  useEffect(() => {
    if (!aktiv) return;
    const takt = window.setInterval(() => setSekunden(Math.floor((Date.now() - start.current) / 1000)), 1000);
    return () => window.clearInterval(takt);
  }, [aktiv]);
  return sekunden;
}

export default function JonGedanken({ text, denktNoch }: { text: string; denktNoch: boolean }) {
  const [offen, setOffen] = useState(false);
  const beginn = useRef(Date.now());
  const ende = useRef<number | null>(null);
  const feld = useRef<HTMLDivElement>(null);
  const laufend = useSekunden(denktNoch);
  if (!denktNoch && ende.current === null) ende.current = Date.now();
  const dauer = denktNoch ? laufend : Math.max(1, Math.round(((ende.current ?? Date.now()) - beginn.current) / 1000));
  const sichtbar = denktNoch || offen;

  useEffect(() => {
    const el = feld.current;
    if (el && denktNoch) el.scrollTop = el.scrollHeight;
  }, [text, denktNoch]);

  return (
    <div className={"jg " + (denktNoch ? "jg-aktiv" : "")}>
      <button type="button" className="jg-kopf" onClick={() => !denktNoch && setOffen((v) => !v)} aria-expanded={sichtbar}>
        <Brain size={13} />
        <span>{denktNoch ? "Jon denkt nach" : "Gedanken"}</span>
        <em>{denktNoch ? sekundenText(laufend) : `${sekundenText(dauer)} gedacht`}</em>
        {!denktNoch && <ChevronDown size={13} className={offen ? "jg-gedreht" : ""} />}
      </button>
      <AnimatePresence initial={false}>
        {sichtbar && (
          <motion.div
            ref={feld}
            className={"jg-text " + (denktNoch ? "jg-live" : "")}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            {text}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
