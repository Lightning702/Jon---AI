import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Brain, ChevronDown, Code2, Image as BildIcon, Loader2, Search, Timer, Video as VideoIcon } from "lucide-react";
import { getModellInfo, modellTestStand, modelleTesten, type ModellInfo, type ModellTestLauf } from "../lib/api";

interface Props {
  provider: string;
  providerLabel: string;
  models: string[];
  model: string;
  onChange: (model: string) => void;
}

type Filter = "alle" | "bild" | "video" | "code" | "schnell";

const FILTER: { id: Filter; name: string }[] = [
  { id: "alle", name: "Alle" },
  { id: "bild", name: "Bild" },
  { id: "video", name: "Video" },
  { id: "code", name: "Code" },
  { id: "schnell", name: "Schnell" },
];

const RANG: Record<ModellInfo["zustand"], number> = { bereit: 0, ungetestet: 1, haengt: 2, fehler: 3, gesperrt: 4, kein_chat: 5 };

const ZUSTAND: Record<ModellInfo["zustand"], { text: string; farbe: string }> = {
  bereit: { text: "Antwortet", farbe: "bg-emerald-400" },
  ungetestet: { text: "Noch nicht getestet", farbe: "bg-white/30" },
  haengt: { text: "Hing im Test ohne Antwort", farbe: "bg-amber-400" },
  fehler: { text: "Fehler im Test", farbe: "bg-rose-400" },
  gesperrt: { text: "Für dein Konto nicht freigeschaltet", farbe: "bg-rose-500" },
  kein_chat: { text: "Kein Chatmodell", farbe: "bg-white/20" },
};

const speicher = new Map<string, { zeit: number; modelle: Record<string, ModellInfo> }>();

function sekunden(wert: number | null | undefined): string {
  if (wert === null || wert === undefined) return "–";
  return `${wert.toLocaleString("de-DE", { maximumFractionDigits: wert < 10 ? 1 : 0 })} s`;
}

function milliarden(wert: number | null | undefined): string {
  if (!wert) return "";
  if (wert < 1) return `${Math.round(wert * 1000)} Mio.`;
  return `${wert.toLocaleString("de-DE", { maximumFractionDigits: 1 })} Mrd.`;
}

function kurzname(id: string): string {
  if (id.startsWith("share:")) return id.slice(id.indexOf("/") + 1);
  return id.includes("/") ? id.slice(id.lastIndexOf("/") + 1) : id;
}

function passt(info: ModellInfo | undefined, filter: Filter): boolean {
  if (filter === "alle") return true;
  if (!info) return false;
  if (filter === "bild") return info.faehigkeiten.includes("bild_zu_text");
  if (filter === "video") return info.faehigkeiten.includes("video_zu_text");
  if (filter === "code") return info.faehigkeiten.includes("code");
  return info.zustand === "bereit" && info.kurz_s !== null && info.kurz_s < 3;
}

function Karte({ info, id, providerLabel, onTesten, laeuft }: { info?: ModellInfo; id: string; providerLabel: string; onTesten: () => void; laeuft: boolean }) {
  const zustand = ZUSTAND[info?.zustand ?? "ungetestet"];
  const p = info?.parameter;
  return (
    <div className="text-[12px] leading-relaxed text-white/80 space-y-2">
      <div>
        <div className="text-white text-[13px] font-medium break-all">{id}</div>
        <div className="text-white/50">
          {info?.hersteller || "Unbekannter Hersteller"} · Anbieter {providerLabel}
          {info?.familie ? ` · Familie ${info.familie}` : ""}
          {info?.quantisierung ? ` · ${info.quantisierung}` : ""}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`inline-block w-2 h-2 rounded-full ${zustand.farbe}`} />
        <span>{zustand.text}</span>
      </div>
      <div>
        <div className="text-white/45 uppercase tracking-wide text-[10px]">Parameter</div>
        {p?.gesamt_mrd ? (
          <div>
            {milliarden(p.gesamt_mrd)} gesamt · {milliarden(p.aktiv_mrd)} aktiv
            {p.moe ? " (Mixture of Experts)" : ""}
          </div>
        ) : (
          <div className="text-white/50">Der Anbieter nennt keine Größe.</div>
        )}
      </div>
      <div>
        <div className="text-white/45 uppercase tracking-wide text-[10px] mb-1">Kann</div>
        <div className="flex flex-wrap gap-1">
          {(info?.faehigkeit_namen ?? ["Text zu Text"]).map((name) => (
            <span key={name} className="px-1.5 py-0.5 rounded-md bg-white/10 border border-white/10">{name}</span>
          ))}
        </div>
      </div>
      <div>
        <div className="text-white/45 uppercase tracking-wide text-[10px] mb-1">Geschätzte Antwortzeit</div>
        <div className="grid grid-cols-[1fr_auto] gap-x-3">
          <span>„Hallo“ – erstes Wort</span>
          <span className="text-right tabular-nums">{sekunden(info?.erstes_wort_s)}</span>
          <span>„Hallo“ – fertig</span>
          <span className="text-right tabular-nums">{sekunden(info?.kurz_s)}</span>
          <span>„Code mir …“ – fertig</span>
          <span className="text-right tabular-nums">{sekunden(info?.lang_s)}</span>
          {info?.bild_s !== null && info?.bild_s !== undefined && (
            <>
              <span>Bild ansehen</span>
              <span className="text-right tabular-nums">{sekunden(info.bild_s)}</span>
            </>
          )}
          {info?.video_s !== null && info?.video_s !== undefined && (
            <>
              <span>Video (3 Standbilder)</span>
              <span className="text-right tabular-nums">{sekunden(info.video_s)}</span>
            </>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between pt-1">
        <span className="text-white/40 text-[11px]">
          {info?.getestet ? `Gemessen am ${new Date(info.getestet * 1000).toLocaleDateString("de-DE")}` : "Noch keine Messung"}
        </span>
        {!id.startsWith("share:") && (
          <button
            type="button"
            onClick={onTesten}
            disabled={laeuft}
            className="px-2 py-1 rounded-md bg-gold/15 text-gold hover:bg-gold/25 disabled:opacity-40"
          >
            {laeuft ? "Test läuft" : "Jetzt testen"}
          </button>
        )}
      </div>
    </div>
  );
}

export default function ModellWahl({ provider, providerLabel, models, model, onChange }: Props) {
  const [offen, setOffen] = useState(false);
  const [suche, setSuche] = useState("");
  const [filter, setFilter] = useState<Filter>("alle");
  const [infos, setInfos] = useState<Record<string, ModellInfo>>(() => speicher.get(provider)?.modelle ?? {});
  const [aktiv, setAktiv] = useState(0);
  const [zeige, setZeige] = useState<string>("");
  const [lauf, setLauf] = useState<ModellTestLauf | null>(null);
  const [lage, setLage] = useState<{ links: number; oben: number; breite: number; karteLinks: boolean }>({ links: 0, oben: 0, breite: 380, karteLinks: false });
  const knopf = useRef<HTMLButtonElement>(null);
  const feld = useRef<HTMLInputElement>(null);
  const liste = useRef<HTMLDivElement>(null);
  const warten = useRef<number | null>(null);

  const laden = useCallback(
    async (frisch = false) => {
      const alt = speicher.get(provider);
      if (alt && !frisch && Date.now() - alt.zeit < 60_000) {
        setInfos(alt.modelle);
        return;
      }
      try {
        const daten = await getModellInfo(provider);
        speicher.set(provider, { zeit: Date.now(), modelle: daten.modelle });
        setInfos(daten.modelle);
        setLauf(daten.lauf);
      } catch {
        setInfos(alt?.modelle ?? {});
      }
    },
    [provider]
  );

  useEffect(() => {
    setInfos(speicher.get(provider)?.modelle ?? {});
  }, [provider]);

  useEffect(() => {
    if (offen) void laden();
  }, [offen, laden]);

  useEffect(() => {
    if (!lauf?.laeuft) return;
    const takt = window.setInterval(async () => {
      try {
        const stand = await modellTestStand();
        setLauf(stand);
        if (!stand.laeuft) void laden(true);
      } catch {
        setLauf(null);
      }
    }, 2000);
    return () => window.clearInterval(takt);
  }, [lauf?.laeuft, laden]);

  const sichtbar = useMemo(() => {
    const wort = suche.trim().toLowerCase();
    const treffer = models.filter((m) => {
      const info = infos[m];
      if (!passt(info, filter)) return false;
      if (!wort) return true;
      const text = [m, info?.hersteller ?? "", ...(info?.faehigkeit_namen ?? [])].join(" ").toLowerCase();
      return wort.split(/\s+/).every((teil) => text.includes(teil));
    });
    return treffer
      .map((m, index) => ({ m, index }))
      .sort((a, b) => {
        const ra = RANG[infos[a.m]?.zustand ?? "ungetestet"];
        const rb = RANG[infos[b.m]?.zustand ?? "ungetestet"];
        return ra - rb || a.index - b.index;
      })
      .map((e) => e.m);
  }, [models, infos, suche, filter]);

  useEffect(() => {
    setAktiv(0);
  }, [suche, filter]);

  useLayoutEffect(() => {
    if (!offen || !knopf.current) return;
    const r = knopf.current.getBoundingClientRect();
    const breite = Math.min(380, window.innerWidth - 16);
    const links = Math.max(8, Math.min(r.left, window.innerWidth - breite - 8));
    setLage({ links, oben: r.bottom + 6, breite, karteLinks: links + breite + 316 > window.innerWidth });
    window.setTimeout(() => feld.current?.focus(), 0);
  }, [offen]);

  useEffect(() => {
    if (!offen) return;
    const zu = (e: MouseEvent) => {
      const ziel = e.target as Node;
      if (knopf.current?.contains(ziel)) return;
      if (document.getElementById("jon-modellwahl")?.contains(ziel)) return;
      setOffen(false);
    };
    window.addEventListener("mousedown", zu);
    return () => window.removeEventListener("mousedown", zu);
  }, [offen]);

  useEffect(() => {
    const zeile = liste.current?.querySelector<HTMLElement>(`[data-index="${aktiv}"]`);
    zeile?.scrollIntoView({ block: "nearest" });
  }, [aktiv]);

  const waehlen = (m: string) => {
    onChange(m);
    setOffen(false);
    setSuche("");
  };

  const testen = async (liste: string[] = []) => {
    try {
      setLauf(await modelleTesten(provider, liste));
    } catch {
      setLauf(null);
    }
  };

  const tasten = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setAktiv((a) => Math.min(a + 1, sichtbar.length - 1));
      setZeige(sichtbar[Math.min(aktiv + 1, sichtbar.length - 1)] ?? "");
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setAktiv((a) => Math.max(a - 1, 0));
      setZeige(sichtbar[Math.max(aktiv - 1, 0)] ?? "");
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (sichtbar[aktiv]) waehlen(sichtbar[aktiv]);
    } else if (e.key === "Escape") {
      setOffen(false);
    }
  };

  const ueber = (m: string) => {
    if (warten.current) window.clearTimeout(warten.current);
    warten.current = window.setTimeout(() => setZeige(m), 220);
  };

  const karteId = zeige && sichtbar.includes(zeige) ? zeige : "";
  const aktuell = infos[model];

  return (
    <>
      <button
        ref={knopf}
        type="button"
        onClick={() => setOffen((o) => !o)}
        title={model}
        className="glass rounded-lg px-2 md:px-3 py-1.5 text-sm text-white/90 outline-none cursor-pointer min-w-0 max-w-[38vw] md:max-w-[240px] flex items-center gap-1.5"
      >
        {aktuell && <span className={`shrink-0 inline-block w-1.5 h-1.5 rounded-full ${ZUSTAND[aktuell.zustand].farbe}`} />}
        <span className="truncate">{kurzname(model) || models[0] || "Modell wählen"}</span>
        <ChevronDown size={14} className="shrink-0 text-white/50" />
      </button>
      {offen && (
        <div
          id="jon-modellwahl"
          className="fixed z-[70] flex items-start gap-2"
          style={{ left: lage.links, top: lage.oben, flexDirection: lage.karteLinks ? "row-reverse" : "row" }}
          onMouseLeave={() => setZeige("")}
        >
          <div className="glass-strong rounded-xl border border-white/10 shadow-2xl bg-ink-800/95 backdrop-blur" style={{ width: lage.breite }}>
            <div className="p-2 border-b border-white/10 space-y-2">
              <div className="flex items-center gap-2 rounded-lg bg-white/5 px-2 py-1.5">
                <Search size={14} className="text-white/40" />
                <input
                  ref={feld}
                  value={suche}
                  onChange={(e) => setSuche(e.target.value)}
                  onKeyDown={tasten}
                  placeholder={`In ${models.length} Modellen suchen …`}
                  className="flex-1 bg-transparent outline-none text-sm text-white placeholder:text-white/35"
                />
              </div>
              <div className="flex gap-1 flex-wrap">
                {FILTER.map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setFilter(f.id)}
                    className={`px-2 py-0.5 rounded-md text-[11px] border ${filter === f.id ? "bg-gold/20 border-gold/40 text-gold" : "border-white/10 text-white/60 hover:text-white"}`}
                  >
                    {f.name}
                  </button>
                ))}
              </div>
            </div>
            <div ref={liste} className="max-h-[52vh] overflow-y-auto py-1">
              {sichtbar.length === 0 && <div className="px-3 py-4 text-sm text-white/45">Kein Modell passt zur Suche.</div>}
              {sichtbar.map((m, index) => {
                const info = infos[m];
                const zustand = ZUSTAND[info?.zustand ?? "ungetestet"];
                return (
                  <button
                    key={m}
                    type="button"
                    data-index={index}
                    onClick={() => waehlen(m)}
                    onMouseEnter={() => {
                      setAktiv(index);
                      ueber(m);
                    }}
                    className={`w-full text-left px-3 py-1.5 flex items-center gap-2 text-sm ${index === aktiv ? "bg-white/10" : ""} ${m === model ? "text-gold" : "text-white/85"}`}
                  >
                    <span className={`shrink-0 w-1.5 h-1.5 rounded-full ${zustand.farbe}`} />
                    <span className="flex-1 min-w-0">
                      <span className="block truncate">{kurzname(m)}</span>
                      <span className="block truncate text-[11px] text-white/40">{info?.hersteller || m.split("/")[0]}</span>
                    </span>
                    <span className="shrink-0 flex items-center gap-1 text-white/45">
                      {info?.faehigkeiten.includes("bild_zu_text") && <BildIcon size={13} aria-label="Bild zu Text" />}
                      {info?.faehigkeiten.includes("video_zu_text") && <VideoIcon size={13} aria-label="Video zu Text" />}
                      {info?.faehigkeiten.includes("code") && <Code2 size={13} aria-label="Code" />}
                      {info?.faehigkeiten.includes("denken") && <Brain size={13} aria-label="Denkt" />}
                      {info?.kurz_s !== null && info?.kurz_s !== undefined && (
                        <span className="flex items-center gap-0.5 text-[11px] tabular-nums">
                          <Timer size={12} />
                          {sekunden(info.kurz_s)}
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
            <div className="px-3 py-2 border-t border-white/10 flex items-center justify-between text-[11px] text-white/50">
              {lauf?.laeuft ? (
                <span className="flex items-center gap-1.5 min-w-0">
                  <Loader2 size={12} className="animate-spin shrink-0" />
                  <span className="truncate">
                    Test {lauf.fertig}/{lauf.gesamt} · {kurzname(lauf.aktuell)}
                  </span>
                </span>
              ) : (
                <span>Maus kurz auf ein Modell halten für Details</span>
              )}
              <button
                type="button"
                disabled={lauf?.laeuft}
                onClick={() => void testen()}
                className="shrink-0 ml-2 text-gold hover:underline disabled:opacity-40"
              >
                Alle testen
              </button>
            </div>
          </div>
          {karteId && (
            <div className="glass-strong rounded-xl border border-white/10 shadow-2xl bg-ink-800/95 backdrop-blur p-3 w-[300px] max-w-[calc(100vw-16px)]">
              <Karte info={infos[karteId]} id={karteId} providerLabel={providerLabel} laeuft={!!lauf?.laeuft} onTesten={() => void testen([karteId])} />
            </div>
          )}
        </div>
      )}
    </>
  );
}
