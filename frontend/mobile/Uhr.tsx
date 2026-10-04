import React, {useEffect, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {AlarmClock, Plus, Timer, Trash2, X} from "lucide-react";
import {call, haptic} from "./bridge";
import {PageProps} from "./Pages";
import {Busy, Circle, Empty, Field, PageHeader, Sheet, Switch, errorText, spring} from "./ui";

const tage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const schnell = [1, 3, 5, 10, 15, 20, 30, 45, 60];

function tageText(liste: number[]) {
  if (!liste?.length) return "Einmalig";
  if (liste.length === 7) return "Täglich";
  if (liste.length === 5 && [1, 2, 3, 4, 5].every(t => liste.includes(t))) return "Wochentags";
  if (liste.length === 2 && liste.includes(6) && liste.includes(7)) return "Am Wochenende";
  return liste.map(t => tage[t - 1]).join(", ");
}

function dauer(ms: number) {
  const s = Math.max(0, Math.ceil(ms / 1000));
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), sek = s % 60;
  return `${h ? `${h}:` : ""}${String(m).padStart(h ? 2 : 1, "0")}:${String(sek).padStart(2, "0")}`;
}

export function UhrPage({shell, back}: PageProps) {
  const [d, setD] = useState<any>(null), [tab, setTab] = useState("wecker"), [neu, setNeu] = useState<any>(null), [minuten, setMinuten] = useState(""), [jetzt, setJetzt] = useState(Date.now()), [basis, setBasis] = useState(0);
  const laden = () => call("uhren").then(v => {setD(v); setBasis(Date.now());}).catch(e => shell.notify(errorText(e)));
  useEffect(() => {laden(); const t = setInterval(laden, 10_000); const u = setInterval(() => setJetzt(Date.now()), 250); return () => {clearInterval(t); clearInterval(u);};}, []);
  async function aktion(op: string, daten: any, text = "") {
    try {const v = await call(op, daten); setD(v); setBasis(Date.now()); haptic("success"); if (text) shell.notify(text);}
    catch (e) {shell.notify(errorText(e));}
  }
  if (!d) return <><PageHeader title="Wecker & Timer" onBack={back}/><Busy/></>;
  const wecker: any[] = d.wecker || [], timer: any[] = d.timer || [];
  const vergangen = jetzt - basis;
  return <>
    <PageHeader title="Wecker & Timer" onBack={back} right={<Circle label="Neu" onClick={() => tab === "wecker" ? setNeu({stunde: 7, minute: 0, zeit: "07:00", tage: [1, 2, 3, 4, 5], name: ""}) : setTab("timer")}><Plus/></Circle>}/>
    <div className="tabs">{[["wecker", "Wecker"], ["timer", "Timer"]].map(([id, label]) => <button key={id} className={tab === id ? "on" : ""} onClick={() => {haptic("tick"); setTab(id);}}>{tab === id && <motion.span layoutId="uhrtab" className="tab-bg" transition={spring}/>}<span>{label}</span></button>)}</div>
    <div className="page-scroll">
      {tab === "wecker" ? <>
        {d.naechster && <p className="hint" style={{margin: "0 8px 14px"}}>{`Nächster Wecker: ${d.naechster} Uhr`}</p>}
        {!wecker.length && <Empty icon={<AlarmClock/>} title="Noch kein Wecker" text="Tippe auf Plus oder sag Jon über „Stimme“: „Weck mich um halb sieben.“"/>}
        <AnimatePresence initial={false}>{wecker.map(w => <motion.div key={w.id} layout className={`wecker ${w.an ? "" : "aus"}`} initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, x: -40}} transition={spring}>
          <button className="wecker-text" onClick={() => setNeu({...w, zeit: `${String(w.stunde).padStart(2, "0")}:${String(w.minute).padStart(2, "0")}`})}>
            <strong>{String(w.stunde).padStart(2, "0")}:{String(w.minute).padStart(2, "0")}</strong>
            <small>{[w.name, tageText(w.tage), w.an && w.naechsterText ? `klingelt ${w.naechsterText}` : ""].filter(Boolean).join(" · ")}</small>
          </button>
          <Switch on={!!w.an} onChange={v => aktion("wecker-setzen", {wecker: {...w, an: v}}, v ? "Wecker an." : "Wecker aus.")}/>
        </motion.div>)}</AnimatePresence>
      </> : <>
        <div className="timer-schnell">{schnell.map((m, i) => <motion.button key={m} initial={{opacity: 0, scale: .9}} animate={{opacity: 1, scale: 1}} transition={{delay: i * .03}} onClick={() => aktion("timer-starten", {sekunden: m * 60}, `Timer läuft: ${m} Min.`)}><Timer/><span>{m}<small>Min.</small></span></motion.button>)}</div>
        <div className="timer-eigen"><Field label="Eigene Dauer in Minuten" type="number" value={minuten} onChange={setMinuten} placeholder="z. B. 12"/><button className="btn primary" disabled={!Number(minuten)} onClick={() => {aktion("timer-starten", {sekunden: Math.round(Number(minuten) * 60)}, "Timer läuft."); setMinuten("");}}>Start</button></div>
        {timer.length > 0 && <div className="group-title">Läuft</div>}
        <AnimatePresence initial={false}>{timer.map(t => {
          const rest = Math.max(0, (t.rest || 0) - vergangen);
          const anteil = t.dauer ? rest / (t.dauer * 1000) : 0;
          return <motion.div key={t.id} layout className="timer-laeuft" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, scale: .95}} transition={spring}>
            <div className="timer-balken" style={{width: `${anteil * 100}%`}}/>
            <strong>{dauer(rest)}</strong><small>{t.name || "Timer"}</small>
            <button aria-label="Timer abbrechen" onClick={() => aktion("timer-abbrechen", {timer: t.id}, "Timer abgebrochen.")}><X/></button>
          </motion.div>;
        })}</AnimatePresence>
        {!timer.length && <p className="hint" style={{textAlign: "center", marginTop: 20}}>Oder sag Jon über „Stimme“: „Timer zehn Minuten.“</p>}
      </>}
    </div>
    <Sheet open={!!neu} title={neu?.id ? "Wecker bearbeiten" : "Neuer Wecker"} onClose={() => setNeu(null)}>
      {neu && <>
        <input className="zeit-eingabe" type="time" value={neu.zeit} onChange={e => setNeu({...neu, zeit: e.target.value})}/>
        <div className="field"><span>Wiederholen</span><div className="chips klein">{tage.map((t, i) => {const n = i + 1; const an = (neu.tage || []).includes(n); return <button key={t} className={`chip ${an ? "on" : ""}`} onClick={() => setNeu({...neu, tage: an ? neu.tage.filter((x: number) => x !== n) : [...(neu.tage || []), n].sort()})}>{t}</button>;})}</div></div>
        <Field label="Name (optional)" value={neu.name || ""} onChange={v => setNeu({...neu, name: v})} placeholder="Schule, Training …"/>
        <button className="btn primary" onClick={() => {const [h, m] = String(neu.zeit || "07:00").split(":").map(Number); aktion("wecker-setzen", {wecker: {id: neu.id, stunde: h, minute: m, tage: neu.tage, name: neu.name, an: true}}).then(() => {shell.notify("Wecker gestellt."); setNeu(null);});}}>Speichern</button>
        {neu.id && <button className="btn danger" style={{marginTop: 10}} onClick={() => aktion("wecker-loeschen", {wecker: neu.id}, "Wecker gelöscht.").then(() => setNeu(null))}><Trash2/>Löschen</button>}
      </>}
    </Sheet>
  </>;
}
