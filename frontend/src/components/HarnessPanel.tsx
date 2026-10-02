import {useEffect, useMemo, useRef, useState} from "react";
import {ArrowLeft, ArrowUp, Check, CheckCircle2, ChevronDown, ChevronRight, Code2, FileCode2, Folder, FolderPlus, GitBranch, ListChecks, Loader2, PanelLeft, PanelRight, Plus, Search, Settings2, ShieldCheck, Square, X} from "lucide-react";
import {addProject, getUserSettings, JonProject, pickFolderDialog} from "../lib/api";
import {finished, HarnessTask, harnessRequest, taskLabels} from "../lib/harness";
import MiniJonWork from "./MiniJonWork";
import MiniJonActivity from "./MiniJonActivity";
import "./harness-workspace.css";

function diffStats(diff: string) {
  let added = 0;
  let removed = 0;
  for (const line of diff.split("\n")) {
    if (line.startsWith("+") && !line.startsWith("+++")) added++;
    if (line.startsWith("-") && !line.startsWith("---")) removed++;
  }
  return {added, removed};
}

export default function HarnessPanel({standalone = false, onClose}: {standalone?: boolean; onClose?: () => void}) {
  const [projects, setProjects] = useState<JonProject[]>([]);
  const [root, setRoot] = useState("");
  const [goal, setGoal] = useState("");
  const [mini, setMini] = useState(true);
  const [modelLabel, setModelLabel] = useState({jon: "Dein Jon-Modell", mini: "Dein MiniJon-Modell"});
  const [tasks, setTasks] = useState<HarnessTask[]>([]);
  const [selected, setSelected] = useState("");
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
  const [settingsOpen, setSettingsOpen] = useState(false);
  const composer = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([harnessRequest<JonProject[]>("/projects", undefined, undefined, controller.signal), harnessRequest<{root: string}>("/harness/project?source=minijon", undefined, undefined, controller.signal)])
      .then(([items, context]) => {if (!controller.signal.aborted) {setProjects(items); setRoot(context.root || items[0]?.root || "");}})
      .catch(e => {if (!controller.signal.aborted) setError(e.message);});
    void getUserSettings().then(value => {if (!controller.signal.aborted) setModelLabel({jon: value.model || "Dein Jon-Modell", mini: value.pet_model || value.model || "Dein MiniJon-Modell"});}).catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        if (!document.hidden) {
          const list = await harnessRequest<HarnessTask[]>("/harness/tasks?brief=true", undefined, undefined, controller.signal);
          if (controller.signal.aborted) return;
          setTasks(list);
          if (!selected && !drafting && list.length) setSelected(list[0].id);
          if (selected) {
            const current = await harnessRequest<HarnessTask>(`/harness/tasks/${selected}`, undefined, undefined, controller.signal);
            if (!controller.signal.aborted) setTask(current);
          }
          setLoading(false);
        }
      } catch(e) {
        if (!controller.signal.aborted) {setError(e instanceof Error ? e.message : "Verbindung unterbrochen"); setLoading(false);}
      } finally {if (!controller.signal.aborted) timer = setTimeout(refresh, 3000);}
    };
    void refresh();
    return () => {controller.abort(); clearTimeout(timer);};
  }, [selected, drafting]);

  const action = async (fn: () => Promise<void>) => {setBusy(true); setError(""); try {await fn();} catch(e) {setError(e instanceof Error ? e.message : "Aktion fehlgeschlagen");} finally {setBusy(false);}};
  const choose = (item: HarnessTask) => {setDrafting(false); setSelected(item.id); setTask(null); setRoot(item.root);};
  const newTask = () => {setDrafting(true); setSelected(""); setTask(null); setGoal(""); setChangesOpen(false); composer.current?.focus();};
  const pick = () => action(async () => {
    const path = await pickFolderDialog();
    if (!path) return;
    const project = await addProject(path);
    setRoot(project.root); setProjects(items => items.some(p => p.id === project.id) ? items : [...items, project]); setSetupOpen(false); newTask();
  });
  const start = () => action(async () => {
    if (!goal.trim() || !root.trim()) return;
    const project = await addProject(root.trim());
    await harnessRequest("/harness/project", {root: project.root, source: "minijon"});
    await harnessRequest("/harness/project", {root: project.root, source: "app"});
    const created = await harnessRequest<HarnessTask>("/harness/tasks", {root: project.root, goal: goal.trim(), source: mini ? "minijon" : "app"});
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
      const counts = diffStats(change.diff);
      item.diffs.push(change.diff); item.added += counts.added; item.removed += counts.removed; result.set(change.path, item);
    }
    return [...result.values()];
  }, [task?.changes]);
  const stats = changes.reduce((sum, value) => ({added: sum.added + value.added, removed: sum.removed + value.removed}), {added: 0, removed: 0});
  const working = !!task && !finished.has(task.status);
  const latest = task?.log?.slice(-1)[0];

  return <section className={"harness-shell " + (standalone ? "harness-shell-full " : "harness-shell-embedded ") + (!sidebar ? "harness-sidebar-hidden " : "") + (changesOpen && task ? "harness-with-review" : "")} aria-label="Jon Harness">
    <nav className="harness-rail" aria-label="Harness Navigation"><button title="Zurück zu Jon" aria-label="Zurück zu Jon" onClick={onClose}><ArrowLeft size={18}/></button><div className="harness-rail-logo"><Code2 size={21}/></div><button title="Neuer Auftrag" aria-label="Neuer Auftrag" onClick={newTask}><Plus size={20}/></button><button title="Projekte" aria-label="Projektleiste einblenden" onClick={() => setSidebar(v => !v)}><Folder size={19}/></button><button title="Änderungen" aria-label="Änderungen einblenden" onClick={() => setChangesOpen(v => !v)} disabled={!task}><GitBranch size={19}/></button><div className="harness-rail-spacer"/><button title="MiniJon Einstellungen" aria-label="MiniJon Einstellungen" onClick={() => setSettingsOpen(v => !v)}><Settings2 size={19}/></button></nav>
    <aside className="harness-sidebar">
      <div className="harness-brand"><span>Jon <b>Harness</b></span><button aria-label="Aufträge durchsuchen" title="Suchen" onClick={() => setSearchOpen(v => !v)}><Search size={17}/></button></div>
      <button className="harness-new" onClick={newTask}><Plus size={16}/>Neuer Auftrag</button>
      {searchOpen && <input autoFocus className="harness-search" aria-label="Aufträge durchsuchen" placeholder="Aufträge suchen …" value={search} onChange={e => setSearch(e.target.value)}/>}
      <div className="harness-section-label"><span>Projekte</span><button title="Projekt hinzufügen" aria-label="Projekt hinzufügen" disabled={busy} onClick={() => void pick()}><FolderPlus size={16}/></button></div>
      <div className="harness-project-list">{projects.map(project => <details key={project.id} open={root === project.root || undefined}><summary onClick={() => setRoot(project.root)}><Folder size={15}/><span>{project.name}</span><ChevronRight size={13}/></summary><div className="harness-task-list">{visibleTasks.filter(item => item.root === project.root).map(item => <button key={item.id} className={selected === item.id ? "selected" : ""} onClick={() => choose(item)}><span>{item.goal}</span><i className={"harness-state-dot state-" + item.status} title={taskLabels[item.status] || item.status}/></button>)}<button className="harness-project-new" onClick={() => {setRoot(project.root); newTask();}}><Plus size={13}/>Auftrag in diesem Projekt</button></div></details>)}{!projects.length && !loading && <button className="harness-empty-project" onClick={() => void pick()}><FolderPlus size={18}/>Erstes Projekt öffnen</button>}</div>
      <div className="harness-section-label">Letzte Aufträge</div>
      <div className="harness-task-list harness-recents">{visibleTasks.slice(0, 8).map(item => <button key={item.id} className={selected === item.id ? "selected" : ""} onClick={() => choose(item)}><span>{item.goal}</span><i className={"harness-state-dot state-" + item.status} title={taskLabels[item.status] || item.status}/></button>)}{loading && <span className="harness-muted">Lädt Aufträge …</span>}{!loading && !visibleTasks.length && <span className="harness-muted">{search ? "Keine passenden Aufträge" : "Dein erster Auftrag wartet auf dich."}</span>}</div>
      <div className="harness-sidebar-foot"><span className="harness-companion-dot"/>MiniJon arbeitet mit dir<button aria-label="Projektpfad eingeben" title="Projektpfad eingeben" onClick={() => setSetupOpen(v => !v)}><Settings2 size={15}/></button></div>
    </aside>
    <div className="harness-main">
      <header className="harness-topbar"><button aria-label="Projektleiste umschalten" title="Projektleiste umschalten" onClick={() => setSidebar(v => !v)}><PanelLeft size={17}/></button><Folder size={16}/><strong>{task?.goal || "Neuer Auftrag"}</strong><div className="harness-topbar-actions">{task && <span className={"harness-status status-" + task.status}>{working && <Loader2 size={13} className="harness-spin"/>}{taskLabels[task.status] || task.status}</span>}<button aria-label="Änderungen anzeigen" title="Änderungen anzeigen" onClick={() => setChangesOpen(v => !v)} disabled={!task}><PanelRight size={17}/></button></div></header>
      {error && <div role="alert" className="harness-error"><span>{error}</span><button aria-label="Fehler schließen" onClick={() => setError("")}><X size={16}/></button></div>}
      <main className="harness-feed">
        {!task && <div className="harness-welcome"><MiniJonActivity activity="coding" label="Bereit, gemeinsam etwas zu bauen"/><h1>Was bauen wir heute?</h1><p>Wähle dein Projekt und beschreibe dein Ziel.<br/>Jon liest, bearbeitet und prüft die Änderungen im Ordner.</p><div className="harness-suggestions">{["Finde und behebe einen Fehler", "Erkläre mir dieses Projekt", "Verbessere die Suche und prüfe sie"].map(value => <button key={value} onClick={() => {setGoal(value); composer.current?.focus();}}>{value}<ArrowUp size={14}/></button>)}</div></div>}
        {task && <div className="harness-thread">
          <div className="harness-user-message">{task.goal}</div>
          <div className="harness-agent-heading"><span className="harness-agent-symbol"><Code2 size={17}/></span><strong>Jon Harness</strong><span>{task.root.split(/[\\/]/).filter(Boolean).at(-1)}</span></div>
          <MiniJonActivity activity={task.status === "planning" ? "planning" : "coding"} status={task.status} label={working ? (latest?.message || (taskLabels[task.status] || task.status)) : (taskLabels[task.status] || task.status)}/>
          {!!task.steps.length && <details className="harness-plan" open><summary><ListChecks size={16}/><span>Arbeitsplan</span><ChevronDown size={14}/></summary><ol>{task.steps.map((step, index) => <li key={index}><span className="harness-step-number">{task.status === "done" ? <Check size={12}/> : index + 1}</span>{step}</li>)}</ol></details>}
          {task.pending && <div className="harness-approval"><div><ShieldCheck size={18}/><strong>Deine Freigabe ist nötig</strong></div><pre>{task.pending.args.command}</pre><p>{task.pending.args.cwd}</p><p>{task.pending.notice}</p><div className="harness-approval-actions"><button disabled={busy} onClick={() => void decide(true)}>Diesen Befehl erlauben</button><button disabled={busy} onClick={() => void decide(false)}>Ablehnen</button></div></div>}
          {task.specialists?.map((agent, index) => <details key={index} className="harness-specialist"><summary><span className="harness-companion-dot"/>{agent.role}<span>{taskLabels[agent.status] || agent.status}</span></summary><p className="harness-muted">{agent.question}</p><p>{agent.result || agent.error || "Prüft die Teilaufgabe …"}</p></details>)}
          {task.summary && <div className="harness-answer">{task.summary}</div>}
          {!!changes.length && <div className="harness-changes-card"><div className="harness-changes-head"><FileCode2 size={21}/><div><strong>{changes.length} {changes.length === 1 ? "Datei bearbeitet" : "Dateien bearbeitet"}</strong><div><span className="harness-added">+{stats.added}</span><span className="harness-removed">−{stats.removed}</span></div></div><button onClick={() => setChangesOpen(true)}>Änderungen anzeigen</button></div>{changes.slice(0, 3).map(item => <button className="harness-file-row" key={item.path} onClick={() => setChangesOpen(true)}><span>{item.path}</span><span><b className="harness-added">+{item.added}</b><b className="harness-removed">−{item.removed}</b></span></button>)}{changes.length > 3 && <button className="harness-more-files" onClick={() => setChangesOpen(true)}>{changes.length - 3} weitere Dateien anzeigen <ChevronDown size={14}/></button>}</div>}
          {!!task.checks.length && <div className="harness-checks">{task.checks.map((check, index) => <details key={index}><summary>{check.ok ? <CheckCircle2 size={16} className="harness-added"/> : <X size={16} className="harness-removed"/>}<code>{check.command}</code><span>{check.ok ? "Bestanden" : "Fehlgeschlagen"}</span></summary><pre>{check.output || "Keine Ausgabe"}</pre></details>)}</div>}
          {!!task.log?.length && <details className="harness-log"><summary>Aktivitätsverlauf <ChevronDown size={13}/></summary><ol>{task.log.map((entry, index) => <li key={index}><time>{new Date(entry.time * 1000).toLocaleTimeString("de-AT", {hour: "2-digit", minute: "2-digit"})}</time><b>{entry.tool || entry.type}</b><span>{entry.message}</span></li>)}</ol></details>}
        </div>}
      </main>
      <div className="harness-composer-wrap">
        {setupOpen && <div className="harness-project-setup"><label>Projektordner<input aria-label="Arbeitsordner" value={root} onChange={e => setRoot(e.target.value)} placeholder="C:\Projekte\MeineApp"/></label><button disabled={busy} onClick={() => void pick()}><FolderPlus size={16}/>Ordner wählen</button><button aria-label="Projektauswahl schließen" onClick={() => setSetupOpen(false)}><X size={15}/></button></div>}
        <form className="harness-composer" onSubmit={e => {e.preventDefault(); void start();}}>
          <textarea ref={composer} aria-label="Dein Auftrag" placeholder={task ? "Beschreibe deinen nächsten Auftrag …" : "Beschreibe, was Jon für dich bauen soll …"} rows={2} value={goal} maxLength={12000} onChange={e => setGoal(e.target.value)} onKeyDown={e => {if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {e.preventDefault(); if (!busy && goal.trim() && root.trim()) void start();}}}/>
          <div className="harness-composer-bar"><button type="button" aria-label="Projekt wählen" title="Projekt wählen" onClick={() => setSetupOpen(v => !v)}><Plus size={19}/></button><button type="button" className="harness-project-badge" title={root || "Projektordner wählen"} onClick={() => setSetupOpen(v => !v)}><Folder size={14}/><span>{projectName}</span><ChevronDown size={12}/></button><span className="harness-access"><ShieldCheck size={13}/>Befehle mit Freigabe</span><div className="harness-composer-spacer"/><label className="harness-model-choice"><select aria-label="Assistent auswählen" value={mini ? "mini" : "jon"} onChange={e => setMini(e.target.value === "mini")}><option value="mini">MiniJon · {modelLabel.mini}</option><option value="jon">Jon · {modelLabel.jon}</option></select><ChevronDown size={12}/></label>{working && <button type="button" className="harness-stop" disabled={busy} title="Aktuellen Auftrag stoppen" aria-label="Aktuellen Auftrag stoppen" onClick={() => void stop()}><Square size={13} fill="currentColor"/></button>}<button className="harness-send" type="submit" aria-label="Auftrag starten" title="Auftrag starten" disabled={busy || !goal.trim() || !root.trim()}>{busy ? <Loader2 size={18} className="harness-spin"/> : <ArrowUp size={19}/>}</button></div>
        </form><p className="harness-composer-note">{root ? "Jon arbeitet im gewählten Projekt. Mehrere Aufträge können in verschiedenen Projekten laufen." : "Wähle zuerst einen Projektordner über + oder die Projektleiste."}</p>
      </div>
    </div>
    {changesOpen && task && <aside className="harness-review"><header><FileCode2 size={16}/><strong>Änderungen</strong><button aria-label="Änderungen schließen" onClick={() => setChangesOpen(false)}><X size={17}/></button></header>{!changes.length && <p className="harness-muted">Noch keine Dateiänderungen.</p>}{changes.map(item => <details key={item.path} open><summary><FileCode2 size={14}/><span>{item.path}</span><b className="harness-added">+{item.added}</b><b className="harness-removed">−{item.removed}</b></summary><div className="harness-diff">{item.diffs.map((diff, index) => <pre key={index}>{diff.split("\n").map((line, row) => <span key={row} className={line.startsWith("+") && !line.startsWith("+++") ? "diff-add" : line.startsWith("-") && !line.startsWith("---") ? "diff-remove" : line.startsWith("@@") ? "diff-location" : ""}>{line || " "}{"\n"}</span>)}</pre>)}</div></details>)}</aside>}
    {settingsOpen && <div className="harness-settings-backdrop" onClick={() => setSettingsOpen(false)}><section className="harness-settings" aria-label="MiniJon Einstellungen" onClick={e => e.stopPropagation()}><header><strong>MiniJon an deiner Seite</strong><button aria-label="Einstellungen schließen" onClick={() => setSettingsOpen(false)}><X size={17}/></button></header><MiniJonWork/></section></div>}
  </section>;
}
