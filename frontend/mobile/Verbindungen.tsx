import React, {useEffect, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {Check, Plus, RefreshCw, Server, Trash2, Waypoints, Zap} from "lucide-react";
import {call, haptic, listen} from "./bridge";
import {PageProps} from "./Pages";
import {useAdmin} from "./Settings";
import {Busy, Circle, PageHeader, Row, Sheet, Switch, errorText, spring} from "./ui";

type Eintrag = {id: string; name: string; adresse: string; aktiv: boolean; erreichbar: boolean | null};

const kurz = (adresse: string) => adresse.replace(/^https?:\/\//, "").replace(/:8756\/?$/, "");

export function ServerPage({shell, back}: PageProps) {
  const [liste, setListe] = useState<Eintrag[] | null>(null), [automatisch, setAutomatisch] = useState(true), [pruefe, setPruefe] = useState(false), [weg, setWeg] = useState<Eintrag | null>(null), [busy, setBusy] = useState("");
  const admin = useAdmin(shell.notify);
  const uebernehmen = (r: any) => {if (Array.isArray(r?.liste)) setListe(r.liste); if (typeof r?.automatisch === "boolean") setAutomatisch(r.automatisch);};
  async function pruefen() {
    setPruefe(true);
    try {uebernehmen(await call("server-pruefen", {}, 60_000));}
    catch (e) {shell.notify(errorText(e));}
    finally {setPruefe(false);}
  }
  useEffect(() => {call("server").then(uebernehmen).catch(e => shell.notify(errorText(e))); void pruefen();}, []);
  useEffect(() => listen("connection", () => {call("server").then(uebernehmen).catch(() => {});}), []);
  async function wechseln(e: Eintrag) {
    setBusy(e.id);
    try {await call("server-wechseln", {id: e.id}, 60_000); haptic("success"); shell.notify(`Jon nutzt jetzt ${e.name}.`); setTimeout(() => location.reload(), 500);}
    catch (err) {shell.notify(errorText(err));}
    finally {setBusy("");}
  }
  async function entfernen(e: Eintrag) {
    setWeg(null);
    setBusy(e.id);
    try {uebernehmen(await call("server-entfernen", {id: e.id}, 30_000)); haptic("success"); shell.notify(`${e.name} entfernt.`); if (e.aktiv) setTimeout(() => location.reload(), 500);}
    catch (err) {shell.notify(errorText(err));}
    finally {setBusy("");}
  }
  const status = (e: Eintrag) => e.aktiv ? (e.erreichbar ? "Aktiv · verbunden" : "Aktiv · gerade nicht erreichbar") : e.erreichbar === true ? "Erreichbar" : e.erreichbar === false ? "Nicht erreichbar" : "Wird geprüft …";
  return <>
    <PageHeader title="Verbindungen" onBack={back} right={<Circle label="Prüfen" onClick={() => {haptic("tick"); void pruefen();}}><RefreshCw className={pruefe ? "spin" : ""}/></Circle>}/>
    <div className="page-scroll">
      <motion.div className="server-held" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={spring}>
        <span className="chip-icon"><Waypoints/></span>
        <div><strong>Mehrere Jons, ein Handy</strong><small>Verbinde das Handy zum Beispiel mit dem Pi und deinem PC. Fällt einer aus, springt es zum nächsten.</small></div>
      </motion.div>
      {liste === null ? <Busy/> : <div className="server-liste">
        <AnimatePresence initial={false}>{liste.map((e, i) => <motion.div layout key={e.id} className={`card server-karte ${e.aktiv ? "aktiv" : ""}`} initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, x: -30}} transition={{...spring, delay: .05 * i}}>
          <div className="server-kopf">
            <span className="server-symbol"><Server/><i className={`server-punkt ${e.erreichbar === true ? "an" : e.erreichbar === false ? "aus" : "offen"}`}/></span>
            <div className="server-text"><strong>{e.name}</strong><small>{status(e)}{e.adresse ? ` · ${kurz(e.adresse)}` : ""}</small></div>
            {e.aktiv && <span className="badge ok"><Check/>Aktiv</span>}
          </div>
          <div className="server-knoepfe">
            {!e.aktiv && <button className="btn soft server-wechsel" disabled={!!busy} onClick={() => admin.guard(() => void wechseln(e))}>{busy === e.id ? <RefreshCw className="spin"/> : <Zap/>}Wechseln</button>}
            <button className="text-link small server-weg" disabled={!!busy} onClick={() => admin.guard(() => setWeg(e))}><Trash2 size={15}/>Entfernen</button>
          </div>
        </motion.div>)}</AnimatePresence>
      </div>}
      <button className="btn primary" style={{marginTop: 14}} onClick={() => shell.push("pair")}><Plus/>Weiteren Jon verbinden</button>
      <div className="group-title">Ausfall</div>
      <div className="group">
        <Row icon={<RefreshCw/>} label="Automatisch wechseln" detail="Wenn der aktive Jon nicht antwortet" right={<Switch on={automatisch} onChange={v => admin.guard(async () => {try {const r = await call("server-automatisch", {an: v}); setAutomatisch(!!r.automatisch);} catch (err) {shell.notify(errorText(err));}})}/>}/>
      </div>
      <p className="hint" style={{margin: "12px 8px 0"}}>Jeder Jon hat eigene Chats und Dateien. Durchsagen, Bildschirmzeit und SOS laufen immer über den aktiven Jon.</p>
    </div>
    {admin.element}
    <Sheet open={!!weg} title={`${weg?.name || "Jon"} entfernen?`} onClose={() => setWeg(null)}>
      <p>{weg?.aktiv ? "Das Handy vergisst den Schlüssel zu diesem Jon und wechselt zum nächsten gespeicherten." : "Das Handy vergisst den Schlüssel zu diesem Jon. Zum Wiederverbinden brauchst du einen neuen QR-Code."}</p>
      <button className="btn danger" onClick={() => {if (weg) void entfernen(weg);}}><Trash2/>Entfernen</button>
    </Sheet>
  </>;
}
