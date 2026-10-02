import React, {useEffect, useRef, useState} from "react";
import {ArrowUp, Brain, Check, MonitorSmartphone, Square, Trash2} from "lucide-react";
import {api, call, native} from "./bridge";
import {PageProps} from "./Pages";
import {Markdown, PageHeader, errorText} from "./ui";
import "../electron/pet3d.js";
import "./minijon.css";
import AgentTeam from "../src/components/AgentTeam";

const teamRequest = async (path: string, body?: unknown, method?: string) => {
  const result = await native("api", {path: "/api" + path, method: method || (body === undefined ? "GET" : "POST"), body}, undefined, 20000).promise;
  return JSON.parse(result.text || "{}");
};

const activities = [{id: "idle", label: "Bei dir"}, {id: "coding", label: "Coden"}, {id: "learning", label: "Lernen"}, {id: "planning", label: "Planen"}, {id: "ideas", label: "Ideen"}];
type Line = {role: "user" | "assistant"; content: string};

export function MiniJonPage({shell, back}: PageProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const pet = useRef<ReturnType<typeof window.Jon3D.create>>(null);
  const operation = useRef<ReturnType<typeof native> | null>(null);
  const connection = useRef(shell.conn.server_id);
  connection.current = shell.conn.server_id;
  const mounted = useRef(true);
  const [status, setStatus] = useState({enabled: false, permission: false, running: false});
  const [activity, setActivity] = useState("idle");
  const [busy, setBusy] = useState(false), [switching, setSwitching] = useState(false);
  const [teamBusy, setTeamBusy] = useState(false);
  const [error, setError] = useState(""), [input, setInput] = useState("");
  const [lines, setLines] = useState<Line[]>([]), [partial, setPartial] = useState("");
  const [conversation, setConversation] = useState<string>();
  const [approval, setApproval] = useState<any>(null);
  const [memories, setMemories] = useState<any[]>([]);
  const loadMemories = async () => {
    if (!shell.conn.connected) return;
    const server = shell.conn.server_id;
    try {const data = await api("/api/mini-jon/memories"); if (mounted.current && connection.current === server) setMemories(data.items || []);}
    catch {if (mounted.current && connection.current === server) setError("Das Alltagsgedächtnis ist nicht erreichbar. Installiere auch das aktuelle Jon-Backend auf deinem Pi.");}
  };
  useEffect(() => {
    mounted.current = true;
    const refresh = () => call("minijon-status").then(setStatus).catch(e => setError(errorText(e)));
    void refresh();
    window.addEventListener("focus", refresh);
    const timer = setInterval(() => {if (!document.hidden) void refresh();}, 5000);
    return () => {mounted.current = false; clearInterval(timer); window.removeEventListener("focus", refresh); operation.current?.cancel();};
  }, []);
  useEffect(() => {setMemories([]); setLines([]); setConversation(undefined); setPartial(""); setBusy(false); setApproval(null); operation.current?.cancel(); operation.current = null;}, [shell.conn.server_id]);
  useEffect(() => {void loadMemories();}, [shell.conn.server_id, shell.conn.connected]);
  useEffect(() => {
    if (!canvas.current) return;
    try {pet.current = window.Jon3D.create(canvas.current); pet.current?.start();} catch {setError("Die 3D-Darstellung ist auf diesem Gerät nicht verfügbar.");}
    const visibility = () => document.hidden ? pet.current?.stop() : pet.current?.start();
    document.addEventListener("visibilitychange", visibility);
    return () => {document.removeEventListener("visibilitychange", visibility); pet.current?.destroy(); pet.current = null;};
  }, []);
  useEffect(() => {pet.current?.setActivity(activity); pet.current?.render();}, [activity]);
  useEffect(() => {pet.current?.setTaskState(busy || teamBusy ? "working" : "idle");}, [busy, teamBusy]);

  async function toggle() {
    setSwitching(true); setError("");
    try {setStatus(await call("minijon-enable", {enabled: !status.enabled || !status.permission}));}
    catch(e) {setError(errorText(e));} finally {setSwitching(false);}
  }
  async function ask(text = input) {
    if (busy || !text.trim()) return;
    setError(""); setInput(""); setPartial(""); setApproval(null); setBusy(true);
    const messages: Line[] = [...lines.slice(-18), {role: "user", content: text.trim()}];
    setLines(messages);
    let answer = "", complete = false;
    const server = shell.conn.server_id;
    const request = native("stream", {body: {messages, conversation_id: conversation, persona: "junior", slot: "emil", source: "handy", persist: true, tool_mode: "ask"}}, event => {
      if (!mounted.current || connection.current !== server) return;
      if (event.type === "meta") setConversation(event.conversation_id);
      if (event.type === "content") {answer += event.delta || ""; setPartial(answer);}
      if (event.type === "tool") {if (event.approval_id) setApproval(event); else if (event.status === "done") setApproval(null);}
      if (event.type === "error") setError(event.message || "Jon konnte nicht antworten.");
      if (event.type === "done") complete = true;
    });
    operation.current = request;
    try {await request.promise; if (!complete && mounted.current && connection.current === server) setError("Die Antwort wurde unterbrochen. Du kannst es erneut versuchen.");}
    catch (e) {if (mounted.current && connection.current === server) setError(errorText(e));}
    finally {if (mounted.current && connection.current === server) {if (answer) setLines([...messages, {role: "assistant", content: answer}]); setPartial(""); setBusy(false); setApproval(null); operation.current = null; void loadMemories();}}
  }
  async function approve(approved: boolean) {
    if (!approval) return;
    try {await api("/api/chat/approve", "POST", {id: approval.approval_id, approved}); setApproval(null);}
    catch (e) {setError(errorText(e));}
  }
  return <>
    <PageHeader title="MiniJon" subtitle="Dein kleiner Alltagsbegleiter" onBack={back}/>
    <div className="page-scroll mini-page">
      <section className="mini-hero">
        <span className="mini-eyebrow"><span className={shell.conn.connected ? "live" : ""}/>{shell.conn.connected ? `Mit ${shell.conn.name || "deinem Pi"} verbunden` : "Wartet auf deinen Pi"}</span>
        <canvas ref={canvas} aria-label="MiniJon als schwarzer und goldener 3D-Roboter"/>
        <h1>Ein kleiner Jon.<br/><span>Immer an deiner Seite.</span></h1>
        <p>Zieh mich an deinen Lieblingsplatz. Tippe mich an, wenn du Hilfe brauchst.</p>
        <div className="mini-modes">{activities.map(item => <button key={item.id} className={activity === item.id ? "selected" : ""} onClick={() => setActivity(item.id)}>{item.label}</button>)}</div>
      </section>
      {error && <div className="mini-error" role="alert">{error}<button onClick={() => setError("")}>Schließen</button></div>}
      <section className="mini-card"><div className="mini-heading"><MonitorSmartphone/><div><strong>Auch außerhalb von Jon</strong><p>{status.running ? "MiniJon ist eingeblendet." : status.enabled && !status.permission ? "Android-Freigabe fehlt noch." : "Über deinen anderen Apps sichtbar."}</p></div></div><button className="mini-primary" disabled={switching} onClick={() => void toggle()}>{status.enabled && status.permission ? "MiniJon ausblenden" : status.enabled ? "Android-Freigabe öffnen" : "MiniJon auf dem Bildschirm zeigen"}</button><small>Android fragt einmal nach „Über anderen Apps anzeigen“. Beim Sperren blendet sich MiniJon aus.</small></section>
      <section className="mini-card"><div className="mini-heading"><Brain/><div><strong>Was beschäftigt dich?</strong><p>Lernen, planen, merken und gemeinsam lösen.</p></div></div>
        {!lines.length && <div className="mini-examples">{["Am Sonntag gibt es Schnitzel zu Mittag", "Erkläre mir den AcI in Latein", "Hilf mir, meine Woche zu planen"].map(text => <button key={text} onClick={() => setInput(text)}>{text}</button>)}</div>}
        <div className="mini-conversation" aria-live="polite">{lines.map((line, i) => <div className={line.role} key={i}><small>{line.role === "user" ? "Du" : "MiniJon"}</small><Markdown text={line.content} notify={shell.notify}/></div>)}{busy && <div className="assistant"><small>MiniJon</small>{partial ? <Markdown text={partial} notify={shell.notify}/> : <p>Ich denke nach …</p>}</div>}</div>
        {approval && <div className="mini-approval"><strong>Deine Freigabe</strong><p>{approval.summary}</p><pre>{JSON.stringify(approval.args, null, 2)}</pre><button onClick={() => void approve(true)}>Erlauben</button><button onClick={() => void approve(false)}>Ablehnen</button></div>}
        <form className="mini-composer" onSubmit={e => {e.preventDefault(); void ask();}}><input aria-label="Nachricht an MiniJon" value={input} onChange={e => setInput(e.target.value)} maxLength={4000} placeholder="Frag MiniJon …" disabled={busy}/>{busy ? <button type="button" aria-label="Antwort stoppen" onClick={() => operation.current?.cancel()}><Square/></button> : <button aria-label="Nachricht senden" disabled={!input.trim() || !shell.conn.connected}><ArrowUp/></button>}</form>
      </section>
      <section className="mini-card"><div className="mini-heading"><Check/><div><strong>Das habe ich mir gemerkt</strong><p>Datierte Essenspläne auf deinem verbundenen Pi.</p></div></div>{!memories.length && <p className="mini-empty">Noch kein Essensplan. Sag mir zum Beispiel, was es am Sonntag gibt.</p>}{memories.map(item => <div className="mini-memory" key={item.id}><div><small>{new Date(item.date + "T12:00:00").toLocaleDateString("de-AT", {weekday: "short", day: "numeric", month: "long"})} · {item.meal}</small><strong>{item.content}</strong></div><button aria-label={`${item.content} vergessen`} onClick={async () => {try {await api(`/api/mini-jon/memories/${encodeURIComponent(item.id)}`, "DELETE"); await loadMemories();} catch(e) {setError(errorText(e));}}}><Trash2 size={18}/></button></div>)}</section>
      {shell.conn.connected && <section className="mini-card"><AgentTeam key={shell.conn.server_id} request={teamRequest} initialSource="minijon" onWorking={setTeamBusy}/></section>}
    </div>
  </>;
}
