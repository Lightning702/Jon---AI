import React, {useEffect, useState} from "react";
import {motion} from "framer-motion";
import {AppWindow, Baby, Bell, BookOpen, EyeOff, Fingerprint, Languages, Bug, Check, ChevronDown, Cloud, Cpu, Database, Delete, Gauge, Globe, HardDrive, Hourglass, Info, KeyRound, Laptop, LayoutGrid, Link2, LogOut, Mic, Moon, Palette, Pencil, Plug, Power, Puzzle, QrCode, RefreshCw, Search, Settings, Shield, ShieldAlert, ShieldCheck, Siren, Smartphone, Sparkles, Sun, User, Volume2, Wifi, Bluetooth, Lock, Zap} from "lucide-react";
import {api, call, haptic, listen} from "./bridge";
import {Shell, compose, providerLabel, shortModel} from "./Chat";
import {PageProps} from "./Pages";
import {Busy, Field, PageHeader, Row, Sheet, Switch, errorText, useLoad} from "./ui";
import {rememberModel} from "./useChats";
import {AppWahl} from "./Apps";
import {KinderEinstellungen, SosEinstellungen} from "./Familie";
import {spracheAnwenden} from "./sprache";

function SprachWahl({open, onClose, notify}: {open: boolean; onClose: () => void; notify: (s: string) => void}) {
  const [stand, setStand] = useState<{wahl: string; code: string} | null>(null);
  useEffect(() => {if (open) call("sprache").then(setStand).catch(e => notify(errorText(e)));}, [open]);
  const optionen: [string, string, string][] = [["auto", "Automatisch (Systemsprache)", "Deutsch oder Englisch"], ["de", "Deutsch", "Deutsch"], ["en", "English", "English"]];
  async function waehlen(wahl: string) {
    try {
      const neu = await call("sprache", {setzen: wahl});
      setStand(neu);
      haptic("success");
      onClose();
      spracheAnwenden(neu.code);
    } catch (e) {notify(errorText(e));}
  }
  return <Sheet open={open} title="Sprache" onClose={onClose}>
    {optionen.map(([wert, titel, text]) => <button key={wert} className="list-row" onClick={() => void waehlen(wert)}><Languages/><span><span translate={wert === "en" ? "no" : undefined}>{titel}</span><small translate={wert === "en" ? "no" : undefined}>{text}</small></span>{stand?.wahl === wert && <Check className="check"/>}</button>)}
  </Sheet>;
}

const accents = [{id: "#3b6cf6", name: "Blau"}, {id: "#8b5cf6", name: "Violett"}, {id: "#ee4fa0", name: "Pink"}, {id: "#1fa37a", name: "Grün"}, {id: "#f07b1d", name: "Orange"}];
const avatarColors = ["#c765ac", "#3b6cf6", "#8b5cf6", "#1fa37a", "#f07b1d", "#e5484d"];
export const initials = (name: string) => (name || "Du").trim().split(/\s+/).map(p => p[0]).join("").slice(0, 2).toUpperCase();

export function PinPad({open, mode, onClose, onDone, finger = false}: {open: boolean; mode: "unlock" | "setup"; onClose: () => void; onDone: (result?: any) => void; finger?: boolean}) {
  const [pin, setPin] = useState(""), [first, setFirst] = useState(""), [error, setError] = useState(""), [shake, setShake] = useState(false), [recovery, setRecovery] = useState(false), [code, setCode] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => {if (open) {setPin(""); setFirst(""); setError(""); setRecovery(false); setCode(""); if (finger && mode === "unlock") void mitFinger();}}, [open]);
  async function mitFinger() {
    try {
      const r = await call("admin", {aktion: "finger"}, 120_000);
      if (r.ok) {haptic("success"); onDone(r);} else if (r.fehler && r.fehler !== "Abgebrochen.") setError(r.fehler);
    } catch (e) {setError(errorText(e));}
  }
  const fail = (text: string) => {setError(text); setShake(true); haptic("error"); setPin(""); setTimeout(() => setShake(false), 420);};
  async function submit(value = pin) {
    if (busy) return;
    if (mode === "setup") {
      if (value.length < 6) return fail("Mindestens 6 Ziffern.");
      if (!first) {setFirst(value); setPin(""); setError(""); return;}
      if (first !== value) {setFirst(""); return fail("Die PINs stimmen nicht überein.");}
      setBusy(true);
      try {const result = await call("admin", {aktion: "einrichten", pin: value}); haptic("success"); onDone(result);} catch (e) {fail(errorText(e));} finally {setBusy(false);}
      return;
    }
    setBusy(true);
    try {
      const result = await call("admin", recovery ? {aktion: "recovery", code} : {aktion: "entsperren", pin: value});
      if (result.ok) {haptic("success"); onDone(result);} else fail(result.fehler || (recovery ? "Recovery-Code stimmt nicht." : "Falsche PIN."));
    } catch (e) {fail(errorText(e));} finally {setBusy(false);}
  }
  const press = (d: string) => {haptic("tick"); if (pin.length < 12) setPin(p => p + d);};
  const title = mode === "setup" ? (first ? "PIN wiederholen" : "Neue Admin-PIN") : recovery ? "Recovery-Code" : "Admin-PIN";
  return <Sheet open={open} title={title} onClose={onClose}>
    {recovery ? <>
      <Field label="Recovery-Code (xxxxxx-xxxxxx-…)" value={code} onChange={setCode} autoFocus/>
      {error && <p className="error-text">{error}</p>}
      <button className="btn primary" disabled={!code.trim() || busy} onClick={() => submit()}>Entsperren</button>
      <button className="btn outline" style={{marginTop: 10}} onClick={() => {setRecovery(false); setError("");}}>PIN verwenden</button>
    </> : <>
      <p className="hint" style={{textAlign: "center"}}>{mode === "setup" ? "6 bis 12 Ziffern. Diese PIN schützt Kiosk, Kopplung und Geräteeinstellungen." : "Gib deine Admin-PIN ein, um die Verwaltung für 5 Minuten zu öffnen."}</p>
      <div className={`pin-dots ${shake ? "shake" : ""}`}>{Array.from({length: Math.max(6, pin.length)}).map((_, i) => <i key={i} className={i < pin.length ? "on" : ""}/>)}</div>
      <p className="error-text" style={{textAlign: "center", minHeight: 24}}>{error}</p>
      <div className="keypad">{["1", "2", "3", "4", "5", "6", "7", "8", "9"].map(d => <button key={d} onClick={() => press(d)}>{d}</button>)}<button onClick={() => {haptic("tick"); setPin(p => p.slice(0, -1));}}><Delete/></button><button onClick={() => press("0")}>0</button><button onClick={() => submit()} style={{background: "var(--fg)", color: "var(--bg)"}}>{busy ? <RefreshCw className="spin"/> : <Check/>}</button></div>
      {mode === "unlock" && finger && <button className="btn soft finger-knopf" style={{marginTop: 14}} onClick={() => {haptic("tap"); void mitFinger();}}><Fingerprint/>Mit Fingerabdruck</button>}
      {mode === "unlock" && <button className="btn outline" style={{marginTop: 10}} onClick={() => {setRecovery(true); setError("");}}>PIN vergessen?</button>}
    </>}
  </Sheet>;
}

export function useAdmin(notify: (s: string) => void) {
  const [pad, setPad] = useState<{mode: "unlock" | "setup"; then?: (result?: any) => void; finger?: boolean} | null>(null);
  async function guard(then: () => void) {
    try {
      const s = await call("admin", {aktion: "status"});
      if (!s.eingerichtet || s.frei) then(); else setPad({mode: "unlock", then, finger: !!s.fingerabdruck});
    } catch (e) {notify(errorText(e));}
  }
  const element = <PinPad open={!!pad} mode={pad?.mode || "unlock"} finger={!!pad?.finger} onClose={() => setPad(null)} onDone={result => {const then = pad?.then; setPad(null); then?.(result);}}/>;
  return {guard, element, setup: (then?: (result?: any) => void) => setPad({mode: "setup", then})};
}

export function ModelSheet({open, onClose, shell}: {open: boolean; onClose: () => void; shell: Shell}) {
  const [query, setQuery] = useState("");
  const c = shell.chats.current;
  useEffect(() => {if (open) setQuery("");}, [open]);
  const usable = shell.providers.filter(p => p.connected && (p.models?.length || p.default_model));
  const q = query.toLowerCase();
  const offline: any[] = (shell.lokal?.modelle || []).filter((m: any) => m.status === "fertig" && (!q || m.titel.toLowerCase().includes(q)));
  function pick(provider: string, model: string) {
    haptic("success");
    shell.chats.update({provider, model});
    rememberModel(provider, model);
    onClose();
  }
  const kind = (p: any) => p.auth === "local" ? <span className="badge local">Lokal auf dem Pi</span> : <span className="badge fast">Cloud · schnell</span>;
  const piAnbieter = !!shell.conn.paired && shell.weg?.weg !== "solo";
  return <Sheet open={open} title="Anbieter und Modell" onClose={onClose} footer={<div style={{padding: "8px 20px 4px"}}><button className="btn accent" onClick={() => {onClose(); shell.push(piAnbieter ? "providers" : "solo");}}><Zap/>Eigenen API-Schlüssel hinzufügen</button></div>}>
    <div className="search-field"><Search/><input placeholder="Modell suchen" value={query} onChange={e => setQuery(e.target.value)}/></div>
    {piAnbieter && !shell.providers.length && <Busy text="Anbieter werden vom Pi geladen …"/>}
    {shell.weg?.weg === "solo" && <button className="list-row" onClick={() => {onClose(); shell.push("solo");}}><Smartphone/><span>Eigener Zugang<small>{shell.weg?.solo?.modell || "Modell wählen"} · Einstellungen → Auf Jon verzichten</small></span>{c.provider !== "handy" && <Check className="check"/>}</button>}
    {offline.length > 0 && <><div className="provider-head">Auf dem Handy<span className="badge local">Ohne Internet</span></div>{offline.map((m: any) => <button key={m.name} className="list-row" onClick={() => pick("handy", m.name)}><Cpu/><span>{m.titel}<small>Ohne Internet · {m.bild ? "Text und Bilder" : "Text"}</small></span>{c.provider === "handy" && c.model === m.name && <Check className="check"/>}</button>)}</>}
    {shell.conn.paired && shell.weg?.weg !== "solo" && <button className="list-row" onClick={() => pick("", "")}><Sparkles/><span>Automatisch<small>Jons Standard auf dem Pi</small></span>{!c.provider && <Check className="check"/>}</button>}
    {piAnbieter && usable.map(p => {
      const models: string[] = Array.from(new Set([...(p.default_model ? [p.default_model] : []), ...(p.models || [])])).filter((m: string) => !q || m.toLowerCase().includes(q) || String(p.label).toLowerCase().includes(q));
      if (!models.length) return null;
      return <div key={p.provider}>
        <div className="provider-head">{p.label}{kind(p)}</div>
        <div className="model-list">{models.slice(0, q ? 60 : 12).map(m => <button key={m} className="list-row" onClick={() => pick(p.provider, m)}><Cpu/><span>{shortModel(m)}<small>{m.includes("/") ? m.split("/")[0] : p.label}</small></span>{c.provider === p.provider && c.model === m && <Check className="check"/>}</button>)}</div>
      </div>;
    })}
    {piAnbieter && !usable.length && shell.providers.length > 0 && <p className="muted">Noch kein Anbieter verbunden. Tippe unten auf „Eigenen API-Schlüssel hinzufügen“.</p>}
    {!offline.length && <button className="list-row" onClick={() => {onClose(); shell.push("offline");}}><Cpu/><span>Offline-Modell laden<small>Gemma 4 und Co. direkt auf dem Handy</small></span></button>}
  </Sheet>;
}

const freigabeText: Record<string, string> = {ask: "Immer fragen", allow: "Nur bei riskanten Aktionen", alles: "Nie fragen – alles erlauben"};

export function SettingsPage({shell, back, arg}: PageProps) {
  const {state, notify, conn, push} = shell;
  const profile = {accent: "#3b6cf6", theme: "dark", avatar: avatarColors[0], ...(state.profile || {}), name: state.profile?.name || shell.name || ""};
  const settings = useLoad<any>(() => conn.paired ? api("/api/settings") : Promise.resolve({}));
  const [panel, setPanel] = useState(arg?.freigabe ? "Freigaben" : ""), [value, setValue] = useState(""), [data, setData] = useState<any>(null), [busy, setBusy] = useState(false);
  const admin = useAdmin(notify);
  const c = shell.chats.current;
  const pi = !!conn.paired;
  const [hintergrund, setHintergrund] = useState<any>(null);
  useEffect(() => {call("hintergrund").then(setHintergrund).catch(() => {});}, []);
  async function saveProfile(patch: any) {
    await shell.saveState({profile: {...profile, ...patch}});
    if (patch.name !== undefined) call("profil-setzen", {name: patch.name}).catch(() => {});
    haptic("success");
  }
  async function freigabeSetzen(modus: string) {
    try {const r = await call("freigabe", {modus}); shell.setFreigabe(r.modus); haptic("success"); notify(freigabeText[r.modus] + "."); setPanel("");}
    catch (e) {notify(errorText(e));}
  }
  function open(name: string, initial = "") {setPanel(name); setValue(initial); setData(null);}
  const accentName = accents.find(a => a.id === profile.accent)?.name || "Blau";
  const themeName = ({dark: "Dunkel", light: "Hell", system: "System"} as Record<string, string>)[profile.theme] || "Dunkel";
  return <>
    <PageHeader title="" onBack={back}/>
    <div className="page-scroll">
      <div className="profile">
        <motion.button className="avatar big" style={{"--avatar": profile.avatar} as React.CSSProperties} initial={{scale: .8, opacity: 0}} animate={{scale: 1, opacity: 1}} transition={{type: "spring", stiffness: 260, damping: 20}} onClick={() => open("Profil", profile.name)}>{initials(profile.name)}<span className="edit"><Pencil/></span></motion.button>
        <h2>{profile.name || "Dein Name"}</h2>
      </div>
      <div className="group-title">Mein Jon</div>
      <div className="group">
        <Row icon={<Smartphone/>} label="Auf Jon verzichten" detail={shell.weg?.solo?.an ? (shell.weg?.solo?.anbieter === "handy" ? "An · offline auf dem Handy" : `An · ${shell.weg?.solo?.liste?.find((a: any) => a.id === shell.weg?.solo?.anbieter)?.name || "eigener Zugang"}`) : "Aus · Jon läuft über PC oder Pi"} onClick={() => push("solo")}/>
        <Row icon={<Cpu/>} label="Offline-KI" detail={shell.lokal?.standard ? `${shell.lokal.modelle?.find((m: any) => m.name === shell.lokal.standard)?.titel || shell.lokal.standard} bereit` : "Modelle aus der Edge Gallery laden"} onClick={() => push("offline")}/>
        <Row icon={<ShieldAlert/>} label="Freigaben" detail={freigabeText[shell.freigabe] || freigabeText.ask} onClick={() => setPanel("Freigaben")}/>
        {pi && <Row icon={<User/>} label="Personalisierung" onClick={() => open("Personalisierung", settings.data?.custom_prompt || "")}/>}
        <Row icon={<BookOpen/>} label="Erinnerung" onClick={() => {open("Erinnerung"); (pi ? api("/api/knowledge") : call("gedaechtnis").then((r: any) => (r.fakten || []).map((f: string, i: number) => ({id: i, title: f, lokal: true})))).then(setData).catch(e => notify(errorText(e)));}}/>
        {pi && <Row icon={<Puzzle/>} label="Plugins" onClick={() => push("plugins")}/>}
      </div>
      <div className="group-title">Konto</div>
      <div className="group">
        <Row icon={<Laptop/>} label="Workspace" detail={conn.name ? `${conn.name} · ${(conn.server || 0) > 1 ? `${conn.server} Verbindungen` : "Persönlich"}` : "Kein Pi verbunden"} onClick={() => push(conn.paired ? "server" : "pair")}/>
        {pi && <Row icon={<Zap/>} label="Schneller antworten" tone="accent" onClick={() => push("providers")}/>}
        <Row icon={<Cpu/>} label="Modell" detail={c.provider === "handy" ? `${shell.lokal?.modelle?.find((m: any) => m.name === c.model)?.titel || c.model} · Auf dem Handy` : c.model ? `${shortModel(c.model)} · ${providerLabel(shell.providers, c.provider)}` : "Automatisch"} onClick={shell.openModel}/>
        {pi && <Row icon={<Gauge/>} label="Nutzung und Grenzwerte" onClick={() => {open("Nutzung"); api("/api/usage").then(setData).catch(e => notify(errorText(e)));}}/>}
        <Row icon={<ShieldCheck/>} label="Kindersicherung" detail={conn.kiosk ? "Kiosk aktiv" : "Kiosk aus"} onClick={() => push("security")}/>
        {shell.appsSichtbar && <Row icon={<Hourglass/>} label="Bildschirmzeit" detail="Limits, Schlafenszeit, Pause" onClick={() => push("zeit")}/>}
        <Row icon={<Siren/>} label="SOS" detail="Standort mitschicken, direkt anrufen" onClick={() => admin.guard(() => setPanel("SOS"))}/>
        <Row icon={<Baby/>} label="Kinder-Modus" detail={shell.kinder?.an ? `An · ${shell.kinder.alter} Jahre · Hausaufgaben-Hilfe` : "Kindgerechte Antworten, sichere Suche"} onClick={() => admin.guard(() => setPanel("Kinder"))}/>
        {pi && <Row icon={<Bell/>} label="Im Hintergrund verbunden" detail={hintergrund?.an ? (hintergrund.benachrichtigungen ? "Nachrichten und Durchsagen auch bei geschlossener App" : "Benachrichtigungen erlauben, damit du sie siehst") : "Aus – nur solange Jon offen ist"} right={<Switch on={!!hintergrund?.an} onChange={v => {call("hintergrund", {an: v}).then(setHintergrund).catch(e => notify(errorText(e))); if (v) call("permission", {name: "benachrichtigungen"}).then(() => call("hintergrund").then(setHintergrund)).catch(() => {});}}/>}/>}
        <Row icon={<Smartphone/>} label="Gerät" detail="WLAN, Bluetooth, Ton, Helligkeit" onClick={() => push("device")}/>
      </div>
      <div className="gap"/>
      <div className="group compact">
        <Row icon={profile.theme === "light" ? <Sun/> : <Moon/>} label="Darstellung" value={themeName} right={<ChevronDown className="chev"/>} onClick={() => setPanel("Darstellung")}/>
        <Row icon={<Palette/>} label="Akzentfarbe" value={<><i className="swatch" style={{background: profile.accent}}/>{accentName}</>} right={<ChevronDown className="chev"/>} onClick={() => setPanel("Akzentfarbe")}/>
      </div>
      <div className="gap"/>
      <div className="group compact">
        <Row icon={<Settings/>} label="Allgemein" onClick={() => open("Allgemein", profile.name)}/>
        <Row icon={<Bell/>} label="Benachrichtigungen" onClick={() => call("permission", {name: "benachrichtigungen"}).then(v => notify(v.granted ? "Benachrichtigungen sind erlaubt." : "Benachrichtigungen sind aus.")).catch(e => notify(errorText(e)))}/>
        <Row icon={<Languages/>} label="Sprache" detail="Deutsch oder Englisch" onClick={() => setPanel("Sprache")}/>
        <Row icon={<Volume2/>} label="Sprachmodus" onClick={() => push("voice-settings")}/>
        <Row icon={<Shield/>} label="Sicherheit und Anmeldung" onClick={() => push("security")}/>
        {pi && <Row icon={<Laptop/>} label="Fernsteuerung" onClick={() => push("remote")}/>}
        {pi && <Row icon={<Globe/>} label="Cloud-Browser" onClick={() => {compose("Öffne im Browser auf dem Pi: ", "coding"); back();}}/>}
        {pi && <Row icon={<HardDrive/>} label="Speicher" onClick={() => {open("Speicher"); api("/api/mobile/status").then(setData).catch(e => notify(errorText(e)));}}/>}
        <Row icon={<ShieldCheck/>} label="Datenschutzzentrum" onClick={() => setPanel("Datenschutz")}/>
        <Row icon={<Database/>} label="Datenkontrollen" onClick={() => push("archive")}/>
        {pi && <Row icon={<Bug/>} label="Fehler melden" onClick={() => open("Fehler melden")}/>}
        <Row icon={<RefreshCw/>} label="Updates" detail="App und Jon auf dem PC oder Pi aktualisieren" onClick={() => push("updates")}/>
        <Row icon={<Info/>} label="Infos" onClick={() => {open("Infos"); Promise.allSettled([pi ? api("/api/health") : Promise.reject(), call("device")]).then(([h, d]) => setData({...(h.status === "fulfilled" ? h.value : {}), app: d.status === "fulfilled" ? d.value.version : ""}));}}/>
      </div>
      <div className="group-title">Datenschutz</div>
      <div className="group">
        <Row icon={<Database/>} label="Sicherung" detail="Auf den PC oder Pi oder als Datei" onClick={() => push("sicherung")}/>
        <Row icon={<ShieldCheck/>} label="Datenschutz" detail="Was wo gespeichert wird · Alle Daten löschen" onClick={() => push("datenschutz")}/>
      </div>
      <div className="gap"/>
      <div className="group compact">
        {pi && <Row icon={<Link2/>} label="Verbindungen" detail="Wechseln, hinzufügen oder trennen" onClick={() => push("server")}/>}
        {!conn.kiosk && !conn.locked && <Row icon={<Power/>} label="Jon schließen" chevron={false} onClick={() => call("beenden").catch(e => notify(errorText(e)))}/>}
      </div>
      <p className="hint" style={{textAlign: "center", margin: "22px 0 8px"}}>Jon Gerät · FelWorks</p>
    </div>
    {admin.element}
    <SosEinstellungen open={panel === "SOS"} onClose={() => setPanel("")} notify={notify}/>
    <SprachWahl open={panel === "Sprache"} onClose={() => setPanel("")} notify={notify}/>
    <KinderEinstellungen open={panel === "Kinder"} onClose={() => setPanel("")} notify={notify} kinder={shell.kinder} setKinder={shell.setKinder}/>
    <Sheet open={panel === "Profil"} title="Profil" onClose={() => setPanel("")}>
      <Field label="Dein Name" value={value} onChange={setValue} autoFocus placeholder="Vorname"/>
      <div className="field"><span>Farbe</span><div style={{display: "flex", gap: 12}}>{avatarColors.map(color => <button key={color} aria-label={color} onClick={() => saveProfile({avatar: color})} style={{width: 44, height: 44, borderRadius: "50%", background: color, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff"}}>{profile.avatar === color && <Check/>}</button>)}</div></div>
      <button className="btn primary" onClick={() => saveProfile({name: value.trim()}).then(() => setPanel(""))}>Speichern</button>
    </Sheet>
    <Sheet open={panel === "Allgemein"} title="Allgemein" onClose={() => setPanel("")}>
      <Field label="So nennt dich Jon" value={value} onChange={setValue} placeholder="Vorname"/>
      <button className="btn primary" onClick={() => saveProfile({name: value.trim()}).then(() => setPanel(""))}>Speichern</button>
    </Sheet>
    <Sheet open={panel === "Personalisierung"} title="Personalisierung" onClose={() => setPanel("")}>
      <Field label="Was soll Jon über dich wissen und wie soll er antworten?" value={value} onChange={setValue} multiline/>
      <button className="btn primary" disabled={busy} onClick={async () => {setBusy(true); try {await api("/api/settings", "PUT", {custom_prompt: value}); await settings.refresh(); notify("Gespeichert."); setPanel("");} catch (e) {notify(errorText(e));} finally {setBusy(false);}}}>Speichern</button>
    </Sheet>
    <Sheet open={panel === "Erinnerung"} title="Erinnerung" onClose={() => setPanel("")}>
      {data ? (data.length ? data.map((item: any, i: number) => <div className="card" key={item.ref || item.id || i}><h4><BookOpen/>{item.title || item.path || item.name}</h4><p>{item.lokal ? "Auf diesem Handy gespeichert" : item.summary || item.preview || "Im Wissen deines Pi gespeichert"}</p>{item.lokal && <button className="text-link small" onClick={() => call("gedaechtnis-vergessen", {index: item.id}).then((r: any) => setData((r.fakten || []).map((f: string, n: number) => ({id: n, title: f, lokal: true}))))}>Vergessen</button>}</div>) : <p className="muted">Jon hat sich noch nichts gemerkt.</p>) : <Busy/>}
      <Field label="Neue Erinnerung" value={value} onChange={setValue} multiline/>
      <button className="btn primary" disabled={!value.trim()} onClick={async () => {try {if (pi) {await api("/api/knowledge/learn", "POST", {text: value, title: "Erinnerung vom Jon Gerät", path: ""}); setData(await api("/api/knowledge"));} else {await call("gedaechtnis-merken", {fakt: value}); const r = await call("gedaechtnis"); setData((r.fakten || []).map((f: string, n: number) => ({id: n, title: f, lokal: true})));} setValue(""); haptic("success");} catch (e) {notify(errorText(e));}}}>Merken</button>
    </Sheet>
    <Sheet open={panel === "Nutzung"} title="Nutzung und Grenzwerte" onClose={() => setPanel("")}>
      {data ? <>{Object.entries(data.usage || data).filter(([, v]) => typeof v === "object").map(([name, v]: [string, any]) => <div className="card" key={name}><h4><Gauge/>{providerLabel(shell.providers, name)}</h4><div className="stat"><span>Anfragen</span><b>{v.requests ?? 0}</b></div><div className="stat"><span>Tokens</span><b>{(v.total_tokens ?? 0).toLocaleString("de-DE")}</b></div><div className="stat"><span>Ø Antwortzeit</span><b>{v.avg_latency ? `${v.avg_latency.toFixed(1)} s` : "–"}</b></div><div className="stat"><span>Zuletzt</span><b>{shortModel(v.last_model || "")}</b></div></div>)}<p className="hint">{data.note}</p></> : <Busy/>}
    </Sheet>
    <Sheet open={panel === "Darstellung"} title="Darstellung" onClose={() => setPanel("")}>
      {[{id: "dark", name: "Dunkel", icon: <Moon/>}, {id: "light", name: "Hell", icon: <Sun/>}, {id: "system", name: "System", icon: <Smartphone/>}].map(t => <button key={t.id} className="list-row" onClick={() => saveProfile({theme: t.id})}>{t.icon}<span>{t.name}</span>{profile.theme === t.id && <Check className="check"/>}</button>)}
    </Sheet>
    <Sheet open={panel === "Akzentfarbe"} title="Akzentfarbe" onClose={() => setPanel("")}>
      {accents.map(a => <button key={a.id} className="list-row" onClick={() => saveProfile({accent: a.id})}><i style={{width: 22, height: 22, borderRadius: "50%", background: a.id}}/><span>{a.name}</span>{profile.accent === a.id && <Check className="check"/>}</button>)}
    </Sheet>
    <Sheet open={panel === "Speicher"} title="Speicher" onClose={() => setPanel("")}>
      {data ? <><div className="stat"><span>Frei auf dem Pi</span><b>{(data.free / 1073741824).toFixed(1)} GB</b></div><div className="stat"><span>Gesamt</span><b>{(data.total / 1073741824).toFixed(0)} GB</b></div><div className="stat"><span>Jons Ordner</span><b>{data.root}</b></div><button className="btn soft" style={{marginTop: 16}} onClick={() => {setPanel(""); push("library");}}>Bibliothek öffnen</button></> : <Busy/>}
    </Sheet>
    <Sheet open={panel === "Datenschutz"} title="Datenschutzzentrum" onClose={() => setPanel("")}>
      <p>„Hey Jon“ wird lokal auf diesem Gerät erkannt. Erst dein Auftrag danach geht verschlüsselt an deinen Pi.</p>
      <p>Chats, Dateien und API-Schlüssel liegen auf deinem Pi, Schlüssel dort verschlüsselt. Der gewählte KI-Anbieter verarbeitet nur die Anfragen, die du stellst.</p>
      <p>Die Verbindung zum Pi ist Ende-zu-Ende verschlüsselt (AES-GCM) und läuft über dein Heimnetz oder Tailscale.</p>
    </Sheet>
    <Sheet open={panel === "Fehler melden"} title="Fehler melden" onClose={() => setPanel("")}>
      <Field label="Was ist passiert?" value={value} onChange={setValue} multiline autoFocus/>
      <button className="btn primary" disabled={!value.trim()} onClick={async () => {try {await api("/api/dateien/erstellen", "POST", {art: "md", titel: "Jon Gerät Fehlerbericht", inhalt: value}); notify("Bericht auf dem Pi gespeichert."); setPanel("");} catch (e) {notify(errorText(e));}}}>Bericht auf dem Pi speichern</button>
    </Sheet>
    <Sheet open={panel === "Infos"} title="Infos" onClose={() => setPanel("")}>
      <div className="stat"><span>App</span><b>Jon Gerät {data?.app || ""}</b></div>
      <div className="stat"><span>Jon auf dem Pi</span><b>{data?.version || "–"}</b></div>
      <div className="stat"><span>Verbindung</span><b>{conn.connected ? `Verbunden mit ${conn.name}` : "Offline"}</b></div>
      <div className="stat"><span>Kiosk</span><b>{conn.kiosk ? "Aktiv" : "Aus"}</b></div>
      <div className="stat"><span>Anbieter auf dem Pi</span><b>{(data?.available_providers || []).join(", ") || "–"}</b></div>
    </Sheet>
    <Sheet open={panel === "Freigaben"} title="Jon fragt vor Aktionen" onClose={() => setPanel("")}>
      <p>Wenn Jon etwas auf deinem Pi oder PC tut – Dateien ändern, Programme starten, Befehle ausführen –, kann er vorher fragen.</p>
      {["ask", "allow", "alles"].filter(m => !(shell.kinder?.an && m === "alles")).map(m => <button key={m} className="list-row" onClick={() => admin.guard(() => freigabeSetzen(m))}>{m === "alles" ? <ShieldAlert/> : m === "allow" ? <Shield/> : <ShieldCheck/>}<span>{freigabeText[m]}<small>{m === "ask" ? "Sicherste Wahl" : m === "allow" ? "Fragt nur bei riskanten Aktionen" : "Jon macht alles ohne Rückfrage – auch Riskantes"}</small></span>{shell.freigabe === m && <Check className="check"/>}</button>)}
      {shell.freigabe === "alles" && <p className="error-text small">Achtung: Jon kann jetzt auch Dateien löschen oder Befehle ausführen, ohne zu fragen.</p>}
    </Sheet>
  </>;
}

export function ProvidersPage({shell, back}: PageProps) {
  const accounts = useLoad<any[]>(() => api("/api/accounts"));
  const ollama = useLoad<any>(() => api("/api/ollama/config"));
  const [selected, setSelected] = useState<any>(null), [key, setKey] = useState(""), [model, setModel] = useState(""), [busy, setBusy] = useState(false), [ollamaOpen, setOllamaOpen] = useState(false), [host, setHost] = useState(""), [port, setPort] = useState("11434"), [test, setTest] = useState("");
  const admin = useAdmin(shell.notify);
  useEffect(() => {if (ollama.data) {setHost(ollama.data.host || "localhost"); setPort(String(ollama.data.port || 11434));}}, [ollama.data]);
  async function done() {await accounts.refresh(); shell.refreshProviders(); haptic("success");}
  const list = accounts.data || [];
  const cloud = list.filter(p => p.auth !== "local");
  const local = list.filter(p => p.auth === "local");
  return <>
    <PageHeader title="Schneller antworten" onBack={back}/>
    <div className="page-scroll">
      <div className="banner"><Zap style={{color: "#9fbcff"}}/><div><strong>Eigener API-Schlüssel</strong><p>Mit einem Cloud-Anbieter antwortet Jon deutlich schneller. Der Schlüssel wird verschlüsselt auf deinem Pi gespeichert – Werkzeuge, Dateien und Aktionen laufen weiter auf dem Pi.</p></div></div>
      <div className="group-title">Lokal auf dem Pi</div>
      <div className="group">{local.map(p => <Row key={p.provider} icon={<Cpu/>} label={p.label} detail={p.connected ? `${p.models?.length || 0} Modelle · ${p.provider === "ollama" ? ollama.data?.model || "" : "bereit"}` : "Nicht erreichbar"} right={<span className={`badge ${p.connected ? "ok" : ""}`}>{p.connected ? "Aktiv" : "Aus"}</span>} onClick={() => p.provider === "ollama" ? admin.guard(() => setOllamaOpen(true)) : shell.notify("LM Studio richtest du am Pi ein.")}/>)}</div>
      <div className="group-title">Cloud-Anbieter</div>
      {accounts.busy ? <Busy/> : accounts.error ? <p className="error-text">{accounts.error}</p> : <div className="group">{cloud.map(p => <Row key={p.provider} icon={<KeyRound/>} label={p.label} detail={p.connected ? (p.source === "env" ? "Über die Pi-Konfiguration" : `Verbunden${p.default_model ? ` · ${shortModel(p.default_model)}` : ""}`) : "Schlüssel hinzufügen"} right={p.connected ? <span className="badge ok">Verbunden</span> : undefined} onClick={() => admin.guard(() => {setSelected(p); setKey(""); setModel(p.default_model || "");})}/>)}</div>}
      <p className="hint" style={{margin: "18px 8px"}}>Welches Modell ein Chat benutzt, wählst du oben im Chat oder unter Einstellungen → Modell.</p>
    </div>
    {admin.element}
    <Sheet open={!!selected} title={selected?.label || ""} onClose={() => setSelected(null)}>
      {selected && <>
        <p className="hint">{selected.connected ? "Dieser Anbieter ist verbunden. Du kannst den Schlüssel ersetzen oder entfernen." : "Füge deinen API-Schlüssel ein. Er verlässt das Gerät nur verschlüsselt und wird auf dem Pi verschlüsselt abgelegt."}{selected.docs ? ` Schlüssel bekommst du unter ${selected.docs.replace(/^https?:\/\//, "")}.` : ""}</p>
        <Field label="API-Schlüssel" type="password" value={key} onChange={setKey} placeholder={selected.connected ? "••••••••••••" : "sk-…"}/>
        {selected.models?.length ? <label className="field">Standardmodell<select value={model} onChange={e => setModel(e.target.value)}><option value="">Automatisch</option>{selected.models.map((m: string) => <option key={m} value={m}>{m}</option>)}</select></label> : <Field label="Standardmodell (optional)" value={model} onChange={setModel}/>}
        <div style={{display: "flex", flexDirection: "column", gap: 10}}>
          <button className="btn primary" disabled={busy || (!key.trim() && !selected.connected)} onClick={async () => {
            setBusy(true);
            try {
              if (key.trim()) await api("/api/accounts/connect", "POST", {provider: selected.provider, api_key: key.trim(), default_model: model || undefined});
              else if (model) await api(`/api/accounts/${selected.provider}/default-model`, "POST", {model});
              setKey("");
              await done();
              shell.notify(`${selected.label} ist verbunden.`);
              setSelected(null);
            } catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}
          }}><Plug/>{selected.connected ? "Speichern" : "Verbinden"}</button>
          {selected.connected && selected.source === "account" && <button className="btn danger" onClick={async () => {try {await api(`/api/accounts/${selected.provider}`, "DELETE"); await done(); setSelected(null); shell.notify("Schlüssel entfernt.");} catch (e) {shell.notify(errorText(e));}}}>Schlüssel entfernen</button>}
        </div>
      </>}
    </Sheet>
    <Sheet open={ollamaOpen} title="Ollama" onClose={() => setOllamaOpen(false)}>
      <p className="hint">Ollama läuft kostenlos und privat. Standard ist der Pi selbst (localhost). Du kannst auch einen stärkeren Rechner im Heimnetz eintragen.</p>
      <div className="row-btn" style={{borderRadius: 18, marginTop: 10}}><Cpu/><span>Ollama benutzen</span><Switch on={!!ollama.data?.enabled} onChange={v => api("/api/ollama/config", "PUT", {enabled: v}).then(() => {ollama.refresh(); done();}).catch(e => shell.notify(errorText(e)))}/></div>
      <Field label="Adresse" value={host} onChange={setHost} placeholder="localhost oder 192.168.x.x"/>
      <Field label="Port" value={port} onChange={setPort} type="number"/>
      {test && <p className="hint">{test}</p>}
      <div style={{display: "flex", gap: 10}}>
        <button className="btn soft" onClick={() => {setTest("Teste …"); api("/api/ollama/test", "POST", {host: host.trim(), port: Number(port) || 11434}).then(v => setTest(v.ok ? `Erreichbar · ${v.models?.length ?? v.count ?? ""} Modelle` : v.error || v.message || "Nicht erreichbar")).catch(e => setTest(errorText(e)));}}>Testen</button>
        <button className="btn primary" onClick={() => api("/api/ollama/config", "PUT", {host: host.trim(), port: Number(port) || 11434}).then(() => {ollama.refresh(); done(); shell.notify("Ollama gespeichert.");}).catch(e => shell.notify(errorText(e)))}>Speichern</button>
      </div>
    </Sheet>
  </>;
}

export function DevicePage({shell, back}: PageProps) {
  const [d, setD] = useState<any>(null), [nets, setNets] = useState<string[]>([]), [wifi, setWifi] = useState<{ssid: string; pass: string; art: string} | null>(null);
  const admin = useAdmin(shell.notify);
  const load = () => call("device").then(setD).catch(e => shell.notify(errorText(e)));
  useEffect(() => {load(); const timer = setInterval(load, 5000); return () => clearInterval(timer);}, []);
  const set = (name: string, value: any) => call("set", {name, value}).then(setD).catch(e => {shell.notify(errorText(e)); load();});
  if (!d) return <><PageHeader title="Gerät" onBack={back}/><Busy/></>;
  const pct = (v: number, max: number) => `${Math.round(v / Math.max(1, max) * 100)}%`;
  return <>
    <PageHeader title="Gerät" onBack={back}/>
    <div className="page-scroll">
      <div className="card"><h4><Smartphone/>{d.modell}</h4><div className="stat"><span>Android</span><b>{d.android}</b></div><div className="stat"><span>Akku</span><b>{d.akku}%{d.laedt ? " · lädt" : ""}</b></div><div className="stat" style={{border: 0}}><span>Pi</span><b>{d.pi?.verbunden ? `${d.pi.name} · ${d.pi.adresse}` : d.pi?.gekoppelt ? "Offline" : "Nicht gekoppelt"}</b></div></div>
      <div className="group-title">Verbindungen</div>
      <div className="group">
        <Row icon={<Wifi/>} label="WLAN" detail={d.wlanName || (d.wlan ? "Eingeschaltet" : "Aus")} right={<Switch on={!!d.wlan} onChange={v => admin.guard(() => set("wlan", v))}/>}/>
        <Row icon={<Search/>} label="WLAN-Netze" detail="Suchen und verbinden" onClick={() => admin.guard(async () => {try {await call("permission", {name: "standort"}); const r = await call("wifi-scan"); setNets(r.netze || []); setWifi({ssid: "", pass: "", art: "wpa2"});} catch (e) {shell.notify(errorText(e));}})}/>
        <Row icon={<Bluetooth/>} label="Bluetooth" detail={d.bluetooth ? "Eingeschaltet" : "Aus"} right={<Switch on={!!d.bluetooth} onChange={v => admin.guard(async () => {try {await call("permission", {name: "bluetooth"}); set("bluetooth", v);} catch (e) {shell.notify(errorText(e));}})}/>}/>
      </div>
      <div className="group-title">Ton und Anzeige</div>
      <div className="group">
        <div className="slider-row" style={{borderTopLeftRadius: 30, borderTopRightRadius: 30}}><label><Volume2/>Medienlautstärke</label><input type="range" min={0} max={d.maximal} value={d.lautstaerke} style={{"--p": pct(d.lautstaerke, d.maximal)} as React.CSSProperties} onChange={e => {const v = Number(e.target.value); setD({...d, lautstaerke: v}); call("set", {name: "lautstaerke", value: v}).catch(() => {});}}/></div>
        <div className="slider-row" style={{borderBottomLeftRadius: 30, borderBottomRightRadius: 30}}><label><Sun/>Helligkeit</label><input type="range" min={10} max={255} value={d.helligkeit} style={{"--p": pct(d.helligkeit - 10, 245)} as React.CSSProperties} onChange={e => {const v = Number(e.target.value); setD({...d, helligkeit: v}); call("set", {name: "helligkeit", value: v}).catch(err => shell.notify(errorText(err)));}}/></div>
      </div>
      {!d.eigentuemer && <p className="hint" style={{margin: "14px 8px"}}>WLAN, Bluetooth und Helligkeit steuert Jon, sobald der Gerätemodus (Device Owner) eingerichtet ist. Bis dahin nutzt Android seine eigenen Schalter.</p>}
    </div>
    {admin.element}
    <Sheet open={!!wifi} title="WLAN verbinden" onClose={() => setWifi(null)}>
      {wifi && <>
        {nets.length ? nets.slice(0, 20).map(n => <button key={n} className="list-row" onClick={() => setWifi({...wifi, ssid: n})}><Wifi/><span>{n}</span>{wifi.ssid === n && <Check className="check"/>}</button>) : <p className="hint">Keine Netze gefunden. Du kannst den Namen auch eintippen.</p>}
        <Field label="Netzwerkname (SSID)" value={wifi.ssid} onChange={v => setWifi({...wifi, ssid: v})}/>
        <label className="field">Sicherheit<select value={wifi.art} onChange={e => setWifi({...wifi, art: e.target.value})}><option value="wpa2">WPA2</option><option value="wpa3">WPA3</option><option value="offen">Offen</option></select></label>
        {wifi.art !== "offen" && <Field label="Passwort" type="password" value={wifi.pass} onChange={v => setWifi({...wifi, pass: v})}/>}
        <button className="btn primary" disabled={!wifi.ssid.trim()} onClick={() => call("wifi-connect", {ssid: wifi.ssid, passwort: wifi.pass, art: wifi.art}).then(() => {shell.notify("WLAN-Verbindung angefordert."); setWifi(null);}).catch(e => shell.notify(errorText(e)))}>Verbinden</button>
      </>}
    </Sheet>
  </>;
}

export function VoiceSettingsPage({shell, back}: PageProps) {
  const [d, setD] = useState<any>(null), [modell, setModell] = useState<any>(null);
  const load = () => call("device").then(setD).catch(e => shell.notify(errorText(e)));
  useEffect(() => {load();}, []);
  useEffect(() => {
    let aus = false;
    const holen = () => call("sprachmodell").then(v => {if (!aus) setModell(v);}).catch(() => {});
    holen();
    const zeit = setInterval(holen, 1500);
    return () => {aus = true; clearInterval(zeit);};
  }, []);
  const modellText = !modell ? "Jon hört lokal auf sein Aktivierungswort" : modell.bereit ? "Jon hört lokal auf sein Aktivierungswort" : modell.laedt ? `Sprachmodell wird geladen … ${Math.round((modell.fortschritt || 0) * 100)} %` : modell.fehler ? modell.fehler : `Beim Einschalten lädt Jon einmal das Sprachmodell (${modell.groesse_mb || 45} MB)`;
  if (!d) return <><PageHeader title="Sprachmodus" onBack={back}/><Busy/></>;
  return <>
    <PageHeader title="Sprachmodus" onBack={back}/>
    <div className="page-scroll">
      <div className="group">
        <Row icon={<Mic/>} label="Mikrofon" detail={d.rechte?.mikrofon ? "Erlaubt" : "Noch nicht erlaubt"} right={d.rechte?.mikrofon ? <span className="badge ok">Erlaubt</span> : undefined} onClick={() => call("permission", {name: "mikrofon"}).then(load).catch(e => shell.notify(errorText(e)))}/>
        <Row icon={<Sparkles/>} label="„Hey Jon“" detail={modellText} right={<Switch on={!!d.wake} onChange={v => call("set", {name: "wake", value: v}).then(setD).catch(e => shell.notify(errorText(e)))}/>}/>
        <Row icon={<Volume2/>} label="Durch Sprechen unterbrechen" detail="Wie bei Mini Jon: einfach reinreden" right={<Switch on={d.unterbrechen !== false} onChange={v => call("set", {name: "unterbrechen", value: v}).then(setD).catch(e => shell.notify(errorText(e)))}/>}/>
      </div>
      <div className="gap"/>
      <div className="group compact">
        <Row icon={<Volume2/>} label="Stimme testen" onClick={() => call("speak", {text: `Hallo ${shell.name}, ich bin Jon. So klinge ich auf deinem Gerät.`}).catch(e => shell.notify(errorText(e)))}/>
        <Row icon={<Mic/>} label="Gespräch starten" onClick={() => call("voice", {mode: "talk"}).catch(e => shell.notify(errorText(e)))}/>
      </div>
      <p className="hint" style={{margin: "16px 8px"}}>Das Mikrofon in der Eingabezeile wandelt deine Sprache in Text um. Die blaue Taste „Stimme“ startet ein echtes Gespräch mit Jon. Spracherkennung und Stimme laufen über deinen Pi.</p>
    </div>
  </>;
}

export function SecurityPage({shell, back}: PageProps) {
  const [d, setD] = useState<any>(null), [code, setCode] = useState(""), [confirm, setConfirm] = useState(""), [busy, setBusy] = useState(false), [appWahl, setAppWahl] = useState(false);
  const admin = useAdmin(shell.notify);
  const load = () => call("device").then(setD).catch(e => shell.notify(errorText(e)));
  useEffect(() => {load(); const timer = setInterval(load, 4000); return () => clearInterval(timer);}, []);
  if (!d) return <><PageHeader title="Sicherheit" onBack={back}/><Busy/></>;
  const a = d.admin || {};
  const freigegeben: any[] = d.apps?.liste || [];
  const checks = [
    {ok: a.eingerichtet && a.bestaetigt, label: "Admin-PIN und Recovery-Code", hint: "Schützt den Ausgang aus dem Kiosk"},
    {ok: d.pi?.verbunden, label: "Mit dem Pi verbunden", hint: d.pi?.name || "Pi koppeln"},
    {ok: d.eigentuemer, label: "Gerätemodus (Device Owner)", hint: d.eigentuemer ? "Eingerichtet" : "Einmalig per USB am PC"},
    {ok: d.rechte?.mikrofon, label: "Mikrofon", hint: "Für Sprache und „Hey Jon“"}
  ];
  const ready = checks.every(c => c.ok);
  async function kiosk(aktion: string) {
    setBusy(true);
    try {setD(await call("kiosk", {aktion})); haptic("success"); shell.notify(aktion === "an" ? "Kiosk ist aktiv. Nur Jon und deine freigegebenen Apps sind erreichbar." : aktion === "aus" ? "Kiosk verlassen. Jon ist jetzt eine normale App – Zurück oder Home schließt sie, der Samsung-Startbildschirm ist zurück." : "Gerätemodus entfernt.");}
    catch (e) {shell.notify(errorText(e));} finally {setBusy(false); load();}
  }
  return <>
    <PageHeader title="Sicherheit" onBack={back}/>
    <div className="page-scroll">
      <div className="group-title">Verwaltung</div>
      <div className="group">
        <Row icon={<Lock/>} label="Admin-PIN" detail={a.eingerichtet ? (a.frei ? "Entsperrt · tippen zum Ändern" : "Eingerichtet") : "Noch nicht eingerichtet"} onClick={() => {const setup = () => admin.setup(r => {if (r?.code) setCode(r.code); load();}); if (a.eingerichtet) admin.guard(setup); else setup();}}/>
        {a.eingerichtet && !a.frei && <Row icon={<KeyRound/>} label="Verwaltung entsperren" onClick={() => admin.guard(load)}/>}
        {a.frei && <Row icon={<Lock/>} label="Verwaltung sperren" onClick={() => call("admin", {aktion: "sperren"}).then(load)}/>}
        {a.eingerichtet && (a.finger_moeglich || a.fingerabdruck) && <Row icon={<Fingerprint/>} label="Fingerabdruck statt PIN" detail={a.fingerabdruck ? "An · neue Fingerabdrücke schalten ihn ab" : "Schneller in die Verwaltung"} right={<Switch on={!!a.fingerabdruck} onChange={v => admin.guard(() => v ? setConfirm("finger") : call("admin", {aktion: "finger-aus"}).then(() => {load(); shell.notify("Fingerabdruck ist aus.");}).catch(e => shell.notify(errorText(e))))}/>}/>}
        {shell.appsSichtbar && <Row icon={<LayoutGrid/>} label="Apps für Jon" detail={freigegeben.length ? freigegeben.map(x => x.name).join(", ") : "Keine – nur Jon"} onClick={() => admin.guard(() => setAppWahl(true))}/>}
        {shell.appsSichtbar && <Row icon={<EyeOff/>} label="Apps verstecken" detail={shell.conn.apps_versteckt ? "An · sichtbar nur nach dem Entsperren" : "Aus · Apps im Menü sichtbar"} right={<Switch on={!!shell.conn.apps_versteckt} onChange={v => admin.guard(() => call("apps-versteckt", {an: v}).then(r => shell.notify(r.versteckt ? "Apps sind versteckt. Nach dem Sperren der Verwaltung sieht sie niemand mehr." : "Apps sind wieder sichtbar.")).catch(e => shell.notify(errorText(e))))}/>}/>}
      </div>
      <div className="group-title">{shell.appsSichtbar ? "Kiosk · nur Jon und freigegebene Apps" : "Kiosk"}</div>
      <div className="card">{checks.map(c => <div className="stat" key={c.label}><span style={{display: "flex", gap: 10, alignItems: "center", color: "var(--fg)"}}>{c.ok ? <Check color="#3ed598"/> : <span style={{width: 22, height: 22, borderRadius: 11, border: "2px solid var(--muted-2)", display: "inline-block"}}/>}{c.label}</span><b style={{color: "var(--muted)", fontWeight: 500, fontSize: 13}}>{c.hint}</b></div>)}</div>
      <div style={{display: "flex", flexDirection: "column", gap: 10, marginTop: 6}}>
        {d.kiosk ? <button className="btn outline" disabled={busy} onClick={() => admin.guard(() => kiosk("aus"))}><LayoutGrid/>Kiosk kontrolliert verlassen</button>
          : <button className="btn accent" disabled={busy || !ready} onClick={() => admin.guard(() => kiosk("an"))}><ShieldCheck/>Kiosk aktivieren</button>}
        {!d.eigentuemer && <p className="hint">Der Gerätemodus wird einmalig per USB vom PC eingerichtet. Dafür dürfen auf dem Handy kurz keine Konten angemeldet sein – danach kannst du sie wieder hinzufügen.</p>}
      </div>
      <div className="group-title">Freigaben</div>
      <div className="group compact">
        {shell.appsSichtbar && <Row icon={<AppWindow/>} label="Medienzugriff für Amazon Music" detail={d.rechte?.medien ? "Erlaubt" : "Für Play, Pause und Titelanzeige"} onClick={() => admin.guard(() => call("system", {ziel: "medien"}).catch(e => shell.notify(errorText(e))))}/>}
        <Row icon={<Hourglass/>} label="Nutzungszugriff" detail={d.nutzungszugriff ? "Erlaubt · Bildschirmzeit misst genau" : "Für genaue Bildschirmzeit"} onClick={() => admin.guard(() => call("system", {ziel: "nutzung"}).catch(e => shell.notify(errorText(e))))}/>
        <Row icon={<Cloud/>} label="Tailscale" detail={d.tailscale ? (d.vpn ? "Verbunden" : "Installiert · nicht aktiv") : "Nicht installiert"} onClick={() => admin.guard(() => call("system", {ziel: "tailscale"}).catch(e => shell.notify(errorText(e))))}/>
        <Row icon={<Link2/>} label="Verbindungen" detail={d.pi?.name || "Nicht gekoppelt"} onClick={() => shell.push(shell.conn.paired ? "server" : "pair")}/>
        <Row icon={<Settings/>} label="Android-Einstellungen" detail="Nur außerhalb des Kiosk" onClick={() => admin.guard(() => call("system", {ziel: "einstellungen"}).catch(e => shell.notify(errorText(e))))}/>
      </div>
      {d.eigentuemer && !d.kiosk && <><div className="group-title">Wiederherstellung</div><div className="group compact"><Row icon={<LogOut/>} label="Gerätemodus entfernen" tone="danger" chevron={false} onClick={() => admin.guard(() => setConfirm("owner"))}/></div></>}
    </div>
    {admin.element}
    <Sheet open={!!code} title="Dein Recovery-Code" onClose={() => {}}>
      <p>Schreib diesen Code auf und bewahre ihn außerhalb des Geräts auf. Mit ihm kommst du in die Verwaltung, falls du die PIN vergisst. Er wird nur jetzt angezeigt.</p>
      <div className="code-box">{code}</div>
      <button className="btn primary" onClick={() => call("admin", {aktion: "bestaetigen"}).then(() => {setCode(""); load(); haptic("success");}).catch(e => shell.notify(errorText(e)))}>Ich habe den Code sicher notiert</button>
    </Sheet>
    <AppWahl open={appWahl} onClose={() => {setAppWahl(false); load();}} notify={shell.notify}/>
    <Sheet open={confirm === "finger"} title="Fingerabdruck statt PIN" onClose={() => setConfirm("")}>
      <p>Jeder Fingerabdruck, der in den Android-Einstellungen dieses Handys gespeichert ist, kann dann die Verwaltung öffnen.</p>
      <div className="banner warn-banner"><ShieldAlert/><div><strong>Nur für Eltern-Finger</strong><p>Schalte das nur ein, wenn auf diesem Handy ausschließlich Fingerabdrücke von Erwachsenen gespeichert sind. Kommt später ein neuer dazu, schaltet Jon den Fingerabdruck automatisch ab.</p></div></div>
      <button className="btn primary" style={{marginTop: 16}} onClick={async () => {setConfirm(""); try {const r = await call("admin", {aktion: "finger-an"}, 120_000); load(); shell.notify(r.ok ? "Fingerabdruck ist an." : "Nicht eingeschaltet.");} catch (e) {shell.notify(errorText(e));}}}><Fingerprint/>Finger auflegen</button>
    </Sheet>
    <Sheet open={confirm === "owner"} title="Gerätemodus entfernen?" onClose={() => setConfirm("")}>
      <p>Jon ist dann nicht mehr Geräteverwalter. Der Kiosk lässt sich erst wieder einschalten, wenn der Gerätemodus neu eingerichtet wird.</p>
      <button className="btn danger" onClick={() => {setConfirm(""); kiosk("entfernen");}}>Entfernen</button>
    </Sheet>
  </>;
}

export function PairPage({shell, back}: PageProps) {
  const [address, setAddress] = useState(""), [code, setCode] = useState(""), [status, setStatus] = useState(""), [busy, setBusy] = useState(false);
  const admin = useAdmin(shell.notify);
  useEffect(() => listen("pairing", v => setStatus(v?.text || "")), []);
  async function pair(data: Record<string, unknown>) {
    setBusy(true);
    setStatus("Pi suchen …");
    const schonVerbunden = !!shell.conn.paired;
    try {const r = await call("pair", data, 200_000); haptic("success"); setStatus(`Mit ${r.name || "deinem Pi"} verbunden.`); shell.notify("Verbunden."); setTimeout(() => schonVerbunden ? location.reload() : back(), 900);}
    catch (e) {setStatus(errorText(e)); haptic("error");} finally {setBusy(false);}
  }
  return <>
    <PageHeader title={shell.conn.paired ? "Weiteren Jon verbinden" : "Mit Jon verbinden"} onBack={back}/>
    <div className="page-scroll">
      <div className="remote" style={{padding: "0 0 16px"}}><QrCode/><h1>{shell.conn.paired ? "Noch ein Jon dazu" : "Mit deinem Jon verbinden"}</h1><p style={{margin: "8px 0 0"}}>{shell.conn.paired ? `Öffne auf dem anderen PC oder Pi „Jon-Gerät einrichten“ und scanne den QR-Code. ${shell.conn.name || "Der bisherige Jon"} bleibt gespeichert.` : "Öffne in Jon am PC oder Pi „Jon-Gerät einrichten“ und scanne den QR-Code."}</p></div>
      {status && <div className="card" style={{textAlign: "center"}}>{busy && <RefreshCw className="spin" style={{marginBottom: 8}}/>}<p style={{margin: 0}}>{status}</p></div>}
      <div style={{display: "flex", flexDirection: "column", gap: 10}}>
        <button className="btn primary" disabled={busy} onClick={() => admin.guard(() => pair({art: "qr"}))}><QrCode/>QR-Code scannen</button>
      </div>
      <div className="group-title">Oder von Hand</div>
      <Field label="Adresse des Pi" value={address} onChange={setAddress} placeholder="100.x.x.x oder felworks.tailnet.ts.net"/>
      <Field label="Kopplungscode" value={code} onChange={v => setCode(v.toUpperCase())} placeholder="XXXX-XXXX-XXXX"/>
      <button className="btn soft" disabled={busy || !address.trim() || !code.trim()} onClick={() => admin.guard(() => pair({art: "code", adresse: address.trim(), code: code.trim()}))}>Verbinden</button>
    </div>
    {admin.element}
  </>;
}
