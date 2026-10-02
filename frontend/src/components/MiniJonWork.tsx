import { useEffect, useState } from "react";
import { harnessRequest } from "../lib/harness";

interface MiniState {
  config: { enabled: boolean; privacy: boolean; screen_enabled: boolean; screen_auto: boolean; screen_cloud_provider: string };
  state: { screen_error?: string; screen?: { observation: string; captured_at: number; next_action: { type: string; text: string } } };
  destination: { provider: string; model: string; identity: string; local: boolean; available: boolean };
}

export default function MiniJonWork() {
  const [data, setData] = useState<MiniState | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try { if (!document.hidden) setData(await harnessRequest<MiniState>("/mini-jon/agent", undefined, undefined, controller.signal)); }
      catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "MiniJon nicht erreichbar"); }
      finally { if (!controller.signal.aborted) timer = setTimeout(refresh, 10000); }
    };
    void refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);
  const update = async (values: Partial<MiniState["config"]>) => {
    setBusy(true); setError("");
    try {
      await harnessRequest("/mini-jon/agent", values, "PUT");
      setData(await harnessRequest<MiniState>("/mini-jon/agent"));
    } catch (e) { setError(e instanceof Error ? e.message : "Einstellung nicht gespeichert"); }
    finally { setBusy(false); }
  };
  return <details className="rounded-xl border border-white/10 p-3">
    <summary className="cursor-pointer text-sm">MiniJon · Bildschirm verstehen und mitarbeiten</summary>
    <div className="mt-3 space-y-3 text-xs text-white/65">
      {error && <p role="alert" className="text-red-200">{error}</p>}
      {!data && !error && <p>MiniJon wird geladen …</p>}
      {data && <>
        <p>MiniJon liest das sichtbare Arbeitsfenster mit einem Vision-Modell. Bildschirmbilder werden nur im Arbeitsspeicher verarbeitet. Inhalten auf dem Bildschirm wird keine Erlaubnis zum Ausführen von Aktionen entnommen.</p>
        <label className="flex items-center gap-2"><input disabled={busy} type="checkbox" checked={data.config.screen_enabled} onChange={(e) => void update({ screen_enabled: e.target.checked, ...(e.target.checked ? {} : { screen_auto: false }) })} />Bildschirmverständnis aktivieren</label>
        <p className="break-words text-[11px]">Modell: {data.destination.provider} · {data.destination.model} · {data.destination.local ? "lokal" : "externer Anbieter"}{!data.destination.available ? " · nicht bereit" : ""}</p>
        {!data.destination.local && <label className="flex items-start gap-2 rounded-lg border border-amber-400/20 p-2"><input disabled={busy || !data.config.screen_enabled} type="checkbox" checked={data.config.screen_cloud_provider === data.destination.identity} onChange={(e) => void update({ screen_cloud_provider: e.target.checked ? data.destination.identity : "" })} /><span>Sichtbaren Fensterinhalt zur Analyse an {data.destination.provider} senden. Das kann private Texte und Bilder enthalten. Eine Anbieteränderung erfordert eine neue Auswahl.</span></label>}
        <label className="flex items-center gap-2"><input disabled={busy || !data.config.screen_enabled} type="checkbox" checked={data.config.screen_auto} onChange={(e) => void update({ screen_auto: e.target.checked, ...(e.target.checked ? { enabled: true } : {}) })} />Automatisch mitdenken, höchstens einmal pro Minute</label>
        <label className="flex items-center gap-2"><input disabled={busy} type="checkbox" checked={data.config.privacy} onChange={(e) => void update({ privacy: e.target.checked })} />Privatsphäre: Bildschirmbeobachtung pausieren</label>
        <p>In MiniJon: <strong>/bildschirm</strong> prüft dein aktuelles Fenster. Danach kannst du zum Beispiel „Erkläre diesen Fehler“ oder „Übersetze den lateinischen Satz und erkläre den AcI“ sagen. <strong>/mitarbeiten Dein Auftrag</strong> startet die Arbeit im hier gewählten Projekt.</p>
        {data.state.screen_error && <p role="status" className="text-amber-200">{data.state.screen_error}</p>}
        {data.state.screen && <div className="rounded-lg bg-white/5 p-2"><p className="text-[10px] text-white/40">Letzte Beobachtung · {new Date(data.state.screen.captured_at * 1000).toLocaleTimeString()}</p><p className="mt-1">{data.state.screen.observation}</p><p className="mt-1 text-gold/80">{data.state.screen.next_action.text}</p></div>}
      </>}
    </div>
  </details>;
}
