import { useEffect, useState } from "react";
import {
  Diagnose,
  Kopplung,
  getDiagnose,
  getKopplung,
  neuesToken,
  protokollUrl,
} from "../lib/api";
import { setToken } from "../lib/token";

function zeit(sekunden: number): string {
  if (sekunden < 90) return Math.round(sekunden) + " s";
  const minuten = Math.floor(sekunden / 60);
  if (minuten < 90) return minuten + " min";
  const stunden = Math.floor(minuten / 60);
  return stunden + " h " + (minuten % 60) + " min";
}

function Feld({
  name,
  wert,
  breit,
  warnung,
}: {
  name: string;
  wert: string;
  breit?: boolean;
  warnung?: boolean;
}) {
  return (
    <div className={breit ? "col-span-2" : ""}>
      <div className="text-[10px] uppercase tracking-wider text-white/35">
        {name}
      </div>
      <div
        className={
          "text-[12px] break-all " + (warnung ? "text-red-300" : "text-white/75")
        }
      >
        {wert}
      </div>
    </div>
  );
}

export default function DiagnosticsModal({ onClose }: { onClose: () => void }) {
  const [daten, setDaten] = useState<Diagnose | null>(null);
  const [kopplung, setKopplung] = useState<Kopplung | null>(null);
  const [fehler, setFehler] = useState("");
  const [hinweis, setHinweis] = useState("");
  const [zeigeToken, setZeigeToken] = useState(false);
  const [laedt, setLaedt] = useState(true);

  const laden = async () => {
    setLaedt(true);
    try {
      const [d, k] = await Promise.all([getDiagnose(), getKopplung()]);
      setDaten(d);
      setKopplung(k);
      setFehler("");
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Diagnose fehlgeschlagen");
    } finally {
      setLaedt(false);
    }
  };

  useEffect(() => {
    void laden();
  }, []);

  const kopieren = async (text: string, was: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setHinweis(was + " kopiert");
      setTimeout(() => setHinweis(""), 2200);
    } catch {
      setHinweis("Kopieren nicht möglich");
    }
  };

  const erneuern = async () => {
    const sicher = window.confirm(
      "Neues Token erzeugen? Alle gekoppelten Handys und Browser müssen danach neu verbunden werden."
    );
    if (!sicher) return;
    try {
      const frisch = await neuesToken();
      setToken(frisch.token);
      setKopplung(frisch);
      setHinweis("Neues Token aktiv");
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Token nicht erneuert");
    }
  };

  const kaputt = new Set(daten?.fehlerhaft ?? []);

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl max-h-[86vh] overflow-y-auto rounded-2xl border border-gold/25 bg-[#0b0b0f] shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 sticky top-0 bg-[#0b0b0f]">
          <div className="text-sm text-gold">Diagnose</div>
          <button
            onClick={onClose}
            className="text-white/50 hover:text-white text-lg leading-none px-2"
          >
            X
          </button>
        </div>

        <div className="p-4 space-y-4 text-[12px] text-white/80">
          {fehler && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-red-200">
              {fehler}
            </div>
          )}
          {hinweis && (
            <div className="rounded-lg border border-gold/30 bg-gold/10 px-3 py-2 text-gold">
              {hinweis}
            </div>
          )}

          {daten && (
            <div className="grid grid-cols-2 gap-2">
              <Feld name="Version" wert={daten.version} />
              <Feld name="Läuft seit" wert={zeit(daten.laufzeit)} />
              <Feld
                name="Erreichbar unter"
                wert={
                  daten.adresse +
                  ":" +
                  daten.port +
                  (daten.lan ? " (WLAN)" : " (nur dieser PC)")
                }
              />
              <Feld
                name="Dienste mit Fehlern"
                wert={
                  daten.fehlerhaft.length === 0
                    ? "keine"
                    : daten.fehlerhaft.join(", ")
                }
                warnung={daten.fehlerhaft.length > 0}
              />
              <Feld
                name="Datenverzeichnis"
                wert={daten.datenverzeichnis}
                breit
              />
            </div>
          )}

          {kopplung && (
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 space-y-2">
              <div className="text-[11px] uppercase tracking-wider text-white/40">
                Handy koppeln
              </div>
              <p className="text-white/60 leading-relaxed">
                {kopplung.lan
                  ? "Öffne diese Adresse im Browser deines Handys. Sie enthält deinen Zugangsschlüssel — gib sie an niemanden weiter."
                  : "Jon ist gerade nur auf diesem PC erreichbar. Für das Handy JON_LAN=1 in der .env setzen und Jon neu starten."}
              </p>
              <div className="flex gap-2">
                <input
                  readOnly
                  value={kopplung.url}
                  onFocus={(e) => e.currentTarget.select()}
                  className="flex-1 bg-black/40 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] font-mono text-white/70"
                />
                <button
                  onClick={() => void kopieren(kopplung.url, "Adresse")}
                  className="px-3 py-1.5 rounded-lg border border-gold/30 text-gold text-[11px] hover:bg-gold/10"
                >
                  Kopieren
                </button>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setZeigeToken((v) => !v)}
                  className="text-[11px] text-white/50 hover:text-white/80 underline"
                >
                  {zeigeToken ? "Token verbergen" : "Token anzeigen"}
                </button>
                <button
                  onClick={() => void erneuern()}
                  className="text-[11px] text-red-300/80 hover:text-red-200 underline"
                >
                  Neues Token
                </button>
              </div>
              {zeigeToken && (
                <div className="font-mono text-[11px] text-white/60 break-all bg-black/40 rounded-lg px-2 py-1.5">
                  {kopplung.token}
                </div>
              )}
            </div>
          )}

          {daten && (
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
              <div className="text-[11px] uppercase tracking-wider text-white/40 mb-2">
                Hintergrunddienste ({daten.dienste.length})
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                {daten.dienste.map((d) => (
                  <div
                    key={d.dienst}
                    className="flex items-center justify-between gap-2"
                    title={d.meldung ?? ""}
                  >
                    <span className="truncate text-white/60">{d.dienst}</span>
                    <span
                      className={
                        kaputt.has(d.dienst)
                          ? "text-red-300 shrink-0"
                          : "text-emerald-300/70 shrink-0"
                      }
                    >
                      {kaputt.has(d.dienst) ? d.fehler + " Fehler" : "läuft"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {daten && (
            <div className="rounded-xl border border-white/10 bg-black/40 p-3">
              <div className="text-[11px] uppercase tracking-wider text-white/40 mb-2">
                Letzte Meldungen
              </div>
              <pre className="text-[10px] leading-relaxed text-white/50 whitespace-pre-wrap max-h-56 overflow-y-auto">
                {daten.meldungen.slice(-60).join("\n") || "nichts protokolliert"}
              </pre>
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button
              onClick={() => void laden()}
              disabled={laedt}
              className="px-3 py-1.5 rounded-lg border border-white/15 text-white/70 text-[11px] hover:bg-white/5 disabled:opacity-40"
            >
              {laedt ? "Lade …" : "Aktualisieren"}
            </button>
            <a
              href={protokollUrl()}
              className="px-3 py-1.5 rounded-lg border border-gold/30 text-gold text-[11px] hover:bg-gold/10"
            >
              Protokoll speichern
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
