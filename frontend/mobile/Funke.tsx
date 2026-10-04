import React, {useEffect, useMemo, useRef, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {ArrowUp, Bell, BookOpen, Brain, CalendarCheck, Check, CloudSun, Layers, Mic, ShieldAlert, Sparkles, Square, Timer, Trash2, Users} from "lucide-react";
import {api, call, haptic, native} from "./bridge";
import {PageProps} from "./Pages";
import {Markdown, PageHeader, errorText, useDictation} from "./ui";
import {ResultCards} from "./Cards";
import AgentTeam from "../src/components/AgentTeam";
import {agentenAnfrage} from "./agenten";
import "./funke-figur.js";
import "./funke.css";

type FunkeFigur = {start(): void; stop(): void; destroy(): void; render(): void; setState(s: string): void; setLevel(v: number): void; setAgents(n: number): void; jubeln(): void};
type Schritt = {name: string; summary?: string; status?: string; ok?: boolean};
type Zeile = {role: "user" | "assistant"; content: string; cards?: any[]; steps?: Schritt[]; fehler?: boolean};
declare global {interface Window {Funke: {create(canvas: HTMLCanvasElement, optionen?: {state?: string}): FunkeFigur | null}}}

const SPEICHER = "funke-verlauf";
const GESPRAECH = "funke-gespraech";

const AKTIONEN: {icon: React.ReactNode; titel: string; hinweis: string; farbe: string; text: string; sofort?: boolean}[] = [
  {icon: <Timer/>, titel: "Timer", hinweis: "10 Minuten", farbe: "#ffc56b", text: "Stell einen Timer auf 10 Minuten.", sofort: true},
  {icon: <Bell/>, titel: "Erinnern", hinweis: "Sag mir wann", farbe: "#f59ccd", text: "Erinnere mich in 30 Minuten an "},
  {icon: <CalendarCheck/>, titel: "Mein Tag", hinweis: "Plan & nächste Schritte", farbe: "#7fe0a4", text: "Plane meinen heutigen Tag mit meinen Terminen und Aufgaben und nenne mir die nächsten drei Schritte.", sofort: true},
  {icon: <BookOpen/>, titel: "Lernen", hinweis: "Schritt für Schritt", farbe: "#79d0ff", text: "Erklär mir Schritt für Schritt: "},
  {icon: <Users/>, titel: "Fachteam", hinweis: "Mehrere Experten", farbe: "#c7a6ff", text: "Lass dein Fachteam gründlich prüfen: "},
  {icon: <CloudSun/>, titel: "Wetter", hinweis: "und was ansteht", farbe: "#8fd8ff", text: "Wie wird das Wetter heute und was steht bei mir an?", sofort: true},
];

let altesBackend = false;

const STUPSER = ["Hehe, das kitzelt!", "Ich bin bereit. Was packen wir an?", "Funke an Bord!", "Gib mir eine Aufgabe, ich erledige sie.", "Ich leuchte nur für dich."];

function laden(): Zeile[] {
  try {const wert = JSON.parse(localStorage.getItem(SPEICHER) || "[]"); return Array.isArray(wert) ? wert.slice(-40) : [];} catch {return [];}
}
function merken(zeilen: Zeile[]) {
  try {localStorage.setItem(SPEICHER, JSON.stringify(zeilen.slice(-40).map(z => ({...z, steps: (z.steps || []).map(s => ({name: s.name, summary: s.summary, ok: s.ok}))}))));} catch {}
}

function begruessung(name: string) {
  const stunde = new Date().getHours();
  const gruss = stunde < 5 ? "Noch wach" : stunde < 11 ? "Guten Morgen" : stunde < 17 ? "Hallo" : stunde < 22 ? "Guten Abend" : "Späte Runde";
  return `${gruss}${name ? ", " + name : ""}! Was soll ich für dich erledigen?`;
}

function Schritte({schritte, live}: {schritte: Schritt[]; live?: boolean}) {
  if (!schritte.length) return null;
  return <div className="funke-schritte">{schritte.map((s, i) => {
    const laeuft = live && s.status === "running";
    return <motion.span key={i} className={`funke-schritt ${laeuft ? "laeuft" : ""} ${s.ok === false ? "fehler" : ""}`} initial={{opacity: 0, scale: .85, y: 4}} animate={{opacity: 1, scale: 1, y: 0}} transition={{type: "spring", stiffness: 420, damping: 26}}>
      {laeuft ? <i className="funke-spinner"/> : s.ok === false ? <span>✕</span> : <Check/>}
      <span>{s.summary || s.name.replaceAll("_", " ")}</span>
    </motion.span>;
  })}</div>;
}

export function FunkePage({shell, back}: PageProps) {
  const leinwand = useRef<HTMLCanvasElement>(null);
  const figur = useRef<FunkeFigur | null>(null);
  const eingabe = useRef<HTMLTextAreaElement>(null);
  const ende = useRef<HTMLDivElement>(null);
  const laufend = useRef<ReturnType<typeof native> | null>(null);
  const aktiv = useRef(true);
  const [zeilen, setZeilen] = useState<Zeile[]>(laden);
  const [text, setText] = useState("");
  const [teil, setTeil] = useState("");
  const [schritte, setSchritte] = useState<Schritt[]>([]);
  const [karten, setKarten] = useState<any[]>([]);
  const [beschaeftigt, setBeschaeftigt] = useState(false);
  const [freigabe, setFreigabe] = useState<any>(null);
  const [fehler, setFehler] = useState("");
  const [stimmung, setStimmung] = useState<string>("");
  const [blase, setBlase] = useState("");
  const [hoert, setHoert] = useState(false);
  const [overlay, setOverlay] = useState({enabled: false, permission: false, running: false});
  const [umschalten, setUmschalten] = useState(false);
  const [erinnerungen, setErinnerungen] = useState<any[]>([]);
  const [teamOffen, setTeamOffen] = useState(false);
  const verbunden = !!shell.conn.connected;

  const diktieren = useDictation("funke", shell.voice, transkript => {
    setHoert(false);
    setText(t => (t.trim() ? `${t.trim()} ${transkript}` : transkript));
    setTimeout(() => eingabe.current?.focus(), 60);
  });

  useEffect(() => {
    aktiv.current = true;
    if (leinwand.current && window.Funke) {
      figur.current = window.Funke.create(leinwand.current, {state: "idle"});
      figur.current?.start();
    }
    const sichtbar = () => document.hidden ? figur.current?.stop() : figur.current?.start();
    document.addEventListener("visibilitychange", sichtbar);
    const status = () => call("minijon-status").then(v => aktiv.current && setOverlay(v)).catch(() => {});
    void status();
    window.addEventListener("focus", status);
    return () => {aktiv.current = false; document.removeEventListener("visibilitychange", sichtbar); window.removeEventListener("focus", status); figur.current?.destroy(); figur.current = null; laufend.current?.cancel();};
  }, []);

  const ladeErinnerungen = async () => {
    if (!verbunden) return;
    try {const daten = await api("/api/mini-jon/memories"); if (aktiv.current) setErinnerungen(daten.items || []);} catch {}
  };
  useEffect(() => {void ladeErinnerungen();}, [shell.conn.server_id, verbunden]);

  const zustand = useMemo(() => {
    if (stimmung) return stimmung;
    if (hoert) return "listening";
    if (!verbunden) return "sleeping";
    if (beschaeftigt && schritte.some(s => s.status === "running")) return "working";
    if (beschaeftigt && teil) return "speaking";
    if (beschaeftigt) return "thinking";
    return "idle";
  }, [stimmung, hoert, verbunden, beschaeftigt, schritte, teil]);

  useEffect(() => {
    figur.current?.setState(zustand);
    figur.current?.setAgents(schritte.filter(s => s.status === "running").length + (karten.some(k => k.kind === "agenten") ? 3 : 0));
  }, [zustand, schritte, karten]);

  useEffect(() => {
    if (!stimmung) return;
    const timer = setTimeout(() => setStimmung(""), stimmung === "error" ? 3500 : 2200);
    return () => clearTimeout(timer);
  }, [stimmung]);

  useEffect(() => {
    if (!hoert) return;
    const timer = setTimeout(() => setHoert(false), 12000);
    return () => clearTimeout(timer);
  }, [hoert]);

  useEffect(() => {ende.current?.scrollIntoView({block: "end", behavior: "smooth"});}, [zeilen.length, teil, schritte.length, karten.length]);

  const laufenderSchritt = [...schritte].reverse().find(s => s.status === "running");
  const sprechblase = blase || (fehler ? "Hoppla, da ist etwas schiefgegangen." : !verbunden ? "Ich schlafe, bis du mich mit deinem Jon verbindest." : laufenderSchritt ? (laufenderSchritt.name === "team" ? "Ich hole mein Fachteam dazu …" : laufenderSchritt.summary || "Ich kümmere mich darum …") : beschaeftigt ? (teil ? "Ich erzähle dir gleich alles." : "Ich denke kurz nach …") : zeilen.length ? "Noch etwas? Ich bin bereit." : begruessung(shell.name));

  async function fragen(inhalt = text) {
    const nachricht = inhalt.trim();
    if (beschaeftigt || !nachricht) return;
    if (!verbunden) {setFehler("Funke braucht die Verbindung zu deinem Jon. Prüfe sie unter Einstellungen → Verbindungen."); return;}
    haptic("tap");
    setFehler(""); setText(""); setTeil(""); setSchritte([]); setKarten([]); setFreigabe(null); setBlase(""); setBeschaeftigt(true);
    const neu: Zeile[] = [...zeilen, {role: "user", content: nachricht}];
    setZeilen(neu);
    merken(neu);
    let antwort = "", fertig = false, gesammelt: any[] = [], liste: Schritt[] = [], fehlertext = "";
    const verlauf = neu.slice(-18).map(z => ({role: z.role, content: z.content}));
    let gespraech: string | undefined;
    try {gespraech = localStorage.getItem(GESPRAECH) || undefined;} catch {}
    const body: Record<string, unknown> = {messages: verlauf, conversation_id: gespraech, source: "handy", persist: true, tool_mode: shell.freigabe || "ask"};
    if (!altesBackend) body.persona = "funke";
    const anfrage = native("stream", {body}, ereignis => {
      if (!aktiv.current) return;
      if (ereignis.type === "meta" && ereignis.conversation_id) {try {localStorage.setItem(GESPRAECH, ereignis.conversation_id);} catch {}}
      if (ereignis.type === "content") {antwort += ereignis.delta || ""; setTeil(antwort);}
      if (ereignis.type === "tool") {
        if (ereignis.status === "running") liste = [...liste, {name: ereignis.name, summary: ereignis.summary, status: "running"}];
        else {
          const index = liste.map(s => s.name).lastIndexOf(ereignis.name);
          if (index >= 0) liste = liste.map((s, i) => i === index ? {...s, status: "done", ok: ereignis.ok} : s);
        }
        setSchritte(liste);
        if (ereignis.card) {gesammelt = [...gesammelt, ereignis.card]; setKarten(gesammelt);}
        if (ereignis.approval_id) setFreigabe(ereignis);
        else if (ereignis.status === "done") setFreigabe(null);
      }
      if (ereignis.type === "error") fehlertext = ereignis.message || "Jon konnte nicht antworten.";
      if (ereignis.type === "done") fertig = true;
    });
    laufend.current = anfrage;
    try {
      await anfrage.promise;
      if (!fertig && !antwort && !fehlertext) fehlertext = "Die Antwort wurde unterbrochen. Versuch es gern noch einmal.";
    } catch (e) {fehlertext = errorText(e);}
    if (fehlertext && !antwort && !altesBackend && /422|persona|unprocessable/i.test(fehlertext)) {
      altesBackend = true;
      laufend.current = null;
      setBeschaeftigt(false);
      setZeilen(zeilen);
      void fragen(nachricht);
      return;
    }
    laufend.current = null;
    if (!aktiv.current) return;
    const fertigeZeilen: Zeile[] = antwort || gesammelt.length ? [...neu, {role: "assistant", content: antwort, cards: gesammelt, steps: liste}] : neu;
    setZeilen(fertigeZeilen);
    merken(fertigeZeilen);
    setTeil(""); setSchritte([]); setKarten([]); setFreigabe(null); setBeschaeftigt(false);
    if (fehlertext) {setFehler(fehlertext); setStimmung("error"); haptic("error");}
    else {setStimmung("happy"); figur.current?.jubeln(); haptic("success");}
    void ladeErinnerungen();
  }

  async function entscheiden(erlauben: boolean) {
    if (!freigabe) return;
    try {await api("/api/chat/approve", "POST", {id: freigabe.approval_id, approved: erlauben}); setFreigabe(null); haptic(erlauben ? "success" : "tick");}
    catch (e) {setFehler(errorText(e));}
  }

  async function overlayUmschalten() {
    setUmschalten(true);
    try {setOverlay(await call("minijon-enable", {enabled: !overlay.enabled || !overlay.permission}));}
    catch (e) {setFehler(errorText(e));} finally {setUmschalten(false);}
  }

  function stupsen() {
    haptic("tick");
    figur.current?.jubeln();
    setStimmung("happy");
    setBlase(STUPSER[Math.floor(Math.random() * STUPSER.length)]);
    setTimeout(() => aktiv.current && setBlase(""), 2600);
  }

  function aktion(a: typeof AKTIONEN[number]) {
    haptic("tick");
    if (a.sofort) {void fragen(a.text); return;}
    setText(a.text);
    setTimeout(() => {const feld = eingabe.current; if (feld) {feld.focus(); feld.setSelectionRange(a.text.length, a.text.length);}}, 50);
  }

  function leeren() {
    haptic("tick");
    setZeilen([]); merken([]);
    try {localStorage.removeItem(GESPRAECH);} catch {}
  }

  return <>
    <PageHeader title="Funke" subtitle="Dein Begleiter, der anpackt" onBack={back}/>
    <div className={`page-scroll funke-seite zustand-${zustand}`}>
      <section className="funke-held">
        <span className="funke-verbindung"><i className={verbunden ? "an" : ""}/>{verbunden ? `Mit ${shell.conn.name || "deinem Jon"} verbunden` : "Nicht verbunden"}</span>
        <button className="funke-figur" onClick={stupsen} aria-label="Funke antippen"><span className="funke-glanz"/><canvas ref={leinwand}/></button>
        <AnimatePresence mode="wait"><motion.p key={sprechblase} className="funke-blase" initial={{opacity: 0, y: 8, scale: .96}} animate={{opacity: 1, y: 0, scale: 1}} exit={{opacity: 0, y: -6, scale: .98}} transition={{duration: .25}}>{sprechblase}</motion.p></AnimatePresence>
      </section>

      <section className="funke-aktionen" aria-label="Schnellaktionen">
        {AKTIONEN.map((a, i) => <motion.button key={a.titel} style={{["--farbe" as string]: a.farbe}} initial={{opacity: 0, y: 14}} animate={{opacity: 1, y: 0}} transition={{delay: .05 * i, type: "spring", stiffness: 300, damping: 26}} whileTap={{scale: .95}} disabled={beschaeftigt} onClick={() => aktion(a)}>
          <span className="funke-aktion-icon">{a.icon}</span><strong>{a.titel}</strong><small>{a.hinweis}</small>
        </motion.button>)}
      </section>

      <AnimatePresence>{fehler && <motion.div className="funke-fehler" role="alert" initial={{opacity: 0, height: 0}} animate={{opacity: 1, height: "auto"}} exit={{opacity: 0, height: 0}}><span>{fehler}</span><button onClick={() => setFehler("")}>OK</button></motion.div>}</AnimatePresence>

      <section className="funke-gespraech" aria-live="polite">
        {!zeilen.length && !beschaeftigt && <div className="funke-leer"><Sparkles/><p>Sag mir einfach, was erledigt werden soll. Ich nutze alles, was Jon kann: Wecker, Erinnerungen, Recherche, Karten, Dateien und sein Fachteam.</p></div>}
        {zeilen.map((z, i) => <motion.div key={i} className={`funke-zeile ${z.role}`} initial={i >= zeilen.length - 2 ? {opacity: 0, y: 10} : false} animate={{opacity: 1, y: 0}} transition={{duration: .3}}>
          {z.role === "assistant" && <span className="funke-avatar" aria-hidden="true"/>}
          <div className="funke-inhalt">
            {!!z.steps?.length && <Schritte schritte={z.steps}/>}
            <ResultCards cards={z.cards || []} notify={shell.notify}/>
            {z.content && (z.role === "assistant" ? <div className="funke-text"><Markdown text={z.content} notify={shell.notify}/></div> : <div className="funke-text">{z.content}</div>)}
          </div>
        </motion.div>)}
        {beschaeftigt && <motion.div className="funke-zeile assistant" initial={{opacity: 0}} animate={{opacity: 1}}>
          <span className="funke-avatar aktiv" aria-hidden="true"/>
          <div className="funke-inhalt">
            <Schritte schritte={schritte} live/>
            <ResultCards cards={karten} notify={shell.notify}/>
            {teil ? <div className="funke-text"><Markdown text={teil} notify={shell.notify}/></div> : <div className="funke-tippt"><i/><i/><i/></div>}
          </div>
        </motion.div>}
        <AnimatePresence>{freigabe && <motion.div className="funke-freigabe" initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: 12}}>
          <strong><ShieldAlert/>Darf ich das?</strong>
          <p>{freigabe.summary || freigabe.name}</p>
          <div><button onClick={() => void entscheiden(false)}>Nein</button><button className="ja" onClick={() => void entscheiden(true)}>Ja, mach</button></div>
        </motion.div>}</AnimatePresence>
        <div ref={ende}/>
      </section>

      <form className="funke-eingabe" onSubmit={e => {e.preventDefault(); void fragen();}}>
        <textarea ref={eingabe} rows={1} value={text} maxLength={4000} placeholder={verbunden ? "Aufgabe für Funke …" : "Verbinde zuerst deinen Jon"} aria-label="Nachricht an Funke" onChange={e => setText(e.target.value)} onKeyDown={e => {if (e.key === "Enter" && !e.shiftKey) {e.preventDefault(); void fragen();}}}/>
        {!text.trim() && !beschaeftigt && <button type="button" className="funke-mikro" aria-label="Diktieren" onClick={() => {setHoert(true); diktieren().catch(err => {setHoert(false); setFehler(errorText(err));});}}><Mic/></button>}
        {beschaeftigt ? <button type="button" className="funke-senden stopp" aria-label="Stoppen" onClick={() => laufend.current?.cancel()}><Square fill="currentColor"/></button> : <button className="funke-senden" aria-label="Senden" disabled={!text.trim()}><ArrowUp/></button>}
      </form>
      {!!zeilen.length && !beschaeftigt && <button className="funke-leeren" onClick={leeren}>Gespräch leeren</button>}

      <section className="funke-karte">
        <div className="funke-karte-kopf"><span style={{["--farbe" as string]: "#ffc56b"}}><Layers/></span><div><strong>Funke über allen Apps</strong><p>{overlay.running ? "Funke schwebt gerade über deinen Apps." : overlay.enabled && !overlay.permission ? "Android-Freigabe fehlt noch." : "Tipp ihn überall an und gib ihm Aufgaben."}</p></div></div>
        <button className={`funke-schalter ${overlay.enabled && overlay.permission ? "an" : ""}`} disabled={umschalten} onClick={() => void overlayUmschalten()} role="switch" aria-checked={overlay.enabled && overlay.permission}><i/></button>
      </section>

      <section className="funke-karte spalte">
        <div className="funke-karte-kopf"><span style={{["--farbe" as string]: "#7fe0a4"}}><Brain/></span><div><strong>Das hat sich Funke gemerkt</strong><p>Datierte Alltagsdinge auf deinem Jon.</p></div></div>
        {!erinnerungen.length && <p className="funke-hinweis">Noch nichts gemerkt. Sag zum Beispiel „Am Sonntag gibt es Schnitzel“.</p>}
        {erinnerungen.map(item => <div className="funke-erinnerung" key={item.id}><div><small>{new Date(item.date + "T12:00:00").toLocaleDateString("de-AT", {weekday: "short", day: "numeric", month: "long"})} · {item.meal}</small><strong>{item.content}</strong></div><button aria-label={`${item.content} vergessen`} onClick={async () => {try {await api(`/api/mini-jon/memories/${encodeURIComponent(item.id)}`, "DELETE"); await ladeErinnerungen();} catch (e) {setFehler(errorText(e));}}}><Trash2/></button></div>)}
      </section>

      {verbunden && <section className="funke-karte spalte">
        <button className="funke-karte-kopf knopf" onClick={() => setTeamOffen(v => !v)} aria-expanded={teamOffen}><span style={{["--farbe" as string]: "#c7a6ff"}}><Users/></span><div><strong>Fachteam direkt beauftragen</strong><p>Mehrere Fachagenten arbeiten parallel und prüfen sich gegenseitig.</p></div></button>
        <AnimatePresence initial={false}>{teamOffen && <motion.div initial={{height: 0, opacity: 0}} animate={{height: "auto", opacity: 1}} exit={{height: 0, opacity: 0}} style={{overflow: "hidden"}}><AgentTeam key={shell.conn.server_id} request={agentenAnfrage} initialSource="app"/></motion.div>}</AnimatePresence>
      </section>}
    </div>
  </>;
}
