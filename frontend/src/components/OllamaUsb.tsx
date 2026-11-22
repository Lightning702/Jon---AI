import { useEffect, useRef, useState } from "react";
import { Check, FileBox, FolderOpen, HardDrive, Loader2, MessageSquare, Plug, Search, TriangleAlert, Unplug, Usb } from "lucide-react";
import { pickFolderDialog } from "../lib/api";
import {
  anbieterNeuLaden,
  groesseText,
  modellWaehlen,
  usbEinbinden,
  usbStand,
  usbSuchen,
  usbTrennen,
  usbVerbinden,
  type UsbFund,
  type UsbLaufwerk,
  type UsbModell,
  type UsbStand,
} from "../lib/usb";

const field =
  "w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50";
const section = "text-[11px] uppercase tracking-wide text-gold/70";
const chip =
  "text-[11px] px-2.5 py-1.5 rounded-lg border border-white/10 bg-white/5 text-white/70 hover:bg-white/10 transition disabled:opacity-40 inline-flex items-center gap-1.5";
const gold =
  "text-[12px] px-3 py-1.5 rounded-lg border border-gold/35 bg-gold/12 text-gold/90 hover:bg-gold/20 transition disabled:opacity-40 inline-flex items-center gap-1.5";

function laufwerkText(eintrag: UsbLaufwerk): string {
  const name = eintrag.name ? ` ${eintrag.name}` : "";
  return `${eintrag.pfad.replace(/\\$/, "")}${name} · ${groesseText(eintrag.frei)} frei`;
}

function modellDetails(modell: UsbModell): string {
  return [groesseText(modell.groesse), modell.familie, modell.parameter, modell.quantisierung].filter(Boolean).join(" · ");
}

function gleicherPfad(a: string, b: string): boolean {
  const norm = (text: string) => text.replace(/[\\/]+$/, "").replace(/\//g, "\\").toLowerCase();
  return !!a && !!b && norm(a) === norm(b);
}

export default function OllamaUsb({ onModelsChanged }: { onModelsChanged?: () => void }) {
  const [stand, setStand] = useState<UsbStand | null>(null);
  const [pfad, setPfad] = useState("");
  const [fund, setFund] = useState<UsbFund | null>(null);
  const [namen, setNamen] = useState<Record<string, string>>({});
  const [suche, setSuche] = useState(false);
  const [arbeit, setArbeit] = useState("");
  const [fehler, setFehler] = useState("");
  const [hinweis, setHinweis] = useState("");
  const lebt = useRef(true);
  const lief = useRef(false);

  const laden = async () => {
    try {
      const neu = await usbStand();
      if (!lebt.current) return;
      setStand(neu);
      if (lief.current && !neu.aufgabe?.laeuft) {
        lief.current = false;
        if (neu.aufgabe?.fertig) {
          setHinweis(neu.aufgabe.text || "Fertig eingebunden.");
          anbieterNeuLaden();
          onModelsChanged?.();
          if (pfad) void durchsuchen(pfad, true);
        }
      }
      if (neu.aufgabe?.laeuft) lief.current = true;
    } catch (err) {
      if (lebt.current) setFehler(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    lebt.current = true;
    void laden();
    return () => {
      lebt.current = false;
    };
  }, []);

  useEffect(() => {
    if (!stand?.aufgabe?.laeuft) return;
    const takt = window.setInterval(() => void laden(), 1500);
    return () => window.clearInterval(takt);
  }, [stand?.aufgabe?.laeuft]);

  const durchsuchen = async (ziel: string, still = false) => {
    const text = ziel.trim();
    if (!text) return;
    setPfad(text);
    setSuche(true);
    setFehler("");
    if (!still) {
      setHinweis("");
      setFund(null);
    }
    try {
      const ergebnis = await usbSuchen(text);
      if (!lebt.current) return;
      setFund(ergebnis);
      setNamen((alt) => {
        const neu = { ...alt };
        for (const datei of ergebnis.gguf) if (!neu[datei.pfad]) neu[datei.pfad] = datei.vorschlag;
        return neu;
      });
    } catch (err) {
      if (lebt.current) setFehler(err instanceof Error ? err.message : String(err));
    } finally {
      if (lebt.current) setSuche(false);
    }
  };

  const ordnerWaehlen = async () => {
    const gewaehlt = await pickFolderDialog();
    if (gewaehlt) void durchsuchen(gewaehlt);
  };

  const verbinden = async (speicher: string) => {
    setArbeit(speicher);
    setFehler("");
    setHinweis("Jon startet Ollama für den Stick – das dauert beim ersten Mal bis zu 30 Sekunden …");
    try {
      const neu = await usbVerbinden(speicher, fund?.programme ?? []);
      if (!lebt.current) return;
      setStand((alt) => ({ ...neu, laufwerke: alt?.laufwerke }));
      setHinweis(neu.modelle.length === 1 ? "Verbunden: 1 Modell vom Stick ist jetzt in Jon wählbar." : `Verbunden: ${neu.modelle.length} Modelle vom Stick sind jetzt in Jon wählbar.`);
      anbieterNeuLaden();
      onModelsChanged?.();
    } catch (err) {
      if (lebt.current) {
        setHinweis("");
        setFehler(err instanceof Error ? err.message : String(err));
      }
    } finally {
      if (lebt.current) setArbeit("");
    }
  };

  const trennen = async () => {
    setArbeit("trennen");
    setFehler("");
    try {
      const neu = await usbTrennen();
      if (!lebt.current) return;
      setStand((alt) => ({ ...neu, laufwerke: alt?.laufwerke }));
      setHinweis("Getrennt. Du kannst den Stick jetzt abziehen.");
      anbieterNeuLaden();
      onModelsChanged?.();
    } catch (err) {
      if (lebt.current) setFehler(err instanceof Error ? err.message : String(err));
    } finally {
      if (lebt.current) setArbeit("");
    }
  };

  const einbinden = async (datei: string) => {
    setFehler("");
    setHinweis("");
    try {
      const neu = await usbEinbinden(datei, namen[datei] || "");
      if (!lebt.current) return;
      lief.current = true;
      setStand((alt) => ({ ...neu, laufwerke: alt?.laufwerke }));
    } catch (err) {
      if (lebt.current) setFehler(err instanceof Error ? err.message : String(err));
    }
  };

  const verwenden = (modell: UsbModell) => {
    modellWaehlen("ollama", modell.id);
    setHinweis(`${modell.name} ist jetzt dein Modell im Chat.`);
  };

  const aufgabe = stand?.aufgabe ?? {};
  const verbunden = !!stand?.aktiv;
  const laufwerke = stand?.laufwerke ?? [];

  return (
    <section className="space-y-2">
      <div className={`${section} flex items-center gap-1.5`}>
        <Usb size={13} /> USB-Stick & Laufwerke
      </div>
      <p className="text-[11px] text-white/40 leading-relaxed">
        Nimm Ollama-Modelle direkt von einem USB-Stick oder einer externen Platte, ohne sie auf den PC zu kopieren.
        Wähle das Laufwerk, zum Beispiel <code>D:\</code> – Jon zeigt alle Modelle, die dort liegen.
      </p>

      {verbunden && stand && (
        <div className="rounded-xl border border-gold/25 bg-gold/[0.06] px-3 py-2.5 space-y-2">
          <div className="flex items-center gap-2 text-[12px]">
            <span className={`w-2 h-2 rounded-full ${stand.laeuft ? "bg-emerald-400" : stand.eingesteckt ? "bg-amber-400" : "bg-rose-400"}`} />
            <span className="text-white/85 flex-1 min-w-0 truncate" title={stand.speicher}>
              {stand.eingesteckt ? (stand.laeuft ? "Verbunden" : "Bereit, startet bei Bedarf") : "Stick nicht eingesteckt"} · {stand.speicher}
            </span>
            <button onClick={() => void trennen()} disabled={!!arbeit} className={chip}>
              <Unplug size={12} /> Trennen
            </button>
          </div>
          {stand.modelle.length > 0 && (
            <div className="space-y-1">
              {stand.modelle.map((modell) => (
                <div key={modell.id} className="flex items-center gap-2 text-[12px]">
                  <div className="flex-1 min-w-0">
                    <div className="text-white/85 truncate">{modell.name}</div>
                    <div className="text-[10.5px] text-white/40 truncate">{modellDetails(modell)}</div>
                  </div>
                  <button onClick={() => verwenden(modell)} disabled={!modell.vollstaendig} className={gold}>
                    <MessageSquare size={12} /> Im Chat verwenden
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {laufwerke.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {laufwerke.map((eintrag) => (
            <button
              key={eintrag.pfad}
              onClick={() => void durchsuchen(eintrag.pfad)}
              disabled={suche}
              title={eintrag.art === "usb" ? "Wechseldatenträger" : eintrag.system ? "Systemlaufwerk" : "Laufwerk"}
              className={`${chip} ${gleicherPfad(pfad, eintrag.pfad) ? "border-gold/40 text-gold/90" : ""}`}
            >
              {eintrag.art === "usb" ? <Usb size={12} /> : <HardDrive size={12} />}
              {laufwerkText(eintrag)}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input
          className={field}
          placeholder="D:\ oder ein Ordner auf dem Stick"
          value={pfad}
          onChange={(e) => setPfad(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void durchsuchen(pfad);
          }}
        />
        <button onClick={() => void ordnerWaehlen()} disabled={suche} className={chip} title="Ordner auswählen">
          <FolderOpen size={13} />
        </button>
        <button onClick={() => void durchsuchen(pfad)} disabled={suche || !pfad.trim()} className={gold}>
          {suche ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
          Suchen
        </button>
      </div>

      {fund && (
        <div className="space-y-2">
          {fund.speicher.map((speicher) => {
            const istVerbunden = verbunden && gleicherPfad(stand?.speicher ?? "", speicher.pfad);
            return (
              <div key={speicher.pfad} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 space-y-1.5">
                <div className="flex items-center gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] text-white/85 truncate" title={speicher.pfad}>
                      {speicher.pfad}
                    </div>
                    <div className="text-[10.5px] text-white/40">
                      {speicher.modelle.length === 1 ? "1 Ollama-Modell" : `${speicher.modelle.length} Ollama-Modelle`} · {groesseText(speicher.groesse)}
                    </div>
                  </div>
                  {istVerbunden ? (
                    <span className="text-[11px] text-emerald-300/90 inline-flex items-center gap-1">
                      <Check size={12} /> Verbunden
                    </span>
                  ) : (
                    <button onClick={() => void verbinden(speicher.pfad)} disabled={!!arbeit || !speicher.modelle.length} className={gold}>
                      {arbeit === speicher.pfad ? <Loader2 size={12} className="animate-spin" /> : <Plug size={12} />}
                      Verbinden
                    </button>
                  )}
                </div>
                {speicher.modelle.map((modell) => (
                  <div key={modell.id} className="flex items-center gap-2 text-[11.5px] pl-1">
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${modell.vollstaendig ? "bg-emerald-400/80" : "bg-amber-400"}`} />
                    <span className="text-white/80 truncate">{modell.name}</span>
                    <span className="text-white/35 truncate">{modellDetails(modell)}</span>
                    {!modell.vollstaendig && <span className="text-amber-300/90 shrink-0">unvollständig kopiert</span>}
                  </div>
                ))}
              </div>
            );
          })}

          {fund.gguf.length > 0 && (
            <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 space-y-2">
              <div className="text-[11px] text-white/50 leading-relaxed">
                Einzelne Modelldateien (.gguf). Mit „Einbinden“ übernimmt Ollama sie in einen Modellordner auf demselben
                Laufwerk – sie bleiben auf dem Stick, brauchen dort aber kurz doppelt Platz.
              </div>
              {fund.gguf.map((datei) => {
                const laeuftHier = aufgabe.laeuft && aufgabe.datei === datei.pfad;
                return (
                  <div key={datei.pfad} className="space-y-1">
                    <div className="flex items-center gap-2 text-[12px]">
                      <FileBox size={13} className="text-white/45 shrink-0" />
                      <span className="text-white/80 truncate flex-1 min-w-0" title={datei.pfad}>
                        {datei.datei}
                      </span>
                      <span className="text-white/40 shrink-0">{groesseText(datei.groesse)}</span>
                    </div>
                    <div className="flex gap-2">
                      <input
                        className={field}
                        value={namen[datei.pfad] ?? datei.vorschlag}
                        onChange={(e) => setNamen((alt) => ({ ...alt, [datei.pfad]: e.target.value }))}
                        placeholder="Name in Ollama"
                      />
                      <button onClick={() => void einbinden(datei.pfad)} disabled={!!aufgabe.laeuft} className={gold}>
                        {laeuftHier ? <Loader2 size={12} className="animate-spin" /> : <Plug size={12} />}
                        Einbinden
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {!fund.speicher.length && !fund.gguf.length && (
            <div className="text-[11.5px] text-white/50 leading-relaxed">
              Auf {fund.pfad} habe ich keine Ollama-Modelle gefunden. Kopiere dafür den Ordner <code>models</code> aus{" "}
              <code>%USERPROFILE%\.ollama</code> auf den Stick, oder leg .gguf-Dateien darauf.
            </div>
          )}
          {fund.abgebrochen && (
            <div className="text-[11px] text-amber-300/80">
              Das Laufwerk ist sehr voll – ich habe nicht alles durchsucht. Wähle am besten direkt den Ordner mit den Modellen.
            </div>
          )}
        </div>
      )}

      {aufgabe.laeuft && (
        <div className="flex items-center gap-2 text-[11.5px] text-white/70">
          <Loader2 size={13} className="animate-spin text-gold/80" />
          <span>{aufgabe.text}</span>
        </div>
      )}
      {!aufgabe.laeuft && aufgabe.fehler && (
        <div className="flex items-start gap-2 text-[11.5px] text-rose-300/90">
          <TriangleAlert size={13} className="shrink-0 mt-0.5" />
          <span>{aufgabe.fehler}</span>
        </div>
      )}
      {fehler && <div className="text-[11.5px] text-rose-300/90">{fehler}</div>}
      {hinweis && !fehler && <div className="text-[11.5px] text-emerald-300/85">{hinweis}</div>}
    </section>
  );
}
