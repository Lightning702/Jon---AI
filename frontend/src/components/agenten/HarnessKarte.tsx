import {AnimatePresence, motion} from "framer-motion";
import {AlertTriangle, ArrowUpRight, Check, CheckCircle2, Code2, FileCode2, ListChecks, ShieldAlert, Square, XCircle} from "lucide-react";
import {useMemo, useState} from "react";
import AgentenBuehne from "./AgentenBuehne";
import AgentenStufen from "./AgentenStufen";
import {Anfrage, dauerText, diffZahlen, ENDE, fehlerText, HARNESS_TEXT, HarnessAuftrag, harnessPhase, quelle, WERKZEUG_ICON, WERKZEUG_TEXT} from "./daten";
import {useJetzt, useLive} from "./live";

const STUFEN = [{key: "planning", label: "Planen"}, {key: "working", label: "Umsetzen"}, {key: "verifying", label: "Prüfen"}, {key: "ende", label: "Fertig"}];

function stufeVon(auftrag: HarnessAuftrag): number {
  if (ENDE.has(auftrag.status)) return 3;
  if (auftrag.status === "verifying" || auftrag.checks.length) return 2;
  if (auftrag.status === "planning" && !auftrag.steps.length) return 0;
  return 1;
}

const klasse = (status: string) => status === "done" ? "ok" : status === "needs_review" ? "offen" : status === "waiting_approval" ? "warten" : ENDE.has(status) ? "fehler" : "laeuft";

export function HarnessAnsicht({auftrag, kompakt = false, onStopp, onEntscheiden, onOeffnen, beschaeftigt}: {auftrag: HarnessAuftrag; kompakt?: boolean; onStopp?: () => void; onEntscheiden?: (erlauben: boolean) => void; onOeffnen?: () => void; beschaeftigt?: boolean}) {
  const aktiv = !ENDE.has(auftrag.status);
  const jetzt = useJetzt(aktiv);
  const [planOffen, setPlanOffen] = useState(!kompakt);
  const knoten = useMemo(() => (auftrag.specialists || []).map((s, i) => ({id: `${i}-${s.role}`, titel: s.role, rolle: s.profil || "coding", status: s.status})), [auftrag.specialists]);
  const letzte = [...(auftrag.log || [])].reverse().find(e => e.tool || e.type === "running_command");
  const werkzeug = letzte?.tool || (letzte?.type === "running_command" ? "running_command" : "");
  const SatIcon = WERKZEUG_ICON[werkzeug];
  const satellit = aktiv && SatIcon ? {icon: SatIcon, text: WERKZEUG_TEXT[werkzeug] || werkzeug} : null;
  const zahlen = useMemo(() => auftrag.changes.reduce((summe, c) => {const z = diffZahlen(c.diff); summe.plus += z.plus; summe.minus += z.minus; summe.dateien.add(c.path); return summe;}, {plus: 0, minus: 0, dateien: new Set<string>()}), [auftrag.changes]);
  const geprueft = auftrag.checks.filter(c => c.ok).length;
  const projekt = auftrag.root.split(/[\\/]/).filter(Boolean).at(-1) || auftrag.root;
  const dauer = auftrag.created_at ? (aktiv ? jetzt : auftrag.updated_at || jetzt) - auftrag.created_at : 0;
  const herkunft = quelle(auftrag.source);
  const aktivitaet = aktiv ? (auftrag.pending ? "Wartet auf deine Freigabe für einen Befehl" : letzte?.message ? `${WERKZEUG_TEXT[werkzeug] ? "Jon " + WERKZEUG_TEXT[werkzeug] + ": " : ""}${letzte.message}` : HARNESS_TEXT[auftrag.status]) : "";
  return <div className={`ab ab-karte ${aktiv ? "aktiv" : ""} ${kompakt ? "ab-kompakt" : ""}`}>
    <div className="ab-kopf">
      <span className="ab-kopf-icon"><Code2/></span>
      <span className="ab-kopf-text"><strong>{kompakt ? auftrag.goal : "Jon Harness · " + projekt}</strong><small>{kompakt ? (HARNESS_TEXT[auftrag.status] || auftrag.status) + " · " + projekt : auftrag.model ? auftrag.model : "Jons Modell"}{auftrag.companion ? " · MiniJon begleitet" : ""}{herkunft ? " · " + herkunft : ""}</small></span>
      {!kompakt && <span className={`ab-status ${klasse(auftrag.status)}`}>{HARNESS_TEXT[auftrag.status] || auftrag.status}</span>}
      {dauer > 0 && <span className="ab-zeit">{dauerText(dauer)}</span>}
      {aktiv && onStopp && <button type="button" className="ab-knopf rund gefahr" disabled={beschaeftigt || auftrag.status === "cancelling"} onClick={onStopp} title="Auftrag stoppen" aria-label="Auftrag stoppen"><Square fill="currentColor"/></button>}
    </div>
    {!kompakt && <p className="ab-aufgabe">{auftrag.goal}</p>}
    <AgentenBuehne phase={harnessPhase(auftrag.status)} knoten={knoten} kernIcon={Code2} kernText="Harness" satellit={satellit} kompakt={kompakt}/>
    <AgentenStufen stufen={STUFEN} aktuell={stufeVon(auftrag)} fertig={!aktiv}/>
    {aktivitaet && <div className="ab-aktivitaet">{SatIcon ? <SatIcon/> : <Code2/>}<AnimatePresence mode="wait" initial={false}><motion.span key={aktivitaet} className={aktiv ? "ab-schimmer" : ""} initial={{opacity: 0, y: 4}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -4}} transition={{duration: 0.2}}>{aktivitaet}</motion.span></AnimatePresence></div>}
    <AnimatePresence>{auftrag.pending && <motion.div className="ab-freigabe" initial={{opacity: 0, scale: 0.97}} animate={{opacity: 1, scale: 1}} exit={{opacity: 0, scale: 0.97}}>
      <strong><ShieldAlert/>Deine Freigabe ist nötig</strong>
      <pre>{auftrag.pending.args.command}</pre>
      <small>{auftrag.pending.args.cwd}</small>
      <small>{auftrag.pending.notice}</small>
      {onEntscheiden && <div className="ab-reihe"><button type="button" className="ab-knopf voll" disabled={beschaeftigt} onClick={() => onEntscheiden(true)}><Check/>Erlauben</button><button type="button" className="ab-knopf" disabled={beschaeftigt} onClick={() => onEntscheiden(false)}>Ablehnen</button></div>}
    </motion.div>}</AnimatePresence>
    {!!auftrag.steps.length && <div>
      <button type="button" className="ab-knopf" onClick={() => setPlanOffen(v => !v)} aria-expanded={planOffen}><ListChecks/>Arbeitsplan · {auftrag.steps.length} Schritte</button>
      <AnimatePresence initial={false}>{planOffen && <motion.ol className="ab-plan" style={{marginTop: 8, overflow: "hidden"}} initial={{height: 0, opacity: 0}} animate={{height: "auto", opacity: 1}} exit={{height: 0, opacity: 0}}>
        {auftrag.steps.map((schritt, i) => <li key={i} className={auftrag.status === "done" ? "erledigt" : ""}><i>{auftrag.status === "done" ? <Check/> : i + 1}</i><span>{schritt}</span></li>)}
      </motion.ol>}</AnimatePresence>
    </div>}
    {(zahlen.dateien.size > 0 || auftrag.checks.length > 0) && <div className="ab-zahlen">
      {zahlen.dateien.size > 0 && <span className="ab-zahl"><FileCode2/><b>{zahlen.dateien.size}</b>{zahlen.dateien.size === 1 ? "Datei" : "Dateien"}<b className="ab-plus">+{zahlen.plus}</b><b className="ab-minus">−{zahlen.minus}</b></span>}
      {auftrag.checks.length > 0 && <span className="ab-zahl">{geprueft === auftrag.checks.length ? <CheckCircle2 className="ab-plus"/> : <XCircle className="ab-minus"/>}<b>{geprueft}/{auftrag.checks.length}</b>Prüfungen bestanden</span>}
    </div>}
    {auftrag.summary && !aktiv && <motion.div className={auftrag.status === "done" ? "ab-ergebnis" : "ab-hinweis " + (auftrag.status === "needs_review" ? "offen" : "fehler")} initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}}>{auftrag.status === "done" ? <h4>Ergebnis</h4> : <AlertTriangle/>}<span>{auftrag.summary}</span></motion.div>}
    {onOeffnen && <div className="ab-reihe ende"><button type="button" className="ab-knopf" onClick={onOeffnen}>Im Harness öffnen<ArrowUpRight/></button></div>}
  </div>;
}

export default function HarnessKarte({id, request, kompakt = false, onOeffnen}: {id: string; request: Anfrage; kompakt?: boolean; onOeffnen?: (id: string) => void}) {
  const pfad = "/harness/tasks/" + encodeURIComponent(id);
  const {daten, setDaten, fehler, fehlversuche, neu} = useLive<HarnessAuftrag>(request, pfad, auftrag => ENDE.has(auftrag.status), 1200);
  const [beschaeftigt, setBeschaeftigt] = useState(false);
  const [aktionsFehler, setAktionsFehler] = useState("");
  const handeln = async (fn: () => Promise<void>) => {
    setBeschaeftigt(true);
    setAktionsFehler("");
    try {await fn();}
    catch (e) {setAktionsFehler(fehlerText(e));}
    finally {setBeschaeftigt(false);}
  };
  if (!daten) {
    return <div className={`ab ab-karte ${fehlversuche >= 6 ? "" : "aktiv"} ${kompakt ? "ab-kompakt" : ""}`}>
      <div className="ab-kopf"><span className="ab-kopf-icon"><Code2/></span><span className="ab-kopf-text"><strong>Jon Harness</strong><small>{fehlversuche >= 6 ? "Dieser Auftrag ist nicht mehr verfügbar" : "Startet den Auftrag"}</small></span></div>
      <AgentenBuehne phase={fehlversuche >= 6 ? "ruhe" : "denken"} knoten={[]} kernIcon={Code2} kompakt={kompakt}/>
      {fehlversuche >= 6 && fehler && <p className="ab-leer">{fehler}</p>}
    </div>;
  }
  return <>
    <HarnessAnsicht auftrag={daten} kompakt={kompakt} beschaeftigt={beschaeftigt}
      onStopp={() => void handeln(async () => {setDaten(await request(pfad + "/cancel", {}));})}
      onEntscheiden={erlauben => void handeln(async () => {if (!daten.pending) return; await request(pfad + "/approve", {approval_id: daten.pending.id, allow: erlauben}); setDaten(await request(pfad)); neu();})}
      onOeffnen={onOeffnen ? () => onOeffnen(id) : undefined}/>
    {aktionsFehler && <p className="ab-leer" role="alert">{aktionsFehler}</p>}
  </>;
}
