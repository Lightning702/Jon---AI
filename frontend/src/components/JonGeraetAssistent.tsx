import { useEffect, useState } from "react";
import { BASE, HandyGeraet, HandyKopplung, HandyStand, VerbundGeraet, handyQrUrl, verbundGeraete } from "../lib/api";

type Vpn = { installiert: boolean; verbunden: boolean; adressen: string[]; geraete: { name: string; adresse: string; online: boolean; system: string }[] };
type AppStand = { verfuegbar: boolean; version?: string; groesse?: number; heimnetz?: boolean; urls?: string[] };

export async function geraeteZielRuf<T>(ziel: string, pfad: string, methode = "GET", rumpf?: object, query?: Record<string, string>): Promise<T> {
  const url = ziel ? `${BASE}/verbund/${encodeURIComponent(ziel)}/rufen` : `${BASE}${pfad.replace(/^\/api/, "")}${query ? `?${new URLSearchParams(query)}` : ""}`;
  const res = await fetch(url, {
    method: ziel ? "POST" : methode,
    headers: { "Content-Type": "application/json" },
    body: ziel ? JSON.stringify({ methode, pfad, rumpf, query }) : rumpf ? JSON.stringify(rumpf) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Der Jon-Server ist nicht erreichbar.");
  if (!ziel) return data as T;
  let result: Record<string, unknown>;
  try { result = JSON.parse(data.text || "{}"); } catch { throw new Error("Der Pi hat eine ungültige Antwort geliefert."); }
  if (!data.ok) throw new Error(String(result.detail || result.fehler || "Der Pi hat die Anfrage abgelehnt."));
  return result as T;
}

export default function JonGeraetAssistent({ onClose, onLegacy }: { onClose: () => void; onLegacy: () => void }) {
  const [vpn, setVpn] = useState<Vpn | null>(null);
  const [ziele, setZiele] = useState<VerbundGeraet[]>([]);
  const [ziel, setZiel] = useState("");
  const [adresse, setAdresse] = useState("");
  const [piCode, setPiCode] = useState("");
  const [paar, setPaar] = useState<HandyKopplung | null>(null);
  const [stand, setStand] = useState<HandyStand>({ status: "leer" });
  const [geraete, setGeraete] = useState<HandyGeraet[]>([]);
  const [fehler, setFehler] = useState("");
  const [hinweis, setHinweis] = useState("");
  const [busy, setBusy] = useState(false);
  const [app, setApp] = useState<AppStand | null>(null);
  const [appUrl, setAppUrl] = useState("");
  const [neustart, setNeustart] = useState(false);
  const button = "rounded-xl border border-gold/30 bg-gold/10 px-4 py-2 text-gold disabled:opacity-40 hover:bg-gold/20";
  const input = "w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2 text-white outline-none focus:border-gold/60";

  async function pruefen() {
    const [v, g] = await Promise.all([geraeteZielRuf<Vpn>("", "/api/handy/vpn"), verbundGeraete()]);
    setVpn(v); setZiele(g);
  }
  useEffect(() => { void pruefen().catch(e => setFehler(e.message)); }, []);
  useEffect(() => {
    setApp(null);
    void geraeteZielRuf<AppStand>(ziel, "/api/handy/app/adressen").then(a => { setApp(a); setAppUrl(a.urls?.[0] ?? ""); }).catch(() => setApp({ verfuegbar: false }));
  }, [ziel]);
  async function heimnetzAn() {
    await geraeteZielRuf(ziel, "/api/system/heimnetz", "POST", { an: true });
    setNeustart(true);
  }
  useEffect(() => {
    if (!paar) return;
    let aktiv = true;
    let timer: ReturnType<typeof setTimeout>;
    const laden = async () => {
      try {
        const s = await geraeteZielRuf<HandyStand>(ziel, "/api/handy/pairing/state");
        if (!aktiv) return;
        setStand(s);
        if (s.status === "verbunden") {
          const d = await geraeteZielRuf<{ geraete: HandyGeraet[] }>(ziel, "/api/handy/devices");
          if (aktiv) setGeraete(d.geraete);
        }
      } catch (e) { if (aktiv) setFehler(e instanceof Error ? e.message : "Verbindung unterbrochen"); }
      if (aktiv) timer = setTimeout(laden, 3000);
    };
    void laden();
    return () => { aktiv = false; clearTimeout(timer); void geraeteZielRuf(ziel, "/api/handy/pairing/cancel", "POST").catch(() => undefined); };
  }, [paar, ziel]);

  async function ausfuehren(action: () => Promise<void>) {
    setBusy(true); setFehler("");
    try { await action(); } catch (e) { setFehler(e instanceof Error ? e.message : "Einrichtung fehlgeschlagen."); }
    finally { setBusy(false); }
  }
  async function starten() {
    const serverVpn = await geraeteZielRuf<Vpn>(ziel, "/api/handy/vpn");
    const heimnetz = Boolean(app?.heimnetz);
    if (!serverVpn.verbunden && !heimnetz) throw new Error("Melde Tailscale auf dem ausgewählten Jon an oder gib ihn oben im Heimnetz frei.");
    const p = await geraeteZielRuf<HandyKopplung>(ziel, "/api/handy/pairing/start", "POST", undefined, { direct_only: "true" });
    const payload = JSON.parse(p.nutzlast);
    const adressen: string[] = payload.us || [];
    const tailscale = adressen.some((a: string) => {
      try { const h = new URL(a).hostname; const parts = h.split(".").map(Number); return parts.length === 4 && parts[0] === 100 && parts[1] >= 64 && parts[1] <= 127; } catch { return false; }
    });
    if (payload.direct_only !== true || !(tailscale || (heimnetz && adressen.length > 0))) {
      await geraeteZielRuf(ziel, "/api/handy/pairing/cancel", "POST");
      throw new Error("Der ausgewählte Jon braucht die neue Version und eine Adresse im Heimnetz oder über Tailscale.");
    }
    setPaar(p); setStand({ status: "offen" });
  }

  return <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
    <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-gold/25 bg-[#0b0b0f] text-white/85 shadow-2xl">
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#0b0b0f] p-4">
        <h2 className="text-lg text-gold">Jon-Gerät einrichten</h2><button onClick={onClose} aria-label="Schließen">✕</button>
      </div>
      <div className="space-y-5 p-5 text-sm">
        <p>Verbinde ein Handy mit Jon auf diesem PC oder auf deinem Pi. Mit dem Pi funktionieren Chat, Sprache und die erlaubten Apps auch unterwegs und bei ausgeschaltetem PC.</p>
        {fehler && <div role="alert" className="rounded-xl border border-red-400/30 bg-red-400/10 p-3 text-red-200">{fehler}</div>}
        {hinweis && <p role="status" className="text-emerald-200">{hinweis}</p>}
        <section className="space-y-3 rounded-xl border border-white/10 p-4">
          <h3 className="text-base">0 · App aufs Handy</h3>
          {!app ? <p className="text-white/50">Prüfe …</p> : !app.verfuegbar ? <p>Auf diesem Jon liegt noch keine App. Sie kommt mit dem nächsten Update automatisch dazu.</p> : !app.heimnetz ? <>
            <p>Damit das Handy die App laden und Jon danach erreichen kann, muss dieser Jon im Heimnetz erreichbar sein.</p>
            {neustart ? <p className="text-amber-200">Freigegeben. Schließe Jon einmal und öffne ihn wieder – danach erscheint hier der QR-Code. Erlaubt Windows den Zugriff im Heimnetz, bitte bestätigen.</p>
              : <button className={button} disabled={busy} onClick={() => void ausfuehren(heimnetzAn)}>Im Heimnetz freigeben</button>}
          </> : <>
            <p>Mit der Handy-Kamera scannen, „Jon Gerät {app.version}“ laden und öffnen. Android fragt einmal, ob Installationen aus dieser Quelle erlaubt sind.</p>
            {(app.urls?.length ?? 0) > 1 && <select className={input} value={appUrl} onChange={e => setAppUrl(e.target.value)}>{app.urls?.map(u => <option key={u} value={u}>{u}</option>)}</select>}
            {appUrl && <img className="h-48 w-48 rounded-xl bg-white p-2" src={handyQrUrl(appUrl)} alt="App herunterladen" />}
            <p className="text-xs text-white/50">{appUrl} · {Math.round((app.groesse ?? 0) / 1_048_576)} MB · Handy im selben WLAN</p>
          </>}
        </section>
        <section className="space-y-3 rounded-xl border border-white/10 p-4">
          <h3 className="text-base">1 · Privates Netz</h3>
          <p>Tailscale einmal auf PC, Pi und Handy installieren und mit demselben persönlichen Konto anmelden.</p>
          <p>{vpn?.verbunden ? "Dieser Jon ist mit Tailscale verbunden." : vpn?.installiert ? "Tailscale ist installiert, aber noch nicht verbunden." : "Tailscale wurde hier noch nicht gefunden."}</p>
          <div className="flex gap-3"><a className={button} href="https://tailscale.com/download" target="_blank" rel="noreferrer">Tailscale öffnen</a><button className={button} disabled={busy} onClick={() => void ausfuehren(pruefen)}>Erneut prüfen</button></div>
        </section>
        <section className="space-y-3 rounded-xl border border-white/10 p-4">
          <h3 className="text-base">2 · Jon-Server wählen</h3>
          <select className={input} value={ziel} disabled={Boolean(paar) || busy} onChange={e => setZiel(e.target.value)}>
            <option value="">Dieser Jon ({window.location.hostname || "PC"})</option>
            {ziele.map(g => <option key={g.id} value={g.id}>{g.name} · {g.adressen.join(", ")}</option>)}
          </select>
          {!paar && <details><summary className="cursor-pointer text-gold">Pi fehlt in der Liste</summary>
            <div className="mt-3 space-y-3">
              <p>Öffne Jon auf dem Pi, starte dort diese Einrichtung mit „Dieser Jon“ und erzeuge einen Code. Trage seine Tailscale-Adresse und den Code hier ein; bestätige anschließend am Pi.</p>
              {vpn?.geraete.filter(g => g.system === "linux").map(g => <button className="block text-gold" key={g.adresse} onClick={() => setAdresse(`http://${g.adresse}:8756`)}>{g.name} · {g.online ? "online" : "offline"} · Adresse übernehmen</button>)}
              <input className={input} value={adresse} onChange={e => setAdresse(e.target.value)} placeholder="http://100.x.x.x:8756" aria-label="Pi-Adresse" />
              <input className={input} value={piCode} onChange={e => setPiCode(e.target.value)} placeholder="Code vom Pi" aria-label="Pi-Kopplungscode" />
              <button className={button} disabled={busy || !adresse || !piCode} onClick={() => void ausfuehren(async () => {
                setHinweis("Die Anfrage jetzt in Jon auf dem Pi bestätigen.");
                const res = await fetch(`${BASE}/verbund/koppeln`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: piCode, adresse }) });
                const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Pi-Kopplung fehlgeschlagen.");
                await pruefen(); setZiel(data.id); setPiCode(""); setHinweis("Pi verbunden. Jetzt das Handy koppeln.");
              })}>Pi hinzufügen</button>
            </div>
          </details>}
        </section>
        <section className="space-y-3 rounded-xl border border-white/10 p-4">
          <h3 className="text-base">3 · Handy mit diesem Server koppeln</h3>
          {!paar ? <button className={button} disabled={busy} onClick={() => void ausfuehren(starten)}>QR-Code erzeugen</button> : <>
            <p className="text-gold">Ziel: {paar.pc.name}</p>
            <p>In der App „Jon Gerät“ unter Einstellungen → Workspace „QR-Code scannen“ wählen. Im selben WLAN geht das direkt, unterwegs braucht das Handy Tailscale.</p>
            <img className="h-56 w-56 rounded-xl bg-white p-2" src={handyQrUrl(paar.nutzlast)} alt={`Kopplung mit ${paar.pc.name}`} />
            <p>Code zum Hinzufügen dieses Pi am Desktop: <strong className="select-all font-mono tracking-widest">{JSON.parse(paar.nutzlast).c}</strong></p>
            <p className="text-xs text-white/50">VPN-Kopplung · kein öffentlicher Relay-Fallback · QR-Code gilt einmal, höchstens zehn Minuten</p>
            <p>Status: {stand.status}{stand.rest !== undefined ? ` · ${Math.ceil(stand.rest / 60)} Minuten` : ""}</p>
            {stand.status === "wartet" && <div className="space-y-2"><p>{stand.geraet?.name} möchte sich verbinden.</p><div className="flex gap-3">
              {[true, false].map(ok => <button key={String(ok)} className={button} disabled={busy} onClick={() => void ausfuehren(async () => {
                await geraeteZielRuf(ziel, "/api/handy/pairing/answer", "POST", { angenommen: ok });
              })}>{ok ? "Dieses Handy verbinden" : "Ablehnen"}</button>)}
            </div></div>}
            <button className={button} onClick={() => { setPaar(null); setStand({ status: "leer" }); }}>Kopplung schließen</button>
          </>}
        </section>
        {stand.status === "verbunden" && <section className="space-y-3 rounded-xl border border-emerald-400/25 p-4">
          <h3 className="text-base text-emerald-200">4 · Verbindung und Gerätemodus prüfen</h3>
          {geraete.map(g => <div key={g.id} className="rounded-lg bg-white/5 p-3">
            <p>{g.name} · {g.online ? "online" : "wartet auf Handy"}</p>
            <p className="text-xs text-white/50">{g.faehigkeiten?.join(" · ") || "Noch keine Fähigkeiten gemeldet"}</p>
            <p className="text-xs">Kiosk: {g.zustand?.kiosk ? "aktiv" : "aus"} · Device Owner: {g.zustand?.device_owner ? "bereit" : "noch einrichten"}</p>
          </div>)}
          <p>In der neuen Android-App „Jon Gerät“ unter „Gerät“ Mikrofon und Medienzugriff freigeben, „Hey Jon“ einschalten, Admin-PIN und Recovery-Code einrichten. Kiosk erst nach erfolgreichem Test aktivieren.</p>
          <p>Abschließend WLAN am Handy ausschalten und über Mobilfunk testen. Der Pi muss laufen; der PC darf ausgeschaltet sein.</p>
        </section>}
        <button className="text-xs text-white/40 underline" onClick={onLegacy}>Bisherige Handy-Kopplung verwenden</button>
      </div>
    </div>
  </div>;
}
