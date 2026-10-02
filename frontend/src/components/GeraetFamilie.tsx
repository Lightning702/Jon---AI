import { ReactNode, Suspense, lazy, useEffect, useState } from "react";
import {
  HandyBildschirmzeit,
  HandyGeraet,
  HandyNacht,
  handyDurchsage,
  handyKlingeln,
  handyMeldungQuittieren,
  handyRegeln,
  handyZeitanfrageBeantworten,
} from "../lib/api";

const Wochenbericht = lazy(() => import("./Wochenbericht"));

function karte(daten: Record<string, string | number | boolean>): string {
  const breite = daten.lat, laenge = daten.lon;
  if (typeof breite !== "number" || typeof laenge !== "number") return "";
  return `https://www.openstreetmap.org/?mlat=${breite.toFixed(5)}&mlon=${laenge.toFixed(5)}#map=17/${breite.toFixed(5)}/${laenge.toFixed(5)}`;
}

const ALTE_APPS: { id: string; name: string }[] = [
  { id: "whatsapp", name: "WhatsApp" },
  { id: "tiktok", name: "TikTok" },
  { id: "amazon", name: "Amazon Music" },
];
const FARBEN = [
  "bg-emerald-400/70",
  "bg-cyan-300/70",
  "bg-sky-400/70",
  "bg-violet-400/70",
  "bg-amber-300/70",
  "bg-pink-400/70",
];
const LIMITS = [0, 15, 30, 45, 60, 90, 120, 180, 240];
const PAUSEN = [15, 30, 60, 120];
const TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const GRUND: Record<string, string> = {
  limit: "Zeit aufgebraucht",
  nacht: "Schlafenszeit",
  pause: "Pause",
};

function uhrzeit(sekunden: number): string {
  return new Date(sekunden * 1000).toLocaleTimeString("de-AT", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function minutenText(m: number): string {
  if (m >= 60) {
    const rest = m % 60;
    return `${Math.floor(m / 60)} Std.${rest ? ` ${rest} Min.` : ""}`;
  }
  return `${m} Min.`;
}

function Knopf({
  children,
  onClick,
  aus,
  ton = "",
}: {
  children: ReactNode;
  onClick: () => void;
  aus?: boolean;
  ton?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={aus}
      className={
        "px-2.5 py-1 rounded-lg border text-[11px] transition-colors disabled:opacity-40 " +
        (ton === "gold"
          ? "border-gold/30 bg-gold/10 hover:bg-gold/20 text-gold/90"
          : ton === "rot"
            ? "border-red-400/30 bg-red-500/10 hover:bg-red-500/20 text-red-200"
            : "border-white/15 bg-white/[0.04] hover:bg-white/10 text-white/80")
      }
    >
      {children}
    </button>
  );
}

export default function GeraetFamilie({
  geraet,
  neuLaden,
  melden,
}: {
  geraet: HandyGeraet;
  neuLaden: () => void;
  melden: (text: string, fehler?: boolean) => void;
}) {
  const rechte = geraet.rechte ?? {};
  const faehig = geraet.faehigkeiten ?? [];
  const kann = (recht: string) =>
    Boolean(rechte[recht]) && faehig.includes(recht);
  const zeit: HandyBildschirmzeit = geraet.zustand?.bildschirmzeit ?? {};
  const APPS = (zeit.apps && zeit.apps.length ? zeit.apps : ALTE_APPS).map(
    (app, i) => ({ id: app.id, name: app.name, farbe: FARBEN[i % FARBEN.length] })
  );
  const [text, setText] = useState("");
  const [vorlesen, setVorlesen] = useState(true);
  const [busy, setBusy] = useState("");
  const [limits, setLimits] = useState<Record<string, number>>({});
  const [nacht, setNacht] = useState<HandyNacht | null>(null);
  const [offen, setOffen] = useState("");

  useEffect(() => {
    if (offen !== "limits") setLimits({ ...(zeit.limits ?? {}) });
    if (offen !== "nacht")
      setNacht(
        zeit.nacht
          ? { ...zeit.nacht }
          : { an: false, von: "21:00", bis: "06:30", tage: [1, 2, 3, 4, 5, 6, 7], apps: ["tiktok"] }
      );
  }, [geraet.zustand_zeit, offen]);

  const sos = (geraet.meldungen ?? []).filter(
    (m) => m.art === "sos" && !m.quittiert
  );
  const anfragen = (geraet.meldungen ?? []).filter(
    (m) => m.art === "zeitanfrage" && !m.quittiert
  );
  const zeigen =
    sos.length > 0 ||
    anfragen.length > 0 ||
    kann("durchsage") ||
    kann("klingeln") ||
    kann("regeln");
  if (!zeigen) return null;

  const ausfuehren = async (
    schluessel: string,
    aktion: () => Promise<unknown>,
    erfolg: string
  ) => {
    setBusy(schluessel);
    try {
      await aktion();
      melden(erfolg);
      neuLaden();
    } catch (e) {
      melden(e instanceof Error ? e.message : "Das hat nicht geklappt", true);
    } finally {
      setBusy("");
    }
  };

  const schritte = geraet.zustand?.schritte;
  const schritteHeute =
    typeof schritte === "number" ? schritte : schritte?.heute;
  const genutztGesamt = APPS.reduce(
    (summe, app) => summe + (zeit.genutzt?.[app.id] ?? 0),
    0
  );

  return (
    <div className="space-y-2">
      <div className="text-[10px] uppercase tracking-wider text-white/35">
        Familie
      </div>

      {sos.map((m) => (
        <div
          key={m.id}
          className="rounded-lg border border-red-400/50 bg-red-500/15 px-3 py-2 flex items-start justify-between gap-3 animate-pulse"
        >
          <div className="min-w-0">
            <div className="text-[12px] text-red-100 font-semibold">
              🆘 SOS um {uhrzeit(m.zeit)}
            </div>
            <div className="text-[10px] text-red-200/80">
              {typeof m.daten.akku === "number" && m.daten.akku >= 0
                ? `Akku ${m.daten.akku} %${m.daten.laedt ? " (lädt)" : ""}`
                : "Akku unbekannt"}
              {m.daten.text ? ` · „${String(m.daten.text)}“` : ""}
            </div>
            {karte(m.daten) && (
              <a
                href={karte(m.daten)}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-block text-[10.5px] font-medium text-red-100 underline underline-offset-2 hover:text-white"
              >
                📍 Standort ansehen
                {typeof m.daten.genau === "number" && m.daten.genau > 0 ? ` (± ${Math.round(m.daten.genau)} m)` : ""}
              </a>
            )}
          </div>
          <Knopf
            ton="rot"
            aus={busy === m.id}
            onClick={() =>
              void ausfuehren(
                m.id,
                () => handyMeldungQuittieren(geraet.id, m.id),
                "SOS als erledigt markiert."
              )
            }
          >
            Erledigt
          </Knopf>
        </div>
      ))}

      {anfragen.map((m) => {
        const app = String(m.daten.name || m.daten.app || "eine App");
        const minuten = Number(m.daten.minuten) || 30;
        return (
          <div
            key={m.id}
            className="rounded-lg border border-gold/35 bg-gold/[0.07] px-3 py-2 space-y-1.5"
          >
            <div className="text-[12px] text-white/90 font-semibold">
              ⏳ {minuten} Min. mehr {app}?
              <span className="text-white/40 font-normal"> · {uhrzeit(m.zeit)}</span>
            </div>
            {m.daten.text ? (
              <div className="text-[10.5px] italic text-white/60">„{String(m.daten.text)}“</div>
            ) : null}
            <div className="flex flex-wrap gap-1.5">
              <Knopf
                ton="gold"
                aus={busy === m.id}
                onClick={() =>
                  void ausfuehren(
                    m.id,
                    () => handyZeitanfrageBeantworten(geraet.id, m.id, true, minuten),
                    `${minuten} Minuten mehr ${app} erlaubt.`
                  )
                }
              >
                Erlauben
              </Knopf>
              {minuten !== 15 && (
                <Knopf
                  aus={busy === m.id}
                  onClick={() =>
                    void ausfuehren(
                      m.id,
                      () => handyZeitanfrageBeantworten(geraet.id, m.id, true, 15),
                      `15 Minuten mehr ${app} erlaubt.`
                    )
                  }
                >
                  Nur 15 Min.
                </Knopf>
              )}
              <Knopf
                aus={busy === m.id}
                onClick={() =>
                  void ausfuehren(
                    m.id,
                    () => handyZeitanfrageBeantworten(geraet.id, m.id, false),
                    "Anfrage abgelehnt."
                  )
                }
              >
                Ablehnen
              </Knopf>
            </div>
          </div>
        );
      })}

      {kann("regeln") && (
        <div className="rounded-lg border border-white/10 bg-white/[0.02] px-2.5 py-2 space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-[11px] text-white/80">
              Bildschirmzeit heute
              <span className="text-white/40">
                {" "}
                · {minutenText(genutztGesamt)}
                {typeof schritteHeute === "number"
                  ? ` · 👣 ${schritteHeute.toLocaleString("de-AT")} Schritte`
                  : ""}
              </span>
            </div>
            <span
              className={
                "text-[10px] rounded-full px-2 py-0.5 " +
                (zeit.nacht_aktiv
                  ? "bg-violet-500/20 text-violet-200"
                  : zeit.pause_aktiv
                    ? "bg-amber-500/20 text-amber-200"
                    : "bg-emerald-500/15 text-emerald-200")
              }
            >
              {zeit.nacht_aktiv
                ? `Schlafenszeit bis ${zeit.nacht_ende ?? "?"}`
                : zeit.pause_aktiv
                  ? `Pause bis ${zeit.pause_ende ?? "?"}`
                  : "Alles frei"}
            </span>
          </div>

          {APPS.map((app) => {
            const limit = zeit.limits?.[app.id] ?? 0;
            const genutzt = zeit.genutzt?.[app.id] ?? 0;
            const gesperrt = zeit.gesperrt?.[app.id];
            const anteil = limit
              ? Math.min(100, (genutzt / limit) * 100)
              : Math.min(100, genutzt / 1.8);
            return (
              <div key={app.id} className="space-y-0.5">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-white/70">{app.name}</span>
                  <span
                    className={gesperrt ? "text-amber-200" : "text-white/40"}
                  >
                    {gesperrt
                      ? GRUND[gesperrt] ?? "Gesperrt"
                      : zeit.frei_bis?.[app.id]
                        ? `frei bis ${zeit.frei_bis[app.id]}`
                        : `${minutenText(genutzt)}${limit ? ` von ${minutenText(limit)}` : " · ohne Limit"}`}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className={
                      "h-full rounded-full transition-all duration-700 " +
                      (gesperrt ? "bg-red-400/70" : app.farbe)
                    }
                    style={{ width: `${anteil}%` }}
                  />
                </div>
              </div>
            );
          })}

          {!zeit.zugriff && (
            <div className="text-[10px] text-white/35">
              Genauer wird es mit „Nutzungszugriff“ am Handy (Einstellungen →
              Sicherheit).
            </div>
          )}

          <div className="flex flex-wrap gap-1.5 pt-1">
            <Knopf
              onClick={() => setOffen(offen === "limits" ? "" : "limits")}
            >
              Tageslimits …
            </Knopf>
            <Knopf onClick={() => setOffen(offen === "nacht" ? "" : "nacht")}>
              Schlafenszeit{zeit.nacht?.an ? ` ${zeit.nacht.von}–${zeit.nacht.bis}` : " aus"} …
            </Knopf>
            <Knopf onClick={() => setOffen(offen === "woche" ? "" : "woche")}>
              {offen === "woche" ? "Woche schließen" : "📊 Woche"}
            </Knopf>
            {zeit.pause_aktiv ? (
              <Knopf
                ton="gold"
                aus={busy === "pause"}
                onClick={() =>
                  void ausfuehren(
                    "pause",
                    () => handyRegeln(geraet.id, { pause_minuten: 0 }),
                    "Pause beendet."
                  )
                }
              >
                Pause beenden
              </Knopf>
            ) : (
              <Knopf onClick={() => setOffen(offen === "pause" ? "" : "pause")}>
                Jetzt Pause …
              </Knopf>
            )}
          </div>

          {offen === "woche" && (
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <Suspense fallback={<div className="text-[11px] text-white/40">Wird geladen …</div>}>
                <Wochenbericht geraet={geraet.id} rahmen={false} />
              </Suspense>
            </div>
          )}

          {offen === "limits" && (
            <div className="space-y-1.5 rounded-lg border border-white/10 bg-black/20 p-2">
              {APPS.map((app) => (
                <div
                  key={app.id}
                  className="flex items-center justify-between gap-2"
                >
                  <span className="text-[11px] text-white/70">{app.name}</span>
                  <select
                    className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white/90 outline-none focus:border-gold/40"
                    value={limits[app.id] ?? 0}
                    onChange={(e) =>
                      setLimits((alt) => ({
                        ...alt,
                        [app.id]: Number(e.target.value),
                      }))
                    }
                  >
                    {LIMITS.map((m) => (
                      <option key={m} value={m}>
                        {m ? minutenText(m) : "Kein Limit"}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
              <div className="flex justify-end">
                <Knopf
                  ton="gold"
                  aus={busy === "limits"}
                  onClick={() =>
                    void ausfuehren(
                      "limits",
                      async () => {
                        await handyRegeln(geraet.id, { limits });
                        setOffen("");
                      },
                      "Tageslimits gespeichert."
                    )
                  }
                >
                  Speichern
                </Knopf>
              </div>
            </div>
          )}

          {offen === "nacht" && nacht && (
            <div className="space-y-2 rounded-lg border border-white/10 bg-black/20 p-2">
              <label className="flex items-center gap-2 text-[11px] text-white/80">
                <input
                  type="checkbox"
                  checked={nacht.an}
                  onChange={(e) => setNacht({ ...nacht, an: e.target.checked })}
                />
                Schlafenszeit aktiv
              </label>
              <div className="flex items-center gap-2 text-[11px] text-white/60">
                von
                <input
                  type="time"
                  value={nacht.von}
                  onChange={(e) => setNacht({ ...nacht, von: e.target.value })}
                  className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-white/90 outline-none focus:border-gold/40"
                />
                bis
                <input
                  type="time"
                  value={nacht.bis}
                  onChange={(e) => setNacht({ ...nacht, bis: e.target.value })}
                  className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-white/90 outline-none focus:border-gold/40"
                />
              </div>
              <div className="flex flex-wrap gap-1">
                {TAGE.map((tag, i) => {
                  const nummer = i + 1;
                  const an = nacht.tage.includes(nummer);
                  return (
                    <button
                      key={tag}
                      onClick={() =>
                        setNacht({
                          ...nacht,
                          tage: an
                            ? nacht.tage.filter((t) => t !== nummer)
                            : [...nacht.tage, nummer].sort(),
                        })
                      }
                      className={
                        "px-2 py-0.5 rounded-md text-[10px] border " +
                        (an
                          ? "border-gold/40 bg-gold/15 text-gold/90"
                          : "border-white/10 text-white/45")
                      }
                    >
                      {tag}
                    </button>
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-1">
                {APPS.map((app) => {
                  const an = nacht.apps.includes(app.id);
                  return (
                    <button
                      key={app.id}
                      onClick={() =>
                        setNacht({
                          ...nacht,
                          apps: an
                            ? nacht.apps.filter((a) => a !== app.id)
                            : [...nacht.apps, app.id],
                        })
                      }
                      className={
                        "px-2 py-0.5 rounded-md text-[10px] border " +
                        (an
                          ? "border-red-300/40 bg-red-500/15 text-red-200"
                          : "border-white/10 text-white/45")
                      }
                    >
                      {an ? "🔒 " : ""}
                      {app.name}
                    </button>
                  );
                })}
              </div>
              <div className="flex justify-end">
                <Knopf
                  ton="gold"
                  aus={busy === "nacht"}
                  onClick={() =>
                    void ausfuehren(
                      "nacht",
                      async () => {
                        await handyRegeln(geraet.id, { nacht });
                        setOffen("");
                      },
                      nacht.an ? "Schlafenszeit gespeichert." : "Schlafenszeit aus."
                    )
                  }
                >
                  Speichern
                </Knopf>
              </div>
            </div>
          )}

          {offen === "pause" && (
            <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-white/10 bg-black/20 p-2">
              <span className="text-[11px] text-white/60 mr-1">
                Apps sperren für
              </span>
              {PAUSEN.map((m) => (
                <Knopf
                  key={m}
                  aus={busy === "pause"}
                  onClick={() =>
                    void ausfuehren(
                      "pause",
                      async () => {
                        await handyRegeln(geraet.id, { pause_minuten: m });
                        setOffen("");
                      },
                      `Pause für ${minutenText(m)}.`
                    )
                  }
                >
                  {minutenText(m)}
                </Knopf>
              ))}
            </div>
          )}
        </div>
      )}

      {kann("durchsage") && (
        <div className="rounded-lg border border-white/10 bg-white/[0.02] px-2.5 py-2 space-y-1.5">
          <div className="text-[11px] text-white/80">📣 Durchsage</div>
          <div className="flex items-center gap-2">
            <input
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-[11px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
              placeholder="z. B. Essen ist fertig!"
              value={text}
              maxLength={500}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && text.trim())
                  void ausfuehren(
                    "durchsage",
                    async () => {
                      await handyDurchsage(geraet.id, text.trim(), vorlesen);
                      setText("");
                    },
                    "Durchsage ist angekommen."
                  );
              }}
            />
            <Knopf
              ton="gold"
              aus={busy === "durchsage" || !text.trim()}
              onClick={() =>
                void ausfuehren(
                  "durchsage",
                  async () => {
                    await handyDurchsage(geraet.id, text.trim(), vorlesen);
                    setText("");
                  },
                  "Durchsage ist angekommen."
                )
              }
            >
              Senden
            </Knopf>
          </div>
          <label className="flex items-center gap-2 text-[10px] text-white/45">
            <input
              type="checkbox"
              checked={vorlesen}
              onChange={(e) => setVorlesen(e.target.checked)}
            />
            Laut vorlesen
          </label>
          {(geraet.durchsagen ?? []).slice(0, 3).map((d) => (
            <div
              key={d.kennung}
              className="flex items-center justify-between text-[10px] text-white/40"
            >
              <span className="truncate pr-2">„{d.text}“</span>
              <span className={d.gelesen ? "text-emerald-300/80" : ""}>
                {d.gelesen ? `✓ gelesen ${uhrzeit(d.gelesen)}` : uhrzeit(d.zeit)}
              </span>
            </div>
          ))}
        </div>
      )}

      {kann("klingeln") && (
        <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.02] px-2.5 py-1.5">
          <div className="text-[11px] text-white/80">
            🔔 Handy klingeln lassen
            <span className="text-white/35"> · auch wenn es leise ist</span>
          </div>
          <Knopf
            aus={busy === "klingeln" || !geraet.online}
            onClick={() =>
              void ausfuehren(
                "klingeln",
                () => handyKlingeln(geraet.id, 30),
                "Das Handy klingelt jetzt 30 Sekunden."
              )
            }
          >
            Klingeln
          </Knopf>
        </div>
      )}
    </div>
  );
}
