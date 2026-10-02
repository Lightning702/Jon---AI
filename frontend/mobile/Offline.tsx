import React, {useEffect, useState} from "react";
import {motion} from "framer-motion";
import {Check, Cloud, Cpu, Database, Download, Feather, HardDrive, Image as ImageIcon, KeyRound, Link2, Mic, PiggyBank, RefreshCw, Server, Smartphone, Sparkles, Trash2, Wifi, Wrench, X, Zap} from "lucide-react";
import {call, haptic} from "./bridge";
import {PageProps} from "./Pages";
import {useAdmin} from "./Settings";
import {Busy, Field, PageHeader, Row, Sheet, Switch, errorText, spring} from "./ui";

const gb = (b: number) => `${(b / 1_000_000_000).toFixed(b >= 10_000_000_000 ? 0 : 1).replace(".", ",")} GB`;
const phaseText: Record<string, string> = {aus: "Nicht geladen", laedt: "Wird gestartet …", bereit: "Bereit", antwortet: "Denkt nach …", fehler: "Fehler"};

export function OfflinePage({shell, back}: PageProps) {
  const [d, setD] = useState<any>(null), [token, setToken] = useState<string | null>(null), [busy, setBusy] = useState("");
  const admin = useAdmin(shell.notify);
  const laden = () => call("ki-katalog").then(setD).catch(e => shell.notify(errorText(e)));
  useEffect(() => {
    laden();
    const t = setInterval(() => laden(), 1500);
    return () => clearInterval(t);
  }, []);
  async function aktion(op: string, daten: any = {}, text = "") {
    setBusy(op + (daten.name || ""));
    try {setD(await call(op, daten, 120_000)); haptic("success"); if (text) shell.notify(text);}
    catch (e) {shell.notify(errorText(e));} finally {setBusy("");}
  }
  if (!d) return <><PageHeader title="Offline-KI" onBack={back}/><Busy/></>;
  const modelle: any[] = d.modelle || [];
  const fertige = modelle.filter(m => m.status === "fertig");
  return <>
    <PageHeader title="Offline-KI" onBack={back} right={<button className="circle" aria-label="Liste aktualisieren" onClick={() => aktion("ki-aktualisieren", {}, "Modellliste aktualisiert.")}><RefreshCw className={busy === "ki-aktualisieren" ? "spin" : ""}/></button>}/>
    <div className="page-scroll">
      <motion.div className="offline-held" initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={spring}>
        <span className="chip-icon"><Cpu/></span>
        <h2>Jon ohne Internet</h2>
        <p>Die Modelle aus Googles AI Edge Gallery laufen direkt auf deinem Handy. Keine Daten verlassen das Gerät.</p>
        <div className="offline-werte"><span><Smartphone/>{String(d.ram).replace(".", ",")} GB RAM</span><span><Database/>{gb(d.belegt || 0)} belegt</span><span><HardDrive/>{gb(d.frei || 0)} frei</span><span className={`phase ${d.ki?.phase}`}>{phaseText[d.ki?.phase] || "Nicht geladen"}{d.ki?.backend ? ` · ${d.ki.backend}` : ""}</span></div>
        {fertige.length > 0 && <button className="btn primary" style={{marginTop: 14}} onClick={() => {const m = d.standard || fertige[0].name; shell.chats.create("chat"); shell.chats.update({provider: "handy", model: m}); back();}}><Sparkles/>Offline-Chat starten</button>}
      </motion.div>
      {modelle.map((m, i) => {
        const laeuft = m.status === "laedt" || m.status === "pausiert";
        const anteil = m.gesamt ? m.geladen / m.gesamt : 0;
        return <motion.div key={m.name} className={`card modell ${m.status}`} initial={{opacity: 0, y: 14}} animate={{opacity: 1, y: 0}} transition={{...spring, delay: i * .04}}>
          <div className="zeile"><strong>{m.titel}</strong><span className="grow"/>{d.standard === m.name && m.status === "fertig" && <span className="badge ok"><Check size={13}/>Standard</span>}<span className="muted small">{gb(m.groesse)}</span></div>
          <p className="small muted" style={{margin: "6px 0 10px"}}>{m.beschreibung}</p>
          <div className="marken">
            {m.bild && <span><ImageIcon/>Bilder</span>}{m.audio && <span><Mic/>Sprache</span>}{m.werkzeuge && <span><Wrench/>Werkzeuge</span>}
            <span className={m.passt === "passt" ? "gut" : m.passt === "knapp" ? "knapp" : "schlecht"}>{m.passt === "passt" ? "Passt aufs Handy" : m.passt === "knapp" ? "Knapp" : `Braucht ${m.ram} GB RAM`}</span>
            {m.groesse > 0 && m.groesse <= 1_000_000_000 && <span className="gut"><Feather/>Sparsam</span>}
            {m.geschuetzt && <span className="knapp"><KeyRound/>Schlüssel nötig</span>}
          </div>
          {laeuft && <><div className="progress"><i style={{width: `${Math.max(2, anteil * 100)}%`}}/></div><small className="muted">{gb(m.geladen)} von {gb(m.gesamt)}{m.status === "pausiert" ? " · wartet auf WLAN" : ""}</small></>}
          {m.fehler && <p className="error-text small">{m.fehler}</p>}
          <div className="modell-knoepfe">
            {m.status === "fehlt" || m.status === "fehler" ? <button className="btn soft" disabled={!!busy} onClick={() => m.geschuetzt && !d.token ? admin.guard(() => setToken("")) : aktion("ki-laden", {name: m.name}, `${m.titel} wird geladen.`)}><Download/>{m.status === "fehler" ? "Nochmal" : "Laden"}</button> : null}
            {laeuft && <button className="btn soft" onClick={() => aktion("ki-abbrechen", {name: m.name}, "Abgebrochen.")}><X/>Abbrechen</button>}
            {m.status === "fertig" && d.standard !== m.name && <button className="btn soft" onClick={() => aktion("ki-standard", {name: m.name}, `${m.titel} ist jetzt Standard.`)}><Check/>Als Standard</button>}
            {m.status === "fertig" && <button className="btn danger" onClick={() => admin.guard(() => aktion("ki-loeschen", {name: m.name}, `${m.titel} gelöscht.`))}><Trash2/></button>}
          </div>
        </motion.div>;
      })}
      <div className="group" style={{marginTop: 18}}>
        <Row icon={<PiggyBank/>} label="Speicher sparen" detail={d.sparsam ? "An · Jon behält nur ein Offline-Modell" : "Aus · mehrere Modelle erlaubt"} right={<Switch on={!!d.sparsam} onChange={v => admin.guard(() => aktion("ki-sparsam", {an: v}, v ? "Jon behält jetzt nur das Standardmodell." : "Mehrere Modelle erlaubt."))}/>}/>
        {fertige.length > 1 && <Row icon={<Trash2/>} label="Nur Standard behalten" detail={`${gb(fertige.filter((m: any) => m.name !== d.standard).reduce((s: number, m: any) => s + (m.groesse || 0), 0))} frei machen`} onClick={() => admin.guard(() => aktion("ki-aufraeumen", {}, "Andere Modelle gelöscht."))}/>}
        <Row icon={<Wifi/>} label="Auch über mobile Daten" detail="Sonst nur im WLAN" right={<Switch on={!!d.mobil} onChange={v => aktion("ki-mobil", {an: v})}/>}/>
        <Row icon={<KeyRound/>} label="Hugging-Face-Schlüssel" detail={d.token ? "Hinterlegt" : "Für Gemma 3n und Gemma 3 1B"} onClick={() => admin.guard(() => setToken(""))}/>
      </div>
      <p className="hint" style={{margin: "18px 8px"}}>Gemma 4 E2B kann am meisten: Text, Bilder und Sprache – braucht aber 2,6 GB. Wenig Platz? Gemma 3 1B braucht nur 0,6 GB. Große Modelle laden am besten über Nacht am Ladekabel.</p>
    </div>
    {admin.element}
    <Sheet open={token !== null} title="Hugging-Face-Schlüssel" onClose={() => setToken(null)}>
      <p>Manche Modelle von Google gibt es nur nach Zustimmung zur Lizenz. Melde dich auf huggingface.co an, akzeptiere die Gemma-Lizenz und erstelle unter Settings → Access Tokens einen Schlüssel (Lesen reicht).</p>
      <Field label="Schlüssel" type="password" value={token || ""} onChange={setToken} placeholder="hf_…"/>
      <button className="btn primary" onClick={() => aktion("ki-token", {token: token || ""}, token ? "Schlüssel gespeichert." : "Schlüssel entfernt.").then(() => setToken(null))}>Speichern</button>
    </Sheet>
  </>;
}

export function SoloPage({shell, back}: PageProps) {
  const [d, setD] = useState<any>(null), [wahl, setWahl] = useState<any>(null), [schluessel, setSchluessel] = useState(""), [modelle, setModelle] = useState<string[]>([]), [modell, setModell] = useState(""), [basis, setBasis] = useState(""), [busy, setBusy] = useState(false), [lokal, setLokal] = useState<any>(null);
  const admin = useAdmin(shell.notify);
  const laden = () => {call("solo").then(setD).catch(e => shell.notify(errorText(e))); call("ki-katalog").then(setLokal).catch(() => {});};
  useEffect(() => {laden();}, []);
  async function setzen(daten: any, text = "") {
    setBusy(true);
    try {setD(await call("solo-setzen", {daten})); haptic("success"); if (text) shell.notify(text); shell.refreshWeg();}
    catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}
  }
  async function modelleLaden(id: string) {
    setModelle([]);
    try {const r = await call("solo-modelle", {anbieter: id}, 40_000); setModelle(r.modelle || []);} catch (e) {shell.notify(errorText(e));}
  }
  async function speichern() {
    setBusy(true);
    try {
      if (wahl.id === "eigener") await call("solo-setzen", {daten: {basis}});
      if (schluessel.trim()) await call("solo-schluessel", {anbieter: wahl.id, schluessel: schluessel.trim()});
      if (modell) await call("solo-setzen", {daten: {fuer: wahl.id, modell}});
      setD(await call("solo-setzen", {daten: {anbieter: wahl.id}}));
      haptic("success");
      shell.notify(`${wahl.name} ist bereit.`);
      setSchluessel("");
      shell.refreshWeg();
      await modelleLaden(wahl.id);
    } catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}
  }
  if (!d) return <><PageHeader title="Auf Jon verzichten" onBack={back}/><Busy/></>;
  const hatLokal = !!lokal?.standard;
  return <>
    <PageHeader title="Auf Jon verzichten" onBack={back}/>
    <div className="page-scroll">
      <motion.div className={`solo-held ${d.an ? "an" : ""}`} initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={spring}>
        <div className="zeile"><span className="chip-icon">{d.an ? <Smartphone/> : <Server/>}</span><div><strong>{d.an ? "Jon läuft auf diesem Handy" : "Jon läuft über deinen PC oder Pi"}</strong><small>{d.an ? "Mit deinem eigenen Zugang – ganz ohne PC." : "Standard. Schalte um, wenn du keinen PC hast."}</small></div><span className="grow"/><Switch on={!!d.an} onChange={v => admin.guard(() => setzen({an: v}, v ? "Jon nutzt jetzt deinen eigenen Zugang." : "Jon nutzt wieder deinen PC oder Pi."))}/></div>
        {shell.conn.paired && <p className="small" style={{margin: "12px 0 0", color: "var(--fg-2)"}}><Link2 size={14} style={{verticalAlign: -2}}/> Du bleibst mit {shell.conn.name || "deinem Pi"} verbunden. Durchsagen, Bildschirmzeit, Dateien und Jon Chat laufen weiter darüber.</p>}
      </motion.div>
      <div className="group-title">Welche KI?</div>
      <div className="group">
        <Row icon={<Cpu/>} label="Offline auf dem Handy" detail={hatLokal ? `Mit ${lokal.modelle?.find((m: any) => m.name === lokal.standard)?.titel || lokal.standard} · ohne Internet` : "Erst ein Modell laden"} right={d.anbieter === "handy" ? <span className="badge ok">Aktiv</span> : undefined} onClick={() => hatLokal ? admin.guard(() => setzen({anbieter: "handy"}, "Jon antwortet offline.")) : shell.push("offline")}/>
        {(d.liste || []).map((a: any) => <Row key={a.id} icon={a.id === "eigener" ? <Server/> : <Cloud/>} label={a.name} detail={a.verbunden ? `Verbunden · ${a.modell || "Modell wählen"}` : "Schlüssel hinzufügen"}
          right={d.anbieter === a.id ? <span className="badge ok">Aktiv</span> : a.verbunden ? <span className="badge">Bereit</span> : undefined}
          onClick={() => admin.guard(() => {setWahl(a); setSchluessel(""); setModell(a.modell || ""); setBasis(a.basis || ""); setModelle([]); if (a.verbunden) modelleLaden(a.id);})}/>)}
      </div>
      <div className="banner" style={{marginTop: 18}}><Zap style={{color: "#9fbcff"}}/><div><strong>Was geht ohne PC?</strong><p>Chat und Work, Websites bauen und ansehen, Wecker, Timer, Wetter, Websuche, Fitness, Fotos, Dateien und Sprache verstehen, Podcasts – und mit OpenAI, Gemini oder xAI auch Bilder malen. Programme am PC steuern geht nur mit Jon am PC.</p></div></div>
    </div>
    {admin.element}
    <Sheet open={!!wahl} title={wahl?.name || ""} onClose={() => setWahl(null)}>
      {wahl && <>
        {wahl.seite && <p className="hint">Deinen Schlüssel bekommst du unter <b>{wahl.seite}</b>. Er bleibt verschlüsselt auf diesem Handy.</p>}
        {wahl.id === "eigener" && <Field label="Adresse (OpenAI-kompatibel)" value={basis} onChange={setBasis} placeholder="http://192.168.1.20:11434/v1"/>}
        <Field label={wahl.id === "eigener" ? "Schlüssel (optional)" : "API-Schlüssel"} type="password" value={schluessel} onChange={setSchluessel} placeholder={wahl.verbunden ? "••••••••••" : "sk-…"}/>
        {modelle.length > 0 && <label className="field">Modell<select value={modell} onChange={e => setModell(e.target.value)}>{modelle.map(m => <option key={m} value={m}>{m}</option>)}</select></label>}
        {!modelle.length && wahl.verbunden && <Field label="Modell" value={modell} onChange={setModell}/>}
        <button className="btn primary" disabled={busy || (!schluessel.trim() && !wahl.verbunden && wahl.id !== "eigener")} onClick={speichern}>{busy ? <RefreshCw className="spin"/> : <Check/>}{wahl.verbunden ? "Speichern und verwenden" : "Verbinden"}</button>
        {wahl.verbunden && <button className="btn danger" style={{marginTop: 10}} onClick={() => call("solo-schluessel", {anbieter: wahl.id, schluessel: ""}).then(v => {setD(v); setWahl(null); shell.notify("Schlüssel entfernt."); shell.refreshWeg();}).catch(e => shell.notify(errorText(e)))}><Trash2/>Schlüssel entfernen</button>}
      </>}
    </Sheet>
  </>;
}
