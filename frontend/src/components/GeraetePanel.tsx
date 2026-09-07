import { useEffect, useRef, useState } from "react";
import {
  HandyGeraet,
  getUserSettings,
  handyDateiSenden,
  handyGeraetLoeschen,
  handyGeraetStand,
  handyGeraetUmbenennen,
  handyGeraete,
  handyRechtSetzen,
  saveUserSettings,
} from "../lib/api";

const STUFEN: { id: string; titel: string; hinweis: string }[] = [
  {
    id: "standard",
    titel: "Standard",
    hinweis: "Gerätestatus und Dateiübertragung",
  },
  {
    id: "persoenlich",
    titel: "Persönlich",
    hinweis: "Nur mit deiner ausdrücklichen Freigabe",
  },
  {
    id: "sensibel",
    titel: "Sensibel",
    hinweis: "Das Handy fragt zusätzlich jedes Mal nach",
  },
];

const REIHE = [
  "status",
  "dateien",
  "hinweise",
  "zwischenablage",
  "standort",
  "kontakte",
  "kamera",
  "mikrofon",
];

function zeitpunkt(wert: number): string {
  if (!wert) return "unbekannt";
  const abstand = Date.now() / 1000 - wert;
  if (abstand < 90) return "jetzt";
  if (abstand < 3600) return `vor ${Math.round(abstand / 60)} Min.`;
  if (abstand < 86400) return `vor ${Math.round(abstand / 3600)} Std.`;
  return new Date(wert * 1000).toLocaleDateString("de-AT");
}

function Schalter({
  an,
  aus,
  beiWechsel,
}: {
  an: boolean;
  aus?: boolean;
  beiWechsel: (wert: boolean) => void;
}) {
  return (
    <button
      onClick={() => beiWechsel(!an)}
      disabled={aus}
      className={
        "relative h-[18px] w-[34px] rounded-full transition-colors " +
        (an ? "bg-gold/70" : "bg-white/15") +
        (aus ? " opacity-40" : "")
      }
    >
      <span
        className={
          "absolute top-[2px] h-[14px] w-[14px] rounded-full bg-white transition-all " +
          (an ? "left-[18px]" : "left-[2px]")
        }
      />
    </button>
  );
}

export default function GeraetePanel({ onPair }: { onPair: () => void }) {
  const [geraete, setGeraete] = useState<HandyGeraet[]>([]);
  const [fehler, setFehler] = useState("");
  const [info, setInfo] = useState("");
  const [pfade, setPfade] = useState<Record<string, string>>({});
  const [laeuft, setLaeuft] = useState("");
  const [ordner, setOrdner] = useState("");
  const [ordnerGemerkt, setOrdnerGemerkt] = useState(false);
  const takt = useRef<number | null>(null);

  const laden = async () => {
    try {
      const daten = await handyGeraete();
      setGeraete(daten.geraete);
    } catch {
      setGeraete([]);
    }
  };

  useEffect(() => {
    void (async () => {
      try {
        const werte = await getUserSettings();
        setOrdner(werte.handy_ordner ?? "");
      } catch {
        setOrdner("");
      }
    })();
  }, []);

  const ordnerSpeichern = async () => {
    setFehler("");
    try {
      await saveUserSettings({ handy_ordner: ordner.trim() });
      setOrdnerGemerkt(true);
      window.setTimeout(() => setOrdnerGemerkt(false), 2000);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Ordner nicht gespeichert");
    }
  };

  useEffect(() => {
    void laden();
    takt.current = window.setInterval(() => void laden(), 6000);
    return () => {
      if (takt.current !== null) window.clearInterval(takt.current);
    };
  }, []);

  const setzen = async (id: string, recht: string, wert: boolean) => {
    setFehler("");
    try {
      const antwort = await handyRechtSetzen(id, recht, wert);
      setGeraete((liste) =>
        liste.map((g) => (g.id === id ? { ...g, rechte: antwort.rechte } : g))
      );
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Nicht gespeichert");
    }
  };

  const umbenennen = async (geraet: HandyGeraet) => {
    const name = window.prompt("Wie soll das Gerät heißen?", geraet.name);
    if (!name) return;
    try {
      await handyGeraetUmbenennen(geraet.id, name);
      void laden();
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Nicht gespeichert");
    }
  };

  const auffrischen = async (geraet: HandyGeraet) => {
    setLaeuft(geraet.id);
    setInfo("");
    setFehler("");
    try {
      const stand = await handyGeraetStand(geraet.id);
      const meldung = stand["hinweis"];
      if (typeof meldung === "string" && meldung) setInfo(meldung);
      void laden();
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Das Handy meldet sich nicht");
    } finally {
      setLaeuft("");
    }
  };

  const senden = async (geraet: HandyGeraet) => {
    const pfad = (pfade[geraet.id] ?? "").trim();
    if (!pfad) return;
    setLaeuft(geraet.id);
    setInfo("");
    setFehler("");
    try {
      const ergebnis = await handyDateiSenden(geraet.id, pfad);
      const ziel = ergebnis["gespeichert"];
      setInfo(
        typeof ziel === "string" && ziel
          ? `Auf dem Handy gespeichert: ${ziel}`
          : "Datei ist beim Handy angekommen."
      );
      setPfade((alt) => ({ ...alt, [geraet.id]: "" }));
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Übertragung fehlgeschlagen");
    } finally {
      setLaeuft("");
    }
  };

  const trennen = async (geraet: HandyGeraet) => {
    if (!window.confirm(`${geraet.name} wirklich trennen?`)) return;
    await handyGeraetLoeschen(geraet.id);
    void laden();
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-white/40 leading-relaxed pr-3">
          Gekoppelte Android-Geräte. Jon nutzt nur die Funktionen, die hier
          eingeschaltet sind – und nur, wenn das Handy sie in Android ebenfalls
          erlaubt.
        </p>
        <button
          onClick={onPair}
          className="shrink-0 px-3 py-1.5 rounded-lg border border-gold/30 bg-gold/10 hover:bg-gold/20 text-[11px] text-gold/90"
        >
          Handy verbinden …
        </button>
      </div>

      {fehler && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-[11px] text-red-200">
          {fehler}
        </div>
      )}
      {info && (
        <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-[11px] text-emerald-200">
          {info}
        </div>
      )}

      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 space-y-1.5">
        <div className="text-[11px] text-white/70">
          Ordner für Dateien und Fotos vom Handy
        </div>
        <div className="flex items-center gap-2">
          <input
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-[11px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
            placeholder="leer = Jon-Datenordner"
            value={ordner}
            onChange={(e) => setOrdner(e.target.value)}
          />
          <button
            onClick={() => void ordnerSpeichern()}
            className="px-3 py-1.5 rounded-lg border border-white/15 bg-white/[0.04] hover:bg-white/10 text-[11px]"
          >
            {ordnerGemerkt ? "Gespeichert ✓" : "Merken"}
          </button>
        </div>
        <div className="text-[10px] text-white/35">
          Leer lassen, dann sammelt Jon alles in seinem Datenordner.
        </div>
      </div>

      {geraete.length === 0 && (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-4 text-[11px] text-white/45">
          Noch kein Handy verbunden. Über „Handy verbinden …“ zeigt Jon einen
          Code und einen QR-Code für die Jon-App am Handy.
        </div>
      )}

      {geraete.map((geraet) => {
        const rechte = geraet.rechte ?? {};
        const stufen = geraet.stufen ?? {};
        const namen = geraet.namen ?? {};
        const zustand = geraet.zustand ?? {};
        const faehig = geraet.faehigkeiten ?? [];
        return (
          <div
            key={geraet.id}
            className="rounded-xl border border-white/10 bg-white/[0.03] p-3 space-y-3"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] text-white/90 truncate">
                    📱 {geraet.name}
                  </span>
                  <span
                    className={
                      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] " +
                      (geraet.online
                        ? "bg-emerald-500/15 text-emerald-200"
                        : "bg-white/10 text-white/45")
                    }
                  >
                    <span
                      className={
                        "h-1.5 w-1.5 rounded-full " +
                        (geraet.online ? "bg-emerald-400" : "bg-white/40")
                      }
                    />
                    {geraet.online ? "Online" : "Offline"}
                  </span>
                </div>
                <div className="text-[10px] text-white/40 mt-0.5">
                  {zustand.modell || geraet.plattform}
                  {zustand.android ? ` · ${zustand.android}` : ""}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => void auffrischen(geraet)}
                  disabled={laeuft === geraet.id}
                  className="text-[11px] text-white/50 hover:text-white/90 disabled:opacity-40"
                >
                  Aktualisieren
                </button>
                <button
                  onClick={() => void umbenennen(geraet)}
                  className="text-[11px] text-white/50 hover:text-white/90"
                >
                  Umbenennen
                </button>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 text-[11px]">
              <div className="rounded-lg border border-white/10 bg-white/[0.02] px-2 py-1.5">
                <div className="text-[10px] text-white/35">Akku</div>
                <div className="text-white/80">
                  {typeof zustand.akku === "number"
                    ? `${zustand.akku} %${zustand.laedt ? " ⚡" : ""}`
                    : "–"}
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/[0.02] px-2 py-1.5">
                <div className="text-[10px] text-white/35">Verbindung</div>
                <div className="text-white/80">{zustand.netz || "–"}</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/[0.02] px-2 py-1.5">
                <div className="text-[10px] text-white/35">
                  Letzter Kontakt
                </div>
                <div className="text-white/80">{zeitpunkt(geraet.gesehen)}</div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-[10px] uppercase tracking-wider text-white/35">
                Berechtigungen
              </div>
              {STUFEN.map((stufe) => {
                const schluessel = REIHE.filter(
                  (name) => (stufen[name] ?? "standard") === stufe.id
                );
                if (schluessel.length === 0) return null;
                return (
                  <div key={stufe.id} className="space-y-1">
                    <div className="flex items-baseline gap-2">
                      <span
                        className={
                          "text-[10px] " +
                          (stufe.id === "sensibel"
                            ? "text-amber-300/80"
                            : "text-white/45")
                        }
                      >
                        {stufe.titel}
                      </span>
                      <span className="text-[10px] text-white/30">
                        {stufe.hinweis}
                      </span>
                    </div>
                    {schluessel.map((name) => {
                      const an = Boolean(rechte[name]);
                      const fehltAmHandy =
                        an && faehig.length > 0 && !faehig.includes(name);
                      return (
                        <div
                          key={name}
                          className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.02] px-2.5 py-1.5"
                        >
                          <div className="min-w-0">
                            <div className="text-[11px] text-white/80">
                              {namen[name] ?? name}
                            </div>
                            {fehltAmHandy && (
                              <div className="text-[10px] text-amber-300/70">
                                Am Handy noch nicht erlaubt – in der Jon-App
                                unter „Verbinder“ freigeben.
                              </div>
                            )}
                          </div>
                          <Schalter
                            an={an}
                            beiWechsel={(wert) =>
                              void setzen(geraet.id, name, wert)
                            }
                          />
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>

            <div className="flex items-center gap-2">
              <input
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-[11px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
                placeholder="Datei auf dem PC, z. B. C:\Users\...\Rechnung.pdf"
                value={pfade[geraet.id] ?? ""}
                onChange={(e) =>
                  setPfade((alt) => ({ ...alt, [geraet.id]: e.target.value }))
                }
              />
              <button
                onClick={() => void senden(geraet)}
                disabled={laeuft === geraet.id || !(pfade[geraet.id] ?? "").trim()}
                className="px-3 py-1.5 rounded-lg border border-white/15 bg-white/[0.04] hover:bg-white/10 text-[11px] disabled:opacity-40"
              >
                Senden
              </button>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[10px] text-white/30">
                Sag Jon auch einfach: „Schick die PDF auf mein Handy.“
              </span>
              <button
                onClick={() => void trennen(geraet)}
                className="text-[11px] text-red-300/80 hover:text-red-200"
              >
                Gerät trennen
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
