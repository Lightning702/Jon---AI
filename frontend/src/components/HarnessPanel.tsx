import {useEffect, useMemo, useRef, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {ArrowLeft, ArrowUp, CheckCircle2, ChevronDown, ChevronRight, Code2, FileCode2, Folder, FolderPlus, GitBranch, Loader2, PanelLeft, PanelRight, Plus, Search, Settings2, ShieldCheck, Sparkles, Square, X} from "lucide-react";
import {addProject, getUserSettings, JonProject, pickFolderDialog} from "../lib/api";
import {finished, HarnessTask, harnessRequest, taskLabels} from "../lib/harness";
import AgentenBuehne from "./agenten/AgentenBuehne";
import {HarnessAnsicht} from "./agenten/HarnessKarte";
import {diffZahlen, rolle, TEIL_TEXT} from "./agenten/daten";
import "./harness-workspace.css";

const VORSCHLAEGE = ["Finde und behebe einen Fehler", "Erkläre mir dieses Projekt", "Schreibe Tests für die wichtigsten Funktionen", "Verbessere die Oberfläche und prüfe den Build"];

export default function HarnessPanel({standalone = false, onClose, initialTask}: {standalone?: boolean; onClose?: () => void; initialTask?: string}) {
  const [projects, setProjects] = useState<JonProject[]>([]);
  const [root, setRoot] = useState("");
  const [goal, setGoal] = useState("");
  const [mini, setMini] = useState(false);
  const [modelLabel, setModelLabel] = useState("Jons Modell");
  const [tasks, setTasks] = useState<HarnessTask[]>([]);
  const [selected, setSelected] = useState(initialTask || "");
  const [task, setTask] = useState<HarnessTask | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [sidebar, setSidebar] = useState(true);
  const [changesOpen, setChangesOpen] = useState(false);
  const [setupOpen, setSetupOpen] = useState(false);
  const composer = useRef<HTMLTextAreaElement>(null);
  const feed = useRef<HTMLElement>(null);
  const startRoot = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([harnessRequest<JonProject[]>("/projects", undefined, undefined, controller.signal), harnessRequest<{root: string}>("/harness/project?source=app", undefined, undefined, controller.signal)])
      .then(([items, context]) => {if (!controller.signal.aborted) {setProjects(items); setRoot(r => r || context.root || items[0]?.root || "");}})
      .catch(e => {if (!controller.signal.aborted) setError(e.message);});
    void getUserSettings().then(value => {if (!controller.signal.aborted) setModelLabel(value.model || "Jons Modell");}).catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      let fast = false;
      try {
        if (!document.hidden) {
          const list = await harnessRequest<HarnessTask[]>("/harness/tasks?brief=true", undefined, undefined, controller.signal);
          if (controller.signal.aborted) return;
          setTasks(list);
          if (!selected && !drafting && list.length) setSelected(list[0].id);
          if (selected) {
            const current = await harnessRequest<HarnessTask>(`/harness/tasks/${selected}`, undefined, undefined, controller.signal);
            if (controller.signal.aborted) return;
            setTask(current);
            if (current.id === initialTask && !startRoot.current) {startRoot.current = true; setRoot(current.root);}
            fast = !finished.has(current.status);
          }
          setLoading(false);
        }
      } catch(e) {
        if (!controller.signal.aborted) {setError(e instanceof Error ? e.message : "Verbindung unterbrochen"); setLoading(false);}
      } finally {if (!controller.signal.aborted) timer = setTimeout(refresh, fast ? 1200 : 3000);}
    };
    void refresh();
    return () => {controller.abort(); clearTimeout(timer);};
  }, [selected, drafting]);

  const action = async (fn: () => Promise<void>) => {setBusy(true); setError(""); try {await fn();} catch(e) {setError(e instanceof Error ? e.message : "Aktion fehlgeschlagen");} finally {setBusy(false);}};
  const choose = (item: HarnessTask) => {setDrafting(false); setSelected(item.id); setTask(null); setRoot(item.root);};
  const newTask = () => {setDrafting(true); setSelected(""); setTask(null); setGoal(""); setChangesOpen(false); setTimeout(() => composer.current?.focus(), 30);};
  const pick = () => action(async () => {
    const path = await pickFolderDialog();
    if (!path) return;
    const project = await addProject(path);
    setRoot(project.root); setProjects(items => items.some(p => p.id === project.id) ? items : [...items, project]); setSetupOpen(false); newTask();
  });
  const start = () => action(async () => {
    if (!goal.trim() || !root.trim()) return;
    const project = await addProject(root.trim());
    await harnessRequest("/harness/project", {root: project.root, source: "app"});
    if (mini) await harnessRequest("/harness/project", {root: project.root, source: "minijon"});
    const created = await harnessRequest<HarnessTask>("/harness/tasks", {root: project.root, goal: goal.trim(), source: "app", companion: mini});
    setProjects(items => items.some(p => p.id === project.id) ? items : [...items, project]);
    setTask(created); setSelected(created.id); setDrafting(false); setTasks(items => [created, ...items]); setGoal("");
    if (mini) await window.jon?.showPet?.().catch(() => setError("Auftrag läuft. MiniJons Fenster konnte nicht geöffnet werden."));
  });
  const decide = (allow: boolean) => action(async () => {
    if (!task?.pending) return;
    await harnessRequest(`/harness/tasks/${task.id}/approve`, {approval_id: task.pending.id, allow});
    setTask(await harnessRequest<HarnessTask>(`/harness/tasks/${task.id}`));
  });
  const stop = () => action(async () => {if (task) setTask(await harnessRequest<HarnessTask>(`/harness/tasks/${task.id}/cancel`, {}));});
  const visibleTasks = tasks.filter(item => (item.goal + " " + item.root).toLowerCase().includes(search.toLowerCase()));
  const projectName = projects.find(p => p.root === root)?.name || root.split(/[\\/]/).filter(Boolean).at(-1) || "Projekt wählen";
  const changes = useMemo(() => {
    const result = new Map<string, {path: string; diffs: string[]; added: number; removed: number}>();
    for (const change of task?.changes || []) {
      const item = result.get(change.path) || {path: change.path, diffs: [], added: 0, removed: 0};
      const counts = diffZahlen(change.diff);
      item.diffs.push(change.diff); item.added += counts.plus; item.removed += counts.minus; result.set(change.path, item);
    }
    return [...result.values()];
  }, [task?.changes]);
  const stats = changes.reduce((sum, value) => ({added: sum.added + value.added, removed: sum.removed + value.removed}), {added: 0, removed: 0});
  const working = !!task && !finished.has(task.status);
  useEffect(() => {if (working) feed.current?.scrollTo({top: feed.current.scrollHeight});}, [working, task?.log?.length, task?.pending?.id]);

  return <section className={"harness-shell " + (standalone ? "harness-shell-full " : "harness-shell-embedded ") + (!sidebar ? "harness-sidebar-hidden " : "") + (changesOpen && task ? "harness-with-review" : "")} aria-label="Jon Harness">
    <nav className="harness-rail" aria-label="Harness Navigation">
      {onClose && <button title="Zurück zu Jon" aria-label="Zurück zu Jon" onClick={onClose}><ArrowLeft size={18}/></button>}
      <div className={"harness-rail-logo " + (working ? "aktiv" : "")}><Code2 size={17}/></div>
      <button title="Neuer Auftrag" aria-label="Neuer Auftrag" onClick={newTask}><Plus size={20}/></button>
      <button title="Projekte" aria-label="Projektleiste einblenden" onClick={() => setSidebar(v => !v)}><Folder size={19}/></button>
      <button title="Änderungen" aria-label="Änderungen einblenden" onClick={() => setChangesOpen(v => !v)} disabled={!task}><GitBranch size={19}/></button>
      <div className="harness-rail-spacer"/>
      <button title="Projektpfad eingeben" aria-label="Projektpfad eingeben" onClick={() => setSetupOpen(v => !v)}><Settings2 size={19}/></button>
    </nav>
    <aside className="harness-sidebar">
      <div className="harness-brand"><span>Jon <b>Harness</b></span><button aria-label="Aufträge durchsuchen" title="Suchen" onClick={() => setSearchOpen(v => !v)}><Search size={17}/></button></div>
      <button className="harness-new" onClick={newTask}><Plus size={16}/>Neuer Auftrag</button>
      <AnimatePresence>{searchOpen && <motion.input initial={{opacity: 0, height: 0}} animate={{opacity: 1, height: "auto"}} exit={{opacity: 0, height: 0}} autoFocus className="harness-search" aria-label="Aufträge durchsuchen" placeholder="Aufträge suchen …" value={search} onChange={e => setSearch(e.target.value)}/>}</AnimatePresence>
      <div className="harness-section-label"><span>Projekte</span><button title="Projekt hinzufügen" aria-label="Projekt hinzufügen" disabled={busy} onClick={() => void pick()}><FolderPlus size={16}/></button></div>
      <div className="harness-project-list">{projects.map(project => <details key={project.id} open={root === project.root || undefined}><summary onClick={() => setRoot(project.root)}><Folder size={15}/><span>{project.name}</span><ChevronRight size={13}/></summary><div className="harness-task-list">{visibleTasks.filter(item => item.root === project.root).map(item => <button key={item.id} className={selected === item.id ? "selected" : ""} onClick={() => choose(item)}><span>{item.goal}</span><i className={"harness-state-dot state-" + item.status} title={taskLabels[item.status] || item.status}/></button>)}<button className="harness-project-new" onClick={() => {setRoot(project.root); newTask();}}><Plus size={13}/>Auftrag in diesem Projekt</button></div></details>)}{!projects.length && !loading && <button className="harness-empty-project" onClick={() => void pick()}><FolderPlus size={18}/>Erstes Projekt öffnen</button>}</div>
      <div className="harness-section-label">Letzte Aufträge</div>
      <div className="harness-task-list harness-recents">{visibleTasks.slice(0, 8).map(item => <button key={item.id} className={selected === item.id ? "selected" : ""} onClick={() => choose(item)}><span>{item.goal}</span><i className={"harness-state-dot state-" + item.status} title={taskLabels[item.status] || item.status}/></button>)}{loading && <span className="harness-muted">Lädt Aufträge …</span>}{!loading && !visibleTasks.length && <span className="harness-muted">{search ? "Keine passenden Aufträge" : "Dein erster Auftrag wartet auf dich."}</span>}</div>
      <div className="harness-sidebar-foot"><span className="harness-companion-dot"/><span>Arbeitet mit <b>{modelLabel}</b></span></div>
    </aside>
    <div className="harness-main">
      <header className="harness-topbar"><button aria-label="Projektleiste umschalten" title="Projektleiste umschalten" onClick={() => setSidebar(v => !v)}><PanelLeft size={17}/></button><Folder size={16}/><strong>{task?.goal || "Neuer Auftrag"}</strong><div className="harness-topbar-actions">{task && <span className={"harness-status status-" + task.status}>{working && <Loader2 size={13} className="harness-spin"/>}{taskLabels[task.status] || task.status}</span>}<button aria-label="Änderungen anzeigen" title="Änderungen anzeigen" onClick={() => setChangesOpen(v => !v)} disabled={!task}><PanelRight size={17}/></button></div></header>
      <AnimatePresence>{error && <motion.div initial={{height: 0, opacity: 0}} animate={{height: "auto", opacity: 1}} exit={{height: 0, opacity: 0}} role="alert" className="harness-error"><span>{error}</span><button aria-label="Fehler schließen" onClick={() => setError("")}><X size={16}/></button></motion.div>}</AnimatePresence>
      <main className="harness-feed" ref={feed}>
        <AnimatePresence mode="wait">
        {!task && <motion.div key="welcome" className="harness-welcome" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -10}}>
          <div className="harness-hero ab"><AgentenBuehne phase="bereit" knoten={[]} kernIcon={Code2} kernText="Harness"/></div>
          <h1>Was bauen wir heute?</h1>
          <p>Wähle ein Projekt und beschreibe dein Ziel. Jon plant, liest, ändert und testet – und holt sich bei Bedarf Fachagenten zur Gegenprüfung.</p>
          <div className="harness-suggestions">{VORSCHLAEGE.map((value, i) => <motion.button key={value} initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={{delay: 0.08 * i}} onClick={() => {setGoal(value); composer.current?.focus();}}>{value}<ArrowUp size={14}/></motion.button>)}</div>
        </motion.div>}
        {task && <motion.div key={task.id} className="harness-thread" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}}>
          <div className="harness-user-message">{task.goal}</div>
          <HarnessAnsicht auftrag={task} beschaeftigt={busy} onStopp={() => void stop()} onEntscheiden={allow => void decide(allow)}/>
          {!!task.specialists?.length && <div className="harness-specialists"><div className="harness-section-label" style={{margin: "22px 0 10px"}}>Fachagenten</div>{task.specialists.map((agent, index) => {
            const r = rolle(agent.profil || "coding");
            const Icon = r.icon;
            return <details key={index} className="harness-specialist" style={{["--farbe" as string]: r.farbe}}><summary><span className="harness-specialist-icon"><Icon size={14}/></span>{agent.role}<span>{TEIL_TEXT[agent.status] || agent.status}{agent.dauer ? ` · ${Math.round(agent.dauer)}s` : ""}</span></summary><p className="harness-muted">{agent.question}</p><p>{agent.result || agent.error || "Prüft die Teilaufgabe …"}</p></details>;
          })}</div>}
          {!!changes.length && <div className="harness-changes-card"><div className="harness-changes-head"><FileCode2 size={21}/><div><strong>{changes.length} {changes.length === 1 ? "Datei bearbeitet" : "Dateien bearbeitet"}</strong><div><span className="harness-added">+{stats.added}</span><span className="harness-removed">−{stats.removed}</span></div></div><button onClick={() => setChangesOpen(true)}>Änderungen anzeigen</button></div>{changes.slice(0, 3).map(item => <button className="harness-file-row" key={item.path} onClick={() => setChangesOpen(true)}><span>{item.path}</span><span><b className="harness-added">+{item.added}</b><b className="harness-removed">−{item.removed}</b></span></button>)}{changes.length > 3 && <button className="harness-more-files" onClick={() => setChangesOpen(true)}>{changes.length - 3} weitere Dateien anzeigen <ChevronDown size={14}/></button>}</div>}
          {!!task.checks.length && <div className="harness-checks">{task.checks.map((check, index) => <details key={index}><summary>{check.ok ? <CheckCircle2 size={16} className="harness-added"/> : <X size={16} className="harness-removed"/>}<code>{check.command}</code><span>{check.ok ? "Bestanden" : "Fehlgeschlagen"}</span></summary><pre>{check.output || "Keine Ausgabe"}</pre></details>)}</div>}
          {!!task.log?.length && <details className="harness-log"><summary>Aktivitätsverlauf <ChevronDown size={13}/></summary><ol>{task.log.map((entry, index) => <li key={index}><time>{new Date(entry.time * 1000).toLocaleTimeString("de-AT", {hour: "2-digit", minute: "2-digit"})}</time><b>{entry.tool || entry.type}</b><span>{entry.message}</span></li>)}</ol></details>}
        </motion.div>}
        </AnimatePresence>
      </main>
      <div className="harness-composer-wrap">
        <AnimatePresence>{setupOpen && <motion.div className="harness-project-setup" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: 8}}><label>Projektordner<input aria-label="Arbeitsordner" value={root} onChange={e => setRoot(e.target.value)} placeholder="C:\Projekte\MeineApp"/></label><button disabled={busy} onClick={() => void pick()}><FolderPlus size={16}/>Ordner wählen</button><button aria-label="Projektauswahl schließen" onClick={() => setSetupOpen(false)}><X size={15}/></button></motion.div>}</AnimatePresence>
        <form className={"harness-composer " + (working ? "arbeitet" : "")} onSubmit={e => {e.preventDefault(); void start();}}>
          <textarea ref={composer} aria-label="Dein Auftrag" placeholder={task ? "Beschreibe deinen nächsten Auftrag …" : "Beschreibe, was Jon für dich bauen soll …"} rows={2} value={goal} maxLength={12000} onChange={e => setGoal(e.target.value)} onKeyDown={e => {if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {e.preventDefault(); if (!busy && goal.trim() && root.trim()) void start();}}}/>
          <div className="harness-composer-bar">
            <button type="button" aria-label="Projekt wählen" title="Projekt wählen" onClick={() => setSetupOpen(v => !v)}><Plus size={19}/></button>
            <button type="button" className="harness-project-badge" title={root || "Projektordner wählen"} onClick={() => setSetupOpen(v => !v)}><Folder size={14}/><span>{projectName}</span><ChevronDown size={12}/></button>
            <span className="harness-access"><ShieldCheck size={13}/>Befehle mit Freigabe</span>
            <div className="harness-composer-spacer"/>
            <button type="button" className={"harness-companion " + (mini ? "an" : "")} aria-pressed={mini} title="MiniJon zeigt den Fortschritt auf deinem Bildschirm" onClick={() => setMini(v => !v)}><Sparkles size={13}/>MiniJon begleitet</button>
            <span className="harness-model" title="Der Harness nutzt immer Jons Modell aus den Einstellungen">Jon · {modelLabel}</span>
            {working && <button type="button" className="harness-stop" disabled={busy} title="Aktuellen Auftrag stoppen" aria-label="Aktuellen Auftrag stoppen" onClick={() => void stop()}><Square size={13} fill="currentColor"/></button>}
            <button className="harness-send" type="submit" aria-label="Auftrag starten" title="Auftrag starten" disabled={busy || !goal.trim() || !root.trim()}>{busy ? <Loader2 size={18} className="harness-spin"/> : <ArrowUp size={19}/>}</button>
          </div>
        </form>
        <p className="harness-composer-note">{root ? "Jon arbeitet im gewählten Projekt. Mehrere Aufträge können in verschiedenen Projekten gleichzeitig laufen." : "Wähle zuerst einen Projektordner über + oder die Projektleiste."}</p>
      </div>
    </div>
    <AnimatePresence>{changesOpen && task && <motion.aside className="harness-review" initial={{opacity: 0, x: 24}} animate={{opacity: 1, x: 0}} exit={{opacity: 0, x: 24}}><header><FileCode2 size={16}/><strong>Änderungen</strong><button aria-label="Änderungen schließen" onClick={() => setChangesOpen(false)}><X size={17}/></button></header>{!changes.length && <p className="harness-muted">Noch keine Dateiänderungen.</p>}{changes.map(item => <details key={item.path} open><summary><FileCode2 size={14}/><span>{item.path}</span><b className="harness-added">+{item.added}</b><b className="harness-removed">−{item.removed}</b></summary><div className="harness-diff">{item.diffs.map((diff, index) => <pre key={index}>{diff.split("\n").map((line, row) => <span key={row} className={line.startsWith("+") && !line.startsWith("+++") ? "diff-add" : line.startsWith("-") && !line.startsWith("---") ? "diff-remove" : line.startsWith("@@") ? "diff-location" : ""}>{line || " "}{"\n"}</span>)}</pre>)}</div></details>)}</motion.aside>}</AnimatePresence>
  </section>;
}
