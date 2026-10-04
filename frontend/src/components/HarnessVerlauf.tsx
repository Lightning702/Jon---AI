import {useMemo} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {AlertTriangle, Check, CheckCircle2, ChevronDown, Clock, Code2, FileCode2, FilePlus2, FileSearch, FolderOpen, Info, ListChecks, Loader2, PenLine, Search, ShieldAlert, SquareTerminal, FlaskConical, Users, XCircle} from "lucide-react";
import {HarnessTask} from "../lib/harness";
import {ENDE, HARNESS_TEXT} from "./agenten/daten";
import {useJetzt} from "./agenten/live";
import "./harness-verlauf.css";

type Eintrag = NonNullable<HarnessTask["log"]>[number];

const PHASEN = ["Planen", "Analysieren", "Implementieren", "Testen", "Fertigstellen"];
const PHASE_VON: Record<string, number> = {plan: 0, list: 1, read: 1, search: 1, delegate: 1, edit: 2, create: 2, command: 2, verify: 3, finish: 4};

const TEST = /(^|[\s/\\])(test|tests|pytest|jest|vitest|unittest|tsc|lint|eslint|check|build)([\s.:_-]|$)|test_\w+|\w+\.test\./i;
const istTest = (e: Eintrag) => e.tool === "verify" || (e.tool === "command" && TEST.test(e.message || ""));

function phaseDes(e: Eintrag): number | undefined {
  if (!e.tool || e.type === "notiz" || PHASE_VON[e.tool] === undefined) return undefined;
  return istTest(e) ? 3 : PHASE_VON[e.tool];
}

function phaseVon(task: HarnessTask, log: Eintrag[]): number {
  if (task.status === "done") return 4;
  if (task.status === "verifying") return 3;
  for (let i = log.length - 1; i >= 0; i--) {
    const phase = phaseDes(log[i]);
    if (phase !== undefined) return phase;
  }
  return 0;
}

function dauer(sekunden: number): string {
  const wert = Math.max(0, Math.round(sekunden));
  if (wert < 60) return `${wert} Sek.`;
  const minuten = Math.floor(wert / 60);
  if (minuten < 60) return `${minuten} min`;
  return `${Math.floor(minuten / 60)} h ${String(minuten % 60).padStart(2, "0")} min`;
}

function vor(sekunden: number): string {
  const wert = Math.max(0, Math.round(sekunden));
  if (wert < 60) return `vor ${wert} Sek.`;
  if (wert < 3600) return `vor ${Math.floor(wert / 60)} Min.`;
  return `vor ${Math.floor(wert / 3600)} Std.`;
}

function uhr(sekunden: number) {
  return new Date(sekunden * 1000).toLocaleTimeString("de-AT", {hour: "2-digit", minute: "2-digit"});
}

function aktion(e: Eintrag): {titel: string; icon: typeof Code2; art: string; text?: string; code?: string} | null {
  const test = istTest(e);
  if (e.type === "running_command") return {titel: test ? "Test gestartet" : "Befehl gestartet", icon: test ? FlaskConical : SquareTerminal, art: "befehl", code: e.message};
  if (e.type === "action_error") return {titel: "Schritt korrigiert", icon: AlertTriangle, art: "warn", text: e.message};
  if (e.type === "approval_required") return {titel: "Freigabe angefragt", icon: ShieldAlert, art: "warn", code: e.message};
  if (e.type === "hinweis") return {titel: "Hinweis", icon: Info, art: "info", text: e.message};
  if (e.type !== "action") return null;
  switch (e.tool) {
    case "plan": return {titel: "Arbeitsplan erstellt", icon: ListChecks, art: "plan", text: e.message};
    case "list": return {titel: "Ordner angesehen", icon: FolderOpen, art: "lesen", code: e.pfad || e.message};
    case "read": return {titel: "Datei gelesen", icon: FileSearch, art: "lesen", code: e.pfad || e.message};
    case "search": return {titel: "Im Projekt gesucht", icon: Search, art: "lesen", code: e.message};
    case "edit": return {titel: "Datei geändert", icon: PenLine, art: "aendern", code: e.pfad || e.message};
    case "create": return {titel: "Datei erstellt", icon: FilePlus2, art: "aendern", code: e.pfad || e.message};
    case "delegate": return {titel: "Fachagent befragt", icon: Users, art: "lesen", text: e.message};
    case "verify":
    case "command": return {titel: test ? (e.ok ? "Test erfolgreich" : "Test fehlgeschlagen") : (e.ok ? "Befehl erfolgreich" : "Befehl fehlgeschlagen"), icon: e.ok ? CheckCircle2 : XCircle, art: e.ok ? "ok" : "fehler", code: e.message};
    default: return {titel: e.tool || "Aktion", icon: Code2, art: "lesen", text: e.message};
  }
}

export default function HarnessVerlauf({task, busy, onStopp, onEntscheiden}: {task: HarnessTask; busy: boolean; onStopp: () => void; onEntscheiden: (allow: boolean) => void}) {
  const aktiv = !ENDE.has(task.status);
  const jetzt = useJetzt(aktiv);
  const log: Eintrag[] = task.log || [];
  const phase = phaseVon(task, log);
  const besucht = useMemo(() => new Set(log.map(phaseDes).filter((p): p is number => p !== undefined)), [log]);
  const planSchritt = task.plan_schritt || (task.steps.length ? 1 : 0);
  const letzteZeit = log.length ? log[log.length - 1].time : task.updated_at || task.created_at || jetzt;
  const laufzeit = (aktiv ? jetzt : task.updated_at || jetzt) - (task.created_at || jetzt);
  const letzteNotiz = [...log].reverse().find(e => e.type === "notiz");
  const laeuftBefehl = aktiv && log.length > 0 && log[log.length - 1].type === "running_command";
  const liveText = task.pending ? "Wartet auf deine Freigabe für einen Befehl." : letzteNotiz && letzteNotiz.time >= letzteZeit - 120 ? letzteNotiz.message : HARNESS_TEXT[task.status] || "Arbeitet …";
  const sichtbar = useMemo(() => log.filter(e => e.type !== "finished"), [log]);
  const LiveIcon = laeuftBefehl ? (istTest(log[log.length - 1]) ? FlaskConical : SquareTerminal) : Code2;

  return <div className="hv">
    <div className="hv-status">
      <div className="hv-phasen" aria-label="Arbeitsstatus">
        {PHASEN.map((name, i) => {
          const fertig = aktiv ? i < phase : task.status === "done" || besucht.has(i);
          const jetztAktiv = i === phase && aktiv;
          return <span key={name} className={"hv-phase " + (fertig ? "fertig" : jetztAktiv ? "aktiv" : "offen")}>
            <i>{fertig ? <Check size={10} strokeWidth={3}/> : jetztAktiv ? <span className="hv-puls"/> : null}</i>{name}
          </span>;
        })}
      </div>
      <div className="hv-zeiten">
        <span><Clock size={12}/>{aktiv ? "Läuft seit " : "Dauer "}<b>{dauer(laufzeit)}</b></span>
        {aktiv && <span>Letzte Aktivität · {vor(jetzt - letzteZeit)}</span>}
        {aktiv && <button className="hv-stopp" disabled={busy || task.status === "cancelling"} onClick={onStopp}>Stop</button>}
      </div>
    </div>

    {task.steps.length > 0 && <details className="hv-plan" open>
      <summary><ListChecks size={14}/><span>Arbeitsplan · {task.steps.length} {task.steps.length === 1 ? "Schritt" : "Schritte"}</span>{aktiv && <em>{PHASEN[phase]}</em>}<ChevronDown size={14} className="hv-pfeil"/></summary>
      <ol>{task.steps.map((schritt, i) => {
        const nummer = i + 1;
        const erledigt = task.status === "done" || nummer < planSchritt;
        const dran = aktiv && nummer === planSchritt;
        return <li key={i} className={erledigt ? "erledigt" : dran ? "dran" : ""}><i>{erledigt ? <Check size={11} strokeWidth={3}/> : dran ? <span className="hv-puls"/> : null}</i><span>{schritt}</span></li>;
      })}</ol>
    </details>}

    <ol className="hv-verlauf">
      {sichtbar.map((e, i) => {
        if (e.type === "notiz") return <motion.li key={i + "-" + e.time} className="hv-jon" initial={{opacity: 0, y: 6}} animate={{opacity: 1, y: 0}} transition={{duration: 0.22}}>
          <span className="hv-avatar">J</span>
          <div><span className="hv-name">Jon <time>{uhr(e.time)}</time></span><p>{e.message}</p></div>
        </motion.li>;
        const info = aktion(e);
        if (!info) return null;
        const Icon = info.icon;
        const offen = laeuftBefehl && e === log[log.length - 1];
        return <motion.li key={i + "-" + e.time} className={"hv-aktion hv-" + info.art} initial={{opacity: 0, x: -4}} animate={{opacity: 1, x: 0}} transition={{duration: 0.18}}>
          <span className="hv-aktion-icon">{offen ? <Loader2 size={13} className="hv-dreh"/> : <Icon size={13}/>}</span>
          <div className="hv-aktion-inhalt">
            <div className="hv-aktion-zeile">
              <b>{info.titel}</b>
              {info.code && <code>{info.code}</code>}
              {(e.plus !== undefined || e.minus !== undefined) && <span className="hv-zahlen"><em className="hv-plus">+{e.plus || 0}</em><em className="hv-minus">−{e.minus || 0}</em></span>}
              {offen && <span className="hv-laeuft">läuft …</span>}
            </div>
            {info.text && <p>{info.text}</p>}
            {e.ausgabe && <pre>{e.ausgabe}</pre>}
          </div>
        </motion.li>;
      })}
      {!sichtbar.length && aktiv && <li className="hv-leer"><Loader2 size={13} className="hv-dreh"/>Jon liest den Auftrag und plant die ersten Schritte …</li>}
    </ol>

    <AnimatePresence>{task.pending && <motion.div className="hv-freigabe" initial={{opacity: 0, scale: 0.98}} animate={{opacity: 1, scale: 1}} exit={{opacity: 0, scale: 0.98}}>
      <strong><ShieldAlert size={15}/>Deine Freigabe ist nötig</strong>
      <pre>{task.pending.args.command}</pre>
      <small>{task.pending.args.cwd}</small>
      {task.pending.notice && <small>{task.pending.notice}</small>}
      <div><button className="hv-erlauben" disabled={busy} onClick={() => onEntscheiden(true)}><Check size={14}/>Erlauben</button><button disabled={busy} onClick={() => onEntscheiden(false)}>Ablehnen</button></div>
    </motion.div>}</AnimatePresence>

    {aktiv && <div className="hv-live" aria-live="polite">
      <span className="hv-live-icon"><LiveIcon size={14}/></span>
      <div><b>Jon arbeitet gerade</b><AnimatePresence mode="wait" initial={false}><motion.p key={liveText} initial={{opacity: 0, y: 3}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -3}} transition={{duration: 0.18}}>{liveText}<i className="hv-cursor">▌</i></motion.p></AnimatePresence></div>
    </div>}

    {!aktiv && task.summary && <motion.div className={"hv-ende " + (task.status === "done" ? "ok" : task.status === "needs_review" ? "offen" : "fehler")} initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}}>
      <span className="hv-ende-titel">{task.status === "done" ? <CheckCircle2 size={16}/> : <AlertTriangle size={16}/>}{task.status === "done" ? "Fertig" : HARNESS_TEXT[task.status] || task.status}</span>
      <p>{task.summary}</p>
    </motion.div>}
    {!aktiv && !task.summary && <div className="hv-ende fehler"><span className="hv-ende-titel"><FileCode2 size={16}/>{HARNESS_TEXT[task.status] || task.status}</span></div>}
  </div>;
}
