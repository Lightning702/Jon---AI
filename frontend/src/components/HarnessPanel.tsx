import {Fragment, useEffect, useMemo, useRef, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {ArrowLeft, ArrowUp, CheckCircle2, ChevronDown, ChevronRight, Code2, FileCode2, Folder, FolderPlus, GitBranch, Loader2, MessagesSquare, Monitor, PanelLeft, Plus, RotateCcw, Search, Settings2, ShieldCheck, ShieldOff, Sparkles, Square, X} from "lucide-react";
import {addProject, getUserSettings, JonProject, pickFolderDialog} from "../lib/api";
import {finished, HarnessSitzung, HarnessTask, harnessRequest, taskLabels} from "../lib/harness";
import AgentenBuehne from "./agenten/AgentenBuehne";
import HarnessVerlauf from "./HarnessVerlauf";
import {diffZahlen, rolle, TEIL_TEXT} from "./agenten/daten";
import HarnessVorschau from "./HarnessVorschau";
import "./harness-workspace.css";

const VORSCHLAEGE = ["Baue mir eine Startseite mit index.html", "Finde und behebe einen Fehler", "Erkläre mir dieses Projekt", "Verbessere die Oberfläche und prüfe den Build"];
const UNTERBROCHEN = new Set(["interrupted", "failed", "needs_review", "cancelled"]);
const FOLGE = ["Mach es schöner und moderner", "Prüfe alles noch einmal und behebe Fehler", "Schreibe Tests dafür", "Erkläre mir, was du geändert hast"];
const ANBIETER: Record<string, string> = {nvidia: "NVIDIA NIM", ollama: "Ollama", openrouter: "OpenRouter", lmstudio: "LM Studio", xai: "xAI", anthropic: "Anthropic", gemini: "Google Gemini", openai: "OpenAI"};
type Rechts = "aenderungen" | "vorschau" | null;

function Ergebnis({task, aktuell, onAenderungen, onVorschau, busy, onStopp, onEntscheiden}: {task: HarnessTask; aktuell: boolean; onAenderungen: () => void; onVorschau: () => void; busy: boolean; onStopp: () => void; onEntscheiden: (allow: boolean) => void}) {
  const dateien = useMemo(() => {
    const result = new Map<string, {path: string; added: number; removed: number}>();
    for (const change of task.changes || []) {
      const item = result.get(change.path) || {path: change.path, added: 0, removed: 0};
      const counts = diffZahlen(change.diff);
      item.added += counts.plus; item.removed += counts.minus; result.set(change.path, item);
    }
    return [...result.values()];
  }, [task.changes]);
  const summe = dateien.reduce((s, v) => ({added: s.added + v.added, removed: s.removed + v.removed}), {added: 0, removed: 0});
  const fertig = finished.has(task.status);
  if (!aktuell) return <details className="harness-frueher">
    <summary><i className={"harness-state-dot state-" + task.status}/><span>{taskLabels[task.status] || task.status}</span>{!!dateien.length && <span className="harness-frueher-zahl"><b className="harness-added">+{summe.added}</b><b className="harness-removed">−{summe.removed}</b> · {dateien.length} {dateien.length === 1 ? "Datei" : "Dateien"}</span>}<ChevronRight size={13}/></summary>
    {task.summary && <p>{task.summary}</p>}
    {!!dateien.length && <div className="harness-frueher-dateien">{dateien.map(d => <button key={d.path} onClick={onAenderungen}><FileCode2 size={12}/>{d.path}</button>)}</div>}
  </details>;
  return <>
    <HarnessVerlauf task={task} busy={busy} onStopp={onStopp} onEntscheiden={onEntscheiden}/>
    {!!task.specialists?.length && <div className="harness-specialists"><div className="harness-section-label" style={{margin: "22px 0 10px"}}>Fachagenten</div>{task.specialists.map((agent, index) => {
      const r = rolle(agent.profil || "coding");
      const Icon = r.icon;
      return <details key={index} className="harness-specialist" style={{["--farbe" as string]: r.farbe}}><summary><span className="harness-specialist-icon"><Icon size={14}/></span>{agent.role}<span>{TEIL_TEXT[agent.status] || agent.status}{agent.dauer ? ` · ${Math.round(agent.dauer)}s` : ""}</span></summary><p className="harness-muted">{agent.question}</p><p>{agent.result || agent.error || "Prüft die Teilaufgabe …"}</p></details>;
    })}</div>}
    {!!dateien.length && <div className="harness-changes-card"><div className="harness-changes-head"><FileCode2 size={21}/><div><strong>{dateien.length} {dateien.length === 1 ? "Datei bearbeitet" : "Dateien bearbeitet"}</strong><div><span className="harness-added">+{summe.added}</span><span className="harness-removed">−{summe.removed}</span></div></div><button onClick={onAenderungen}>Änderungen</button>{fertig && <button className="harness-vorschau-cta" onClick={onVorschau}><Monitor size={13}/>Vorschau</button>}</div>{dateien.slice(0, 3).map(item => <button className="harness-file-row" key={item.path} onClick={onAenderungen}><span>{item.path}</span><span><b className="harness-added">+{item.added}</b><b className="harness-removed">−{item.removed}</b></span></button>)}{dateien.length > 3 && <button className="harness-more-files" onClick={onAenderungen}>{dateien.length - 3} {dateien.length === 4 ? "weitere Datei" : "weitere Dateien"} anzeigen <ChevronDown size={14}/></button>}</div>}
    {fertig && !!task.checks.length && <div className="harness-checks">{task.checks.map((check, index) => <details key={index}><summary>{check.ok ? <CheckCircle2 size={16} className="harness-added"/> : <X size={16} className="harness-removed"/>}<code>{check.command}</code><span>{check.ok ? "Bestanden" : "Fehlgeschlagen"}</span></summary><pre>{check.output || "Keine Ausgabe"}</pre></details>)}</div>}
  </>;
}

export default function HarnessPanel({standalone = false, onClose, initialTask}: {standalone?: boolean; onClose?: () => void; initialTask?: string}) {
  const [projects, setProjects] = useState<JonProject[]>([]);
  const [root, setRoot] = useState("");
  const [goal, setGoal] = useState("");
  const [mini, setMini] = useState(false);
  const [modelLabel, setModelLabel] = useState("Jons Modell");
  const [anbieter, setAnbieter] = useState("");
  const [sitzungen, setSitzungen] = useState<HarnessSitzung[]>([]);
  const [selected, setSelected] = useState("");
  const [tasks, setTasks] = useState<HarnessTask[]>([]);
  const [drafting, setDrafting] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [sidebar, setSidebar] = useState(true);
  const [rechts, setRechts] = useState<Rechts>(null);
  const [setupOpen, setSetupOpen] = useState(false);
  const [neuLaden, setNeuLaden] = useState(0);
  const [bereit, setBereit] = useState(!initialTask);
  const composer = useRef<HTMLTextAreaElement>(null);
  const feed = useRef<HTMLElement>(null);
  const vorher = useRef<Record<string, string>>({});
  const sitzungsStand = useRef("");
  const aufgabenStand = useRef("");
  const amEnde = useRef(true);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([harnessRequest<JonProject[]>("/projects", undefined, undefined, controller.signal), harnessRequest<{root: string}>("/harness/project?source=app", undefined, undefined, controller.signal)])
      .then(([items, context]) => {if (!controller.signal.aborted) {setProjects(items); setRoot(r => r || context.root || items[0]?.root || "");}})
      .catch(e => {if (!controller.signal.aborted) setError(e.message);});
    void getUserSettings().then(value => {if (!controller.signal.aborted) {setModelLabel(value.model || "Jons Modell"); setAnbieter(value.provider || "");}}).catch(() => {});
    if (initialTask) void harnessRequest<HarnessTask>(`/harness/tasks/${initialTask}`, undefined, undefined, controller.signal)
      .then(t => {if (!controller.signal.aborted) {setSelected(t.thread || t.id); setRoot(t.root);}})
      .catch(() => {})
      .finally(() => {if (!controller.signal.aborted) setBereit(true);});
    return () => controller.abort();
  }, [initialTask]);

  useEffect(() => {
    if (!bereit) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      let fast = false;
      try {
        if (!document.hidden) {
          const list = await harnessRequest<HarnessSitzung[]>("/harness/threads", undefined, undefined, controller.signal);
          if (controller.signal.aborted) return;
          const sitzungsText = JSON.stringify(list);
          if (sitzungsText !== sitzungsStand.current) {sitzungsStand.current = sitzungsText; setSitzungen(list);}
          if (!selected && !drafting && list.length) {setSelected(list[0].id); setRoot(list[0].root);}
          if (selected) {
            try {
              const data = await harnessRequest<{root: string; tasks: HarnessTask[]}>(`/harness/threads/${selected}`, undefined, undefined, controller.signal);
              if (controller.signal.aborted) return;
              const stand = JSON.stringify(data.tasks.map(t => [t.id, t.status, t.updated_at, t.step, t.log?.length, t.changes.length, t.checks.length, t.pending?.id, t.specialists?.map(a => a.status).join(), t.summary.length]));
              if (stand !== aufgabenStand.current) {aufgabenStand.current = stand; setTasks(data.tasks);}
              fast = data.tasks.some(t => !finished.has(t.status));
              let geaendert = false;
              for (const t of data.tasks) {
                const alt = vorher.current[t.id];
                if (alt && !finished.has(alt) && finished.has(t.status) && t.changes.length) geaendert = true;
                vorher.current[t.id] = t.status;
              }
              if (geaendert) setNeuLaden(n => n + 1);
            } catch (e) {
              if (controller.signal.aborted) return;
              if (e instanceof Error && /nicht gefunden/.test(e.message)) {setSelected(""); setTasks([]);}
              else throw e;
            }
          }
          setLoading(false);
        }
      } catch (e) {
        if (!controller.signal.aborted) {setError(e instanceof Error ? e.message : "Verbindung unterbrochen"); setLoading(false);}
      } finally {if (!controller.signal.aborted) timer = setTimeout(refresh, fast ? 1200 : 3000);}
    };
    void refresh();
    return () => {controller.abort(); clearTimeout(timer);};
  }, [selected, drafting, bereit]);

  const sitzung = sitzungen.find(s => s.id === selected);
  const letzte = tasks.at(-1);
  const [allesErlaubt, setAllesErlaubt] = useState<boolean | null>(null);
  useEffect(() => {
    let aktiv = true;
    harnessRequest<{alles: boolean}>("/harness/freigabe").then(d => {if (aktiv) setAllesErlaubt(d.alles);}).catch(() => {if (aktiv) setAllesErlaubt(false);});
    return () => {aktiv = false;};
  }, []);
  const freigabeUmschalten = async () => {
    const neu = !allesErlaubt;
    if (neu && !window.confirm("Alle Befehle erlauben? Jon führt dann Shellbefehle ohne Nachfrage mit deinen Benutzerrechten aus, auch außerhalb des Projektordners. Nur offensichtlich zerstörerische Befehle wie Formatieren oder rekursives Löschen fragen weiterhin nach.")) return;
    try {setAllesErlaubt((await harnessRequest<{alles: boolean}>("/harness/freigabe", {alles: neu})).alles);}
    catch (e) {setError(e instanceof Error ? e.message : "Die Einstellung konnte nicht gespeichert werden.");}
  };
  const working = tasks.some(t => !finished.has(t.status));
  const action = async (fn: () => Promise<void>) => {setBusy(true); setError(""); try {await fn();} catch (e) {setError(e instanceof Error ? e.message : "Aktion fehlgeschlagen");} finally {setBusy(false);}};
  const choose = (item: HarnessSitzung) => {if (item.id === selected) return; aufgabenStand.current = ""; amEnde.current = true; setDrafting(false); setSelected(item.id); setTasks([]); setRoot(item.root); setRechts(r => r === "aenderungen" ? null : r);};
  const newTask = (projekt?: string) => {aufgabenStand.current = ""; setDrafting(true); setSelected(""); setTasks([]); setGoal(""); setRechts(r => r === "aenderungen" ? null : r); if (projekt) setRoot(projekt); setTimeout(() => composer.current?.focus(), 30);};
  const pick = () => action(async () => {
    const path = await pickFolderDialog();
    if (!path) return;
    const project = await addProject(path);
    setProjects(items => items.some(p => p.id === project.id) ? items : [...items, project]); setSetupOpen(false); newTask(project.root);
  });
  const start = (text = goal) => action(async () => {
    if (!text.trim() || !root.trim()) return;
    const project = await addProject(root.trim());
    const thread = selected && !drafting && tasks[0]?.root === project.root ? selected : "";
    await harnessRequest("/harness/project", {root: project.root, source: "app"});
    if (mini) await harnessRequest("/harness/project", {root: project.root, source: "minijon"});
    const created = await harnessRequest<HarnessTask>("/harness/tasks", {root: project.root, goal: text.trim(), source: "app", companion: mini, thread});
    setProjects(items => items.some(p => p.id === project.id) ? items : [...items, project]);
    vorher.current[created.id] = created.status;
    const id = created.thread || created.id;
    if (id === selected) setTasks(items => [...items, created]);
    else {setTasks([created]); setSelected(id);}
    setDrafting(false); setGoal("");
    if (mini) await window.jon?.showPet?.().catch(() => setError("Auftrag läuft. MiniJons Fenster konnte nicht geöffnet werden."));
  });
  const decide = (task: HarnessTask, allow: boolean) => action(async () => {
    if (!task.pending) return;
    await harnessRequest(`/harness/tasks/${task.id}/approve`, {approval_id: task.pending.id, allow});
    const neu = await harnessRequest<HarnessTask>(`/harness/tasks/${task.id}`);
    setTasks(items => items.map(t => t.id === neu.id ? neu : t));
  });
  const stop = (task: HarnessTask) => action(async () => {
    const neu = await harnessRequest<HarnessTask>(`/harness/tasks/${task.id}/cancel`, {});
    setTasks(items => items.map(t => t.id === neu.id ? neu : t));
  });
  const visible = sitzungen.filter(item => (item.title + " " + item.root).toLowerCase().includes(search.toLowerCase()));
  const projectName = projects.find(p => p.root === root)?.name || root.split(/[\\/]/).filter(Boolean).at(-1) || "Projekt wählen";
  const changes = useMemo(() => {
    const result = new Map<string, {path: string; diffs: string[]; added: number; removed: number}>();
    for (const task of tasks) for (const change of task.changes || []) {
      const item = result.get(change.path) || {path: change.path, diffs: [], added: 0, removed: 0};
      const counts = diffZahlen(change.diff);
      item.diffs.push(change.diff); item.added += counts.plus; item.removed += counts.minus; result.set(change.path, item);
    }
    return [...result.values()];
  }, [tasks]);
  const imThread = !!selected && !drafting && !!tasks.length;
  const sendbar = !busy && !working && !!goal.trim() && !!root.trim();
  useEffect(() => {
    const el = feed.current;
    if (!el) return;
    const merken = () => {amEnde.current = el.scrollHeight - el.scrollTop - el.clientHeight < 140;};
    el.addEventListener("scroll", merken, {passive: true});
    return () => el.removeEventListener("scroll", merken);
  }, []);
  useEffect(() => {
    const el = feed.current;
    if (working && el && amEnde.current) requestAnimationFrame(() => {el.scrollTop = el.scrollHeight;});
  }, [working, letzte?.log?.length, letzte?.pending?.id, tasks.length]);
  const umschalten = (ziel: Exclude<Rechts, null>) => setRechts(r => r === ziel ? null : ziel);
  const liste = (items: HarnessSitzung[], eingerueckt = false) => items.map(item => <button key={item.id} className={(selected === item.id && !drafting ? "selected " : "") + (eingerueckt ? "" : "harness-recent")} onClick={() => choose(item)}><span>{item.title}</span>{item.tasks > 1 && <em className="harness-anzahl" title={`${item.tasks} Aufträge in dieser Sitzung`}>{item.tasks}</em>}<i className={"harness-state-dot state-" + item.status} title={taskLabels[item.status] || item.status}/></button>);

  return <section className={"harness-shell " + (standalone ? "harness-shell-full " : "harness-shell-embedded ") + (!sidebar ? "harness-sidebar-hidden " : "") + (rechts && (rechts === "vorschau" ? root : imThread) ? "harness-with-review " : "") + (rechts === "vorschau" ? "harness-mit-vorschau" : "")} aria-label="Jon Harness">
    <nav className="harness-rail" aria-label="Harness Navigation">
      {onClose && <button title="Zurück zu Jon" aria-label="Zurück zu Jon" onClick={onClose}><ArrowLeft size={18}/></button>}
      <div className={"harness-rail-logo " + (working ? "aktiv" : "")}><Code2 size={17}/></div>
      <button title="Neue Sitzung" aria-label="Neue Sitzung" onClick={() => newTask()}><Plus size={20}/></button>
      <button title="Projekte" aria-label="Projektleiste einblenden" onClick={() => setSidebar(v => !v)}><Folder size={19}/></button>
      <button title="Änderungen" aria-label="Änderungen einblenden" className={rechts === "aenderungen" ? "an" : ""} onClick={() => umschalten("aenderungen")} disabled={!imThread}><GitBranch size={19}/></button>
      <button title="Vorschau" aria-label="Vorschau einblenden" className={rechts === "vorschau" ? "an" : ""} onClick={() => umschalten("vorschau")} disabled={!root}><Monitor size={19}/></button>
      <div className="harness-rail-spacer"/>
      <button title="Projektpfad eingeben" aria-label="Projektpfad eingeben" onClick={() => setSetupOpen(v => !v)}><Settings2 size={19}/></button>
    </nav>
    <aside className="harness-sidebar">
      <div className="harness-brand"><span>Jon <b>Harness</b></span><button aria-label="Sitzungen durchsuchen" title="Suchen" onClick={() => setSearchOpen(v => !v)}><Search size={17}/></button></div>
      <button className="harness-new" onClick={() => newTask()}><Plus size={16}/>Neue Sitzung</button>
      <AnimatePresence>{searchOpen && <motion.input initial={{opacity: 0, height: 0}} animate={{opacity: 1, height: "auto"}} exit={{opacity: 0, height: 0}} autoFocus className="harness-search" aria-label="Sitzungen durchsuchen" placeholder="Sitzungen suchen …" value={search} onChange={e => setSearch(e.target.value)}/>}</AnimatePresence>
      <div className="harness-section-label"><span>Projekte</span><button title="Projekt hinzufügen" aria-label="Projekt hinzufügen" disabled={busy} onClick={() => void pick()}><FolderPlus size={16}/></button></div>
      <div className="harness-project-list">{projects.map(project => <details key={project.id} open={root === project.root || undefined}><summary onClick={() => setRoot(project.root)}><Folder size={15}/><span>{project.name}</span><ChevronRight size={13}/></summary><div className="harness-task-list">{liste(visible.filter(item => item.root === project.root), true)}<button className="harness-project-new" onClick={() => newTask(project.root)}><Plus size={13}/>Neue Sitzung in diesem Projekt</button></div></details>)}{!projects.length && !loading && <button className="harness-empty-project" onClick={() => void pick()}><FolderPlus size={18}/>Erstes Projekt öffnen</button>}</div>
      <div className="harness-section-label">Letzte Sitzungen</div>
      <div className="harness-task-list harness-recents">{liste(visible.slice(0, 8))}{loading && <span className="harness-muted">Lädt Sitzungen …</span>}{!loading && !visible.length && <span className="harness-muted">{search ? "Keine passenden Sitzungen" : "Deine erste Sitzung wartet auf dich."}</span>}</div>
      <div className="harness-sidebar-foot" title={modelLabel}><span className="harness-companion-dot"/><span>Arbeitet mit <b>{ANBIETER[anbieter || letzte?.provider || ""] || modelLabel}</b></span></div>
    </aside>
    <div className="harness-main">
      <header className="harness-topbar"><button aria-label="Projektleiste umschalten" title="Projektleiste umschalten" onClick={() => setSidebar(v => !v)}><PanelLeft size={17}/></button>{imThread ? <MessagesSquare size={16}/> : <Folder size={16}/>}<strong>{imThread ? sitzung?.title || tasks[0]?.goal : "Neue Sitzung"}</strong>{imThread && <span className="harness-topbar-meta">Jon Harness · {ANBIETER[letzte?.provider || anbieter] || letzte?.provider || anbieter || "Jons Modell"} · Coding-Agent</span>}{imThread && tasks.length > 1 && <span className="harness-topbar-zahl">{tasks.length} Aufträge</span>}<div className="harness-topbar-actions">{letzte && imThread && <span className={"harness-status status-" + letzte.status}>{working && <Loader2 size={13} className="harness-spin"/>}{taskLabels[letzte.status] || letzte.status}</span>}<button className={"harness-topbar-knopf " + (rechts === "vorschau" ? "an" : "")} aria-label="Vorschau anzeigen" title="Vorschau deines Projekts" onClick={() => umschalten("vorschau")} disabled={!root}><Monitor size={15}/><span>Vorschau</span></button><button className={"harness-topbar-knopf " + (rechts === "aenderungen" ? "an" : "")} aria-label="Änderungen anzeigen" title="Änderungen dieser Sitzung" onClick={() => umschalten("aenderungen")} disabled={!imThread}><GitBranch size={15}/><span>Änderungen</span>{!!changes.length && <em>{changes.length}</em>}</button></div></header>
      <AnimatePresence>{error && <motion.div initial={{height: 0, opacity: 0}} animate={{height: "auto", opacity: 1}} exit={{height: 0, opacity: 0}} role="alert" className="harness-error"><span>{error}</span><button aria-label="Fehler schließen" onClick={() => setError("")}><X size={16}/></button></motion.div>}</AnimatePresence>
      <main className="harness-feed" ref={feed}>
        <AnimatePresence mode="wait">
        {!imThread && <motion.div key="welcome" className="harness-welcome" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -10}}>
          <div className="harness-hero ab"><AgentenBuehne phase="bereit" knoten={[]} kernIcon={Code2} kernText="Harness"/></div>
          <h1>Was bauen wir heute?</h1>
          <p>Wähle ein Projekt und beschreibe dein Ziel. Jon plant, liest, ändert und testet. Folgeaufträge bleiben in derselben Sitzung, und mit der Vorschau siehst du das Ergebnis sofort.</p>
          <div className="harness-suggestions">{VORSCHLAEGE.map((value, i) => <motion.button key={value} initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={{delay: 0.08 * i}} onClick={() => {setGoal(value); composer.current?.focus();}}>{value}<ArrowUp size={14}/></motion.button>)}</div>
        </motion.div>}
        {imThread && <motion.div key={selected} className="harness-thread" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}}>
          {tasks.map((task, index) => {
            const aktuell = index === tasks.length - 1;
            return <Fragment key={task.id}>
              {index > 0 && <div className="harness-trenner"><span>Folgeauftrag {index + 1}</span></div>}
              <motion.div className="harness-user-message" initial={aktuell && index > 0 ? {opacity: 0, y: 12, scale: 0.98} : false} animate={{opacity: 1, y: 0, scale: 1}}>{task.goal}</motion.div>
              <Ergebnis task={task} aktuell={aktuell} busy={busy} onAenderungen={() => setRechts("aenderungen")} onVorschau={() => setRechts("vorschau")} onStopp={() => void stop(task)} onEntscheiden={allow => void decide(task, allow)}/>
            </Fragment>;
          })}
          {!working && letzte && <motion.div className="harness-folge" initial={{opacity: 0, y: 6}} animate={{opacity: 1, y: 0}} transition={{delay: 0.15}}>{UNTERBROCHEN.has(letzte.status) && <button className="harness-fortsetzen" disabled={busy || !root.trim()} onClick={() => void start("fahre fort")} title="Jon macht genau dort weiter, wo er aufgehört hat"><RotateCcw size={13}/>Fahre fort</button>}{FOLGE.map(value => <button key={value} onClick={() => {setGoal(value); composer.current?.focus();}}>{value}</button>)}</motion.div>}
        </motion.div>}
        </AnimatePresence>
      </main>
      <div className="harness-composer-wrap">
        <AnimatePresence>{setupOpen && <motion.div className="harness-project-setup" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: 8}}><label>Projektordner<input aria-label="Arbeitsordner" value={root} onChange={e => {setRoot(e.target.value); if (imThread) setDrafting(true);}} placeholder="C:\Projekte\MeineApp"/></label><button disabled={busy} onClick={() => void pick()}><FolderPlus size={16}/>Ordner wählen</button><button aria-label="Projektauswahl schließen" onClick={() => setSetupOpen(false)}><X size={15}/></button></motion.div>}</AnimatePresence>
        <form className={"harness-composer " + (working ? "arbeitet" : "")} onSubmit={e => {e.preventDefault(); if (sendbar) void start();}}>
          {imThread && <div className="harness-sitzung-hinweis"><MessagesSquare size={12}/><span>{working ? "Jon arbeitet gerade. Dein nächster Auftrag kommt in diese Sitzung, sobald er fertig ist." : "Folgeauftrag in dieser Sitzung · Jon kennt alles, was bisher passiert ist"}</span><button type="button" onClick={() => newTask(root)}>Neue Sitzung</button></div>}
          <textarea ref={composer} aria-label="Dein Auftrag" placeholder={imThread ? "Was soll Jon als Nächstes tun?" : "Beschreibe, was Jon für dich bauen soll …"} rows={2} value={goal} maxLength={12000} onChange={e => setGoal(e.target.value)} onKeyDown={e => {if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {e.preventDefault(); if (sendbar) void start();}}}/>
          <div className="harness-composer-bar">
            <button type="button" aria-label="Projekt wählen" title="Projekt wählen" onClick={() => setSetupOpen(v => !v)}><Plus size={19}/></button>
            <button type="button" className="harness-project-badge" title={root || "Projektordner wählen"} onClick={() => setSetupOpen(v => !v)}><Folder size={14}/><span>{projectName}</span><ChevronDown size={12}/></button>
            <button type="button" className={"harness-access " + (allesErlaubt ? "frei" : "")} aria-pressed={!!allesErlaubt} disabled={allesErlaubt === null} onClick={() => void freigabeUmschalten()} title={allesErlaubt ? "Jon führt Befehle ohne Nachfrage aus. Klicken, um wieder jeden Befehl freizugeben." : "Jon fragt vor jedem Befehl. Klicken, um alle Befehle zu erlauben."}>{allesErlaubt ? <ShieldOff size={13}/> : <ShieldCheck size={13}/>}{allesErlaubt ? "Alle Befehle erlaubt" : "Befehle mit Freigabe"}</button>
            <div className="harness-composer-spacer"/>
            <button type="button" className={"harness-companion " + (mini ? "an" : "")} aria-pressed={mini} title="MiniJon zeigt den Fortschritt auf deinem Bildschirm" onClick={() => setMini(v => !v)}><Sparkles size={13}/><span>MiniJon begleitet</span></button>
            <span className="harness-model" title="Der Harness nutzt immer Jons Modell aus den Einstellungen">Jon · {modelLabel}</span>
            {working && letzte && <button type="button" className="harness-stop" disabled={busy} title="Aktuellen Auftrag stoppen" aria-label="Aktuellen Auftrag stoppen" onClick={() => void stop(letzte)}><Square size={13} fill="currentColor"/></button>}
            <button className="harness-send" type="submit" aria-label={imThread ? "Folgeauftrag senden" : "Auftrag starten"} title={working ? "Warte, bis der laufende Auftrag fertig ist" : imThread ? "Folgeauftrag senden" : "Auftrag starten"} disabled={!sendbar}>{busy ? <Loader2 size={18} className="harness-spin"/> : <ArrowUp size={19}/>}</button>
          </div>
        </form>
        <p className="harness-composer-note">{!root ? "Wähle zuerst einen Projektordner über + oder die Projektleiste." : imThread ? "Enter sendet den Folgeauftrag in diese Sitzung. Für ein neues Thema starte eine neue Sitzung." : "Jon arbeitet im gewählten Projekt. Mehrere Sitzungen können in verschiedenen Projekten gleichzeitig laufen."}</p>
      </div>
    </div>
    <AnimatePresence mode="wait">
      {rechts === "vorschau" && root && <motion.div key={"vorschau-" + root} className="harness-rechts" initial={{opacity: 0, x: 24}} animate={{opacity: 1, x: 0}} exit={{opacity: 0, x: 24}}><HarnessVorschau root={root} neuLaden={neuLaden} onClose={() => setRechts(null)}/></motion.div>}
      {rechts === "aenderungen" && imThread && <motion.aside key="aenderungen" className="harness-review" initial={{opacity: 0, x: 24}} animate={{opacity: 1, x: 0}} exit={{opacity: 0, x: 24}}><header><FileCode2 size={16}/><strong>Änderungen der Sitzung</strong><button aria-label="Änderungen schließen" onClick={() => setRechts(null)}><X size={17}/></button></header>{!changes.length && <p className="harness-muted">Noch keine Dateiänderungen.</p>}{changes.map(item => <details key={item.path} open><summary><FileCode2 size={14}/><span>{item.path}</span><b className="harness-added">+{item.added}</b><b className="harness-removed">−{item.removed}</b></summary><div className="harness-diff">{item.diffs.map((diff, index) => <pre key={index}>{diff.split("\n").map((line, row) => <span key={row} className={line.startsWith("+") && !line.startsWith("+++") ? "diff-add" : line.startsWith("-") && !line.startsWith("---") ? "diff-remove" : line.startsWith("@@") ? "diff-location" : ""}>{line || " "}{"\n"}</span>)}</pre>)}</div></details>)}</motion.aside>}
    </AnimatePresence>
  </section>;
}
