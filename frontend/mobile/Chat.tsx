import React, {useEffect, useLayoutEffect, useRef, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {Archive, ArrowDown, Code2, Users, ArrowUp, BookOpen, CalendarPlus, Camera, Check, CloudSun, Cpu, Dumbbell, FileUp, Globe, Home, Image as ImageIcon, Laptop, ListChecks, MapPin, Mic, MoreVertical, MousePointerClick, Music2, Paperclip, Pencil, Pin, Plus, Podcast, Presentation, Search, Server, Share2, ShieldAlert, Smartphone, Sparkles, Square, SquarePen, Telescope, Terminal, ThumbsDown, ThumbsUp, Timer, Trash2, Volume2, Wrench, X, ChevronDown, ChevronRight, Copy, FileText, Folder, FolderPlus} from "lucide-react";
import {api, call, haptic, listen, native, toBase64} from "./bridge";
import {Chats, LANG, Message, Step} from "./useChats";
import {ResultCards, FilePill} from "./Cards";
import {PremiumMarke} from "./Premium";
import {BefehlsListe, ausfuehren, befehle} from "./Befehle";
import {ErgebnisKarten, Plan, PlanKarte, planErkennen} from "./Work";
import {Busy, Circle, DashedChat, Field, Markdown, MenuLines, Orb, Popover, Sheet, WaveIcon, errorText, spring, useDictation} from "./ui";

export type Conn = {connected?: boolean; paired?: boolean; name?: string; kiosk?: boolean; owner?: boolean; wake?: boolean; battery?: number; charging?: boolean; locked?: boolean; server?: number; server_id?: string; apps_versteckt?: boolean; klemmt?: boolean};
export type Shell = {
  chats: Chats; conn: Conn; state: any; saveState: (patch: any) => Promise<any>; notify: (s: string) => void;
  push: (id: string, arg?: any) => void; openModel: () => void; providers: any[]; refreshProviders: () => void; voice: any; name: string; secret: () => void;
  defaults?: {provider: string; model: string};
  weg: any; refreshWeg: () => void; freigabe: string; setFreigabe: (v: string) => void; vorlesen: boolean; setVorlesen: (v: boolean) => void; lokal: any;
  kinder: {an: boolean; alter: number}; setKinder: (v: {an: boolean; alter: number}) => void;
  appsSichtbar: boolean;
};

export type Tool = {id: string; label: string; hint: string; ph: string; icon: React.ReactNode; work?: boolean; vorlage?: (t: string) => string; pi?: boolean};
export const tools: Tool[] = [
  {id: "website", ph: "Was für eine Website?", label: "Website", hint: "Baut sie und zeigt sie dir", icon: <Globe/>, work: true, vorlage: t => `Baue mir eine vollständige Website: ${t}. Lege sie als eigenen Ordner an (index.html, style.css, script.js) – modern, schön, responsiv fürs Handy und ohne Build-Werkzeuge. Nenne am Ende den Pfad der index.html.`},
  {id: "podcast", ph: "Worum geht's im Podcast?", label: "Podcast", hint: "Zwei Stimmen, als Audiodatei", icon: <Podcast/>, work: true, vorlage: t => `Erstelle einen Podcast über: ${t}. Schreib ein lebendiges Gespräch zwischen zwei Sprechern (A moderiert, B ist Gast), etwa drei Minuten lang, und nimm es danach mit dem Werkzeug podcast_erstellen auf.`},
  {id: "deep_learning", ph: "Was soll Jon recherchieren?", label: "Deep Research", hint: "Jon recherchiert gründlich im Web", icon: <Telescope/>, work: true, pi: true},
  {id: "create_pptx", ph: "Thema der Präsentation", label: "Präsentation", hint: "PowerPoint mit Folien", icon: <Presentation/>, work: true, pi: true},
  {id: "datei_erstellen", ph: "Was soll ins Dokument?", label: "Dokument", hint: "Word, PDF, Excel, Text", icon: <FileText/>, work: true, pi: true},
  {id: "browser_task", ph: "Was soll Jon im Web erledigen?", label: "Browser-Agent", hint: "Jon erledigt Webaufgaben", icon: <MousePointerClick/>, work: true, pi: true},
  {id: "run_cmd", ph: "Welcher Befehl auf dem Pi?", label: "Terminal", hint: "Befehle auf dem Pi", icon: <Terminal/>, work: true, pi: true},
  {id: "maps", ph: "Wohin oder was suchst du?", label: "Jon Maps", hint: "Orte, Routen und Umgebung", icon: <MapPin/>, pi: true},
  {id: "web_search", ph: "Wonach soll Jon suchen?", label: "Websuche", hint: "Aktuelle Infos aus dem Netz", icon: <Search/>},
  {id: "create_image", ph: "Beschreibe dein Bild", label: "Bild erstellen", hint: "Jon malt ein Bild", icon: <ImageIcon/>},
  {id: "get_weather", ph: "Für welchen Ort?", label: "Wetter", hint: "Vorhersage für deinen Ort", icon: <CloudSun/>},
  {id: "fitness", ph: "Was hast du trainiert?", label: "Fitness", hint: "Training eintragen", icon: <Dumbbell/>, vorlage: t => `Trag bitte dieses Training in mein Fitness-Tagebuch ein: ${t}`},
  {id: "start_timer", ph: "Wie lange?", label: "Timer", hint: "Timer und Wecker am Handy", icon: <Timer/>, vorlage: t => `Stell einen Timer auf ${t}`},
  {id: "calendar_add", ph: "Welcher Termin?", label: "Kalender", hint: "Termine eintragen", icon: <CalendarPlus/>, pi: true},
  {id: "amazon_play", ph: "Was möchtest du hören?", label: "Musik", hint: "Amazon Music abspielen", icon: <Music2/>, vorlage: t => `Spiel auf Amazon Music: ${t}`}
];

export function compose(text: string, mode?: string) {window.dispatchEvent(new CustomEvent("jon-draft", {detail: {text, mode}}));}

export function readUpload(file: File) {
  if (file.size > 4_000_000) throw new Error("Bitte eine Datei bis 4 MB auswählen.");
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
    reader.onerror = () => reject(new Error("Datei konnte nicht gelesen werden."));
    reader.readAsDataURL(file);
  });
}

export const providerLabel = (providers: any[], id: string) => id === "handy" ? "Auf dem Handy" : id.startsWith("solo-") ? "Eigener Zugang" : providers.find(p => p.provider === id)?.label || ({ollama: "Ollama", nvidia: "NVIDIA", openai: "OpenAI", anthropic: "Anthropic", gemini: "Gemini", lmstudio: "LM Studio"} as Record<string, string>)[id] || id;
export const shortModel = (model: string) => (model || "").split("/").pop() || "";

function stepIcon(step: Step) {
  const n = String(step.name || "");
  if (n === "team") return <Users/>;
  if (n === "harness_task") return <Code2/>;
  if (/datei|file|read|write|blender|dokument/.test(n)) return <FileText/>;
  if (/cmd|shell|powershell|terminal|run/.test(n)) return <Terminal/>;
  if (/web|browser|search|such|research|webseite/.test(n)) return <Globe/>;
  if (/map/.test(n)) return <MapPin/>;
  if (/timer|stopwatch|wecker|zeit|uhren/.test(n)) return <Timer/>;
  if (/image|bild/.test(n)) return <ImageIcon/>;
  if (/fitness/.test(n)) return <Dumbbell/>;
  if (/podcast/.test(n)) return <Podcast/>;
  if (/android|music|app|musik/.test(n)) return <Music2/>;
  return <Wrench/>;
}

function thoughtLabel(seconds?: number) {
  if (!seconds) return "Nachgedacht";
  if (seconds < 60) return `${seconds}s nachgedacht`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s nachgedacht`;
}

function Steps({steps, live}: {steps: Step[]; live?: boolean}) {
  return <div className="steps">{steps.map((s, i) => {
    const running = live && s.status === "running";
    return <motion.div key={i} className={`step ${running ? "live" : ""} ${s.ok === false ? "fail" : ""}`} initial={{opacity: 0, x: -6}} animate={{opacity: 1, x: 0}} transition={{duration: .25}}>
      <span className="ico">{stepIcon(s)}</span><span className={running ? "shimmer" : ""}>{s.summary || String(s.name || "").replaceAll("_", " ")}</span>
    </motion.div>;
  })}</div>;
}

function Thought({message, work}: {message: Message; work: boolean}) {
  const [open, setOpen] = useState(work && !!message.steps?.length);
  if (!message.steps?.length && !message.reasoning) return null;
  return <>
    <button className={`thought ${open ? "open" : ""}`} onClick={() => setOpen(!open)}>{thoughtLabel(message.seconds)}<ChevronDown/></button>
    <AnimatePresence initial={false}>{open && <motion.div initial={{height: 0, opacity: 0}} animate={{height: "auto", opacity: 1}} exit={{height: 0, opacity: 0}} transition={{duration: .28}} style={{overflow: "hidden"}}>
      {!!message.steps?.length && <Steps steps={message.steps}/>}
      {message.reasoning && <div className="reasoning-box">{message.reasoning.slice(0, 4000)}</div>}
    </motion.div>}</AnimatePresence>
  </>;
}

function splitUser(content: string) {
  const index = content.indexOf("\n\nDatei:");
  if (index < 0) return {text: content, file: ""};
  const file = /Datei:\s*(.+)/.exec(content.slice(index))?.[1] || "Datei";
  return {text: content.slice(0, index), file};
}

function Assistant({m, shell, work, onShare}: {m: Message; shell: Shell; work: boolean; onShare: (text: string) => void}) {
  const [vote, setVote] = useState<string>(shell.state.feedback?.[m.id] || "");
  const [more, setMore] = useState(false);
  const notify = shell.notify;
  async function give(value: string) {
    haptic("tick");
    setVote(value);
    try {await shell.saveState({feedback: {[m.id]: value}}); notify("Danke für dein Feedback.");} catch {}
  }
  return <article className="assistant">
    <Thought message={m} work={work}/>
    {m.content && <Markdown text={m.content} notify={notify}/>}
    <ResultCards cards={m.cards || []} notify={notify} ohneDateien/>
    <ErgebnisKarten m={m} shell={shell}/>
    <div className="actions">
      <button aria-label="Kopieren" onClick={() => call("copy", {text: m.content}).then(() => {haptic("success"); notify("Kopiert.");}).catch(e => notify(errorText(e)))}><Copy/></button>
      <button aria-label="Gute Antwort" className={vote === "good" ? "on" : ""} onClick={() => give("good")}><ThumbsUp fill={vote === "good" ? "currentColor" : "none"}/></button>
      <button aria-label="Schlechte Antwort" className={vote === "bad" ? "on" : ""} onClick={() => give("bad")}><ThumbsDown fill={vote === "bad" ? "currentColor" : "none"}/></button>
      <button aria-label="Vorlesen" onClick={() => call("speak", {text: m.content}).catch(e => notify(errorText(e)))}><Volume2/></button>
      <button aria-label="Teilen" onClick={() => onShare(m.content)}><Share2/></button>
      <button aria-label="Mehr" onClick={() => setMore(true)}><MoreVertical/></button>
      <span className="spacer"/>
      {m.model && <span className="model-tag">{shortModel(m.model)}</span>}
    </div>
    <Sheet open={more} title="Antwort" onClose={() => setMore(false)}>
      <button className="list-row" onClick={() => call("save", {name: "Jon-Antwort.md", mime: "text/markdown", data: toBase64(m.content)}).then(() => {notify("In Downloads/Jon gespeichert."); setMore(false);}).catch(e => notify(errorText(e)))}><FileText/><span>Als Datei speichern</span></button>
      <button className="list-row" onClick={() => {setMore(false); onShare(m.content);}}><Share2/><span>An WhatsApp senden</span></button>
      <button className="list-row" onClick={() => {setMore(false); call("speak", {text: m.content}).catch(e => notify(errorText(e)));}}><Volume2/><span>Mit Jons Stimme vorlesen</span></button>
    </Sheet>
  </article>;
}

function Composer({shell, text, setText, send, attach, input, dictate, tool, clearTool, plan, setPlan}: {shell: Shell; text: string; setText: (v: string) => void; send: () => void; attach: () => void; input: React.RefObject<HTMLTextAreaElement>; dictate: () => void; tool: Tool | null; clearTool: () => void; plan: boolean; setPlan: (v: boolean) => void}) {
  const c = shell.chats.current;
  const v = shell.voice;
  const dictating = v?.mode === "dictate" && v?.open;
  const [levels, setLevels] = useState<number[]>(() => Array(34).fill(0));
  useEffect(() => {if (dictating) setLevels(old => [...old.slice(1), Math.min(1, (v.level || 0) * 1.6)]); else setLevels(Array(34).fill(0));}, [v?.level, v?.seq, dictating]);
  useLayoutEffect(() => {const el = input.current; if (!el) return; el.style.height = "auto"; el.style.height = `${Math.min(Math.max(150, Math.round(window.innerHeight * .38)), el.scrollHeight)}px`;}, [text]);
  const empty = !c.messages.length && !c.busy;
  const work = c.mode === "coding";
  const tall = ((work && empty) || !!tool) && !dictating;
  const placeholder = tool ? tool.ph : work ? (plan ? "Ziel beschreiben" : empty ? "Aufgabe für Work" : "Antworten") : empty ? "Jon fragen" : "Jon antworten";
  const start = (mode: string) => {haptic("tap"); call("voice", {mode}).catch(e => shell.notify(errorText(e)));};
  return <div className={`composer ${tall ? "tall" : ""}`}>
    {dictating ? <>
      <button className="round-btn" aria-label="Diktat abbrechen" onClick={() => call("voice-cancel").catch(() => {})}><X/></button>
      <div className="dictation">{v.partial ? <span className="live">{v.partial}</span> : <div className="wave">{levels.map((l, i) => <i key={i} style={{height: `${4 + l * 34}px`, opacity: .35 + l * .65}}/>)}</div>}</div>
      <button className="round-btn ok" aria-label="Diktat übernehmen" onClick={() => call("voice-finish").catch(() => {})}>{v.phase === "THINKING" ? <span className="spin" style={{display: "flex"}}><Check/></span> : <Check/>}</button>
    </> : <>
      <button className="icon-btn plus" aria-label="Hinzufügen" onClick={() => {haptic("tick"); attach();}}><Plus/></button>
      <textarea ref={input} rows={1} aria-label="Nachricht an Jon" placeholder={placeholder} value={text} onChange={e => setText(e.target.value)}/>
      {tool && <motion.span className="tool-chip" initial={{scale: .7, opacity: 0}} animate={{scale: 1, opacity: 1}} transition={spring}>{tool.icon}<span>{tool.label}</span><button aria-label="Werkzeug entfernen" onClick={clearTool}><X/></button></motion.span>}
      {work && !tool && <motion.button className={`tool-chip plan ${plan ? "an" : ""}`} initial={{scale: .7, opacity: 0}} animate={{scale: 1, opacity: 1}} onClick={() => {haptic("tick"); setPlan(!plan);}}><ListChecks/><span>Plan</span></motion.button>}
      {tall && <span className="grow"/>}
      <button className="icon-btn" aria-label="Diktieren" onClick={dictate}><Mic/></button>
      {c.busy ? <button className="send-btn" aria-label="Antwort stoppen" onClick={() => {haptic("tap"); shell.chats.stop();}}><Square size={17} fill="currentColor"/></button>
        : text.trim() ? <motion.button initial={{scale: .6, opacity: 0}} animate={{scale: 1, opacity: 1}} className="send-btn" aria-label="Senden" onClick={() => {haptic("tap"); send();}}><ArrowUp/></motion.button>
        : <motion.button layout transition={spring} className={`voice-pill ${empty && !tool ? "" : "round"}`} aria-label="Mit Jon sprechen" onClick={() => start("talk")}><WaveIcon/>{empty && !tool && <span>Stimme</span>}</motion.button>}
    </>}
  </div>;
}

const PLAN_AUFTRAG = "Du planst eine Aufgabe für Jon im Work-Modus. Zerlege das Ziel in 3 bis 8 klare, prüfbare Arbeitsschritte in sinnvoller Reihenfolge. Nutze keine Werkzeuge. Antworte NUR mit JSON in der Form {\"schritte\": [\"...\", \"...\"]}.";

type Anhang = {name: string; content: string; bilder: string[]; vorschau?: string; art?: string};

export function ChatScreen({shell, openDrawer, onEdge}: {shell: Shell; openDrawer: () => void; onEdge: (e: React.PointerEvent) => void}) {
  const {chats, conn, state, notify, push} = shell;
  const c = chats.current;
  const [text, setText] = useState(""), [menu, setMenu] = useState(false), [sheet, setSheet] = useState(""), [anhang, setAnhang] = useState<Anhang | null>(null), [uploading, setUploading] = useState(""), [planModus, setPlanModus] = useState(() => {try {return localStorage.getItem("jon-plan") !== "0";} catch {return true;}});
  const [find, setFind] = useState<string | null>(null), [value, setValue] = useState(""), [projects, setProjects] = useState<any[]>([]), [shareText, setShareText] = useState(""), [atBottom, setAtBottom] = useState(true), [plan, setPlan] = useState<Plan | null>(null);
  const scroll = useRef<HTMLDivElement>(null), input = useRef<HTMLTextAreaElement>(null);
  const near = useRef(true);
  const planStopp = useRef(false);
  const vorgelesen = useRef("");
  const baseline = useRef({key: "", count: 0});
  if (baseline.current.key !== c.key) baseline.current = {key: c.key, count: c.messages.length};
  const meta = state.chats?.[c.id || ""] || {};
  const empty = !c.messages.length && !c.busy && !plan;
  const work = c.mode === "coding";
  const piWeg = shell.weg?.weg === "pi" && c.provider !== "handy";

  const [tool, setTool] = useState<Tool | null>(null);
  const draft = useRef<string | null>(null);
  const chatsRef = useRef(chats);
  chatsRef.current = chats;
  const geteiltRef = useRef<any>(null);
  useEffect(() => {near.current = true; setText(draft.current ?? ""); draft.current = null; setAnhang(null); setFind(null); setTool(null); setPlan(null);}, [c.key]);
  useEffect(() => {
    const handler = (e: Event) => {
      const {text: t, mode} = (e as CustomEvent).detail || {};
      if (mode) {draft.current = t; chatsRef.current.create(mode);} else setText(t);
      setTimeout(() => input.current?.focus(), 380);
    };
    const anhangEmpfangen = (e: Event) => {const d = (e as CustomEvent).detail; if (d) bildAnhaengen(d.name, d.bilder?.[0] || d.vorschau || "");};
    const teilen = (e: Event) => {
      const d = (e as CustomEvent).detail || {};
      call("teilen-erledigt").catch(() => {});
      const geteilterText = String(d.text || "").trim();
      const dateien: any[] = Array.isArray(d.dateien) ? d.dateien : [];
      const nurLink = /^https?:\/\/\S+$/i.test(geteilterText);
      draft.current = dateien.length ? geteilterText : nurLink ? `Fasse diese Seite kurz zusammen: ${geteilterText}` : geteilterText;
      chatsRef.current.create("chat");
      haptic("success");
      if (!dateien.length) {setTimeout(() => input.current?.focus(), 420); return;}
      if (dateien.length > 1) notify(`${dateien.length} Dateien geteilt – ich nehme die erste. Die anderen bitte einzeln teilen.`);
      geteiltRef.current = dateien[0];
      setTimeout(() => {if (piWeg && shell.conn.connected) setSheet("wohin"); else hochladen("handy");}, 450);
    };
    window.addEventListener("jon-draft", handler);
    window.addEventListener("jon-anhang", anhangEmpfangen);
    window.addEventListener("jon-teilen", teilen);
    return () => {window.removeEventListener("jon-draft", handler); window.removeEventListener("jon-anhang", anhangEmpfangen); window.removeEventListener("jon-teilen", teilen);};
  }, [piWeg, shell.conn.connected]);
  useEffect(() => {
    const el = scroll.current;
    if (el && near.current) requestAnimationFrame(() => {el.scrollTop = el.scrollHeight;});
  }, [c.messages.length, c.partial, c.steps?.length, c.cards?.length, c.busy, c.key, plan?.phase, plan?.schritte.length]);
  useEffect(() => {
    if (!shell.vorlesen || c.busy) return;
    const letzte = c.messages[c.messages.length - 1];
    if (letzte?.role === "assistant" && !letzte.lokal && letzte.id !== vorgelesen.current && letzte.content) {
      vorgelesen.current = letzte.id;
      call("speak", {text: letzte.content}).catch(() => {});
    }
  }, [c.messages.length, c.busy, shell.vorlesen]);
  const dictate = useDictation("chat", shell.voice, transcript => {
    setText(t => (t.trim() ? `${t.trim()} ${transcript}` : transcript));
    setTimeout(() => input.current?.focus(), 60);
  });

  async function bildAnhaengen(name: string, daten: string) {
    if (!daten) return;
    const eintrag: Anhang = {name, content: `Datei: ${name}`, bilder: piWeg ? [] : [daten], vorschau: daten, art: "bild"};
    setAnhang(eintrag);
    if (!piWeg) return;
    setUploading("Jon schaut sich das Bild an …");
    try {
      const r = await api<any>("/api/attachments/extract", "POST", {name, mime: "image/jpeg", data: daten, provider: c.provider && c.provider !== "handy" ? c.provider : undefined});
      setAnhang({...eintrag, content: `Datei: ${name}\nBeschreibung des Bildes:\n${r.content || r.text || r.description || ""}`});
    } catch (e) {notify(errorText(e));} finally {setUploading("");}
  }

  async function hochladen(ziel: string) {
    setSheet("");
    const geteilteDatei = geteiltRef.current;
    geteiltRef.current = null;
    setUploading(geteilteDatei ? `Lese ${geteilteDatei.name} …` : "Datei wählen …");
    try {
      const fortschritt = (chunk: any) => {if (chunk?.fortschritt) setUploading(chunk.fortschritt);};
      const r = geteilteDatei ? await native<any>("teilen-datei", {marke: geteilteDatei.marke, ziel}, fortschritt, LANG).promise
        : await native<any>("datei-waehlen", {ziel}, fortschritt, LANG).promise;
      setAnhang({name: r.name, content: r.anhang, bilder: r.bilder || [], vorschau: r.vorschau, art: r.art});
      haptic("success");
      if (r.art === "audio" || r.art === "video") notify(r.transkript ? "Fertig transkribiert." : "Datei ist bereit.");
    } catch (e) {if (errorText(e) !== "Abgebrochen") notify(errorText(e));} finally {setUploading("");}
  }

  async function fotografieren() {
    setSheet("");
    try {
      const r = await call<any>("kamera", {ziel: "chat"}, LANG);
      if (r?.data) await bildAnhaengen(r.name || "Foto.jpg", r.data);
    } catch (e) {if (errorText(e) !== "Abgebrochen") notify(errorText(e));}
  }

  function uploadFragen() {
    if (conn.connected) setSheet("wohin"); else hochladen("handy");
  }

  async function planen(ziel: string) {
    setText("");
    setPlan({ziel, schritte: [], phase: "planen"});
    let inhalt = "";
    try {
      const motor = shell.weg?.weg || "pi";
      const op = piWeg ? native("stream", {body: {messages: [{role: "system", content: PLAN_AUFTRAG}, {role: "user", content: ziel}], persist: false, mode: "chat", source: "handy", tool_mode: "ask", werkzeuge: "klein", provider: c.provider || undefined, model: c.model || undefined}}, e => {if (e.type === "content") inhalt += e.delta || "";}, 180_000)
        : native("ki-stream", {motor: c.provider === "handy" ? "lokal" : motor, modell: c.provider === "handy" ? c.model : "", verlauf: [], text: `${PLAN_AUFTRAG}\n\nZiel: ${ziel}`, modus: "chat", name: shell.name}, e => {if (e.type === "content") inhalt += e.delta || "";}, 180_000);
      await op.promise;
      const schritte = planErkennen(inhalt);
      if (!schritte.length) throw new Error("Jon konnte keinen Plan erstellen.");
      setPlan({ziel, schritte: schritte.map(s => ({text: s, status: "offen"})), phase: "bereit"});
      haptic("success");
    } catch (e) {notify(errorText(e)); setPlan(null); setText(ziel);}
  }

  async function planStarten() {
    if (!plan) return;
    planStopp.current = false;
    const schritte = plan.schritte.map(s => ({...s}));
    setPlan({...plan, schritte, phase: "laeuft"});
    for (let i = 0; i < schritte.length; i++) {
      if (planStopp.current) break;
      schritte[i].status = "laeuft";
      setPlan(p => p && {...p, schritte: schritte.map(s => ({...s}))});
      const antwort = await chats.send(`Schritt ${i + 1} von ${schritte.length}: ${schritte[i].text}\n\nGesamtziel: ${plan.ziel}. Erledige nur diesen Schritt vollständig und sag danach kurz, was du gemacht hast.`);
      schritte[i].status = antwort ? "fertig" : "fehler";
      setPlan(p => p && {...p, schritte: schritte.map(s => ({...s}))});
      if (!antwort) break;
    }
    if (!planStopp.current && schritte.every(s => s.status === "fertig")) await chats.send("Fasse kurz zusammen, was jetzt fertig ist, und nenne alle Dateien mit ihrem vollständigen Pfad.");
    setPlan(p => p && {...p, phase: planStopp.current ? "abgebrochen" : "fertig"});
    haptic("success");
  }

  async function send() {
    const content = text.trim();
    if (!content || c.busy) return;
    if (content.startsWith("/") && !anhang) {
      const erledigt = await ausfuehren(content, {
        shell,
        senden: (t, force = "") => {chatsRef.current.send(t, "", undefined, force).catch(() => {});},
        melden: (inhalt, karte) => chats.hinzufuegen(inhalt, karte ? {cards: [karte]} : {}),
        hochladen: uploadFragen,
        fotografieren,
        vorlesenSetzen: shell.setVorlesen
      });
      if (erledigt) {setText(""); return;}
    }
    if (!work && !anhang && !tool && content.length < 90) {
      const r = await call<any>("uhr-befehl", {text: content}).catch(() => ({}));
      if (r?.antwort) {
        setText("");
        chats.hinzufuegen(content, {}, "user");
        chats.hinzufuegen(`⏰ ${r.antwort}`);
        haptic("success");
        return;
      }
    }
    if (work && planModus && !anhang && !tool && !c.messages.length) {planen(content); return;}
    setText("");
    const angehaengt = anhang;
    setAnhang(null);
    near.current = true;
    const nachricht = tool?.vorlage ? tool.vorlage(content) : content;
    const force = tool && !tool.vorlage && piWeg ? tool.id : "";
    await chats.send(nachricht, angehaengt?.content || "", undefined, force, angehaengt?.bilder || []);
  }
  async function patchChat(patch: any) {
    if (!c.id) {notify("Schreib zuerst eine Nachricht, dann kann Jon den Chat speichern."); return;}
    await shell.saveState({chats: {[c.id]: {...meta, ...patch}}});
  }
  function exportText() {return c.messages.map(m => `${m.role === "user" ? "Du" : "Jon"}: ${m.content}`).join("\n\n");}
  function share(textToShare: string) {setShareText(textToShare); setSheet("share");}

  const lastChat = chats.list.find(item => item.id !== c.id && !state.chats?.[item.id]?.archived);
  const homePins = chats.list.filter(item => state.chats?.[item.id]?.home);
  const suggestions: {icon: React.ReactNode; label: React.ReactNode; run: () => void; emoji?: boolean}[] = [
    ...homePins.slice(0, 2).map(item => ({icon: <Pin/>, label: <>{state.chats[item.id]?.title || item.title}</>, run: () => chats.open(item.id).catch(e => notify(errorText(e)))})),
    ...(work ? [
      ...(piWeg && conn.connected ? [{icon: <Code2/>, label: <>Harness im Projekt coden lassen</>, run: () => {setText("Starte den Harness in meinem Projekt und "); setTimeout(() => input.current?.focus(), 60);}}] : []),
      {icon: "🌐", emoji: true, label: <>Eine Website bauen und ansehen</>, run: () => {setTool(tools.find(t => t.id === "website") || null); input.current?.focus();}},
      {icon: "🎙️", emoji: true, label: <>Einen Podcast aufnehmen lassen</>, run: () => {setTool(tools.find(t => t.id === "podcast") || null); input.current?.focus();}},
      conn.connected ? {icon: <Laptop/>, label: <>Auf deinem Pi arbeiten <em>· {conn.name || "Pi"}</em></>, run: () => push("remote")} : {icon: <FileUp/>, label: <>Datei hochladen und auswerten</>, run: uploadFragen}
    ] : [
      ...(shell.kinder?.an ? [
        {icon: "📚", emoji: true, label: <>Hilfe bei den Hausaufgaben</>, run: () => {setText("Hilf mir bei meiner Hausaufgabe, aber verrate nicht gleich die Lösung: "); setTimeout(() => input.current?.focus(), 60);}},
        {icon: "📷", emoji: true, label: <>Aufgabe fotografieren</>, run: () => {setText("Hilf mir bei dieser Aufgabe Schritt für Schritt."); fotografieren();}}
      ] : []),
      ...(lastChat ? [{icon: <Sparkles/>, label: <>{state.chats?.[lastChat.id]?.title || lastChat.title}</>, run: () => chats.open(lastChat.id).catch(e => notify(errorText(e)))}] : []),
      ...(piWeg && conn.connected ? [{icon: <Users/>, label: <>Fachteam gründlich prüfen lassen</>, run: () => {setText("Lass dein Fachteam gründlich prüfen: "); setTimeout(() => input.current?.focus(), 60);}}] : []),
      {icon: "📷", emoji: true, label: <>Foto machen und Jon fragen</>, run: fotografieren},
      {icon: "⏰", emoji: true, label: <>Wecker & Timer</>, run: () => push("uhr")}
    ])
  ].slice(0, 4);

  const lokalTitel = shell.lokal?.modelle?.find((m: any) => m.name === (c.provider === "handy" ? c.model : shell.lokal?.standard))?.titel;
  const modelName = c.provider === "handy" ? lokalTitel || c.model : shell.weg?.weg === "solo" ? shortModel(shell.weg?.solo?.modell || "") : shell.weg?.weg === "lokal" ? lokalTitel || "Handy-KI" : shortModel(c.model || shell.defaults?.model || "") || "Automatisch";
  const providerId = c.provider === "handy" ? "handy" : shell.weg?.weg === "solo" ? `solo-${shell.weg?.solo?.anbieter}` : shell.weg?.weg === "lokal" ? "handy" : c.provider || shell.defaults?.provider || "";
  const offline = !conn.connected && piWeg;
  const visible = find ? c.messages.filter(m => m.content.toLowerCase().includes(find.trim().toLowerCase())) : c.messages;
  const uploads = c.messages.filter(m => m.role === "user" && m.content.includes("\n\nDatei:")).map(m => {
    const name = /Datei:\s*(.+)/.exec(m.content)?.[1] || "Datei";
    const path = /Pfad auf dem Pi:\s*(.+)/.exec(m.content)?.[1] || "";
    return {name, path};
  }).filter(u => u.path);
  const createdFiles = c.messages.flatMap(m => (m.cards || []).filter(card => card.kind === "datei").flatMap(card => card.data?.dateien || []));

  const menuItems = [
    {label: "Teilen", icon: <Share2/>, run: () => share(exportText())},
    {label: meta.pinned ? "Loslösen" : "Anpinnen", icon: <Pin/>, run: () => patchChat({pinned: !meta.pinned}).then(() => notify(meta.pinned ? "Losgelöst." : "Angeheftet."))},
    {label: "Umbenennen", icon: <Pencil/>, run: () => {setValue(meta.title || c.title); setSheet("rename");}},
    ...(c.lokal ? [] : [{label: "Zum Projekt hinzufügen", icon: <FolderPlus/>, chevron: true, run: () => {api("/api/projects").then(setProjects).catch(e => notify(errorText(e))); setSheet("project");}}]),
    {label: "Hochgeladene Dateien", icon: <Paperclip/>, run: () => setSheet("files")},
    {label: "Im Chat suchen", icon: <Search/>, run: () => setFind("")},
    {label: meta.home ? "Vom Startbildschirm entfernen" : "Zum Startbildschirm hinzufügen", icon: <Home/>, run: () => patchChat({home: !meta.home}).then(() => notify(meta.home ? "Vom Startbildschirm entfernt." : "Auf dem Startbildschirm."))},
    {label: meta.archived ? "Aus Archiv holen" : "Archivieren", icon: <Archive/>, run: () => patchChat({archived: !meta.archived}).then(() => {if (!meta.archived) {chats.create(c.mode); notify("Chat archiviert.");}})},
    {label: "Löschen", icon: <Trash2/>, danger: true, run: () => setSheet("delete")}
  ];
  const sichtbareWerkzeuge = tools.filter(t => (!t.pi || piWeg) && (shell.appsSichtbar || t.id !== "amazon_play"));

  return <>
    <div className="edge" style={{position: "absolute", left: 0, top: "var(--top)", bottom: 0, width: 18, zIndex: 5, touchAction: "none"}} onPointerDown={onEdge}/>
    <header className="chat-header">
      <button className="home-menu" aria-label="Menü öffnen" onClick={openDrawer}><MenuLines/><span>Menü</span></button>
      <PremiumMarke/>
      {empty ? <div className="segmented">
        {["chat", "coding"].map(mode => <button key={mode} onClick={() => {haptic("tick"); chats.update({mode});}}>{c.mode === mode && <motion.span layoutId="seg" className="thumb" style={{left: 0, right: 0}} transition={spring}/>}<span style={{position: "relative"}}>{mode === "chat" ? "Chat" : "Work"}</span></button>)}
      </div> : <div className="header-title"><button onClick={shell.openModel}>{work ? "Work" : "Jon"}<ChevronDown/></button><small>{c.temp ? "Temporärer Chat" : `${modelName}${providerId ? ` · ${providerLabel(shell.providers, providerId)}` : ""}`}</small></div>}
      {empty ? <Circle label="Temporärer Chat" className={c.temp ? "on" : ""} onClick={() => {chats.update({temp: !c.temp}); notify(c.temp ? "Temporärer Chat aus." : "Temporärer Chat: wird nirgends gespeichert.");}}>{c.temp ? <span style={{color: "#9fbcff", display: "flex"}}><DashedChat/></span> : <DashedChat/>}</Circle>
        : <div className="pill-group"><button aria-label="Neuer Chat" onClick={() => {haptic("tick"); chats.create(c.mode);}}><SquarePen/></button><button aria-label="Chatmenü" onClick={() => {haptic("tick"); setMenu(true);}}><MoreVertical/></button></div>}
    </header>
    <nav className="home-shortcuts" aria-label="Schnellzugriff"><button onClick={() => push("minijon")}><span className="mini-dot"/>Funke öffnen<span className="hint">Dein Begleiter, der anpackt</span><ChevronRight size={16}/></button></nav>
    {empty && <button className={`model-chip ${offline ? "offline" : ""} ${!piWeg ? "handy" : ""}`} onClick={() => conn.paired || !piWeg ? shell.openModel() : push("pair")}><span className="led"/>{!piWeg ? <>{providerId === "handy" ? <Cpu size={14}/> : <Smartphone size={14}/>}{c.temp ? "Temporär · " : ""}{modelName} · {providerLabel(shell.providers, providerId)}</> : !conn.paired ? "Mit deinem Pi verbinden" : offline ? "Pi offline · Verbindung wird gesucht" : `${c.temp ? "Temporär · " : ""}${modelName}${providerId ? ` · ${providerLabel(shell.providers, providerId)}` : ""}`}<ChevronDown/></button>}
    {find !== null && <div className="inline-search"><Search size={18}/><input autoFocus placeholder="Im Chat suchen" value={find} onChange={e => setFind(e.target.value)}/><small>{find.trim() ? visible.length : ""}</small><button className="icon-btn" onClick={() => setFind(null)}><X/></button></div>}
    {empty ? <div className="empty-hero">
      <Orb size={Math.min(190, Math.round(window.innerWidth * .46))} phase={offline ? "offline" : "idle"} onClick={shell.secret}/>
      <motion.h1 key={`${work}`} initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={spring}>{work ? "Woran arbeiten wir?" : shell.name ? `Hey ${shell.name}` : "Hallo!"}</motion.h1>
      <p>{work ? (planModus ? "Beschreib dein Ziel – Jon plant, arbeitet Schritt für Schritt und zeigt dir das Ergebnis." : "Websites, Dokumente, Code und mehr.") : "Was kann ich heute für dich tun?"}</p>
    </div> : <div className="chat-scroll" ref={scroll} onScroll={() => {const el = scroll.current; if (!el) return; const n = el.scrollHeight - el.scrollTop - el.clientHeight < 140; near.current = n; if (n !== atBottom) setAtBottom(n);}}>
      {visible.map((m, index) => {
        const fresh = index >= baseline.current.count;
        const body = m.role === "user" ? (() => {const {text: t, file: f} = splitUser(m.content); return <div className="user-row"><div className="user-stack">{m.bilder?.[0] && <img className="user-bild" src={`data:image/jpeg;base64,${m.bilder[0]}`} alt=""/>}{f && <div className="attachment"><span className="file-badge">{f.split(".").pop()?.toUpperCase().slice(0, 4)}</span><span>{f}</span></div>}{t && <div className="user-bubble">{t}</div>}</div></div>;})()
          : <Assistant m={m} shell={shell} work={work} onShare={share}/>;
        return fresh ? <motion.div key={`${c.key}-${index}`} initial={{opacity: 0, y: 14, scale: .99}} animate={{opacity: 1, y: 0, scale: 1}} transition={{duration: .36, ease: [.2, .8, .2, 1]}}>{body}</motion.div> : <div key={`${c.key}-${index}`}>{body}</div>;
      })}
      <AnimatePresence>{plan && <PlanKarte plan={plan} starten={planStarten} abbrechen={() => {planStopp.current = true; if (plan.phase === "laeuft") chats.stop(); else {setText(plan.ziel); setPlan(null);}}} entfernen={i => setPlan({...plan, schritte: plan.schritte.filter((_, n) => n !== i)})}/>}</AnimatePresence>
      {c.busy && <motion.article className="assistant" initial={{opacity: 0}} animate={{opacity: 1}}>
        {!!c.steps?.length && <Steps steps={c.steps} live/>}
        {c.reasoning && !c.partial && <div className="reasoning-box shimmer">{c.reasoning.slice(-280)}</div>}
        {c.partial ? <Markdown text={c.partial} notify={notify}/> : !c.steps?.length && <span className="typing"><i/><i/><i/></span>}
        {!c.partial && !!c.steps?.length && <span className="shimmer" style={{fontSize: 15}}>{c.approval ? "Wartet auf deine Freigabe" : "Jon arbeitet …"}</span>}
        <ResultCards cards={c.cards || []} notify={notify}/>
      </motion.article>}
      {c.error && <div className="chat-error"><p>{c.error}</p><button onClick={() => {const last = [...c.messages].reverse().find(m => m.role === "user"); if (last) setText(splitUser(last.content).text);}}>Nachricht erneut bearbeiten</button></div>}
    </div>}
    <AnimatePresence>{c.approval && <motion.div className="approval" initial={{opacity: 0, y: 20}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: 20}} transition={spring}>
      <strong><ShieldAlert/>Jon möchte eine Aktion ausführen</strong><p>{c.approval.summary || c.approval.name}</p>
      <div className="row"><button onClick={() => chats.approve(false).catch(e => notify(errorText(e)))}>Ablehnen</button><button className="yes" onClick={() => {haptic("success"); chats.approve(true).catch(e => notify(errorText(e)));}}>Erlauben</button></div>
      <button className="text-link small" style={{marginTop: 8}} onClick={() => push("settings", {freigabe: true})}>Nicht mehr fragen …</button>
    </motion.div>}</AnimatePresence>
    {empty && <div className="suggestions">{suggestions.map((s, i) => <motion.button key={i} className="suggestion" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={{delay: .05 * i}} onClick={() => {haptic("tick"); s.run();}}><span className={`glyph ${s.emoji ? "emoji" : ""}`}>{s.icon}</span><span>{s.label}</span></motion.button>)}</div>}
    <div className="composer-wrap">
      <BefehlsListe text={text} waehlen={b => {if (b.args) {setText(`${b.name} `); setTimeout(() => input.current?.focus(), 30);} else {setText(b.name); setTimeout(() => {setText(""); ausfuehren(b.name, {shell, senden: (t, f = "") => {chatsRef.current.send(t, "", undefined, f).catch(() => {});}, melden: (inhalt, karte) => chats.hinzufuegen(inhalt, karte ? {cards: [karte]} : {}), hochladen: uploadFragen, fotografieren, vorlesenSetzen: shell.setVorlesen});}, 10);}}}/>
      <AnimatePresence>{!atBottom && !empty && <motion.button className="jump" initial={{opacity: 0, scale: .7}} animate={{opacity: 1, scale: 1}} exit={{opacity: 0, scale: .7}} onClick={() => {const el = scroll.current; if (el) el.scrollTo({top: el.scrollHeight, behavior: "smooth"});}}><ArrowDown/></motion.button>}</AnimatePresence>
      <AnimatePresence>{anhang && <motion.div className="attachment anhang" initial={{opacity: 0, y: 8, scale: .96}} animate={{opacity: 1, y: 0, scale: 1}} exit={{opacity: 0, scale: .9}} transition={spring}>
        {anhang.vorschau ? <img src={`data:image/jpeg;base64,${anhang.vorschau}`} alt=""/> : <span className="file-badge">{anhang.name.split(".").pop()?.toUpperCase().slice(0, 4)}</span>}
        <span>{anhang.name}<small>{anhang.art === "audio" ? "Transkript bereit" : anhang.art === "video" ? "Video ausgewertet" : anhang.art === "bild" ? "Bild" : /Pfad auf dem Pi/.test(anhang.content) ? "Auf dem Pi" : "Auf dem Handy"}</small></span>
        <button onClick={() => setAnhang(null)}><X/></button>
      </motion.div>}</AnimatePresence>
      {uploading && <Busy text={uploading}/>}
      {c.fortschritt && c.busy && <Busy text={c.fortschritt}/>}
      <Composer shell={shell} text={text} setText={setText} send={send} attach={() => setSheet("attach")} input={input} dictate={() => dictate().catch(e => notify(errorText(e)))} tool={tool} clearTool={() => {haptic("tick"); setTool(null);}} plan={planModus} setPlan={v => {setPlanModus(v); try {localStorage.setItem("jon-plan", v ? "1" : "0");} catch {}}}/>
      {!conn.kiosk && conn.owner && empty && <button className="setup-note" onClick={() => push("security")}>Einrichtungsmodus · Kiosk noch aus</button>}
    </div>

    <Popover open={menu} onClose={() => setMenu(false)}>
      <div className="head">{meta.title || c.title}</div>
      {menuItems.map(item => <button key={item.label} className={`list-row ${item.danger ? "danger" : ""}`} onClick={() => {haptic("tick"); setMenu(false); item.run();}}>{item.icon}<span>{item.label}</span>{item.chevron && <ChevronRight size={18}/>}</button>)}
    </Popover>

    <Sheet open={sheet === "attach"} title="Hinzufügen" onClose={() => setSheet("")}>
      <button className="list-row" onClick={() => {setSheet(""); uploadFragen();}}><FileUp/><span>Datei vom Handy<small>Bilder, Videos, Audio, PDFs – Jon wertet sie aus</small></span></button>
      <button className="list-row" onClick={fotografieren}><Camera/><span>Foto aufnehmen<small>Jon schaut es sich an</small></span></button>
      {conn.connected && <button className="list-row" onClick={() => {setSheet(""); push("library");}}><BookOpen/><span>Aus der Bibliothek</span></button>}
      {conn.connected && <button className="list-row" onClick={() => {setSheet(""); push("images");}}><ImageIcon/><span>Bild erstellen</span></button>}
      <div className="section-title" style={{margin: "14px 6px 4px", fontSize: 15}}>Werkzeuge</div>
      <div className="tool-grid-sheet">{sichtbareWerkzeuge.map(t => <button key={t.id} className={tool?.id === t.id ? "on" : ""} onClick={() => {haptic("tick"); setSheet(""); setTool(t); if (t.work && c.mode !== "coding" && !c.messages.length) chats.update({mode: "coding"}); setTimeout(() => input.current?.focus(), 300);}}>{t.icon}<span>{t.label}<br/><small>{t.hint}</small></span></button>)}</div>
      <div className="befehle-hinweis"><b>/</b> im Eingabefeld zeigt dir alle {befehle.length} Befehle</div>
      <button className="list-row" onClick={() => {setSheet(""); shell.openModel();}}><Sparkles/><span>Anbieter und Modell<small>{modelName}</small></span></button>
    </Sheet>

    <Sheet open={sheet === "wohin"} title="Wohin mit der Datei?" onClose={() => setSheet("")}>
      <p>Jon wertet die Datei auf jeden Fall aus: Bilder werden beschrieben, Videos angesehen und Sprache wird zu Text.</p>
      <button className="list-row" onClick={() => hochladen("pi")}><Server/><span>Auf den Pi hochladen<small>{conn.name || "Pi"} · landet in deiner Bibliothek</small></span></button>
      <button className="list-row" onClick={() => hochladen("handy")}><Smartphone/><span>Nur auf dem Handy<small>Bleibt in Jons Ordner auf diesem Gerät</small></span></button>
    </Sheet>

    <Sheet open={sheet === "share"} title="Teilen" onClose={() => setSheet("")}>
      <button className="list-row" onClick={() => {setSheet(""); call("share", {text: shareText, ziel: "whatsapp"}).catch(e => notify(errorText(e)));}}><span className="file-badge" style={{background: "linear-gradient(145deg,#25d366,#128c7e)"}}>WA</span><span>An WhatsApp senden</span></button>
      <button className="list-row" onClick={() => {setSheet(""); call("copy", {text: shareText}).then(() => notify("Kopiert.")).catch(e => notify(errorText(e)));}}><Copy/><span>Text kopieren</span></button>
      <button className="list-row" onClick={() => {setSheet(""); call("save", {name: `${(meta.title || c.title || "Jon").replace(/[<>:"/\\|?*]/g, "-")}.md`, mime: "text/markdown", data: toBase64(shareText)}).then(() => notify("In Downloads/Jon gespeichert.")).catch(e => notify(errorText(e)));}}><FileText/><span>Als Datei speichern</span></button>
    </Sheet>

    <Sheet open={sheet === "rename"} title="Chat umbenennen" onClose={() => setSheet("")}>
      <Field label="Name" value={value} onChange={setValue} autoFocus/>
      <button className="btn primary" onClick={() => patchChat({title: value.trim() || c.title}).then(() => setSheet(""))}>Speichern</button>
    </Sheet>

    <Sheet open={sheet === "project"} title="Zum Projekt hinzufügen" onClose={() => setSheet("")}>
      {projects.length ? projects.map(p => <button className="list-row" key={p.id} onClick={() => {patchChat({project: p.id}).then(() => {chats.update({workspace: p.root, mode: "coding"}); setSheet(""); notify(`Zu ${p.name} hinzugefügt.`);});}}><Folder/><span>{p.name}<small>{p.root}</small></span>{meta.project === p.id && <Check className="check"/>}</button>) : <p className="muted">Noch keine Projekte.</p>}
      <button className="btn soft" onClick={() => {setSheet(""); push("projects");}}><Plus/>Neues Projekt</button>
    </Sheet>

    <Sheet open={sheet === "files"} title="Dateien in diesem Chat" onClose={() => setSheet("")}>
      {!uploads.length && !createdFiles.length && <p className="muted">In diesem Chat gibt es noch keine Dateien auf dem Pi.</p>}
      {uploads.map((u, i) => <FilePill key={`u${i}`} file={{name: u.name, path: u.path, sizeText: "Hochgeladen"}} notify={notify}/>)}
      {createdFiles.map((f: any, i: number) => <FilePill key={`c${i}`} file={f} notify={notify}/>)}
    </Sheet>

    <Sheet open={sheet === "delete"} title="Chat löschen?" onClose={() => setSheet("")}>
      <p>{`„${meta.title || c.title}“ wird ${c.lokal ? "auf diesem Handy" : "auf deinem Pi"} gelöscht. Das lässt sich nicht rückgängig machen.`}</p>
      <button className="btn danger" onClick={async () => {
        try {
          if (c.id) await chats.loeschen(c.id);
          chats.create(c.mode);
          setSheet("");
          notify("Chat gelöscht.");
        } catch (e) {notify(errorText(e));}
      }}><Trash2/>Endgültig löschen</button>
    </Sheet>
  </>;
}

export function useVoiceEvents(setVoice: (v: any) => void) {
  useEffect(() => listen("voice", value => setVoice(value), true), []);
  useEffect(() => {native("voice-state").promise.then(v => v && setVoice(v)).catch(() => {});}, []);
}
