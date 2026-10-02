import React, {useEffect, useState} from "react";
import {Check, Search} from "lucide-react";
import {call, haptic} from "./bridge";
import {Busy, Sheet, errorText} from "./ui";

export type JonApp = {id: string; paket: string; name: string; installiert?: boolean};

export const alteApps: JonApp[] = [
  {id: "whatsapp", paket: "com.whatsapp", name: "WhatsApp"},
  {id: "tiktok", paket: "com.zhiliaoapp.musically", name: "TikTok"},
  {id: "amazon", paket: "com.amazon.mp3", name: "Amazon Music"}
];

const symbole = new Map<string, string>();
const offen = new Set<string>();
const hoerer = new Set<() => void>();
let geplant: ReturnType<typeof setTimeout> | null = null;

function nachladen() {
  geplant = null;
  const pakete = Array.from(offen).slice(0, 24);
  pakete.forEach(p => offen.delete(p));
  if (!pakete.length) return;
  call<Record<string, string>>("apps-symbole", {pakete}).then(r => {
    pakete.forEach(p => symbole.set(p, r?.[p] || ""));
  }).catch(() => pakete.forEach(p => symbole.set(p, ""))).finally(() => {
    hoerer.forEach(h => h());
    if (offen.size && !geplant) geplant = setTimeout(nachladen, 16);
  });
}

export function AppSymbol({paket, name = "", groesse = 28}: {paket: string; name?: string; groesse?: number}) {
  const [, setStand] = useState(0);
  useEffect(() => {
    const h = () => setStand(s => s + 1);
    hoerer.add(h);
    if (!symbole.has(paket) && !offen.has(paket)) {
      offen.add(paket);
      if (!geplant) geplant = setTimeout(nachladen, 16);
    }
    return () => {hoerer.delete(h);};
  }, [paket]);
  const bild = symbole.get(paket);
  if (bild) return <img className="app-symbol" src={`data:image/png;base64,${bild}`} alt={name} style={{width: groesse, height: groesse}}/>;
  return <span className="app-symbol leer" style={{width: groesse, height: groesse, fontSize: Math.round(groesse * .45)}}>{name.slice(0, 1).toUpperCase()}</span>;
}

export function useApps() {
  const [apps, setApps] = useState<JonApp[] | null>(null);
  useEffect(() => {
    let aktiv = true;
    const laden = () => call("apps").then((r: any) => {if (aktiv) setApps(Array.isArray(r?.liste) ? r.liste : alteApps.map(a => ({...a, installiert: r?.[a.id] !== false})));}).catch(() => {if (aktiv) setApps([]);});
    laden();
    window.addEventListener("jon-apps", laden);
    return () => {aktiv = false; window.removeEventListener("jon-apps", laden);};
  }, []);
  return apps;
}

export function AppWahl({open, onClose, notify}: {open: boolean; onClose: () => void; notify: (s: string) => void}) {
  const [liste, setListe] = useState<any[] | null>(null), [wahl, setWahl] = useState<string[]>([]), [suche, setSuche] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    setListe(null);
    setSuche("");
    call("apps-installiert").then((r: any) => {
      const alle: any[] = r?.apps || [];
      setListe(alle);
      setWahl(alle.filter(a => a.gewaehlt).map(a => a.paket));
    }).catch(e => {notify(errorText(e)); setListe([]);});
  }, [open]);
  const sichtbar = (liste || []).filter(a => !suche.trim() || a.name.toLowerCase().includes(suche.trim().toLowerCase()));
  const gewaehlt = sichtbar.filter(a => wahl.includes(a.paket));
  const rest = sichtbar.filter(a => !wahl.includes(a.paket));
  async function speichern() {
    setBusy(true);
    try {
      const r = await call("apps-setzen", {pakete: wahl});
      haptic("success");
      notify(`${(r?.liste || []).length} Apps sind freigegeben.`);
      window.dispatchEvent(new Event("jon-apps"));
      onClose();
    } catch (e) {notify(errorText(e));} finally {setBusy(false);}
  }
  const zeile = (a: any) => {
    const an = wahl.includes(a.paket);
    return <button key={a.paket} className={`list-row app-wahl ${an ? "an" : ""}`} onClick={() => {haptic("tick"); setWahl(w => an ? w.filter(x => x !== a.paket) : [...w, a.paket]);}}>
      <AppSymbol paket={a.paket} name={a.name} groesse={38}/>
      <span>{a.name}{a.laden && <small className="warn-text">Darüber lassen sich neue Apps installieren</small>}</span>
      <span className={`haken ${an ? "an" : ""}`}>{an && <Check/>}</span>
    </button>;
  };
  return <Sheet open={open} title="Apps für Jon" onClose={onClose} footer={<div style={{padding: "8px 20px 4px"}}><button className="btn primary" disabled={busy || liste === null} onClick={speichern}>{wahl.length === 1 ? "1 App freigeben" : `${wahl.length} Apps freigeben`}</button></div>}>
    <p>Diese Apps lassen sich aus Jon öffnen. Im Kiosk sind nur sie erreichbar, und für sie gelten Limits und Schlafenszeit.</p>
    <div className="search-field"><Search/><input placeholder="App suchen" value={suche} onChange={e => setSuche(e.target.value)}/></div>
    {liste === null ? <Busy/> : <>
      {gewaehlt.length > 0 && <div className="provider-head">Freigegeben</div>}
      {gewaehlt.map(zeile)}
      {rest.length > 0 && <div className="provider-head">Weitere Apps</div>}
      {rest.map(zeile)}
      {!sichtbar.length && <p className="muted">Keine App gefunden.</p>}
    </>}
  </Sheet>;
}
