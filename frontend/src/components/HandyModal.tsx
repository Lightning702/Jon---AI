import { useEffect, useRef, useState } from "react";
import {
  HandyGeraet,
  HandyKopplung,
  HandyStand,
  handyGeraete,
  handyGeraetLoeschen,
  handyKopplungAbbrechen,
  handyKopplungAntworten,
  handyKopplungStarten,
  handyKopplungStand,
  handyQrUrl,
} from "../lib/api";

function zeitpunkt(wert: number): string {
  if (!wert) return "unbekannt";
  return new Date(wert * 1000).toLocaleString("de-AT", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function HandyModal({ onClose }: { onClose: () => void }) {
  const [kopplung, setKopplung] = useState<HandyKopplung | null>(null);
  const [stand, setStand] = useState<HandyStand>({ status: "leer" });
  const [geraete, setGeraete] = useState<HandyGeraet[]>([]);
  const [fehler, setFehler] = useState("");
  const [laedt, setLaedt] = useState(false);
  const [wartesekunden, setWartesekunden] = useState(0);
  const takt = useRef<number | null>(null);

  const geraeteLaden = async () => {
    try {
      const daten = await handyGeraete();
      setGeraete(daten.geraete);
    } catch {
      setGeraete([]);
    }
  };

  const starten = async () => {
    setLaedt(true);
    setFehler("");
    try {
      const daten = await handyKopplungStarten();
      setKopplung(daten);
      setStand({ status: "offen", relay: daten.relay });
      setWartesekunden(0);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Kopplung fehlgeschlagen");
    } finally {
      setLaedt(false);
    }
  };

  useEffect(() => {
    void geraeteLaden();
    void starten();
    return () => {
      void handyKopplungAbbrechen();
    };
  }, []);

  useEffect(() => {
    if (!kopplung) return;
    takt.current = window.setInterval(async () => {
      setWartesekunden((wert) => wert + 1.5);
      try {
        const neu = await handyKopplungStand();
        setStand(neu);
        if (neu.status === "verbunden") {
          void geraeteLaden();
        }
      } catch {
        return;
      }
    }, 1500);
    return () => {
      if (takt.current !== null) window.clearInterval(takt.current);
    };
  }, [kopplung]);

  const antworten = async (angenommen: boolean) => {
    try {
      await handyKopplungAntworten(angenommen);
      const neu = await handyKopplungStand();
      setStand(neu);
      void geraeteLaden();
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Antwort fehlgeschlagen");
    }
  };

  const relayStand = stand.relay ?? kopplung?.relay;
  const relayBereit = Boolean(relayStand?.verbunden);
  const relayUnbekannt = relayStand === undefined;
  const relayLange = Boolean(
    relayStand && !relayStand.verbunden && wartesekunden > 12
  );
  const abgelaufen = stand.status === "abgelaufen";
  const wartet = stand.status === "wartet";
  const fertig = stand.status === "verbunden";

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl max-h-[86vh] overflow-y-auto rounded-2xl border border-gold/25 bg-[#0b0b0f] shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 sticky top-0 bg-[#0b0b0f]">
          <div className="text-sm text-gold">Handy verbinden</div>
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

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="text-[11px] text-white/60 mb-3">
              Öffne die Jon-App am Handy und tippe auf „Mit Jon verbinden“.
              Tippe dort den Code ein – oder scanne den QR-Code. Beides geht auch
              von unterwegs, ohne dass ihr im selben WLAN seid.
            </div>
            {kopplung && !kopplung.heimnetz && (
              <div className="mb-3 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-[11px] text-white/60">
                Jon lauscht nur auf diesem PC. Die Kopplung läuft deshalb über das
                Jon-Relay – das funktioniert auch von unterwegs. Wenn du zusätzlich
                den schnellen Weg im Heimnetz willst, schalte in der .env
                <span className="text-white/80"> JON_LAN=true</span> ein und starte
                Jon neu.
              </div>
            )}
            <div className="mb-4 rounded-xl border border-gold/30 bg-gold/[0.07] p-4 text-center">
              <div className="text-[10px] uppercase tracking-wider text-white/40 mb-1">
                Code am Handy eintippen
              </div>
              <div className="font-mono text-[30px] tracking-[0.18em] text-gold select-all leading-tight">
                {kopplung?.code_gruppiert ?? "…"}
              </div>
              <div className="mt-2 flex items-center justify-center gap-2">
                <button
                  onClick={() => {
                    if (kopplung) void navigator.clipboard?.writeText(kopplung.code_gruppiert);
                  }}
                  className="px-3 py-1 rounded-lg border border-white/15 bg-white/[0.04] hover:bg-white/10 text-[11px]"
                >
                  Kopieren
                </button>
                <span className="text-[11px] text-white/40">
                  gilt einmal, {Math.max(0, Math.round((stand.rest ?? 0) / 60))} Min. übrig
                </span>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="rounded-xl bg-white p-2 shrink-0">
                {kopplung ? (
                  <img
                    src={handyQrUrl(kopplung.nutzlast)}
                    alt="QR-Code zum Koppeln"
                    className="w-[220px] h-[220px] block"
                  />
                ) : (
                  <div className="w-[220px] h-[220px] flex items-center justify-center text-black/40 text-[11px]">
                    {laedt ? "wird erstellt …" : "kein Code"}
                  </div>
                )}
              </div>
              <div className="space-y-2 grow">
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-white/35">
                    Dieser PC
                  </div>
                  <div className="text-white/75">
                    {kopplung ? `${kopplung.pc.name} (${kopplung.pc.id})` : "…"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-white/35">
                    Im Heimnetz
                  </div>
                  <div className="text-white/75 break-all">
                    {kopplung?.adresse ?? "…"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-white/35">
                    Von unterwegs
                  </div>
                  <div className="text-white/75 break-all">
                    Jon-Relay über {kopplung?.broker.host ?? "…"} – keine
                    Portweiterleitung nötig
                  </div>
                  <div
                    className={
                      "mt-1 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] " +
                      (relayBereit
                        ? "bg-emerald-500/15 text-emerald-200"
                        : relayUnbekannt
                          ? "bg-amber-500/15 text-amber-200"
                          : "bg-white/10 text-white/50")
                    }
                  >
                    <span
                      className={
                        "h-1.5 w-1.5 rounded-full " +
                        (relayBereit
                          ? "bg-emerald-400"
                          : relayUnbekannt
                            ? "bg-amber-400"
                            : "bg-white/40")
                      }
                    />
                    {relayBereit
                      ? "Relay bereit"
                      : relayUnbekannt
                        ? "Alte Jon-Fassung – bitte Jon neu starten"
                        : "Relay verbindet …"}
                  </div>
                  {relayLange && (
                    <div className="mt-1 text-[10px] text-white/45">
                      Das dauert ungewöhnlich lange. Prüfe die Internetverbindung
                      dieses PCs.
                    </div>
                  )}
                </div>
                <button
                  onClick={() => void starten()}
                  className="mt-2 px-3 py-1.5 rounded-lg border border-white/15 bg-white/[0.04] hover:bg-white/10 text-[11px]"
                >
                  Neuen Code erzeugen
                </button>
              </div>
            </div>
          </div>

          {wartet && (
            <div className="rounded-xl border border-gold/40 bg-gold/10 p-4">
              <div className="text-gold text-[13px] mb-1">
                {stand.geraet?.name ?? "Ein Android-Gerät"} möchte sich verbinden
              </div>
              <div className="text-white/60 text-[11px] mb-3">
                {stand.geraet?.plattform ?? "Android"} – nur bestätigen, wenn du
                das gerade selbst am Handy gestartet hast.
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => void antworten(true)}
                  className="px-3 py-1.5 rounded-lg border border-gold/40 bg-gold/20 hover:bg-gold/30 text-[11px] text-gold"
                >
                  Verbinden
                </button>
                <button
                  onClick={() => void antworten(false)}
                  className="px-3 py-1.5 rounded-lg border border-white/15 bg-white/[0.04] hover:bg-white/10 text-[11px]"
                >
                  Ablehnen
                </button>
              </div>
            </div>
          )}

          {fertig && (
            <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-emerald-200">
              Handy verbunden. Es hat jetzt einen eigenen Schlüssel.
            </div>
          )}

          {abgelaufen && (
            <div className="rounded-xl border border-white/15 bg-white/[0.04] px-3 py-2 text-white/60">
              Der Code ist abgelaufen. Erzeuge einen neuen.
            </div>
          )}

          <div>
            <div className="text-[10px] uppercase tracking-wider text-white/35 mb-2">
              Verbundene Handys
            </div>
            {geraete.length === 0 ? (
              <div className="text-white/45 text-[11px]">
                Noch kein Handy verbunden.
              </div>
            ) : (
              <div className="space-y-2">
                {geraete.map((geraet) => (
                  <div
                    key={geraet.id}
                    className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"
                  >
                    <div>
                      <div className="text-white/80">{geraet.name}</div>
                      <div className="text-white/40 text-[10px]">
                        {geraet.plattform} · zuletzt {zeitpunkt(geraet.gesehen)}
                      </div>
                    </div>
                    <button
                      onClick={async () => {
                        await handyGeraetLoeschen(geraet.id);
                        void geraeteLaden();
                      }}
                      className="text-red-300/80 hover:text-red-200 text-[11px]"
                    >
                      Trennen
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
