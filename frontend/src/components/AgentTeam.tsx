import {useEffect, useState} from "react";
import "./agent-team.css";

type Profile = {id: string; name: string; activity: string; focus: string};
type Part = {titel: string; auftrag: string; rolle: string; status: string; ergebnis?: string; fehler?: string};
type Run = {id: string; aufgabe: string; source: string; status: string; antwort?: string; fehler?: string; hinweis?: string; teile?: Part[]; pruefung?: {ok: boolean; probleme: string[]; korrektur: string}};
type Request = (path: string, body?: unknown, method?: string) => Promise<any>;
const ended = new Set(["done", "needs_review", "failed", "cancelled", "interrupted"]);
const labels: Record<string, string> = {planning: "Plant die Teilaufgaben", queued: "Wartet", working: "Arbeitet", verifying: "Prüft die Ergebnisse", summarizing: "Fasst zusammen", done: "Abgeschlossen", needs_review: "Offene Prüfpunkte", failed: "Fehlgeschlagen", cancelled: "Gestoppt", interrupted: "Unterbrochen"};
const failure = (e: unknown) => e instanceof Error ? e.message : "Fachteam nicht erreichbar.";

export default function AgentTeam({request, initialSource = "app", onWorking}: {request: Request; initialSource?: "app" | "minijon"; onWorking?: (value: boolean) => void}) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [source, setSource] = useState(initialSource);
  const [research, setResearch] = useState(false);
  const [limit, setLimit] = useState(3);
  const [goal, setGoal] = useState("");
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    request("/agents/profiles").then(value => {if (active) setProfiles(value);}).catch(e => {if (active) setError(failure(e));});
    return () => {active = false;};
  }, [request]);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        if (!document.hidden) {
          const items: Run[] = await request("/agents/runs?brief=true");
          if (!active) return;
          setRuns(items);
          if (!selected && items.length) setSelected(items[0].id);
          if (selected) {
            const current = await request("/agents/runs/" + selected);
            if (!active) return;
            setRun(current);
          }
          setLoading(false);
        }
      } catch(e) {if (active) {setError(failure(e)); setLoading(false);}}
      finally {if (active) timer = setTimeout(refresh, 3000);}
    };
    void refresh();
    return () => {active = false; clearTimeout(timer);};
  }, [request, selected]);

  const working = !!run && !ended.has(run.status);
  useEffect(() => {onWorking?.(working); return () => onWorking?.(false);}, [working, onWorking]);
  const action = async (operation: () => Promise<void>) => {
    setBusy(true); setError("");
    try {await operation();} catch(e) {setError(failure(e));} finally {setBusy(false);}
  };
  const start = () => action(async () => {
    const created: Run = await request("/agents/runs", {aufgabe: goal.trim(), max_agenten: limit, source, research, roles});
    setRun(created); setSelected(created.id); setRuns(items => [created, ...items]);
  });
  return <section className="agent-team" aria-label="Jon Fachteam">
    <div className="agent-team-heading"><span className={working ? "agent-face working" : "agent-face"} aria-hidden="true">◕‿◕</span><div><h2>Jon Fachteam</h2><p>Passende Fachagenten bearbeiten deine Aufgabe. Eine eigene Gegenprüfung sucht nach Fehlern.</p></div></div>
    {error && <div className="agent-error" role="alert">{error}<button onClick={() => setError("")}>Schließen</button></div>}
    <label>Deine Aufgabe<textarea value={goal} maxLength={12000} rows={3} placeholder="Zum Beispiel: Übersetze diesen lateinischen Satz und prüfe die Grammatik …" onChange={e => setGoal(e.target.value)}/></label>
    <fieldset><legend>Fachrichtungen · ohne Auswahl entscheidet Jon</legend><div className="agent-chips">{profiles.map(p => <button key={p.id} type="button" aria-pressed={roles.includes(p.id)} title={p.focus} onClick={() => setRoles(values => values.includes(p.id) ? values.filter(key => key !== p.id) : [...values, p.id])}>{p.name}</button>)}</div></fieldset>
    <div className="agent-options"><label>Begleiter<select value={source} onChange={e => setSource(e.target.value as "app" | "minijon")}><option value="app">Jon</option><option value="minijon">MiniJon</option></select></label><label>Höchstens<select value={limit} onChange={e => setLimit(Number(e.target.value))}>{[1,2,3,4].map(n => <option key={n} value={n}>{n} Fachagent{n > 1 ? "en" : ""}</option>)}</select></label></div>
    <label className="agent-check"><input type="checkbox" checked={research} onChange={e => setResearch(e.target.checked)}/>Webrecherche für diese Aufgabe erlauben</label>
    <button className="agent-primary" disabled={busy || !goal.trim() || !profiles.length} onClick={() => void start()}>Fachteam starten</button>
    <p className="agent-note">Analysen und Vorschläge, keine selbständigen Dateiänderungen. Die gewählten Modelle können Nutzungskosten verursachen. Gegenprüfungen können ebenfalls Fehler übersehen.</p>
    <label>Aufträge<select aria-label="Fachauftrag auswählen" value={selected} onChange={e => {setRun(null); setSelected(e.target.value);}}><option value="">Auftrag auswählen</option>{runs.map(item => <option key={item.id} value={item.id}>{labels[item.status] || item.status} · {item.aufgabe.slice(0,70)}</option>)}</select></label>
    {loading && <p role="status">Lädt die Aufträge …</p>}
    {!loading && !runs.length && <p className="agent-note">Noch kein Fachauftrag. Du kannst das Team auch im Chat darum bitten.</p>}
    {run && <article className="agent-run">
      <div className="agent-run-top"><strong aria-live="polite">{labels[run.status] || run.status}</strong>{!ended.has(run.status) ? <button disabled={busy} onClick={() => void action(async () => setRun(await request("/agents/runs/" + run.id + "/cancel", {})))}>Stoppen</button> : <button disabled={busy} onClick={() => void action(async () => {await request("/agents/runs/" + run.id, undefined, "DELETE"); setRuns(items => items.filter(item => item.id !== run.id)); setRun(null); setSelected("");})}>Auftrag löschen</button>}</div>
      <p className="agent-goal">{run.aufgabe}</p>
      {run.hinweis && <p className="agent-note">{run.hinweis}</p>}
      {run.fehler && <p className="agent-error">{run.fehler}</p>}
      <div className="agent-parts">{run.teile?.map((part, index) => <details key={index}><summary><span aria-hidden="true">✦</span> {part.titel} <small>{labels[part.status] || part.status}</small></summary><p>{part.auftrag}</p><pre>{part.ergebnis || part.fehler || "Bearbeitet die Teilfrage …"}</pre></details>)}</div>
      {run.pruefung && <details className="agent-review" open={!run.pruefung.ok}><summary>Gegenprüfung · {run.pruefung.ok ? "Keine offenen Punkte gemeldet" : "Prüfung offen"}</summary>{run.pruefung.probleme.map((item, index) => <p key={index}>{item}</p>)}{run.pruefung.korrektur && <pre>{run.pruefung.korrektur}</pre>}</details>}
      {run.antwort && <div className="agent-answer"><h3>Ergebnis</h3><p>{run.antwort}</p></div>}
    </article>}
  </section>;
}
