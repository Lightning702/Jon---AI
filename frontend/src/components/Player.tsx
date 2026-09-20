import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  mediathekBildUrl,
  mediathekDateiUrl,
  mediathekListe,
  mediathekLoeschen,
} from "../lib/api";
import type { MediaEintrag } from "../lib/api";

function dauerText(sekunden: number): string {
  const ganz = Math.max(0, Math.floor(sekunden));
  const stunden = Math.floor(ganz / 3600);
  const minuten = Math.floor((ganz % 3600) / 60);
  const rest = ganz % 60;
  const zwei = (w: number) => String(w).padStart(2, "0");
  if (stunden) return `${stunden}:${zwei(minuten)}:${zwei(rest)}`;
  return `${minuten}:${zwei(rest)}`;
}

function groesseText(bytes: number): string {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(0)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export default function Player({ onClose }: { onClose: () => void }) {
  const [eintraege, setEintraege] = useState<MediaEintrag[]>([]);
  const [ordner, setOrdner] = useState("");
  const [gesamt, setGesamt] = useState(0);
  const [aktiv, setAktiv] = useState("");
  const [filter, setFilter] = useState<"alle" | "video" | "musik">("alle");
  const [suche, setSuche] = useState("");
  const [laedt, setLaedt] = useState(true);
  const [fehler, setFehler] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  const laden = useCallback(async () => {
    try {
      const daten = await mediathekListe();
      setEintraege(daten.eintraege);
      setOrdner(daten.ordner);
      setGesamt(daten.groesse);
      setFehler("");
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setLaedt(false);
    }
  }, []);

  useEffect(() => {
    void laden();
  }, [laden]);

  useEffect(() => {
    const zu = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", zu);
    return () => window.removeEventListener("keydown", zu);
  }, [onClose]);

  const sichtbar = useMemo(() => {
    const wort = suche.trim().toLowerCase();
    return eintraege.filter(
      (e) =>
        (filter === "alle" || e.art === filter) &&
        (!wort ||
          e.name.toLowerCase().includes(wort) ||
          e.kanal.toLowerCase().includes(wort))
    );
  }, [eintraege, filter, suche]);

  const gewaehlt = sichtbar.find((e) => e.id === aktiv) ?? null;

  const weiter = (richtung: number) => {
    if (!sichtbar.length) return;
    const stelle = sichtbar.findIndex((e) => e.id === aktiv);
    const naechste = sichtbar[(stelle + richtung + sichtbar.length) % sichtbar.length];
    if (naechste) setAktiv(naechste.id);
  };

  const entfernen = async (id: string) => {
    try {
      await mediathekLoeschen(id);
    } catch {
      /* die Liste wird ohnehin neu geladen */
    }
    if (aktiv === id) setAktiv("");
    await laden();
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-5xl h-[86vh] flex flex-col rounded-2xl border border-white/10 bg-[#0d0d12] shadow-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-white/10">
          <span className="text-[13px] text-white/90 font-medium">Player</span>
          <span className="text-[10.5px] text-white/35">
            {eintraege.length} Aufnahmen · {groesseText(gesamt)} · offline verfügbar
          </span>
          <div className="flex-1" />
          <input
            value={suche}
            onChange={(e) => setSuche(e.target.value)}
            placeholder="Suchen …"
            className="w-40 bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white/85 placeholder-white/25 outline-none focus:border-gold/50"
          />
          <div className="flex rounded-lg border border-white/10 overflow-hidden">
            {(["alle", "video", "musik"] as const).map((art) => (
              <button
                key={art}
                onClick={() => setFilter(art)}
                className={`px-2.5 py-1 text-[10.5px] transition ${
                  filter === art
                    ? "bg-white/15 text-white/90"
                    : "text-white/45 hover:text-white/75"
                }`}
              >
                {art === "alle" ? "Alle" : art === "video" ? "Videos" : "Musik"}
              </button>
            ))}
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg border border-white/10 text-white/50 hover:bg-white/10 transition"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 flex min-h-0">
          <div className="w-[290px] shrink-0 border-r border-white/10 overflow-y-auto">
            {laedt && (
              <div className="p-4 text-[11px] text-white/40">Lade Mediathek …</div>
            )}
            {!laedt && !sichtbar.length && (
              <div className="p-4 text-[11px] leading-relaxed text-white/40">
                Noch nichts da. Lade im Downloader ein Video oder einen Song — Jon
                legt alles hier ab, damit du es jederzeit offline anschauen kannst.
              </div>
            )}
            {sichtbar.map((eintrag) => (
              <button
                key={eintrag.id}
                onClick={() => setAktiv(eintrag.id)}
                className={`w-full flex gap-2.5 px-2.5 py-2 text-left border-b border-white/5 transition ${
                  eintrag.id === aktiv ? "bg-white/[0.09]" : "hover:bg-white/[0.05]"
                }`}
              >
                <div className="w-[62px] h-[38px] shrink-0 rounded-md overflow-hidden bg-white/[0.06] flex items-center justify-center">
                  {eintrag.bild ? (
                    <img
                      src={mediathekBildUrl(eintrag.id)}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span className="text-[15px] opacity-50">
                      {eintrag.art === "musik" ? "♪" : "▶"}
                    </span>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] text-white/85 leading-snug line-clamp-2">
                    {eintrag.name}
                  </div>
                  <div className="text-[9.5px] text-white/35 mt-0.5 truncate">
                    {eintrag.kanal || (eintrag.art === "musik" ? "Musik" : "Video")}
                    {eintrag.dauer ? ` · ${dauerText(eintrag.dauer)}` : ""} ·{" "}
                    {groesseText(eintrag.groesse)}
                  </div>
                </div>
              </button>
            ))}
          </div>

          <div className="flex-1 flex flex-col min-w-0">
            {!gewaehlt && (
              <div className="flex-1 flex items-center justify-center text-[11.5px] text-white/30">
                {fehler || "Wähl links eine Aufnahme aus."}
              </div>
            )}
            {gewaehlt && (
              <>
                <div className="flex-1 min-h-0 bg-black flex items-center justify-center">
                  {gewaehlt.art === "video" ? (
                    <video
                      ref={videoRef}
                      key={gewaehlt.id}
                      src={mediathekDateiUrl(gewaehlt.id)}
                      controls
                      autoPlay
                      onEnded={() => weiter(1)}
                      className="max-h-full max-w-full"
                    />
                  ) : (
                    <div className="flex flex-col items-center gap-4 px-8">
                      <div className="w-40 h-40 rounded-2xl overflow-hidden bg-white/[0.06] flex items-center justify-center">
                        {gewaehlt.bild ? (
                          <img
                            src={mediathekBildUrl(gewaehlt.id)}
                            alt=""
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <span className="text-[46px] opacity-40">♪</span>
                        )}
                      </div>
                      <audio
                        ref={audioRef}
                        key={gewaehlt.id}
                        src={mediathekDateiUrl(gewaehlt.id)}
                        controls
                        autoPlay
                        onEnded={() => weiter(1)}
                        className="w-[360px]"
                      />
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 px-4 py-2.5 border-t border-white/10">
                  <div className="min-w-0 flex-1">
                    <div className="text-[12px] text-white/90 truncate">
                      {gewaehlt.name}
                    </div>
                    <div className="text-[10px] text-white/35 truncate">
                      {gewaehlt.kanal}
                      {gewaehlt.kanal && gewaehlt.quelle ? " · " : ""}
                      {gewaehlt.quelle}
                    </div>
                  </div>
                  <button
                    onClick={() => weiter(-1)}
                    className="px-2.5 py-1 rounded-lg border border-white/10 text-[11px] text-white/60 hover:bg-white/10 transition"
                  >
                    ‹ Zurück
                  </button>
                  <button
                    onClick={() => weiter(1)}
                    className="px-2.5 py-1 rounded-lg border border-white/10 text-[11px] text-white/60 hover:bg-white/10 transition"
                  >
                    Weiter ›
                  </button>
                  <button
                    onClick={() => void entfernen(gewaehlt.id)}
                    className="px-2.5 py-1 rounded-lg border border-red-300/20 bg-red-400/10 text-[11px] text-red-200/80 hover:bg-red-400/20 transition"
                  >
                    Löschen
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {ordner && (
          <div className="px-4 py-1.5 border-t border-white/10 text-[9.5px] text-white/25 truncate">
            {ordner}
          </div>
        )}
      </div>
    </div>
  );
}
