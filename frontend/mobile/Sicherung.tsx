import React, {useEffect, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {Archive, CloudUpload, Download, FolderOpen, History, RefreshCw, Upload} from "lucide-react";
import {call, haptic, native} from "./bridge";
import {PageProps} from "./Pages";
import {useAdmin} from "./Settings";
import {Busy, PageHeader, Row, Sheet, Switch, errorText, spring} from "./ui";

function wann(ms: number) {
  if (!ms) return "noch nie";
  const minuten = Math.round((Date.now() - ms) / 60_000);
  if (minuten < 2) return "gerade eben";
  if (minuten < 60) return `vor ${minuten} Min.`;
  if (minuten < 60 * 24) return `vor ${Math.round(minuten / 60)} Std.`;
  return new Date(ms).toLocaleDateString("de-DE", {day: "numeric", month: "long"});
}

export function SicherungPage({shell, back}: PageProps) {
  const [d, setD] = useState<any>(null), [fortschritt, setFortschritt] = useState(""), [waehlen, setWaehlen] = useState<any>(null);
  const admin = useAdmin(shell.notify);
  const pi = !!shell.conn.connected;
  const laden = () => call("sicherung", {}, 60_000).then(setD).catch(e => {shell.notify(errorText(e)); setD({stand: {}, liste: []});});
  useEffect(() => {laden();}, []);
  async function jetzt() {
    setFortschritt("Starte …");
    try {
      await native("sicherung-jetzt", {}, teil => setFortschritt(teil?.fortschritt || ""), 20 * 60_000).promise;
      haptic("success");
      shell.notify("Gesichert.");
      laden();
    } catch (e) {shell.notify(errorText(e));} finally {setFortschritt("");}
  }
  async function einspielen(name: string) {
    setWaehlen(null);
    setFortschritt("Hole die Sicherung …");
    try {await native("sicherung-einspielen", {name}, teil => setFortschritt(teil?.fortschritt || ""), 20 * 60_000).promise;}
    catch (e) {shell.notify(errorText(e)); setFortschritt("");}
  }
  const liste: any[] = d?.liste || [];
  return <>
    <PageHeader title="Sicherung" onBack={back}/>
    <div className="page-scroll">
      <motion.div className="sicherung-held" initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={spring}>
        <span className="chip-icon"><Archive/></span>
        <div><strong>{d?.stand?.zuletzt ? "Deine Daten sind gesichert" : "Deine Daten sind noch nicht gesichert"}</strong><small>Letzte Sicherung: {wann(d?.stand?.zuletzt || 0)}</small></div>
      </motion.div>
      <p className="hint" style={{margin: "0 6px 14px"}}>Gesichert werden Chats auf dem Handy, Erinnerungen, Fitness, Wecker, Regeln, Profil und Jons Arbeitsordner. Schlüssel und Offline-Modelle bleiben draußen.</p>
      <AnimatePresence>{fortschritt && <motion.div className="card" initial={{opacity: 0, height: 0}} animate={{opacity: 1, height: "auto"}} exit={{opacity: 0, height: 0}}><p className="small" style={{margin: 0, display: "flex", gap: 8, alignItems: "center"}}><RefreshCw className="spin" size={16}/>{fortschritt}</p></motion.div>}</AnimatePresence>
      {shell.conn.paired && <>
        <div className="group-title">Auf deinem PC oder Pi</div>
        <div className="group">
          <Row icon={<CloudUpload/>} label="Jetzt sichern" detail={pi ? "Verschlüsselt übertragen, die letzten 10 bleiben" : "Gerade nicht verbunden"} onClick={() => pi && !fortschritt && jetzt()}/>
          <Row icon={<History/>} label="Täglich automatisch" detail="Einmal am Tag, wenn Jon verbunden ist" right={<Switch on={d?.stand?.automatisch !== false} onChange={v => call("sicherung-automatisch", {an: v}).then(stand => setD((alt: any) => ({...alt, stand})))}/>}/>
        </div>
        {d === null ? <Busy/> : liste.length > 0 && <>
          <div className="group-title">Wiederherstellen</div>
          <div className="group compact">{liste.map((s: any) => <Row key={s.name} icon={<Upload/>} label={new Date(s.zeit * 1000).toLocaleString("de-DE", {weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"})} detail={`${Math.max(1, Math.round(s.groesse / 1_048_576))} MB`} onClick={() => admin.guard(() => setWaehlen(s))}/>)}</div>
        </>}
      </>}
      <div className="group-title">Als Datei</div>
      <div className="group">
        <Row icon={<Download/>} label="In Downloads speichern" detail="Download/Jon – zum Aufheben oder Umziehen" onClick={() => {setFortschritt("Packe deine Daten …"); call("sicherung-datei", {}, 10 * 60_000).then((r: any) => {haptic("success"); shell.notify(`${r.saved} gespeichert.`); laden();}).catch(e => shell.notify(errorText(e))).finally(() => setFortschritt(""));}}/>
        <Row icon={<FolderOpen/>} label="Aus Datei wiederherstellen" detail="Eine Jon-Sicherung auswählen" onClick={() => admin.guard(() => {setFortschritt("Datei wählen …"); call("sicherung-aus-datei", {}, 10 * 60_000).catch(e => {if (errorText(e) !== "Abgebrochen") shell.notify(errorText(e)); setFortschritt("");});})}/>
      </div>
    </div>
    {admin.element}
    <Sheet open={!!waehlen} title="Sicherung einspielen?" onClose={() => setWaehlen(null)}>
      <p>Jon übernimmt die Daten aus dieser Sicherung und startet danach neu. Was seitdem auf dem Handy dazugekommen ist, wird ersetzt.</p>
      <button className="btn primary" onClick={() => waehlen && einspielen(waehlen.name)}><Upload/>Einspielen</button>
    </Sheet>
  </>;
}
