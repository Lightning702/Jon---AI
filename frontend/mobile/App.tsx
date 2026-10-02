import React, {useEffect, useRef, useState} from "react";
import {animate, AnimatePresence, motion, PresenceContext, useDragControls, useMotionValue, useTransform} from "framer-motion";
import {AlarmClock, BookOpen, BatteryCharging, Camera, Clock, Dumbbell, Folder, Headphones, Hourglass, Image as ImageIcon, Laptop, LayoutGrid, MessageCircle, MessagesSquare, Music2, Pin, Puzzle, Search, SquarePen, X} from "lucide-react";
import {api, call, haptic, listen, native} from "./bridge";
import {ChatScreen, Conn, Shell, useVoiceEvents} from "./Chat";
import {AppsPage, ArchivePage, ImagesPage, LibraryPage, PageProps, PluginsPage, ProjectsPage, RemotePage, SearchPage, TasksPage} from "./Pages";
import {DevicePage, ModelSheet, PairPage, ProvidersPage, SecurityPage, SettingsPage, VoiceSettingsPage, initials} from "./Settings";
import {VoiceMode} from "./Voice";
import {ViewerPage} from "./Viewer";
import {Anzeigen, SosKnopf, ZeitPage} from "./Familie";
import {spracheAnwenden} from "./sprache";
import {ServerPage} from "./Verbindungen";
import {UhrPage} from "./Uhr";
import {KameraPage} from "./Kamera";
import {FitnessPage} from "./Fitness";
import {OfflinePage, SoloPage} from "./Offline";
import {JonChatPage} from "./JonChat";
import {LiveAnsicht} from "./Befehle";
import {Willkommen} from "./Willkommen";
import {AppSymbol, useApps} from "./Apps";
import {DatenschutzPage} from "./Datenschutz";
import {UpdatesPage} from "./Updates";
import {SicherungPage} from "./Sicherung";
import {Sparkles} from "lucide-react";
import {MiniJonPage} from "./MiniJon";
import {Circle, Fehlergrenze, JonMark, Lightbox, Modal, WaveIcon, errorText, handleBack, spring} from "./ui";
import {Umgebung, useChats} from "./useChats";

type Route = {key: string; id: string; arg?: any};

const routes: Record<string, (p: PageProps) => React.ReactElement> = {
  minijon: MiniJonPage,
  images: ImagesPage, library: LibraryPage, projects: ProjectsPage, remote: RemotePage, tasks: TasksPage, plugins: PluginsPage,
  search: SearchPage, archive: ArchivePage, apps: AppsPage, settings: SettingsPage, providers: ProvidersPage, device: DevicePage,
  "voice-settings": VoiceSettingsPage, security: SecurityPage, pair: PairPage, viewer: ViewerPage,
  zeit: ZeitPage, uhr: UhrPage, kamera: KameraPage, fitness: FitnessPage, offline: OfflinePage, solo: SoloPage, jonchat: JonChatPage,
  datenschutz: DatenschutzPage, updates: UpdatesPage, sicherung: SicherungPage, server: ServerPage
};

const nav: {id: string; label: string; icon: React.ReactNode; pi?: boolean}[] = [
  {id: "minijon", label: "MiniJon", icon: <Sparkles/>},
  {id: "jonchat", label: "Jon Chat", icon: <MessagesSquare/>, pi: true},
  {id: "kamera", label: "Kamera", icon: <Camera/>},
  {id: "uhr", label: "Wecker & Timer", icon: <AlarmClock/>},
  {id: "fitness", label: "Fitness", icon: <Dumbbell/>},
  {id: "images", label: "Bilder", icon: <ImageIcon/>, pi: true},
  {id: "library", label: "Bibliothek", icon: <BookOpen/>, pi: true},
  {id: "projects", label: "Projekte", icon: <Folder/>, pi: true},
  {id: "remote", label: "Fernzugriff", icon: <Laptop/>, pi: true},
  {id: "tasks", label: "Planen", icon: <Clock/>, pi: true},
  {id: "plugins", label: "Plugins", icon: <Puzzle/>, pi: true},
  {id: "zeit", label: "Bildschirmzeit", icon: <Hourglass/>},
  {id: "apps", label: "Apps", icon: <LayoutGrid/>}
];

function loadSeen(): Record<string, string> {try {return JSON.parse(localStorage.getItem("jon-gesehen") || "null") || {};} catch {return {};}}
function storeSeen(value: Record<string, string>) {try {localStorage.setItem("jon-gesehen", JSON.stringify(value));} catch {}}
function lokalerStatus(): any {try {return JSON.parse(localStorage.getItem("jon-status") || "{}") || {};} catch {return {};}}
function statusMerken(wert: any) {try {localStorage.setItem("jon-status", JSON.stringify(wert));} catch {}}

function StatusBar({conn, battery, weg}: {conn: Conn; battery: {level: number; charging: boolean} | null; weg: string}) {
  const [now, setNow] = useState(new Date());
  useEffect(() => {const timer = setInterval(() => setNow(new Date()), 15_000); return () => clearInterval(timer);}, []);
  const eigen = weg === "solo" || weg === "lokal";
  return <div className="statusbar">
    <div className="side">{now.toLocaleTimeString("de-DE", {hour: "2-digit", minute: "2-digit"})}</div>
    <div className="side">
      <span className={`dot ${conn.connected || eigen ? "" : "off"} ${eigen ? "eigen" : ""}`}/>
      <span className="pi">{weg === "lokal" ? "Handy-KI" : weg === "solo" ? "Eigener Zugang" : conn.connected ? conn.name || "Pi" : conn.paired ? "Offline" : "Kein Pi"}</span>
      {battery && <span className="battery">{battery.charging && <BatteryCharging/>}<span>{battery.level}%</span><span className="battery-shape"><span className={`battery-level ${battery.level <= 15 ? "low" : ""}`} style={{width: `${battery.level}%`, display: "block"}}/></span></span>}
    </div>
  </div>;
}

export function App() {
  const umgebung = useRef<Umgebung>({weg: "pi", freigabe: "ask", name: "", verbunden: false, gekoppelt: false});
  const chats = useChats(umgebung);
  const c = chats.current;
  const apps = useApps();
  const [stack, setStack] = useState<Route[]>([]);
  const [drawer, setDrawer] = useState(false);
  const [state, setState] = useState<any>(lokalerStatus);
  const [conn, setConn] = useState<Conn>({});
  const [voice, setVoice] = useState<any>(null);
  const [toast, setToast] = useState<{text: string; id: number} | null>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const [defaults, setDefaults] = useState({provider: "", model: ""});
  const [modelOpen, setModelOpen] = useState(false);
  const [battery, setBattery] = useState<{level: number; charging: boolean} | null>(null);
  const [pause, setPause] = useState(false);
  const [seen, setSeen] = useState<Record<string, string>>(loadSeen);
  const [weg, setWeg] = useState<any>({weg: "pi"});
  const [lokal, setLokal] = useState<any>(null);
  const [freigabe, setFreigabe] = useState("ask");
  const [kinder, setKinder] = useState<{an: boolean; alter: number}>({an: false, alter: 10});
  const [adminFrei, setAdminFrei] = useState(false);
  const [vorlesen, setVorlesenState] = useState(() => {try {return localStorage.getItem("jon-vorlesen") === "1";} catch {return false;}});
  const [profilName, setProfilName] = useState("");
  const [willkommen, setWillkommen] = useState(false);
  const [ungelesen, setUngelesen] = useState(0);
  const taps = useRef({count: 0, at: 0});
  const width = Math.min(Math.round(window.innerWidth * .84), 350);
  const x = useMotionValue(-width);
  const scrim = useTransform(x, [-width, 0], [0, 1]);
  const shift = useTransform(x, [-width, 0], [0, 56]);
  const drag = useDragControls();
  useVoiceEvents(setVoice);

  const name = String(state.profile?.name || profilName || "").trim();
  const appsSichtbar = !conn.apps_versteckt || adminFrei;
  umgebung.current = {weg: (weg.weg || "pi") as any, freigabe, name, verbunden: !!conn.connected, gekoppelt: !!conn.paired};
  const notify = (text: string) => setToast({text, id: Date.now()});
  const push = (id: string, arg?: any) => {haptic("tick"); setDrawer(false); setStack(s => [...s, {key: `${id}-${Date.now()}`, id, arg}]);};
  const pop = () => setStack(s => s.slice(0, -1));
  const reset = () => {setStack([]); setDrawer(false);};
  const refreshWeg = () => {call("weg").then(setWeg).catch(() => {}); call("ki-katalog").then(setLokal).catch(() => {});};
  const setVorlesen = (an: boolean) => {setVorlesenState(an); try {localStorage.setItem("jon-vorlesen", an ? "1" : "0");} catch {}};

  async function saveState(patch: any) {
    if (conn.paired && conn.connected) {
      try {const value = await api("/api/mobile/state", "PATCH", patch); setState(value); statusMerken(value); return value;}
      catch (e) {notify(errorText(e)); throw e;}
    }
    const alt = lokalerStatus();
    const neu = {...alt};
    for (const [k, v] of Object.entries(patch)) neu[k] = v && typeof v === "object" && !Array.isArray(v) ? {...(alt[k] || {}), ...(v as any)} : v;
    statusMerken(neu);
    setState(neu);
    return neu;
  }
  function refreshProviders() {if (conn.paired) api<any[]>("/api/accounts").then(v => Array.isArray(v) && setProviders(v)).catch(() => {});}
  async function loadAll() {
    const [list, st, health] = await Promise.allSettled([chats.refresh(), api("/api/mobile/state"), api("/api/health")]);
    if (st.status === "fulfilled") {setState(st.value); statusMerken(st.value);}
    if (health.status === "fulfilled") setDefaults({provider: health.value.default_provider || "", model: health.value.default_model || ""});
    if (list.status === "fulfilled" && !localStorage.getItem("jon-gesehen")) {
      const initial: Record<string, string> = {};
      for (const item of list.value || []) initial[item.id] = item.updated_at || "";
      setSeen(initial);
      storeSeen(initial);
    }
    api<any[]>("/api/accounts").then(v => Array.isArray(v) && setProviders(v)).catch(() => {});
    if ([list, st, health].every(r => r.status === "rejected")) notify("Pi nicht erreichbar. Heimnetz oder Tailscale prüfen.");
  }

  useEffect(() => {
    native("ready").promise.then(async v => {
      setConn(v);
      umgebung.current = {...umgebung.current, verbunden: !!v.connected, gekoppelt: !!v.paired};
      const [w, f, p, k] = await Promise.allSettled([call("weg"), call("freigabe"), call("profil"), call("ki-katalog")]);
      call("kinder").then(v => v && setKinder({an: !!v.an, alter: Number(v.alter) || 10})).catch(() => {});
      call("sprache").then(v => spracheAnwenden(v?.code || "de")).catch(() => {});
      if (w.status === "fulfilled") setWeg(w.value);
      if (f.status === "fulfilled") setFreigabe(f.value.modus || "ask");
      if (p.status === "fulfilled") setProfilName(p.value.name || "");
      if (k.status === "fulfilled") setLokal(k.value);
      if (v.paired) loadAll(); else chats.refresh().catch(() => {});
      if (v.connected) {
        let zuletzt = 0;
        try {zuletzt = Number(localStorage.getItem("jon-update-geprueft") || 0);} catch {}
        if (Date.now() - zuletzt > 20 * 3600_000) {
          try {localStorage.setItem("jon-update-geprueft", String(Date.now()));} catch {}
          call("update-pruefen").then((u: any) => {if (u?.neu) notify(`Jon ${u.neue_version} ist bereit – Einstellungen → Updates.`);}).catch(() => {});
        }
      }
      const bereit = w.status === "fulfilled" && (w.value.solo?.bereit || w.value.lokal);
      let gesehen = false;
      try {gesehen = !!localStorage.getItem("jon-willkommen");} catch {}
      if (!v.paired && !bereit && !gesehen) setWillkommen(true);
    }).catch(e => notify(errorText(e)));
  }, []);
  useEffect(() => listen("connection", value => setConn(old => {if (!old.connected && value.connected) {loadAll(); refreshWeg();} if (old.connected && !value.connected) refreshWeg(); return value;})), []);
  useEffect(() => listen("admin", value => setAdminFrei(!!value?.frei), true), []);
  useEffect(() => listen("server-gewechselt", value => {
    if (value?.automatisch) notify(`${value.von || "Jon"} ist nicht erreichbar – Jon nutzt jetzt ${value.zu || "einen anderen Jon"}.`);
    loadAll().catch(() => {});
    refreshWeg();
  }), []);
  useEffect(() => listen("battery", value => setBattery({level: value.level, charging: !!value.charging}), true), []);
  useEffect(() => listen("insets", value => {
    document.documentElement.style.setProperty("--safe-top", `${value.top || 0}px`);
    document.documentElement.style.setProperty("--safe-bottom", `${value.bottom || 0}px`);
  }, true), []);
  useEffect(() => listen("home", () => {reset(); handleBack();}), []);
  useEffect(() => listen("oeffnen", daten => {
    const seite = String(daten?.seite || "");
    reset();
    handleBack();
    if (seite && seite !== "chat" && routes[seite]) setTimeout(() => push(seite), 80);
  }, true), []);
  useEffect(() => listen("teilen", daten => {
    if (!daten) return;
    reset();
    handleBack();
    setTimeout(() => window.dispatchEvent(new CustomEvent("jon-teilen", {detail: daten})), 60);
  }, true), []);
  useEffect(() => {
    const oeffnen = (e: Event) => {const detail = (e as CustomEvent).detail; if (detail?.path) push("viewer", detail);};
    window.addEventListener("jon-open", oeffnen);
    return () => window.removeEventListener("jon-open", oeffnen);
  }, []);
  useEffect(() => listen("back", () => {
    if (handleBack()) return;
    if (drawer) {setDrawer(false); return;}
    if (stack.length) {pop(); return;}
    call("back-unhandled").catch(() => {});
  }), [drawer, stack.length]);
  useEffect(() => {if (!toast) return; const timer = setTimeout(() => setToast(null), 4200); return () => clearTimeout(timer);}, [toast]);
  useEffect(() => {animate(x, drawer ? 0 : -width, spring);}, [drawer]);
  useEffect(() => {
    const p = state.profile || {};
    const root = document.documentElement;
    root.style.setProperty("--accent", p.accent || "#3b6cf6");
    const theme = p.theme === "system" ? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark") : p.theme || "dark";
    root.dataset.theme = theme;
    call("darstellung", {hell: theme === "light"}).catch(() => {});
  }, [state.profile]);
  useEffect(() => {
    if (!c.id) return;
    const item = chats.list.find(v => v.id === c.id);
    if (item && seen[c.id] !== item.updated_at) {const next = {...seen, [c.id]: item.updated_at || ""}; setSeen(next); storeSeen(next);}
  }, [c.id, chats.list]);
  useEffect(() => {
    if (!conn.connected) {setUngelesen(0); return;}
    let aktiv = true;
    const tick = async () => {
      try {
        const info = await api<any>("/api/p2p/info");
        if (aktiv) setUngelesen(info.unread || 0);
        const neu = await api<any[]>("/api/p2p/notifications?channel=handy");
        const offen = stack[stack.length - 1]?.id === "jonchat";
        if (aktiv && !offen && Array.isArray(neu) && neu.length) {
          const n = neu[neu.length - 1];
          haptic("tick");
          notify(`💬 ${n.group_name ? `${n.group_name} · ` : ""}${n.sender_name}: ${(n.text || (n.media_kind === "image" ? "📷 Foto" : n.media_kind === "audio" ? "🎤 Sprachnachricht" : "📎 Datei")).slice(0, 80)}`);
        }
      } catch {}
    };
    tick();
    const timer = setInterval(tick, 8000);
    return () => {aktiv = false; clearInterval(timer);};
  }, [conn.connected, stack.length]);
  useEffect(() => {
    let active = 0, idle = 0, shown = false;
    const mark = () => {idle = 0;};
    window.addEventListener("pointerdown", mark, {passive: true});
    const timer = setInterval(() => {
      if (document.hidden) return;
      idle += 1;
      if (idle > 15) {active = 0; shown = false; return;}
      active += 1;
      if (active >= 60 && !shown) {shown = true; setPause(true);}
    }, 60_000);
    return () => {clearInterval(timer); window.removeEventListener("pointerdown", mark);};
  }, []);

  const shell: Shell = {
    chats, conn, state, saveState, notify, push, providers, refreshProviders, voice, name,
    weg, refreshWeg, freigabe, setFreigabe, vorlesen, setVorlesen, lokal, kinder, setKinder, appsSichtbar,
    openModel: () => {haptic("tick"); if (!providers.length) refreshProviders(); refreshWeg(); setModelOpen(true);},
    secret: () => {
      const now = Date.now();
      taps.current = now - taps.current.at < 1800 ? {count: taps.current.count + 1, at: now} : {count: 1, at: now};
      if (taps.current.count >= 5) {taps.current = {count: 0, at: 0}; haptic("success"); push("security");}
    }
  };
  const threadForDisplay = {...shell, defaults};
  const visibleChats = chats.list.filter(item => !state.chats?.[item.id]?.archived);
  const pinned = visibleChats.filter(item => state.chats?.[item.id]?.pinned);
  const recent = visibleChats.filter(item => !state.chats?.[item.id]?.pinned).slice(0, 40);
  const open = (id: string) => {haptic("tick"); chats.open(id).then(() => setDrawer(false)).catch(e => notify(errorText(e)));};
  const unread = (item: any) => item.id !== c.id && seen[item.id] !== undefined ? (seen[item.id] || "") < (item.updated_at || "") : item.id !== c.id && !(item.id in seen) && Object.keys(seen).length > 0;
  const modelLabel = c.provider === "handy" ? c.model : weg.weg === "solo" ? weg.solo?.modell || "" : c.model || defaults.model;
  const sichtbareNav = nav.filter(item => (!item.pi || conn.paired) && (appsSichtbar || (item.id !== "apps" && item.id !== "zeit")));

  return <main className="app">
    <StatusBar conn={conn} battery={battery} weg={weg.weg || "pi"}/>
    <motion.div className="layer" style={{zIndex: 10}} animate={{x: stack.length ? "-22%" : "0%", opacity: stack.length ? .5 : 1, scale: stack.length ? .985 : 1}} transition={spring}>
      <motion.section className="screen chat" style={{x: shift}}>
        <Fehlergrenze><ChatScreen shell={threadForDisplay} openDrawer={() => setDrawer(true)} onEdge={e => drag.start(e, {snapToCursor: false})}/></Fehlergrenze>
      </motion.section>
    </motion.div>

    <AnimatePresence initial={false}>{stack.map((route, index) => {
      const Page = routes[route.id];
      const depth = stack.length - 1 - index;
      return <motion.section key={route.key} className="screen page" initial={{x: "100%"}} animate={{x: depth ? "-24%" : "0%", opacity: depth ? .6 : 1}} exit={{x: "100%"}} transition={spring}>
        <PageEdge onBack={pop}/>
        <PresenceContext.Provider value={null}><Fehlergrenze zurueck={pop}>{Page ? <Page shell={threadForDisplay} back={pop} arg={route.arg}/> : null}</Fehlergrenze></PresenceContext.Provider>
      </motion.section>;
    })}</AnimatePresence>

    <div className={`drawer-root ${drawer ? "open" : ""}`}>
      <motion.div className="drawer-scrim" style={{opacity: scrim, pointerEvents: drawer ? "auto" : "none"}} onClick={() => setDrawer(false)}/>
      <motion.aside className="drawer" style={{x, pointerEvents: "auto"}} drag="x" dragControls={drag} dragConstraints={{left: -width, right: 0}} dragElastic={.03} dragMomentum={false}
        onDragEnd={(_, info) => {const next = info.velocity.x > 350 || (info.velocity.x > -350 && x.get() > -width / 2); if (next === drawer) animate(x, next ? 0 : -width, spring); setDrawer(next);}}>
        <div className="drawer-head"><button className="brand" onClick={shell.secret}><JonMark/>Jon</button><span className="grow"/><SosKnopf notify={notify}/><Circle label="Suchen" onClick={() => push("search")}><Search/></Circle></div>
        <div className="drawer-scroll">
          {sichtbareNav.map((item, i) => <motion.button key={item.id} className="nav-item" initial={false} animate={drawer ? {opacity: 1, x: 0} : {opacity: 0, x: -14}} transition={{delay: drawer ? .025 * i + .05 : 0, duration: .22}} onClick={() => push(item.id)}>{item.icon}<span>{item.label}</span>{item.id === "jonchat" && ungelesen > 0 && <b className="nav-zahl">{ungelesen}</b>}</motion.button>)}
          {appsSichtbar && apps && apps.length > 0 && <div className="app-strip">{apps.slice(0, 6).map(app => <button key={app.id} className="app-chip" onClick={() => {haptic("tap"); call("app", {app: app.id}).catch(e => notify(errorText(e)));}}><AppSymbol paket={app.paket} name={app.name} groesse={26}/><span>{app.name.replace(/ Music$/, "")}</span></button>)}</div>}
          {pinned.length > 0 && <><h3>Angeheftet</h3>{pinned.map(item => <button key={item.id} className={`chat-item ${c.id === item.id ? "current" : ""}`} onClick={() => open(item.id)}><Pin/><span>{state.chats[item.id]?.title || item.title}</span></button>)}</>}
          <h3>Letzte</h3>
          {recent.map(item => <button key={item.id} className={`chat-item ${c.id === item.id ? "current" : ""}`} onClick={() => open(item.id)}><span>{state.chats?.[item.id]?.title || item.title}</span>{item.lokal && <small className="lokal-marke">Handy</small>}{unread(item) && <i className="unread"/>}</button>)}
          {!recent.length && <p className="hint" style={{padding: "0 12px"}}>{conn.paired || weg.weg !== "pi" ? "Deine Chats erscheinen hier." : "Verbinde dein Gerät mit deinem Pi oder nutze Jon ohne PC."}</p>}
          <button className="chat-item" style={{color: "var(--muted)"}} onClick={() => push("archive")}><span>Archivierte Chats</span></button>
        </div>
        <div className="drawer-foot">
          <button className="new-chat" onClick={() => {haptic("tap"); chats.create(c.mode); reset();}}><SquarePen/>Chat</button>
          <span className="grow"/>
          <button className="avatar" style={{"--avatar": state.profile?.avatar || "#c765ac"} as React.CSSProperties} aria-label="Einstellungen" onClick={() => push("settings")}>{initials(name)}</button>
          <button className="voice-orb-btn" aria-label="Mit Jon sprechen" onClick={() => {setDrawer(false); call("voice", {mode: "talk"}).catch(e => notify(errorText(e)));}}><span><WaveIcon/></span></button>
        </div>
      </motion.aside>
    </div>

    <ModelSheet open={modelOpen} onClose={() => setModelOpen(false)} shell={shell}/>
    <VoiceMode voice={voice} model={modelLabel ? modelLabel.split("/").pop() || "" : ""} notify={notify}/>
    <Anzeigen name={name}/>
    <LiveAnsicht piName={conn.name || ""}/>
    <Modal open={pause} onClose={() => setPause(false)}>
      <button className="x" aria-label="Schließen" onClick={() => setPause(false)}><X/></button>
      <h2>Bereit für eine Pause?</h2>
      <p>Du bist schon eine Weile hier. Kurz aufstehen, etwas trinken – Jon wartet solange auf dich.</p>
    </Modal>
    <AnimatePresence>{willkommen && <Willkommen fertig={n => {setWillkommen(false); if (n) {setProfilName(n); saveState({profile: {...(state.profile || {}), name: n}}).catch(() => {});}}} oeffnen={seite => {if (seite === "pair") push("pair"); if (seite === "solo") push("solo"); if (seite === "offline") push("offline");}}/>}</AnimatePresence>
    <AnimatePresence>{conn.klemmt && <motion.div key="klemmt" className="klemmt" initial={{opacity: 0, y: -20}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -20}} transition={spring}>
      <strong>Android hält den Kiosk noch fest</strong>
      <span>Eine Systemseite ist hängen geblieben. Ein Neustart gibt alle Apps wieder frei.</span>
      <button className="btn primary" onClick={() => call("neustarten").catch(e => notify(errorText(e)))}>Jetzt neu starten</button>
    </motion.div>}</AnimatePresence>
    <AnimatePresence>{toast && <motion.div key={toast.id} className="toast" role="status" initial={{opacity: 0, y: 24, scale: .96}} animate={{opacity: 1, y: 0, scale: 1}} exit={{opacity: 0, y: 16, scale: .98}} transition={spring}><span>{toast.text}</span><button aria-label="Schließen" onClick={() => setToast(null)}><X/></button><motion.i className="toast-zeit" initial={{scaleX: 1}} animate={{scaleX: 0}} transition={{duration: 4.2, ease: "linear"}}/></motion.div>}</AnimatePresence>
    <div id="overlay-host" style={{position: "absolute", inset: 0, pointerEvents: "none", zIndex: 100}}/>
    <Lightbox/>
  </main>;
}

function PageEdge({onBack}: {onBack: () => void}) {
  const start = useRef<{x: number; y: number} | null>(null);
  return <div style={{position: "absolute", left: 0, top: "var(--top)", bottom: 0, width: 20, zIndex: 30, touchAction: "none"}}
    onPointerDown={e => {start.current = {x: e.clientX, y: e.clientY}; (e.target as HTMLElement).setPointerCapture(e.pointerId);}}
    onPointerUp={e => {const s = start.current; start.current = null; if (s && e.clientX - s.x > 70 && Math.abs(e.clientY - s.y) < 80) {haptic("tick"); onBack();}}}
    onPointerCancel={() => {start.current = null;}}/>;
}
