import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, CornerDownRight, ListPlus, Loader2, MessageCircle, X } from "lucide-react";
import { btwFragen, btwHoeren, btwKontext, BtwQuelle, QUELLEN_NAME } from "../lib/btw";
import "./btw.css";

interface Eintrag {
  id: number;
  frage: string;
  antwort: string;
  art: string;
  quelle: BtwQuelle;
}

let laufend = 0;

function Text({ inhalt }: { inhalt: string }) {
  const teile = inhalt.replace(/^#{1,6}\s+/gm, "").split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <span>
      {teile.map((teil, index) =>
        teil.startsWith("**") && teil.endsWith("**") && teil.length > 4 ? (
          <b key={index}>{teil.slice(2, -2)}</b>
        ) : teil.startsWith("`") && teil.endsWith("`") && teil.length > 2 ? (
          <code key={index}>{teil.slice(1, -1)}</code>
        ) : (
          teil
        )
      )}
    </span>
  );
}

export default function BtwFenster() {
  const [offen, setOffen] = useState(false);
  const [text, setText] = useState("");
  const [eintraege, setEintraege] = useState<Eintrag[]>([]);
  const [quelle, setQuelle] = useState<BtwQuelle>("chat");
  const [arbeitet, setArbeitet] = useState(false);
  const feld = useRef<HTMLTextAreaElement>(null);
  const liste = useRef<HTMLDivElement>(null);

  const fragen = async (roh: string) => {
    const frage = roh.trim();
    if (!frage) return;
    const kontext = btwKontext();
    const id = ++laufend;
    setQuelle(kontext.quelle);
    setEintraege((alt) => [...alt.slice(-19), { id, frage, antwort: "", art: "wartet", quelle: kontext.quelle }]);
    try {
      const ergebnis = await btwFragen(frage, kontext);
      if (ergebnis.art === "nachauftrag" && ergebnis.auftrag && !kontext.taskId) kontext.nachauftrag?.(ergebnis.auftrag);
      setEintraege((alt) => alt.map((e) => (e.id === id ? { ...e, antwort: ergebnis.antwort, art: ergebnis.art } : e)));
    } catch (fehler) {
      setEintraege((alt) => alt.map((e) => (e.id === id ? { ...e, antwort: fehler instanceof Error ? fehler.message : String(fehler), art: "fehler" } : e)));
    }
  };

  useEffect(
    () =>
      btwHoeren((frage) => {
        const kontext = btwKontext();
        setQuelle(kontext.quelle);
        setArbeitet(!!kontext.arbeitet);
        setOffen(true);
        if (frage && frage.trim()) void fragen(frage);
        setTimeout(() => feld.current?.focus(), 40);
      }),
    []
  );

  useEffect(() => {
    const taste = (e: KeyboardEvent) => {
      if (e.altKey && !e.ctrlKey && !e.metaKey && (e.key === "b" || e.key === "B")) {
        e.preventDefault();
        setOffen((alt) => {
          if (!alt) {
            const kontext = btwKontext();
            setQuelle(kontext.quelle);
            setArbeitet(!!kontext.arbeitet);
            setTimeout(() => feld.current?.focus(), 40);
          }
          return !alt;
        });
      }
    };
    window.addEventListener("keydown", taste);
    return () => window.removeEventListener("keydown", taste);
  }, []);

  useEffect(() => {
    const el = liste.current;
    if (el) requestAnimationFrame(() => (el.scrollTop = el.scrollHeight));
  }, [eintraege, offen]);

  const senden = () => {
    const wert = text.trim();
    if (!wert) return;
    setText("");
    void fragen(wert);
  };

  return (
    <AnimatePresence>
      {offen && (
        <motion.div
          className="btw-fenster"
          role="dialog"
          aria-label="Nebenbei fragen"
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 12, scale: 0.98 }}
          transition={{ duration: 0.16 }}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              e.stopPropagation();
              setOffen(false);
            }
          }}
        >
          <header>
            <MessageCircle size={15} />
            <div>
              <strong>Nebenbei</strong>
              <span>
                {QUELLEN_NAME[quelle]}
                {arbeitet ? " · Jon arbeitet weiter" : ""}
              </span>
            </div>
            <button aria-label="Schließen" title="Schließen (Esc)" onClick={() => setOffen(false)}>
              <X size={15} />
            </button>
          </header>
          <div className="btw-liste" ref={liste}>
            {!eintraege.length && (
              <div className="btw-leer">
                <p>Frag Jon etwas, während er arbeitet – seine Arbeit läuft weiter.</p>
                <p>
                  Mit <b>danach: …</b> merkst du einen Auftrag vor, den Jon automatisch erledigt, sobald er fertig ist.
                </p>
                <div className="btw-beispiele">
                  {["Wie weit bist du?", "Was machst du gerade?", "danach: fass mir das Ergebnis kurz zusammen"].map((b) => (
                    <button key={b} onClick={() => void fragen(b)}>
                      {b}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {eintraege.map((e) => (
              <div key={e.id} className="btw-eintrag">
                <div className="btw-frage">{e.frage}</div>
                <div className={"btw-antwort " + e.art}>
                  {e.art === "wartet" ? (
                    <span className="btw-wartet">
                      <Loader2 size={13} className="btw-dreht" /> Jon überlegt …
                    </span>
                  ) : (
                    <>
                      {e.art === "nachauftrag" ? <ListPlus size={13} /> : <CornerDownRight size={13} />}
                      <Text inhalt={e.antwort} />
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="btw-eingabe">
            <textarea
              ref={feld}
              rows={1}
              value={text}
              maxLength={4000}
              placeholder="Frage stellen oder „danach: …“"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  senden();
                }
              }}
            />
            <button aria-label="Fragen" title="Fragen (Enter)" disabled={!text.trim()} onClick={senden}>
              <ArrowUp size={15} />
            </button>
          </div>
          <footer>Alt+B öffnet und schließt · Esc schließt</footer>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
