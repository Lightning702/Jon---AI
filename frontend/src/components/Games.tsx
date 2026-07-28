import { useCallback, useEffect, useRef, useState } from "react";
import {
  Spiel,
  SpielStatus,
  buildSpiel,
  getSpiele,
  spielSeitenUrl,
  spielVorschauUrl,
  startSpiel,
  stopSpiel,
} from "../lib/api";

const STATUS_TEXT: Record<SpielStatus, string> = {
  bereit: "bereit",
  laeuft: "läuft",
  baut: "wird gebaut …",
  nicht_gebaut: "noch nicht gebaut",
  fehler: "Fehler",
  fehlt: "Datei fehlt",
  nicht_verfuegbar: "nicht verfügbar",
};

const STATUS_STIL: Record<SpielStatus, string> = {
  bereit: "border-emerald-400/35 bg-emerald-400/10 text-emerald-300",
  laeuft: "border-sky-400/35 bg-sky-400/10 text-sky-300",
  baut: "border-gold/35 bg-gold/10 text-gold",
  nicht_gebaut: "border-white/15 bg-white/5 text-white/50",
  fehler: "border-rose-400/35 bg-rose-400/10 text-rose-300",
  fehlt: "border-rose-400/35 bg-rose-400/10 text-rose-300",
  nicht_verfuegbar: "border-white/15 bg-white/5 text-white/40",
};

export default function Games({ onClose, fokus }: { onClose: () => void; fokus?: string }) {
  const [spiele, setSpiele] = useState<Spiel[]>([]);
  const [laden, setLaden] = useState(true);
  const [fehler, setFehler] = useState("");
  const [busy, setBusy] = useState("");
  const [meldungen, setMeldungen] = useState<Record<string, string>>({});
  const [fehlerJeSpiel, setFehlerJeSpiel] = useState<Record<string, string>>({});
  const fokusRef = useRef<HTMLDivElement | null>(null);

  const laden_ = useCallback(async (frisch = false) => {
    try {
      setSpiele(await getSpiele(frisch));
      setFehler("");
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setLaden(false);
    }
  }, []);

  useEffect(() => {
    laden_(true);
  }, [laden_]);

  useEffect(() => {
    const timer = window.setInterval(() => laden_(), 5000);
    return () => window.clearInterval(timer);
  }, [laden_]);

  useEffect(() => {
    if (fokus && fokusRef.current) fokusRef.current.scrollIntoView({ block: "nearest" });
  }, [fokus, spiele.length]);

  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);

  const notiz = (id: string, text: string) => setMeldungen((m) => ({ ...m, [id]: text }));
  const problem = (id: string, text: string) => setFehlerJeSpiel((m) => ({ ...m, [id]: text }));

  const fuehreAus = async (spiel: Spiel, aktion: () => Promise<{ hinweis?: string; typ?: string; pfad?: string }>) => {
    setBusy(spiel.id);
    problem(spiel.id, "");
    notiz(spiel.id, "");
    try {
      const res = await aktion();
      if (res.typ === "web" && res.pfad) {
        const fenster = window.open(spielSeitenUrl(res.pfad), "_blank", "noopener");
        notiz(
          spiel.id,
          fenster
            ? `${spiel.titel} läuft jetzt in einem eigenen Tab.`
            : "Der Browser hat das neue Fenster blockiert — bitte Pop-ups für Jon erlauben."
        );
      } else if (res.hinweis) {
        notiz(spiel.id, res.hinweis);
      }
      await laden_(true);
    } catch (e) {
      problem(spiel.id, e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  };

  const karte = (spiel: Spiel) => {
    const arbeitet = busy === spiel.id;
    const startbar = spiel.status === "bereit" || spiel.status === "laeuft";
    const zeigeBauen = spiel.baubar && (spiel.status === "nicht_gebaut" || spiel.status === "fehler");

    return (
      <div
        key={spiel.id}
        ref={fokus === spiel.id ? fokusRef : undefined}
        className={`rounded-2xl border overflow-hidden flex flex-col transition ${
          fokus === spiel.id ? "border-gold/45 bg-gold/[0.06]" : "border-white/10 bg-white/[0.03]"
        }`}
      >
        <div className="relative h-32 shrink-0 bg-gradient-to-br from-white/10 to-black/40">
          {spiel.vorschau ? (
            <img
              src={spielVorschauUrl(spiel.id)}
              alt={spiel.titel}
              className="w-full h-full object-cover opacity-90"
              onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-4xl opacity-70">{spiel.icon}</div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent" />
          <div className="absolute left-3 right-3 bottom-2 flex items-end justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-white/95 truncate">
                {spiel.icon} {spiel.titel}
              </div>
              {spiel.genre && <div className="text-[10.5px] text-white/50 truncate">{spiel.genre}</div>}
            </div>
            <span className={`shrink-0 px-2 py-0.5 rounded-full border text-[9.5px] ${STATUS_STIL[spiel.status]}`}>
              {STATUS_TEXT[spiel.status]}
            </span>
          </div>
        </div>

        <div className="p-3.5 flex flex-col gap-2 flex-1">
          {spiel.kurz && <div className="text-[12px] text-gold/80 italic">{spiel.kurz}</div>}
          <div className="text-[12px] text-white/60 leading-relaxed">{spiel.beschreibung}</div>
          {spiel.steuerung && <div className="text-[10.5px] text-white/35 leading-relaxed">{spiel.steuerung}</div>}

          <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-white/30 mt-auto pt-1">
            {spiel.version && <span>Version {spiel.version}</span>}
            {spiel.herausgeber && <span>{spiel.herausgeber}</span>}
            {spiel.gebaut_am && <span>Stand {spiel.gebaut_am}</span>}
          </div>

          {(fehlerJeSpiel[spiel.id] || meldungen[spiel.id] || (spiel.hinweis && !startbar)) && (
            <div
              className={`text-[11px] rounded-lg px-2.5 py-1.5 border ${
                fehlerJeSpiel[spiel.id]
                  ? "border-rose-400/25 bg-rose-400/10 text-rose-200"
                  : "border-white/10 bg-white/5 text-white/55"
              }`}
            >
              {fehlerJeSpiel[spiel.id] || meldungen[spiel.id] || spiel.hinweis}
            </div>
          )}

          <div className="flex gap-1.5 pt-0.5">
            <button
              onClick={() => fuehreAus(spiel, () => startSpiel(spiel.id))}
              disabled={arbeitet || spiel.status === "baut"}
              className="flex-1 py-2 rounded-xl border border-gold/40 bg-gold/15 text-gold text-[12.5px] font-semibold hover:bg-gold/25 disabled:opacity-35 disabled:hover:bg-gold/15 transition"
            >
              {arbeitet ? "…" : spiel.status === "laeuft" ? "Nochmal starten" : "Starten"}
            </button>
            {zeigeBauen && (
              <button
                onClick={() => fuehreAus(spiel, () => buildSpiel(spiel.id))}
                disabled={arbeitet}
                className="px-3 py-2 rounded-xl border border-white/12 bg-white/5 text-white/60 text-[12px] hover:bg-white/10 disabled:opacity-40 transition"
              >
                Bauen
              </button>
            )}
            {spiel.status === "laeuft" && spiel.typ === "nativ" && (
              <button
                onClick={() => fuehreAus(spiel, () => stopSpiel(spiel.id))}
                disabled={arbeitet}
                className="px-3 py-2 rounded-xl border border-white/12 bg-white/5 text-white/60 text-[12px] hover:bg-white/10 disabled:opacity-40 transition"
              >
                Beenden
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={onClose}>
      <div
        className="glass rounded-2xl border border-white/15 w-[760px] max-w-[94vw] max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">🕹️</span>
            <span className="text-[14px] text-white/90">Spiele</span>
            <span className="text-[11px] text-white/35">starten erst auf Klick — Jon bleibt offen</span>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => laden_(true)}
              title="Liste neu einlesen"
              className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
            >
              ⟳
            </button>
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="p-4 overflow-y-auto">
          {fehler && (
            <div className="mb-3 text-[12px] rounded-xl border border-rose-400/25 bg-rose-400/10 text-rose-200 px-3 py-2">
              {fehler} — läuft das Jon-Backend?
            </div>
          )}
          {laden ? (
            <div className="text-[12px] text-white/40 py-8 text-center">Spiele werden gesucht …</div>
          ) : spiele.length === 0 ? (
            <div className="text-[12px] text-white/40 py-8 text-center">
              Keine Spiele gefunden. Lege einen Spielordner mit einer jon-spiele.json neben Jon ab.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{spiele.map(karte)}</div>
          )}
        </div>
      </div>
    </div>
  );
}
