import React, {useEffect, useRef, useState} from "react";
import {createPortal} from "react-dom";
import {AnimatePresence, motion} from "framer-motion";
import {AlarmClock, BellRing, Check, Clock, Headphones, Hourglass, LoaderCircle, MapPin, Megaphone, MessageCircle, Moon, Music2, PartyPopper, PhoneCall, Play, Send, ShieldCheck, Siren, SlidersHorizontal, Timer} from "lucide-react";
import {api, call, haptic, listen} from "./bridge";
import {PageProps} from "./Pages";
import {useAdmin} from "./Settings";
import {Busy, Field, PageHeader, Row, Sheet, Switch, Zaehler, errorText, spring, useBackHandler} from "./ui";
import {AppSymbol, JonApp, alteApps} from "./Apps";

export const appNamen: Record<string, string> = {whatsapp: "WhatsApp", tiktok: "TikTok", amazon: "Amazon Music"};
const tage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const grundText: Record<string, string> = {limit: "Zeit aufgebraucht", nacht: "Schlafenszeit", pause: "Pause"};

function Uhrzeit() {
  const [jetzt, setJetzt] = useState(new Date());
  useEffect(() => {const t = setInterval(() => setJetzt(new Date()), 1000); return () => clearInterval(t);}, []);
  return <>{jetzt.toLocaleTimeString("de-DE", {hour: "2-digit", minute: "2-digit"})}</>;
}

function prioritaet(a: any) {
  const art = a?.art;
  return art === "wecker" || art === "timer" || art === "suchen" ? 3 : art === "durchsage" || art === "zeitantwort" ? 2 : 1;
}

function AnfrageFormular({app, name, onGesendet}: {app: string; name: string; onGesendet: (stand: any) => void}) {
  const [minuten, setMinuten] = useState(30), [text, setText] = useState(""), [busy, setBusy] = useState(false), [fehler, setFehler] = useState("");
  async function senden() {
    setBusy(true);
    setFehler("");
    try {const stand = await call("zeit-anfragen", {app, minuten, text}, 25_000); haptic("success"); onGesendet(stand);}
    catch (e) {haptic("error"); setFehler(errorText(e));}
    finally {setBusy(false);}
  }
  return <div className="anfrage">
    <div className="chips">{[15, 30, 60].map(m => <button key={m} className={`chip ${minuten === m ? "on" : ""}`} onClick={() => {haptic("tick"); setMinuten(m);}}><Hourglass/>{m} Min.</button>)}</div>
    <Field label="Warum? (freiwillig)" value={text} onChange={v => setText(v.slice(0, 200))} placeholder="Zum Beispiel: Hausaufgaben sind fertig"/>
    <AnimatePresence>{fehler && <motion.p className="anfrage-fehler" initial={{opacity: 0, y: -6}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}}>{fehler}</motion.p>}</AnimatePresence>
    <button className="btn primary" disabled={busy} onClick={senden}>{busy ? <LoaderCircle className="spin"/> : <Send/>}{`${minuten} Min. ${name} anfragen`}</button>
  </div>;
}

export function ZeitAnfrage({app, onClose, onGesendet, notify}: {app: {id: string; name: string; grund?: string} | null; onClose: () => void; onGesendet?: (stand: any) => void; notify: (s: string) => void}) {
  const letzte = useRef(app);
  if (app) letzte.current = app;
  const a = app || letzte.current;
  return <Sheet open={!!app} title={a ? `Mehr Zeit für ${a.name}` : "Mehr Zeit"} onClose={onClose}>
    {a && <>
      <p className="muted" style={{margin: "0 2px 14px"}}>{a.grund ? `${grundText[a.grund] || "Gesperrt"}. ` : ""}Deine Eltern bekommen die Anfrage sofort und können mit einem Tipp Ja sagen.</p>
      <AnfrageFormular key={a.id} app={a.id} name={a.name} onGesendet={stand => {notify("Anfrage gesendet. Ich sag dir Bescheid, sobald die Antwort da ist."); onGesendet?.(stand); onClose();}}/>
    </>}
  </Sheet>;
}

function RegelAnzeige({aktiv, schliessen}: {aktiv: any; schliessen: () => void}) {
  const [modus, setModus] = useState<"" | "fragen" | "gesendet">("");
  useEffect(() => {call("zeit").then(s => {if (s?.anfrage && s.anfrage.app === aktiv.app) setModus("gesendet");}).catch(() => {});}, [aktiv.app]);
  return <>
    <motion.div className="puls klein" initial={{scale: .7}} animate={{scale: 1}} transition={spring}>{modus === "gesendet" ? <Send/> : <Hourglass/>}</motion.div>
    <div className="anzeige-zeit klein">{modus === "gesendet" ? "Anfrage läuft" : grundText[aktiv.grund] || "Gesperrt"}</div>
    <div className="anzeige-text">{modus === "gesendet" ? `Deine Anfrage für ${aktiv.name || "die App"} ist unterwegs. Ich sag dir Bescheid, sobald die Antwort da ist.` : aktiv.text}</div>
    <AnimatePresence initial={false}>{modus === "fragen" && <motion.div key="fragen" className="anzeige-anfrage" initial={{opacity: 0, height: 0}} animate={{opacity: 1, height: "auto"}} exit={{opacity: 0, height: 0}} transition={spring}>
      <AnfrageFormular app={aktiv.app} name={aktiv.name || "App"} onGesendet={() => setModus("gesendet")}/>
    </motion.div>}</AnimatePresence>
    <div className="anzeige-knoepfe">
      {aktiv.anfragbar && aktiv.app && modus === "" && <button className="btn soft" onClick={() => {haptic("tap"); setModus("fragen");}}><Hourglass/>Mehr Zeit anfragen</button>}
      <button className={`btn ${modus === "fragen" ? "soft" : "primary"}`} onClick={() => modus === "fragen" ? setModus("") : schliessen()}>{modus === "fragen" ? "Abbrechen" : "Okay"}</button>
    </div>
  </>;
}

function Konfetti() {
  const farben = ["#ffd166", "#3ed598", "#6ea8ff", "#ff7aa8", "#c9aaff"];
  return <div className="konfetti">{Array.from({length: 28}).map((_, i) => <motion.i key={i} style={{left: `${(i * 37) % 100}%`, background: farben[i % farben.length]}} initial={{y: -40, opacity: 0, rotate: 0}} animate={{y: ["0vh", "70vh"], opacity: [0, 1, 1, 0], rotate: (i % 2 ? 1 : -1) * 360}} transition={{duration: 2.4 + (i % 5) * .3, delay: (i % 9) * .08, ease: "easeIn"}}/>)}</div>;
}

export function Anzeigen({name}: {name: string}) {
  const [liste, setListe] = useState<any[]>([]);
  useEffect(() => listen("anzeige", v => setListe(Array.isArray(v?.liste) ? v.liste : []), true), []);
  const aktiv = [...liste].sort((a, b) => prioritaet(b) - prioritaet(a))[0];
  const schliessen = (gelesen = false) => {haptic("success"); call("anzeige-schliessen", {anzeige: aktiv?.id, gelesen}).catch(() => {});};
  useBackHandler(!!aktiv, () => {if (aktiv?.art === "regel" || aktiv?.art === "nacht" || aktiv?.art === "zeitantwort") schliessen();});
  const klingelt = aktiv && ["wecker", "timer", "suchen"].includes(aktiv.art);
  return createPortal(<AnimatePresence>{aktiv && <motion.div key={aktiv.id} className={`anzeige ${aktiv.art}`} initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} transition={{duration: .35}}>
    <div className="anzeige-glanz"/>
    {klingelt && <>
      <div className="anzeige-kopf">{aktiv.art === "suchen" ? "Jon wird gesucht" : aktiv.art === "timer" ? "Timer" : "Wecker"}</div>
      <motion.div className="puls" animate={{scale: [1, 1.08, 1]}} transition={{duration: 1.1, repeat: Infinity, ease: "easeInOut"}}>
        <span className="welle"/><span className="welle zwei"/>
        {aktiv.art === "suchen" ? <BellRing/> : aktiv.art === "timer" ? <Timer/> : <AlarmClock/>}
      </motion.div>
      <div className="anzeige-zeit">{aktiv.art === "suchen" ? "Hier bin ich!" : <Uhrzeit/>}</div>
      <div className="anzeige-text">{aktiv.art === "suchen" ? "Tippe auf Gefunden, dann höre ich auf zu klingeln." : aktiv.titel}</div>
      <div className="anzeige-knoepfe">
        {aktiv.art === "wecker" && <button className="btn soft" onClick={() => {haptic("tap"); call("schlummern").catch(() => {});}}><Clock/>Schlummern · 5 Min.</button>}
        <button className="btn primary" onClick={() => {haptic("success"); call("klingeln-stopp").catch(() => {});}}><Check/>{aktiv.art === "suchen" ? "Gefunden" : "Stopp"}</button>
      </div>
    </>}
    {aktiv.art === "durchsage" && <>
      <div className="anzeige-kopf">Durchsage</div>
      <motion.div className="puls klein" initial={{scale: .6, rotate: -12}} animate={{scale: 1, rotate: 0}} transition={spring}><Megaphone/></motion.div>
      <div className="anzeige-von">{`von ${aktiv.von || "Jon"}`}</div>
      <motion.div className="anzeige-nachricht" initial={{y: 20, opacity: 0}} animate={{y: 0, opacity: 1}} transition={{...spring, delay: .1}}>{aktiv.text}</motion.div>
      <div className="anzeige-knoepfe"><button className="btn primary" onClick={() => schliessen(true)}><Check/>Verstanden</button></div>
    </>}
    {aktiv.art === "nacht" && <>
      <motion.div className="mond" initial={{y: 30, opacity: 0}} animate={{y: 0, opacity: 1}} transition={{duration: 1.2}}><Moon/></motion.div>
      <div className="sterne">{Array.from({length: 26}).map((_, i) => <i key={i} style={{left: `${(i * 37) % 100}%`, top: `${(i * 23) % 60}%`, animationDelay: `${(i % 7) * .4}s`}}/>)}</div>
      <div className="anzeige-zeit klein">Schlafenszeit</div>
      <div className="anzeige-text">{`Gute Nacht${name ? `, ${name}` : ""}! Bis ${aktiv.bis} Uhr ${(aktiv.apps || []).length ? `sind ${(aktiv.apps || []).join(", ")} gesperrt` : "ist Ruhe"}. Mit mir kannst du trotzdem reden.`}</div>
      <div className="anzeige-knoepfe"><button className="btn soft" onClick={() => schliessen()}>Gute Nacht</button></div>
    </>}
    {aktiv.art === "regel" && <RegelAnzeige aktiv={aktiv} schliessen={() => schliessen()}/>}
    {aktiv.art === "zeitantwort" && <>
      {aktiv.erlaubt && <Konfetti/>}
      <motion.div className={`puls klein ${aktiv.erlaubt ? "ja" : ""}`} initial={{scale: .4, rotate: -25}} animate={{scale: 1, rotate: 0}} transition={{...spring, stiffness: 300}}>{aktiv.erlaubt ? <PartyPopper/> : <Hourglass/>}</motion.div>
      <div className="anzeige-zeit klein">{aktiv.erlaubt ? "Ja, klar!" : "Diesmal nicht"}</div>
      <motion.div className="anzeige-text" initial={{y: 14, opacity: 0}} animate={{y: 0, opacity: 1}} transition={{...spring, delay: .12}}>{aktiv.text}</motion.div>
      <div className="anzeige-knoepfe">
        {aktiv.erlaubt && aktiv.app && <button className="btn primary" onClick={() => {schliessen(); call("app", {app: aktiv.app}).catch(() => {});}}><Play/>{`${aktiv.name || "App"} öffnen`}</button>}
        <button className={`btn ${aktiv.erlaubt ? "soft" : "primary"}`} onClick={() => schliessen()}>Okay</button>
      </div>
    </>}
  </motion.div>}</AnimatePresence>, document.body);
}

export function SosKnopf({notify}: {notify: (s: string) => void}) {
  const [halten, setHalten] = useState(false), [senden, setSenden] = useState(false);
  const zeit = useRef<ReturnType<typeof setTimeout> | null>(null);
  const start = () => {
    if (senden) return;
    haptic("tick");
    setHalten(true);
    zeit.current = setTimeout(async () => {
      setHalten(false);
      setSenden(true);
      haptic("error");
      try {
        const r = await call("sos", {}, 45_000);
        notify(r?.gesendet === false ? "Jon ruft jetzt an." : `SOS gesendet${r?.standort ? " – mit deinem Standort" : ""}. ${r?.angerufen ? "Jon ruft gleich an." : "Deine Familie wurde benachrichtigt."}`);
      }
      catch (e) {notify(errorText(e));}
      finally {setSenden(false);}
    }, 1300);
  };
  const ende = () => {if (zeit.current) clearTimeout(zeit.current); zeit.current = null; setHalten(false);};
  return <button className={`sos ${halten ? "halten" : ""} ${senden ? "senden" : ""}`} aria-label="SOS – lange drücken" onPointerDown={start} onPointerUp={ende} onPointerLeave={ende} onPointerCancel={ende} onContextMenu={e => e.preventDefault()}>
    <svg viewBox="0 0 40 40" className="sos-ring"><circle cx="20" cy="20" r="17"/></svg>
    <Siren/><span>{senden ? "…" : "SOS"}</span>
  </button>;
}

export function KinderEinstellungen({open, onClose, notify, kinder, setKinder}: {open: boolean; onClose: () => void; notify: (s: string) => void; kinder: {an: boolean; alter: number}; setKinder: (v: {an: boolean; alter: number}) => void}) {
  const [busy, setBusy] = useState(false);
  async function setzen(neu: Partial<{an: boolean; alter: number}>, text?: string) {
    setBusy(true);
    try {const v = await call("kinder", {setzen: {...kinder, ...neu}}); setKinder({an: !!v.an, alter: Number(v.alter) || 10}); haptic("success"); if (text) notify(text);}
    catch (e) {notify(errorText(e));}
    finally {setBusy(false);}
  }
  const punkte = [
    ["🧒", "Kindgerechte Antworten", "Einfache Sprache, passend zum Alter."],
    ["📚", "Hausaufgaben-Hilfe", "Jon erklärt Schritt für Schritt, statt nur die Lösung zu verraten."],
    ["🔎", "Sichere Suche", "SafeSearch ist an, Seiten für Erwachsene werden aussortiert."],
    ["🛡️", "Keine riskanten Aktionen", "Keine Befehle am PC, keine Dateien, keine Webcam."],
    ["💬", "Hilfe bei Sorgen", "Bei Kummer verweist Jon auf Eltern und Rat auf Draht (147)."]
  ];
  return <Sheet open={open} title="Kinder-Modus" onClose={onClose}>
    <div className="row-btn" style={{borderRadius: 18}}><ShieldCheck/><span>Kinder-Modus<small>{kinder.an ? `An · für ${kinder.alter} Jahre` : "Aus"}</small></span><Switch on={kinder.an} onChange={v => void setzen({an: v}, v ? "Kinder-Modus ist an." : "Kinder-Modus ist aus.")}/></div>
    <div className="field"><span>Alter</span><div className="chips klein">{[5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16].map(j => <button key={j} disabled={busy} className={`chip ${kinder.alter === j ? "on" : ""}`} onClick={() => {haptic("tick"); void setzen({alter: j});}}>{j}</button>)}</div></div>
    <div className="kinder-punkte">{punkte.map(([symbol, titel, text], i) => <motion.div key={titel} className="kinder-punkt" initial={{opacity: 0, x: -10}} animate={{opacity: 1, x: 0}} transition={{...spring, delay: .04 * i}}><span>{symbol}</span><div><strong>{titel}</strong><small>{text}</small></div></motion.div>)}</div>
    <p className="hint" style={{margin: "12px 4px 0"}}>Gilt für Jon auf dem PC oder Pi, für deinen eigenen Zugang und für die Offline-KI auf dem Handy.</p>
  </Sheet>;
}

export function SosEinstellungen({open, onClose, notify}: {open: boolean; onClose: () => void; notify: (s: string) => void}) {
  const [d, setD] = useState<any>(null), [nummer, setNummer] = useState(""), [name, setName] = useState(""), [busy, setBusy] = useState(false);
  const uebernehmen = (v: any) => {setD(v); setNummer(v?.nummer || ""); setName(v?.name || "");};
  useEffect(() => {if (open) call("sos-einstellungen").then(uebernehmen).catch(e => notify(errorText(e)));}, [open]);
  const gueltig = nummer.replace(/[^0-9+]/g, "").length >= 3;
  async function setzen(neu: any, text?: string) {
    setBusy(true);
    try {uebernehmen(await call("sos-einstellungen", {setzen: neu})); haptic("success"); if (text) notify(text);}
    catch (e) {notify(errorText(e));}
    finally {setBusy(false);}
  }
  async function standort(an: boolean) {
    if (an) {
      const r = await call("permission", {name: "ort"}).catch(() => ({granted: false}));
      if (!r?.granted) return notify("Ohne Standortfreigabe kann Jon den Ort nicht mitschicken.");
    }
    setzen({standort: an});
  }
  async function anruf(an: boolean) {
    if (an && !gueltig) return notify("Trag zuerst eine Telefonnummer ein.");
    if (an && d?.telefon) await call("permission", {name: "anruf"}).catch(() => {});
    setzen({anruf: an, nummer, name});
  }
  return <Sheet open={open} title="SOS" onClose={onClose}>
    {!d ? <Busy/> : <>
      <p className="muted" style={{margin: "0 2px 14px"}}>Lange auf SOS drücken schickt sofort eine Nachricht an deine Familie – an Jon am PC oder Pi und per Telegram.</p>
      <div className="row-btn" style={{borderRadius: 18}}><MapPin/><span>Standort mitschicken<small>{d.standort && !d.standort_erlaubt ? "Standortfreigabe fehlt noch" : "Deine Eltern sehen, wo du bist"}</small></span><Switch on={!!d.standort} onChange={v => void standort(v)}/></div>
      <div className="row-btn" style={{borderRadius: 18, marginTop: 10}}><PhoneCall/><span>Danach direkt anrufen<small>{!d.telefon ? "Dieses Gerät kann nicht telefonieren" : d.anruf ? `Ruft ${d.name || d.nummer} an` : "Nach dem SOS eine Nummer wählen"}</small></span><Switch on={!!d.anruf} onChange={v => void anruf(v)}/></div>
      <div style={{display: "flex", gap: 12}}>
        <Field label="Wer?" value={name} onChange={v => setName(v.slice(0, 40))} placeholder="Zum Beispiel: Papa"/>
        <Field label="Telefonnummer" type="tel" value={nummer} onChange={v => setNummer(v.replace(/[^0-9+*# ]/g, "").slice(0, 24))} placeholder="+43 …"/>
      </div>
      <button className="btn primary" disabled={busy} onClick={() => setzen({nummer, name, anruf: !!d.anruf && gueltig}, "SOS-Einstellungen gespeichert.")}>Speichern</button>
      {d.anruf && d.telefon && !d.anruf_erlaubt && <p className="hint" style={{margin: "12px 4px 0"}}>Ohne Anruf-Erlaubnis öffnet Jon die Nummer im Telefon – dann nur noch auf Anrufen tippen.</p>}
    </>}
  </Sheet>;
}

function Ring({wert, max, farbe = "var(--accent)", groesse = 150, children}: {wert: number; max: number; farbe?: string; groesse?: number; children: React.ReactNode}) {
  const r = 44, umfang = 2 * Math.PI * r;
  const anteil = Math.max(0, Math.min(1, max > 0 ? wert / max : 0));
  return <div className="kreis" style={{width: groesse, height: groesse}}>
    <svg viewBox="0 0 100 100"><circle cx="50" cy="50" r={r} className="spur"/><motion.circle cx="50" cy="50" r={r} className="wert" style={{stroke: farbe}} strokeDasharray={umfang} initial={{strokeDashoffset: umfang}} animate={{strokeDashoffset: umfang * (1 - anteil)}} transition={{duration: 1.1, ease: [.2, .8, .2, 1]}}/></svg>
    <div className="kreis-innen">{children}</div>
  </div>;
}

export {Ring};

function WochenBalken({bericht}: {bericht: any}) {
  const tage: any[] = Array.isArray(bericht?.tage) ? bericht.tage : [];
  const hoechstes = Math.max(60, ...tage.map(t => Number(t.minuten) || 0));
  const dauer = (m: number) => m >= 60 ? `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} min` : ""}` : `${m} min`;
  const aenderung = bericht?.vorwoche ? Math.round((bericht.gesamt - bericht.vorwoche) * 100 / bericht.vorwoche) : null;
  return <motion.div className="card woche-karte" initial={{opacity: 0, y: 14}} animate={{opacity: 1, y: 0}} transition={spring}>
    <div className="woche-kopf">
      <div><strong>{dauer(Number(bericht.gesamt) || 0)}</strong><small>in 7 Tagen · Ø {dauer(Number(bericht.schnitt) || 0)} am Tag</small></div>
      {aenderung !== null && <span className={`badge ${aenderung > 0 ? "warn" : "ok"}`}>{aenderung > 0 ? "+" : ""}{aenderung} %</span>}
    </div>
    <div className="woche-balken">{tage.map((t, i) => <div key={t.tag} className="woche-tag">
      <motion.i className={i === tage.length - 1 ? "heute" : t.erfasst ? "" : "leer"} initial={{height: 0}} animate={{height: `${Math.max(t.erfasst ? 5 : 3, (Number(t.minuten) || 0) / hoechstes * 100)}%`}} transition={{type: "spring", stiffness: 140, damping: 18, delay: .05 * i}}/>
      <span>{t.wochentag}</span>
    </div>)}</div>
    {Number(bericht.schritte) > 0 && <small className="muted woche-fuss">👣 {Number(bericht.schritte).toLocaleString("de-AT")} Schritte diese Woche</small>}
  </motion.div>;
}

export function ZeitPage({shell, back}: PageProps) {
  const [d, setD] = useState<any>(null), [panel, setPanel] = useState(""), [limits, setLimits] = useState<Record<string, number>>({}), [nacht, setNacht] = useState<any>(null), [busy, setBusy] = useState(false);
  const [anfrage, setAnfrage] = useState<{id: string; name: string; grund?: string} | null>(null);
  const [woche, setWoche] = useState<any>(null);
  useEffect(() => {if (shell.conn.connected) api("/api/handy/mein-bericht").then(setWoche).catch(() => {});}, [shell.conn.connected]);
  const admin = useAdmin(shell.notify);
  const laden = () => call("zeit").then(setD).catch(e => shell.notify(errorText(e)));
  useEffect(() => {laden(); const t = setInterval(laden, 15_000); return () => clearInterval(t);}, []);
  if (!d) return <><PageHeader title="Bildschirmzeit" onBack={back}/><Busy/></>;
  const appListe: JonApp[] = Array.isArray(d.apps) && d.apps.length ? d.apps : alteApps;
  const apps = appListe.map(a => a.id);
  const appName = (id: string) => appListe.find(a => a.id === id)?.name || appNamen[id] || id;
  const symbol = (id: string) => {const a = appListe.find(x => x.id === id); return <AppSymbol paket={a?.paket || id} name={a?.name || id} groesse={30}/>;};
  const gesamt = apps.reduce((s, a) => s + (d.genutzt?.[a] || 0), 0);
  const stunden = (m: number) => m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`;
  async function setzen(regeln: any, text: string) {
    setBusy(true);
    try {setD(await call("zeit-setzen", {regeln})); haptic("success"); shell.notify(text); setPanel("");}
    catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}
  }
  const status = d.nacht_aktiv ? `Schlafenszeit bis ${d.nacht_ende} Uhr` : d.pause_aktiv ? `Pause bis ${d.pause_ende} Uhr` : "Alles frei";
  return <>
    <PageHeader title="Bildschirmzeit" onBack={back}/>
    <div className="page-scroll">
      <motion.div className="zeit-held" initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={spring}>
        <Ring wert={gesamt} max={Math.max(60, apps.reduce((s, a) => s + (d.limits?.[a] || 0), 0) || 180)}><strong><Zaehler wert={gesamt} format={n => stunden(Math.round(n))}/></strong><small>heute</small></Ring>
        <span className={`zeit-status ${d.nacht_aktiv ? "nacht" : d.pause_aktiv ? "pause" : ""}`}>{d.nacht_aktiv ? <Moon/> : d.pause_aktiv ? <Hourglass/> : <ShieldCheck/>}{status}</span>
      </motion.div>
      {apps.map((a, i) => {
        const limit = d.limits?.[a] || 0, genutzt = d.genutzt?.[a] || 0, gesperrt = d.gesperrt?.[a];
        return <motion.div key={a} className="card app-zeit" initial={{opacity: 0, y: 14}} animate={{opacity: 1, y: 0}} transition={{...spring, delay: .05 * i}}>
          <div className="zeile"><span className="logo">{symbol(a)}</span><strong>{appName(a)}</strong><span className="grow"/>{gesperrt ? <span className="badge warn">{grundText[gesperrt]}</span> : d.frei_bis?.[a] ? <span className="badge ok">frei bis {d.frei_bis[a]}</span> : limit ? <span className="badge">{`noch ${d.rest?.[a] ?? 0} Min.`}</span> : <span className="badge ok">ohne Limit</span>}</div>
          <div className="progress"><i style={{width: `${limit ? Math.min(100, genutzt / limit * 100) : Math.min(100, genutzt / 1.8)}%`, background: gesperrt ? "linear-gradient(90deg,#ff8a5c,#ff5c63)" : undefined}}/></div>
          <small className="muted">{genutzt} Min. genutzt{limit ? ` von ${limit} Min.` : ""}</small>
          {gesperrt && (d.anfrage?.app === a
            ? <span className="anfrage-laeuft"><Send/>Anfrage läuft – warte auf Antwort</span>
            : <button className="text-link small anfrage-link" onClick={() => {haptic("tap"); setAnfrage({id: a, name: appName(a), grund: gesperrt});}}><Hourglass size={15}/>Mehr Zeit anfragen</button>)}
        </motion.div>;
      })}
      {woche?.tage?.length > 0 && <><div className="group-title">Diese Woche</div><WochenBalken bericht={woche}/></>}
      <div className="group-title">Fokuszeit</div>
      <p className="hint" style={{margin: "0 8px 12px"}}>Sperrt alle freigegebenen Apps für eine Weile – ideal zum Lernen. Beenden kann sie nur ein Erwachsener.</p>
      <div className="chips">{[15, 30, 60, 90].map(m => <button key={m} className="chip" disabled={busy} onClick={async () => {setBusy(true); try {setD(await call("fokus", {minuten: m})); haptic("success"); shell.notify(`Fokuszeit läuft ${m} Minuten.`);} catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}}}><Timer/>{m} Min.</button>)}</div>
      <div className="group-title">Für Eltern</div>
      <div className="group">
        <Row icon={<SlidersHorizontal/>} label="Tageslimits" detail={apps.map(a => d.limits?.[a] ? `${appName(a)} ${d.limits[a]} Min.` : "").filter(Boolean).join(" · ") || "Keine Limits"} onClick={() => admin.guard(() => {setLimits({...d.limits}); setPanel("limits");})}/>
        <Row icon={<Moon/>} label="Schlafenszeit" detail={d.nacht?.an ? `${d.nacht.von} bis ${d.nacht.bis} Uhr` : "Aus"} onClick={() => admin.guard(() => {setNacht({...d.nacht}); setPanel("nacht");})}/>
        {d.pause_aktiv && <Row icon={<Hourglass/>} label="Pause beenden" tone="accent" detail={`läuft bis ${d.pause_ende} Uhr`} onClick={() => admin.guard(() => setzen({pause_minuten: 0}, "Pause beendet."))}/>}
        {!d.pause_aktiv && <Row icon={<Hourglass/>} label="Jetzt Pause" detail="Apps sofort sperren" onClick={() => admin.guard(() => setPanel("pause"))}/>}
      </div>
      {!d.zugriff && <div className="banner" style={{marginTop: 18}}><Clock style={{color: "#9fbcff"}}/><div><strong>Genauer messen</strong><p>Mit „Nutzungszugriff“ zählt Jon auch, wenn Apps nicht über Jon geöffnet werden.</p><button className="text-link" onClick={() => admin.guard(() => call("system", {ziel: "nutzung"}).catch(e => shell.notify(errorText(e))))}>Nutzungszugriff erlauben</button></div></div>}
      {!d.verwaltet && <p className="hint" style={{margin: "16px 8px"}}>Ohne Gerätemodus kann Jon Apps nur beim Öffnen über Jon sperren. Mit Gerätemodus sperrt er sie überall.</p>}
    </div>
    {admin.element}
    <ZeitAnfrage app={anfrage} onClose={() => setAnfrage(null)} onGesendet={setD} notify={shell.notify}/>
    <Sheet open={panel === "limits"} title="Tageslimits" onClose={() => setPanel("")}>
      {apps.map(a => <div key={a} className="limit-zeile"><span className="logo">{symbol(a)}</span><strong>{appName(a)}</strong>
        <div className="chips klein">{[0, 15, 30, 60, 90, 120, 180].map(m => <button key={m} className={`chip ${(limits[a] || 0) === m ? "on" : ""}`} onClick={() => {haptic("tick"); setLimits({...limits, [a]: m});}}>{m ? `${m}` : "Aus"}</button>)}</div>
      </div>)}
      <button className="btn primary" disabled={busy} onClick={() => setzen({limits}, "Limits gespeichert.")}>Speichern</button>
    </Sheet>
    <Sheet open={panel === "nacht" && !!nacht} title="Schlafenszeit" onClose={() => setPanel("")}>
      {nacht && <>
        <div className="row-btn" style={{borderRadius: 18}}><Moon/><span>Schlafenszeit</span><Switch on={!!nacht.an} onChange={v => setNacht({...nacht, an: v})}/></div>
        <div style={{display: "flex", gap: 12, marginTop: 12}}><Field label="Von" type="time" value={nacht.von} onChange={v => setNacht({...nacht, von: v})}/><Field label="Bis" type="time" value={nacht.bis} onChange={v => setNacht({...nacht, bis: v})}/></div>
        <div className="field"><span>An diesen Abenden</span><div className="chips klein">{tage.map((t, i) => {const n = i + 1; const an = (nacht.tage || []).includes(n); return <button key={t} className={`chip ${an ? "on" : ""}`} onClick={() => setNacht({...nacht, tage: an ? nacht.tage.filter((x: number) => x !== n) : [...(nacht.tage || []), n]})}>{t}</button>;})}</div></div>
        <div className="field"><span>Gesperrte Apps</span><div className="chips klein">{apps.map(a => {const an = (nacht.apps || []).includes(a); return <button key={a} className={`chip ${an ? "on" : ""}`} onClick={() => setNacht({...nacht, apps: an ? nacht.apps.filter((x: string) => x !== a) : [...(nacht.apps || []), a]})}>{appName(a)}</button>;})}</div></div>
        <button className="btn primary" disabled={busy} onClick={() => setzen({nacht}, nacht.an ? "Schlafenszeit gespeichert." : "Schlafenszeit aus.")}>Speichern</button>
      </>}
    </Sheet>
    <Sheet open={panel === "pause"} title="Jetzt Pause" onClose={() => setPanel("")}>
      <p>Wie lange sollen alle freigegebenen Apps gesperrt sein?</p>
      <div className="chips">{[15, 30, 60, 120, 240].map(m => <button key={m} className="chip" onClick={() => setzen({pause_minuten: m}, `Pause für ${m} Minuten.`)}>{m >= 60 ? `${m / 60} Std.` : `${m} Min.`}</button>)}</div>
    </Sheet>
  </>;
}
