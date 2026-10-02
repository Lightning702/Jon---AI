import React, {useEffect, useLayoutEffect, useRef, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {ArrowLeft, ArrowUp, Camera, Check, CheckCheck, Clock, Copy, FileText, MessageSquarePlus, Paperclip, Play, Reply, Search, ShieldBan, Trash2, UserPlus, Users, X} from "lucide-react";
import {api, binary, call, enc, haptic} from "./bridge";
import {readUpload} from "./Chat";
import {PageProps} from "./Pages";
import {LANG} from "./useChats";
import {Busy, Circle, Empty, Field, PageHeader, Sheet, errorText, showImage, spring, useBackHandler} from "./ui";

type Nachricht = {id: string; peer_id: string; group_id: string | null; direction: "in" | "out"; sender_name: string; text: string; media_kind: string | null; media_name: string | null; media_mime: string | null; transcript: string | null; reply_to: string | null; reply_preview: string | null; reactions: Record<string, string[]>; deleted: boolean; delivered: boolean; read: boolean; has_media: boolean; created_at: string};
type Ziel = {art: "peer" | "gruppe"; id: string; name: string; avatar: string; peer?: any; gruppe?: any};
const reaktionen = ["❤️", "👍", "😂", "😮", "😢", "🙏"];
const alsListe = <T,>(v: unknown): T[] => Array.isArray(v) ? v as T[] : [];

function zeit(iso: string) {
  const d = new Date(iso);
  const heute = new Date();
  return d.toDateString() === heute.toDateString() ? d.toLocaleTimeString("de-DE", {hour: "2-digit", minute: "2-digit"}) : d.toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit"});
}

function Medien({m, notify}: {m: Nachricht; notify: (s: string) => void}) {
  const [quelle, setQuelle] = useState(""), [text, setText] = useState(m.transcript || "");
  const laden = async () => {
    try {const r = await binary(`/api/p2p/media/${enc(m.id)}`); const q = `data:${r.mime};base64,${r.data}`; setQuelle(q); return q;} catch (e) {notify(errorText(e)); return "";}
  };
  useEffect(() => {if (m.media_kind === "image") laden();}, [m.id]);
  if (m.media_kind === "image") return <div className="jc-bild" onClick={() => quelle && showImage(quelle, m.media_name || "Bild.jpg")}>{quelle ? <img src={quelle} alt=""/> : <span className="slide-skeleton"/>}</div>;
  if (m.media_kind === "audio") return <div className="jc-audio">
    {quelle ? <audio src={quelle} controls autoPlay/> : <button onClick={laden}><Play/>Sprachnachricht</button>}
    {text ? <p className="jc-transkript">{text}</p> : <button className="text-link small" onClick={() => api<any>(`/api/p2p/messages/${enc(m.id)}/transcribe`, "POST").then(r => setText(r.transcript || r.text || "")).catch(e => notify(errorText(e)))}>Text anzeigen</button>}
  </div>;
  if (m.media_kind === "video") return quelle ? <video className="jc-video" src={quelle} controls/> : <button className="jc-datei" onClick={laden}><Play/>{m.media_name || "Video"}</button>;
  return <button className="jc-datei" onClick={() => {notify("Download beginnt"); binary(`/api/p2p/media/${enc(m.id)}`).then(r => call("save", {...r, name: m.media_name || "Datei"})).then(() => notify("In Downloads/Jon gespeichert.")).catch(e => notify(errorText(e)));}}><FileText/>{m.media_name || "Datei"}</button>;
}

export function JonChatPage({shell, back}: PageProps) {
  const [ich, setIch] = useState<any>(null), [peers, setPeers] = useState<any[]>([]), [gruppen, setGruppen] = useState<any[]>([]), [anfragen, setAnfragen] = useState<any[]>([]), [einladungen, setEinladungen] = useState<any[]>([]);
  const [ziel, setZiel] = useState<Ziel | null>(null), [nachrichten, setNachrichten] = useState<Nachricht[]>([]), [tippt, setTippt] = useState<any[]>([]);
  const [text, setText] = useState(""), [antwort, setAntwort] = useState<Nachricht | null>(null), [menue, setMenue] = useState<Nachricht | null>(null), [sheet, setSheet] = useState(""), [wert, setWert] = useState(""), [busy, setBusy] = useState(false), [suche, setSuche] = useState(""), [treffer, setTreffer] = useState<any[]>([]), [auswahl, setAuswahl] = useState<string[]>([]);
  const liste = useRef<HTMLDivElement>(null), getippt = useRef(0), datei = useRef<HTMLInputElement>(null);
  const verbunden = shell.conn.connected;
  const notify = shell.notify;
  useBackHandler(!!ziel, () => setZiel(null));

  const ladenListe = async () => {
    const [me, p, g, a, e] = await Promise.allSettled([api("/api/p2p/me"), api<any[]>("/api/p2p/peers"), api<any[]>("/api/p2p/groups"), api<any[]>("/api/p2p/requests"), api<any[]>("/api/p2p/groups/invites")]);
    if (me.status === "fulfilled") setIch(me.value);
    if (p.status === "fulfilled") setPeers(alsListe(p.value));
    if (g.status === "fulfilled") setGruppen(alsListe(g.value));
    if (a.status === "fulfilled") setAnfragen(alsListe(a.value));
    if (e.status === "fulfilled") setEinladungen(alsListe(e.value));
  };
  const ladenChat = async (z = ziel) => {
    if (!z) return;
    try {setNachrichten(alsListe(await api<Nachricht[]>(`/api/p2p/messages/${enc(z.id)}`)));} catch {}
    try {const t = await api<any>("/api/p2p/typing"); setTippt(alsListe(t?.typing));} catch {}
  };
  useEffect(() => {if (!verbunden) return; ladenListe(); const t = setInterval(ladenListe, 5000); return () => clearInterval(t);}, [verbunden]);
  useEffect(() => {if (!ziel) {setNachrichten([]); return;} ladenChat(ziel); const t = setInterval(() => ladenChat(ziel), 2500); return () => clearInterval(t);}, [ziel?.id]);
  useLayoutEffect(() => {const el = liste.current; if (el) el.scrollTop = el.scrollHeight;}, [nachrichten.length, ziel?.id]);

  async function senden(media?: {name: string; mime: string; data: string}) {
    if (!ziel || (!text.trim() && !media)) return;
    const inhalt = text.trim();
    setText("");
    const reply = antwort?.id || "";
    setAntwort(null);
    haptic("tap");
    try {await api("/api/p2p/send", "POST", {peer_id: ziel.art === "peer" ? ziel.id : "", group_id: ziel.art === "gruppe" ? ziel.id : "", text: inhalt, media, reply_to: reply}); ladenChat();}
    catch (e) {notify(errorText(e)); setText(inhalt);}
  }
  async function fotoSenden() {
    try {
      const r = await call("kamera", {ziel: "chat"}, LANG);
      if (r?.data) await senden({name: r.name || "Foto.jpg", mime: "image/jpeg", data: r.data});
    } catch (e) {if (errorText(e) !== "Abgebrochen") notify(errorText(e));}
  }
  function tippen(v: string) {
    setText(v);
    if (!ziel || Date.now() - getippt.current < 3000) return;
    getippt.current = Date.now();
    api("/api/p2p/typing", "POST", {peer_id: ziel.art === "peer" ? ziel.id : "", group_id: ziel.art === "gruppe" ? ziel.id : ""}).catch(() => {});
  }

  if (!verbunden) return <><PageHeader title="Jon Chat" onBack={back}/><Empty icon={<Users/>} title="Jon Chat braucht deinen Pi" text="Freunde-Chat läuft über Jon am PC oder Pi. Verbinde dein Gerät, dann schreibst du hier wie gewohnt."/></>;
  if (!ich) return <><PageHeader title="Jon Chat" onBack={back}/><Busy/></>;

  if (ziel) {
    const status = ziel.art === "gruppe" ? (ziel.gruppe?.member_names || []).join(", ") : tippt.some(t => t.peer_id === ziel.id && !t.group_id) ? "schreibt …" : ziel.peer?.online ? "online" : ziel.peer?.waiting ? "wartet auf Annahme" : "offline";
    return <>
      <header className="page-header jc-kopf"><Circle label="Zurück" onClick={() => setZiel(null)}><ArrowLeft/></Circle><div className="jc-wer"><span className="avatar-emoji">{ziel.avatar}</span><div><strong>{ziel.name}</strong><small className={status === "schreibt …" ? "tippt" : ""}>{status}</small></div></div><div className="slot"/></header>
      <div className="jc-verlauf" ref={liste}>
        {!nachrichten.length && <p className="hint" style={{textAlign: "center", marginTop: 40}}>Schreib die erste Nachricht. Alles ist Ende-zu-Ende verschlüsselt.</p>}
        {nachrichten.map((m, i) => <motion.div key={m.id} className={`jc-zeile ${m.direction}`} initial={i >= nachrichten.length - 3 ? {opacity: 0, y: 8, scale: .98} : false} animate={{opacity: 1, y: 0, scale: 1}} transition={spring}>
          <div className="jc-blase" onContextMenu={e => {e.preventDefault(); haptic("tick"); setMenue(m);}} onClick={() => {}} onPointerDown={() => {const t = setTimeout(() => {haptic("tick"); setMenue(m);}, 480); const aus = () => {clearTimeout(t); window.removeEventListener("pointerup", aus);}; window.addEventListener("pointerup", aus);}}>
            {ziel.art === "gruppe" && m.direction === "in" && <b className="jc-absender">{m.sender_name}</b>}
            {m.reply_preview && <div className="jc-zitat">{m.reply_preview}</div>}
            {m.deleted ? <i className="muted">Nachricht gelöscht</i> : <>{m.has_media && <Medien m={m} notify={notify}/>}{m.text && <span className="jc-text">{m.text}</span>}</>}
            <span className="jc-meta">{zeit(m.created_at)}{m.direction === "out" && (m.read ? <CheckCheck className="gelesen"/> : m.delivered ? <CheckCheck/> : <Clock/>)}</span>
            {Object.keys(m.reactions || {}).length > 0 && <span className="jc-reaktionen">{Object.entries(m.reactions).map(([emoji, wer]) => <span key={emoji}>{emoji}{wer.length > 1 ? wer.length : ""}</span>)}</span>}
          </div>
        </motion.div>)}
      </div>
      <div className="jc-eingabe">
        <AnimatePresence>{antwort && <motion.div className="jc-antwort" initial={{opacity: 0, y: 6}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}}><Reply/><span>{antwort.text || antwort.media_name || "Medien"}</span><button onClick={() => setAntwort(null)}><X/></button></motion.div>}</AnimatePresence>
        <div className="jc-leiste">
          <button className="icon-btn" aria-label="Foto" onClick={fotoSenden}><Camera/></button>
          <button className="icon-btn" aria-label="Datei" onClick={() => datei.current?.click()}><Paperclip/></button>
          <textarea rows={1} placeholder="Nachricht" value={text} onChange={e => tippen(e.target.value)}/>
          <button className="send-btn" disabled={!text.trim()} aria-label="Senden" onClick={() => senden()}><ArrowUp/></button>
        </div>
      </div>
      <input ref={datei} type="file" hidden onChange={async e => {const f = e.target.files?.[0]; e.target.value = ""; if (!f) return; try {await senden({name: f.name, mime: f.type || "application/octet-stream", data: await readUpload(f)});} catch (err) {notify(errorText(err));}}}/>
      <Sheet open={!!menue} title="Nachricht" onClose={() => setMenue(null)}>
        {menue && <>
          <div className="jc-reaktion-wahl">{reaktionen.map(r => <button key={r} onClick={() => {api(`/api/p2p/messages/${enc(menue.id)}/react`, "POST", {emoji: r}).then(() => ladenChat()).catch(e => notify(errorText(e))); setMenue(null);}}>{r}</button>)}</div>
          <button className="list-row" onClick={() => {setAntwort(menue); setMenue(null);}}><Reply/><span>Antworten</span></button>
          {menue.text && <button className="list-row" onClick={() => {call("copy", {text: menue.text}).then(() => notify("Kopiert.")); setMenue(null);}}><Copy/><span>Kopieren</span></button>}
          {menue.has_media && menue.media_kind !== "image" && <button className="list-row" onClick={() => {binary(`/api/p2p/media/${enc(menue.id)}`).then(r => call("save", {...r, name: menue.media_name || "Datei"})).then(() => notify("Gespeichert.")).catch(e => notify(errorText(e))); setMenue(null);}}><FileText/><span>Speichern</span></button>}
          <button className="list-row danger" onClick={() => {api(`/api/p2p/messages/${enc(menue.id)}`, "DELETE").then(() => ladenChat()).catch(e => notify(errorText(e))); setMenue(null);}}><Trash2/><span>Für mich löschen</span></button>
          {menue.direction === "out" && !menue.deleted && <button className="list-row danger" onClick={() => {api(`/api/p2p/messages/${enc(menue.id)}?for_all=true`, "DELETE").then(() => ladenChat()).catch(e => notify(errorText(e))); setMenue(null);}}><Trash2/><span>Für alle löschen</span></button>}
        </>}
      </Sheet>
    </>;
  }

  const chats: Ziel[] = [
    ...gruppen.map(g => ({art: "gruppe" as const, id: g.id, name: g.name, avatar: "👥", gruppe: g})),
    ...peers.map(p => ({art: "peer" as const, id: p.id, name: p.name, avatar: p.avatar || "🙂", peer: p}))
  ];
  return <>
    <PageHeader title="Jon Chat" onBack={back} right={<Circle label="Freund hinzufügen" onClick={() => {setWert(""); setSheet("freund");}}><UserPlus/></Circle>}/>
    <div className="page-scroll">
      {!ich.name ? <div className="card"><h4>Wie heißt du im Jon Chat?</h4><Field label="Dein Name" value={wert} onChange={setWert} autoFocus/><button className="btn primary" disabled={!wert.trim()} onClick={() => api("/api/p2p/me", "PUT", {name: wert.trim(), avatar: "🙂"}).then(v => {setIch(v); setWert("");}).catch(e => notify(errorText(e)))}>Speichern</button></div> : <>
        <div className="jc-ich"><span className="avatar-emoji gross">{ich.avatar || "🙂"}</span><div><strong>{ich.name}</strong><small>Dein Jon-Code: <b>{ich.code}</b></small></div><button className="circle small" aria-label="Code kopieren" onClick={() => call("copy", {text: ich.code}).then(() => notify("Jon-Code kopiert."))}><Copy/></button></div>
        <label className="search-pill jc-suche"><Search/><input placeholder="In allen Chats suchen" value={suche} onChange={e => {setSuche(e.target.value); if (e.target.value.trim().length > 1) api<any[]>(`/api/p2p/search?q=${enc(e.target.value.trim())}`).then(v => setTreffer(alsListe(v))).catch(() => {}); else setTreffer([]);}}/></label>
        {treffer.length > 0 && <div className="card">{treffer.slice(0, 12).map((t: any) => <button key={t.id} className="list-row" onClick={() => {const z = chats.find(c => c.id === (t.chat_id || t.group_id || t.peer_id)); if (z) {setZiel(z); setSuche(""); setTreffer([]);}}}><span><b>{t.chat_name || t.sender_name}</b><small>{t.text || t.transcript}</small></span></button>)}</div>}
        {(anfragen.length > 0 || einladungen.length > 0) && <div className="group-title">Anfragen</div>}
        {anfragen.map(a => <motion.div key={a.id} className="card jc-anfrage" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}}><div className="zeile"><span className="avatar-emoji">{a.avatar || "🙂"}</span><div><strong>{a.name}</strong><small className="muted">möchte mit dir schreiben{a.location ? ` · ${a.location}` : ""}</small></div></div>
          <div className="aktionen"><button className="mini haupt" onClick={() => api(`/api/p2p/requests/${enc(a.id)}/accept`, "POST").then(() => {haptic("success"); ladenListe();}).catch(e => notify(errorText(e)))}><Check/>Annehmen</button><button className="mini" onClick={() => api(`/api/p2p/requests/${enc(a.id)}/reject`, "POST").then(ladenListe)}><X/>Ablehnen</button><button className="mini" onClick={() => api(`/api/p2p/requests/${enc(a.id)}/block`, "POST").then(ladenListe)}><ShieldBan/>Blockieren</button></div></motion.div>)}
        {einladungen.map(g => <div key={g.id} className="card jc-anfrage"><div className="zeile"><span className="avatar-emoji">👥</span><div><strong>{g.name}</strong><small className="muted">Einladung von {g.from_name}</small></div></div>
          <div className="aktionen"><button className="mini haupt" onClick={() => api(`/api/p2p/groups/${enc(g.id)}/accept`, "POST").then(ladenListe).catch(e => notify(errorText(e)))}><Check/>Beitreten</button><button className="mini" onClick={() => api(`/api/p2p/groups/${enc(g.id)}/reject`, "POST").then(ladenListe)}><X/>Ablehnen</button></div></div>)}
        <div className="group-title" style={{display: "flex", alignItems: "center"}}>Chats<span className="grow"/><button className="text-link small" onClick={() => {setWert(""); setAuswahl([]); setSheet("gruppe");}}><MessageSquarePlus size={15}/> Gruppe</button></div>
        {!chats.length && <p className="hint" style={{margin: "0 8px"}}>Noch keine Freunde. Tippe oben auf das Plus und gib den Namen (im selben WLAN) oder den Jon-Code deines Freundes ein.</p>}
        <div className="jc-liste">{chats.map((c, i) => {
          const ungelesen = c.art === "peer" ? c.peer?.unread : c.gruppe?.unread;
          return <motion.button key={c.id} className="jc-chat" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={{...spring, delay: Math.min(i, 10) * .03}} onClick={() => {haptic("tick"); setZiel(c);}}>
            <span className="avatar-emoji">{c.avatar}{c.art === "peer" && c.peer?.online && <i className="online"/>}</span>
            <span className="jc-name"><strong>{c.name}</strong><small>{c.art === "gruppe" ? `${(c.gruppe?.member_names || []).length + 1} Mitglieder` : c.peer?.waiting ? "wartet auf Annahme" : c.peer?.typing ? "schreibt …" : c.peer?.online ? "online" : "offline"}</small></span>
            {ungelesen ? <span className="jc-ungelesen">{ungelesen}</span> : null}
          </motion.button>;
        })}</div>
      </>}
    </div>
    <Sheet open={sheet === "freund"} title="Freund hinzufügen" onClose={() => setSheet("")}>
      <p>Im selben WLAN reicht der Name. Woanders braucht Jon den Jon-Code deines Freundes.</p>
      <Field label="Name oder Jon-Code" value={wert} onChange={setWert} autoFocus/>
      <button className="btn primary" disabled={!wert.trim() || busy} onClick={async () => {setBusy(true); const eingabe = wert.trim(); try {await api("/api/p2p/peers", "POST", /^[A-Z0-9-]{6,}$/i.test(eingabe) && /\d/.test(eingabe) ? {code: eingabe} : {name: eingabe}); haptic("success"); notify("Anfrage gesendet."); setSheet(""); ladenListe();} catch (e) {notify(errorText(e));} finally {setBusy(false);}}}><UserPlus/>Anfrage senden</button>
    </Sheet>
    <Sheet open={sheet === "gruppe"} title="Neue Gruppe" onClose={() => setSheet("")}>
      <Field label="Name der Gruppe" value={wert} onChange={setWert}/>
      {peers.map(p => <button key={p.id} className="list-row" onClick={() => setAuswahl(a => a.includes(p.id) ? a.filter(x => x !== p.id) : [...a, p.id])}><span className="avatar-emoji">{p.avatar || "🙂"}</span><span>{p.name}</span>{auswahl.includes(p.id) && <Check className="check"/>}</button>)}
      <button className="btn primary" disabled={!wert.trim() || !auswahl.length} onClick={() => api("/api/p2p/groups", "POST", {name: wert.trim(), members: auswahl}).then(() => {haptic("success"); setSheet(""); ladenListe(); notify("Gruppe erstellt. Die Eingeladenen müssen beitreten.");}).catch(e => notify(errorText(e)))}><Users/>Gruppe erstellen</button>
    </Sheet>
  </>;
}
