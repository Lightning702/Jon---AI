import {useEffect, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {ArrowUp, Globe, History, Loader2, Users} from "lucide-react";
import AgentenBuehne from "./agenten/AgentenBuehne";
import {FachteamAnsicht} from "./agenten/FachteamKarte";
import {Anfrage, ENDE, fehlerText, LAUF_TEXT, Lauf, rolle} from "./agenten/daten";
import {useLive} from "./agenten/live";
import "./agent-team.css";

type Profile = {id: string; name: string; activity: string; focus: string};
type Kurz = {id: string; aufgabe: string; source: string; status: string; created_at: number};

const BEISPIELE = ["Übersetze „Marcus dicit puellam legere“ und erkläre den AcI", "Plane meine Lernwoche für drei Prüfungen", "Vergleiche zwei Ideen für mein Projekt und prüfe sie gegen"];

export default function AgentTeam({request, initialSource = "app", onWorking}: {request: Anfrage; initialSource?: "app" | "minijon"; onWorking?: (value: boolean) => void}) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [research, setResearch] = useState(false);
  const [limit, setLimit] = useState(3);
  const [goal, setGoal] = useState("");
  const [runs, setRuns] = useState<Kurz[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [verlauf, setVerlauf] = useState(false);

  useEffect(() => {
    let active = true;
    request("/agents/profiles").then(value => {if (active) setProfiles(value);}).catch(e => {if (active) setError(fehlerText(e, "Fachteam nicht erreichbar."));});
    request("/agents/runs?brief=true").then((items: Kurz[]) => {if (active) {setRuns(items); setSelected(s => s || items[0]?.id || "");}}).catch(() => {});
    return () => {active = false;};
  }, [request]);

  const {daten: run, setDaten: setRun} = useLive<Lauf>(request, selected ? "/agents/runs/" + selected : null, value => ENDE.has(value.status), 900);
  const working = !!run && !ENDE.has(run.status);
  useEffect(() => {onWorking?.(working); return () => onWorking?.(false);}, [working, onWorking]);
  useEffect(() => {if (run) setRuns(items => items.map(item => item.id === run.id ? {...item, status: run.status} : item));}, [run?.id, run?.status]);

  const action = async (operation: () => Promise<void>) => {
    setBusy(true); setError("");
    try {await operation();} catch(e) {setError(fehlerText(e, "Fachteam nicht erreichbar."));} finally {setBusy(false);}
  };
  const start = () => action(async () => {
    const created: Lauf = await request("/agents/runs", {aufgabe: goal.trim(), max_agenten: limit, source: initialSource, research, roles});
    setRun(created); setSelected(created.id); setRuns(items => [{id: created.id, aufgabe: created.aufgabe, source: initialSource, status: created.status, created_at: created.created_at || Date.now() / 1000}, ...items]); setGoal("");
  });
  const vorschau = roles.slice(0, limit);

  return <section className="agent-team ab" aria-label="Jon Fachteam">
    <div className="agent-team-hero">
      <div className="agent-team-stage"><AgentenBuehne phase={working ? "verteilen" : "bereit"} knoten={vorschau.map((key, i) => ({id: key + i, titel: rolle(key).name, rolle: key, status: "queued"}))} kernText="Jon" kompakt/></div>
      <div className="agent-team-intro"><span className="ab-kopf-icon"><Users/></span><div><h2>Jon Fachteam</h2><p>Jon verteilt deine Aufgabe auf passende Fachagenten, lässt sie parallel arbeiten und prüft die Ergebnisse gegen.</p></div></div>
    </div>
    <AnimatePresence>{error && <motion.div className="ab-hinweis fehler" role="alert" initial={{opacity: 0, y: -6}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}}><span style={{flex: 1}}>{error}</span><button type="button" className="ab-knopf" onClick={() => setError("")}>Schließen</button></motion.div>}</AnimatePresence>
    <form className="agent-team-composer" onSubmit={e => {e.preventDefault(); if (!busy && goal.trim() && profiles.length) void start();}}>
      <textarea value={goal} maxLength={12000} rows={3} placeholder="Was soll das Team für dich klären?" aria-label="Deine Aufgabe" onChange={e => setGoal(e.target.value)} onKeyDown={e => {if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {e.preventDefault(); if (!busy && goal.trim() && profiles.length) void start();}}}/>
      {!goal && <div className="agent-team-beispiele">{BEISPIELE.map(text => <button type="button" key={text} onClick={() => setGoal(text)}>{text}</button>)}</div>}
      <div className="agent-chips" role="group" aria-label="Fachrichtungen">{profiles.map(p => {
        const r = rolle(p.id);
        const Icon = r.icon;
        return <motion.button whileTap={{scale: 0.94}} key={p.id} type="button" aria-pressed={roles.includes(p.id)} title={p.focus} style={{["--farbe" as string]: r.farbe}} onClick={() => setRoles(values => values.includes(p.id) ? values.filter(key => key !== p.id) : [...values, p.id])}><Icon/>{p.name}</motion.button>;
      })}</div>
      <div className="agent-team-leiste">
        <label className="agent-team-anzahl"><span>Agenten</span>{[1, 2, 3, 4].map(n => <button type="button" key={n} aria-pressed={limit === n} onClick={() => setLimit(n)}>{n}</button>)}</label>
        <button type="button" className={"agent-team-web " + (research ? "an" : "")} aria-pressed={research} onClick={() => setResearch(v => !v)}><Globe/>Web</button>
        <span className="agent-team-platz"/>
        <button type="submit" className="agent-team-senden" disabled={busy || !goal.trim() || !profiles.length} aria-label="Fachteam starten" title="Fachteam starten">{busy ? <Loader2 className="ab-dreht"/> : <ArrowUp/>}</button>
      </div>
      <p className="agent-note">{roles.length ? "Gewählte Fachrichtungen werden bevorzugt." : "Ohne Auswahl stellt Jon das Team selbst zusammen."} Analysen und Vorschläge, keine Dateiänderungen. Du kannst das Team auch im Chat beauftragen.</p>
    </form>
    <AnimatePresence mode="wait">{run && <motion.div key={run.id} initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -10}}>
      <FachteamAnsicht lauf={run} beschaeftigt={busy}
        onStopp={() => void action(async () => setRun(await request("/agents/runs/" + run.id + "/cancel", {})))}
        onLoeschen={() => void action(async () => {await request("/agents/runs/" + run.id, undefined, "DELETE"); const rest = runs.filter(item => item.id !== run.id); setRuns(rest); setRun(null); setSelected(rest[0]?.id || "");})}/>
    </motion.div>}</AnimatePresence>
    {runs.length > 1 && <div className="agent-team-verlauf">
      <button type="button" className="ab-knopf" onClick={() => setVerlauf(v => !v)} aria-expanded={verlauf}><History/>Frühere Aufträge · {runs.length}</button>
      <AnimatePresence initial={false}>{verlauf && <motion.div className="agent-team-liste" initial={{height: 0, opacity: 0}} animate={{height: "auto", opacity: 1}} exit={{height: 0, opacity: 0}}>
        {runs.map(item => <button type="button" key={item.id} className={item.id === selected ? "an" : ""} onClick={() => {setRun(null); setSelected(item.id);}}><i className={"agent-punkt " + item.status}/><span>{item.aufgabe}</span><small>{LAUF_TEXT[item.status] || item.status}</small></button>)}
      </motion.div>}</AnimatePresence>
    </div>}
  </section>;
}
