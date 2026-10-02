import React, {useEffect, useState} from "react";
import {motion} from "framer-motion";
import {Bike, Dumbbell, Flame, Footprints, Mountain, Plus, Sparkles, Target, Trash2, Trophy, Waves, Wind} from "lucide-react";
import {call, haptic} from "./bridge";
import {compose} from "./Chat";
import {Ring} from "./Familie";
import {PageProps} from "./Pages";
import {Busy, Circle, Field, PageHeader, Sheet, Zaehler, errorText, spring} from "./ui";

const arten: {id: string; name: string; icon: React.ReactNode}[] = [
  {id: "gym", name: "Gym", icon: <Dumbbell/>}, {id: "laufen", name: "Laufen", icon: <Footprints/>}, {id: "rad", name: "Rad", icon: <Bike/>},
  {id: "schwimmen", name: "Schwimmen", icon: <Waves/>}, {id: "yoga", name: "Yoga", icon: <Wind/>}, {id: "wandern", name: "Wandern", icon: <Mountain/>}
];
const wochentag = (datum: string) => new Date(`${datum}T12:00:00`).toLocaleDateString("de-DE", {weekday: "short"}).replace(".", "");

export function FitnessPage({shell, back}: PageProps) {
  const [d, setD] = useState<any>(null), [neu, setNeu] = useState<any>(null), [ziele, setZiele] = useState(false), [weg, setWeg] = useState<any>(null), [busy, setBusy] = useState(false);
  const laden = () => call("fitness").then(setD).catch(e => shell.notify(errorText(e)));
  useEffect(() => {laden(); const t = setInterval(laden, 20_000); return () => clearInterval(t);}, []);
  if (!d) return <><PageHeader title="Fitness" onBack={back}/><Busy/></>;
  const verlauf: any[] = d.verlauf || [];
  const max = Math.max(d.heute?.ziel || 8000, ...verlauf.map(v => v.schritte || 0));
  async function eintragen() {
    setBusy(true);
    try {
      const r = await call("fitness-eintragen", {training: {...neu, dauer_min: Number(neu.dauer_min) || 0, distanz_km: neu.distanz_km || 0}});
      haptic("success");
      shell.notify(`${r.titel} eingetragen${r.volumen ? ` · ${Math.round(r.volumen)} kg bewegt` : ""}.`);
      setNeu(null);
      laden();
    } catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}
  }
  const zusammenfassung = (t: any) => [t.dauer_min ? `${t.dauer_min} Min.` : "", t.distanz_km ? `${String(t.distanz_km).replace(".", ",")} km` : "", (t.uebungen || []).length ? `${t.uebungen.length} Übungen` : "", t.volumen ? `${Math.round(t.volumen)} kg` : ""].filter(Boolean).join(" · ");
  return <>
    <PageHeader title="Fitness" onBack={back} right={<Circle label="Training eintragen" onClick={() => setNeu({art: "gym", titel: "", text: "", dauer_min: "", distanz_km: "", datum: "heute"})}><Plus/></Circle>}/>
    <div className="page-scroll">
      <motion.div className="fit-held" initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={spring}>
        <Ring wert={d.heute?.schritte || 0} max={d.heute?.ziel || 8000} farbe="#3ed598" groesse={168}><Footprints/><strong><Zaehler wert={d.heute?.schritte || 0}/></strong><small>von {(d.heute?.ziel || 8000).toLocaleString("de-DE")}</small></Ring>
        <div className="balken">{verlauf.map((v, i) => <div key={v.datum}><motion.i initial={{height: 0}} animate={{height: `${Math.max(3, (v.schritte || 0) / max * 100)}%`}} transition={{...spring, delay: i * .05}} className={v.schritte >= (d.heute?.ziel || 8000) ? "voll" : ""}/><span>{wochentag(v.datum)}</span></div>)}</div>
      </motion.div>
      {!d.schritte_erlaubt && d.schritte_verfuegbar && <div className="banner"><Footprints style={{color: "#3ed598"}}/><div><strong>Schritte zählen</strong><p>Erlaube „Körperliche Aktivität“, dann zählt Jon deine Schritte.</p><button className="text-link" onClick={() => call("permission", {name: "bewegung"}).then(v => {if (v.granted) laden();}).catch(e => shell.notify(errorText(e)))}>Erlauben</button></div></div>}
      <div className="fit-werte">
        <div><Dumbbell/><strong>{d.woche?.trainings || 0}/{d.woche?.ziel || 3}</strong><small>Trainings diese Woche</small></div>
        <div><Flame/><strong>{d.serie || 0}</strong><small>Tage in Folge</small></div>
        <div><Target/><strong>{d.woche?.minuten || 0}</strong><small>Minuten</small></div>
      </div>
      <div className="chips" style={{marginTop: 14}}>
        <button className="chip" onClick={() => setZiele(true)}><Target/>Ziele</button>
        <button className="chip" onClick={() => {compose("Erstelle mir einen Trainingsplan für diese Woche passend zu meinen letzten Trainings: ", "coding"); back();}}><Sparkles/>Plan von Jon</button>
      </div>
      <div className="group-title">Letzte Trainings</div>
      {!(d.trainings || []).length && <p className="hint" style={{margin: "0 8px"}}>Noch nichts eingetragen. Tippe auf Plus oder sag Jon einfach: „Ich war im Gym, Bankdrücken 3x10 mit 60 kg.“</p>}
      {(d.trainings || []).map((t: any, i: number) => <motion.div key={t.id} className="card training" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{...spring, delay: Math.min(i, 8) * .04}}>
        <div className="zeile"><span className="logo">{arten.find(a => a.id === t.art)?.icon || <Dumbbell/>}</span><div><strong>{t.titel}</strong><small className="muted">{new Date(`${t.datum}T12:00:00`).toLocaleDateString("de-DE", {weekday: "long", day: "numeric", month: "long"})}</small></div><span className="grow"/><button aria-label="Löschen" onClick={() => setWeg(t)}><Trash2/></button></div>
        {zusammenfassung(t) && <p className="small muted" style={{margin: "8px 0 0"}}>{zusammenfassung(t)}</p>}
        {(t.uebungen || []).slice(0, 6).map((u: any, j: number) => <p key={j} className="uebung"><b>{u.name}</b>{(u.saetze || []).length ? ` · ${u.saetze.length}×${u.saetze[0].wdh}${u.saetze[0].gewicht ? ` · ${String(u.saetze[0].gewicht).replace(".", ",")} kg` : ""}` : ""}</p>)}
      </motion.div>)}
      {(d.rekorde || []).length > 0 && <><div className="group-title">Rekorde</div><div className="card">{d.rekorde.map((r: any) => <div className="stat" key={r.name}><span style={{display: "flex", gap: 8, alignItems: "center"}}><Trophy size={16} color="#ffcf6e"/>{r.name}</span><b>{String(r.gewicht).replace(".", ",")} kg × {r.wdh}</b></div>)}</div></>}
    </div>
    <Sheet open={!!neu} title="Training eintragen" onClose={() => setNeu(null)}>
      {neu && <>
        <div className="chips klein">{arten.map(a => <button key={a.id} className={`chip ${neu.art === a.id ? "on" : ""}`} onClick={() => {haptic("tick"); setNeu({...neu, art: a.id});}}>{a.icon}{a.name}</button>)}</div>
        <Field label="Titel (optional)" value={neu.titel} onChange={v => setNeu({...neu, titel: v})} placeholder={neu.art === "gym" ? "Push Day" : "Morgenrunde"}/>
        {["gym", "yoga"].includes(neu.art) && <Field label="Übungen" value={neu.text} onChange={v => setNeu({...neu, text: v})} multiline placeholder="Bankdrücken 3x10 60kg, Kniebeugen 4x8 80kg, 20 Liegestütze"/>}
        <div style={{display: "flex", gap: 12}}>
          <Field label="Minuten" type="number" value={neu.dauer_min} onChange={v => setNeu({...neu, dauer_min: v})}/>
          {!["gym", "yoga"].includes(neu.art) && <Field label="Kilometer" value={neu.distanz_km} onChange={v => setNeu({...neu, distanz_km: v})} placeholder="5,2"/>}
        </div>
        <div className="chips klein">{["heute", "gestern"].map(t => <button key={t} className={`chip ${neu.datum === t ? "on" : ""}`} onClick={() => setNeu({...neu, datum: t})}>{t === "heute" ? "Heute" : "Gestern"}</button>)}</div>
        <button className="btn primary" disabled={busy} onClick={eintragen}>Eintragen</button>
      </>}
    </Sheet>
    <Sheet open={ziele} title="Deine Ziele" onClose={() => setZiele(false)}>
      <div className="field"><span>Schritte pro Tag</span><div className="chips klein">{[5000, 6000, 8000, 10000, 12000, 15000].map(z => <button key={z} className={`chip ${d.ziele?.schritte === z ? "on" : ""}`} onClick={() => call("fitness-ziele", {schritte: z}).then(() => {haptic("success"); laden();})}>{z.toLocaleString("de-DE")}</button>)}</div></div>
      <div className="field"><span>Trainings pro Woche</span><div className="chips klein">{[2, 3, 4, 5, 6].map(z => <button key={z} className={`chip ${d.ziele?.trainings_pro_woche === z ? "on" : ""}`} onClick={() => call("fitness-ziele", {wochen: z}).then(() => {haptic("success"); laden();})}>{z}×</button>)}</div></div>
    </Sheet>
    <Sheet open={!!weg} title="Training löschen?" onClose={() => setWeg(null)}>
      <p>„{weg?.titel}“ wird aus deinem Tagebuch entfernt.</p>
      <button className="btn danger" onClick={() => call("fitness-loeschen", {training: weg.id}).then(() => {setWeg(null); laden(); shell.notify("Gelöscht.");}).catch(e => shell.notify(errorText(e)))}><Trash2/>Löschen</button>
    </Sheet>
  </>;
}
