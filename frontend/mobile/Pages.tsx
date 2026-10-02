import React, {useEffect, useRef, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {Archive, ArrowUp, BookOpen, Check, ChevronDown, ChevronRight, Code, Download, FileText, Folder, Globe, Headphones, Heart, Hourglass, Image as ImageIcon, Laptop, Lock, MessageCircle, Mic, Monitor, MoreHorizontal, MoreVertical, Music2, Pause, Play, Plus, RefreshCw, Search, Server, Settings2, SkipBack, SkipForward, SlidersHorizontal, Sparkles, Terminal, X} from "lucide-react";
import {api, call, enc, haptic, saveFile} from "./bridge";
import {Shell, compose, readUpload} from "./Chat";
import {openFile} from "./Viewer";
import {FilePill, fileExt, fileName, filePath} from "./Cards";
import {Busy, Circle, Empty, Field, Markdown, Modal, PageHeader, PiImage, Sheet, errorText, saveStudio, spring, useDictation, useLoad} from "./ui";
import {AppSymbol, AppWahl, useApps} from "./Apps";
import {useAdmin} from "./Settings";
import {ZeitAnfrage} from "./Familie";

export type PageProps = {shell: Shell; back: () => void; arg?: any};

function Art({kind}: {kind: number}) {
  const common = {className: "art", viewBox: "0 0 200 200", preserveAspectRatio: "xMidYMid slice"} as const;
  if (kind === 0) return <svg {...common}><rect width="200" height="200" fill="#f4f1ea"/><path d="M-10 40C30 10 80 30 70 70S0 110-10 80Z" fill="#ffd53d"/><circle cx="45" cy="55" r="30" fill="#161616"/><path d="M22 36l6-20 12 16M68 36l-6-20-12 16" fill="#161616"/><circle cx="35" cy="52" r="6" fill="#f7d34a"/><circle cx="56" cy="52" r="6" fill="#f7d34a"/><circle cx="150" cy="50" r="30" fill="#1d7a45"/><rect x="138" y="54" width="24" height="18" rx="4" fill="#ff7ab6"/><path d="M150 54c-10-10-12-20-4-26M150 54c10-12 16-18 8-26" stroke="#9be08c" strokeWidth="6" strokeLinecap="round" fill="none"/><rect x="92" y="98" width="84" height="84" rx="18" fill="#f26b1d" transform="rotate(-8 134 140)"/><circle cx="134" cy="140" r="24" fill="#ffd9b8"/><path d="M114 130c6-18 34-18 40 0" fill="#e0572a"/><circle cx="126" cy="140" r="3" fill="#222"/><circle cx="142" cy="140" r="3" fill="#222"/><path d="M126 150q8 6 16 0" stroke="#222" strokeWidth="3" fill="none" strokeLinecap="round"/></svg>;
  if (kind === 1) return <svg {...common}><rect width="200" height="200" fill="#f3f2ec"/><text x="16" y="36" fontSize="22" fontWeight="800" fill="#14381f" fontFamily="sans-serif">PHOTO-</text><text x="16" y="58" fontSize="22" fontWeight="800" fill="#14381f" fontFamily="sans-serif">SYNTHESE</text><path d="M100 190V92" stroke="#3f7d2c" strokeWidth="6"/><path d="M100 120C60 110 50 80 70 70c20 8 30 30 30 50zM100 110c40-12 54-40 34-54-22 8-34 32-34 54z" fill="#58a83b"/><circle cx="170" cy="30" r="14" fill="#ffc933"/><path d="M150 40L120 70M160 50l-20 34" stroke="#ffc933" strokeWidth="3" strokeDasharray="4 5"/><ellipse cx="150" cy="130" rx="26" ry="18" fill="#2f8a4a"/><ellipse cx="150" cy="130" rx="18" ry="10" fill="#8fd86b"/><path d="M40 150h30M170 170l14-8" stroke="#4a7dd8" strokeWidth="3"/></svg>;
  if (kind === 2) return <svg {...common}><rect width="200" height="200" fill="#d9c49a"/><path d="M30 0C60 40 20 80 50 120s-10 60 10 80" stroke="#6b9bc7" strokeWidth="14" fill="none"/><g stroke="#8a6a3c" strokeWidth="2" fill="none"><path d="M80 20l100 30M70 80l120 10M90 150l90-40M110 0l-10 200M150 0l10 200"/></g><g fill="#a8845a"><circle cx="120" cy="60" r="12"/><circle cx="160" cy="120" r="16"/><rect x="92" y="110" width="30" height="22" rx="4"/><circle cx="140" cy="170" r="10"/></g><circle cx="120" cy="60" r="5" fill="#f3e6c8"/></svg>;
  if (kind === 3) return <svg {...common}><rect width="200" height="200" fill="#efe6d4"/><text x="100" y="40" textAnchor="middle" fontSize="15" fontWeight="800" fill="#2d2a26" fontFamily="serif">ZEITLEISTE</text><path d="M14 90h172" stroke="#2d2a26" strokeWidth="3"/>{[30, 64, 98, 132, 166].map((x, i) => <g key={x}><circle cx={x} cy="90" r="6" fill={i % 2 ? "#7a2b22" : "#2c3f6b"}/><rect x={x - 14} y="104" width="28" height="36" rx="3" fill="#d8c8a8"/><circle cx={x} cy="166" r="12" fill="#b8a482"/></g>)}</svg>;
  if (kind === 4) return <svg {...common}><rect width="200" height="200" fill="#f4efdf"/><rect x="26" y="40" width="148" height="140" rx="30" fill="#7bbf5a" stroke="#3e7a2d" strokeWidth="6"/><rect x="38" y="52" width="124" height="116" rx="22" fill="#cfe9b8"/><circle cx="78" cy="96" r="24" fill="#9a6ad6"/><circle cx="78" cy="96" r="9" fill="#5b2f99"/><ellipse cx="130" cy="130" rx="26" ry="18" fill="#a9d7f2" opacity=".85"/>{[[120, 76], [140, 92], [70, 146], [100, 150]].map(([x, y], i) => <ellipse key={i} cx={x} cy={y} rx="11" ry="6" fill="#3f8f2f" transform={`rotate(${i * 30} ${x} ${y})`}/>)}</svg>;
  return <svg {...common}><defs><linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#1e2a55"/><stop offset=".55" stopColor="#e87a45"/><stop offset="1" stopColor="#ffd08a"/></linearGradient></defs><rect width="200" height="200" fill="#2a1d1a"/><rect x="18" y="20" width="100" height="120" rx="4" fill="url(#sun)"/><path d="M18 110l30-20 30 14 40-24v50H18z" fill="#141c33"/><path d="M68 20v120M18 80h100" stroke="#3a2b25" strokeWidth="4"/><rect x="120" y="120" width="80" height="80" fill="#3b2c26"/><rect x="0" y="150" width="200" height="50" fill="#20150f"/><path d="M130 20q30 20 70 4" stroke="#ffd98a" strokeWidth="1.5" fill="none" strokeDasharray="1 7" strokeLinecap="round"/>{[[140, 40], [160, 52], [180, 44], [150, 70], [175, 80]].map(([x, y], i) => <circle key={i} cx={x} cy={y} r="2.6" fill="#ffe3a0"/>)}</svg>;
}

const templates = [
  {name: "Sticker", prompt: "Erstelle ein Set aus drei verspielten Stickern mit dickem weißem Rand: "},
  {name: "Fotosynthese als Diagramm", prompt: "Erstelle ein beschriftetes, farbiges Lerndiagramm zur Fotosynthese auf Deutsch."},
  {name: "Karte des antiken Roms", prompt: "Erstelle eine detaillierte, illustrierte Karte des antiken Roms im Stil einer alten Pergamentkarte."},
  {name: "Zeitleiste", prompt: "Erstelle eine illustrierte Zeitleiste mit den wichtigsten Ereignissen zu "},
  {name: "Pflanzenzelle", prompt: "Erstelle eine beschriftete, wissenschaftliche Illustration einer Pflanzenzelle auf Deutsch."},
  {name: "Gemütliches Zimmer", prompt: "Erstelle ein fotorealistisches, gemütliches Zimmer bei Sonnenuntergang mit Lichterketten."}
];

export function ImagesPage({shell, back}: PageProps) {
  const gallery = useLoad<any>(() => api("/api/studio/gallery"));
  const config = useLoad<any>(() => api("/api/studio/config"));
  const [prompt, setPrompt] = useState(""), [busy, setBusy] = useState(false), [selected, setSelected] = useState<any>(null), [options, setOptions] = useState(false);
  const [provider, setProvider] = useState(""), [model, setModel] = useState(""), [size, setSize] = useState("1024x1024");
  const [banner, setBanner] = useState(() => {try {return !localStorage.getItem("jon-bilder-banner");} catch {return true;}});
  const input = useRef<HTMLTextAreaElement>(null);
  const dictate = useDictation("images", shell.voice, t => setPrompt(p => p ? `${p} ${t}` : t));
  async function generate() {
    if (!prompt.trim() || busy) return;
    setBusy(true);
    haptic("tap");
    try {
      const result = await api("/api/studio/generate", "POST", {prompt, kind: "bild", provider: provider || undefined, model: model || undefined, size});
      setSelected(result);
      setPrompt("");
      haptic("success");
      await gallery.refresh();
    } catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}
  }
  const items: any[] = gallery.data?.galerie || [];
  return <>
    <PageHeader title="Bilder" onBack={back} right={<Circle label="Bildeinstellungen" onClick={() => setOptions(true)}><Settings2/></Circle>}/>
    <div className="page-scroll">
      <AnimatePresence>{banner && <motion.div className="banner" exit={{opacity: 0, height: 0, marginBottom: 0}}><div style={{flex: 1}}><strong>Deine Bilder sind auch in der Bibliothek</strong><p>Alles, was Jon für dich erstellt, findest du zusätzlich unter „Bibliothek“.</p></div><button aria-label="Hinweis schließen" onClick={() => {setBanner(false); try {localStorage.setItem("jon-bilder-banner", "1");} catch {}}}><X/></button></motion.div>}</AnimatePresence>
      <div className="section-title strong">Ein Bild erstellen</div>
      <div className="templates">{templates.map((t, i) => <motion.button key={t.name} className="template" initial={{opacity: 0, y: 14}} animate={{opacity: 1, y: 0}} transition={{delay: i * .04}} onClick={() => {haptic("tick"); setPrompt(t.prompt); setTimeout(() => input.current?.focus(), 80);}}><Art kind={i}/><strong>{t.name}</strong></motion.button>)}</div>
      <div className="section-title strong" style={{marginTop: 26}}>Deine Bilder</div>
      {busy && <div className="tile" style={{minHeight: 200, alignItems: "center", justifyContent: "center", marginBottom: 12}}><span className="shimmer" style={{fontSize: 16, fontWeight: 600}}>Jon malt dein Bild …</span></div>}
      {gallery.busy ? <Busy/> : gallery.error ? <p className="error-text">{gallery.error}</p> : !items.length ? <p className="muted">Deine erstellten Bilder erscheinen hier.</p> : <div className="masonry">{items.map(item => <button className="tile image" key={item.id} onClick={() => setSelected(item)}><PiImage path={`/api/studio/file/${enc(item.datei)}`} alt={item.prompt}/></button>)}</div>}
    </div>
    <div className="prompt-bar">
      <textarea ref={input} rows={1} placeholder="Ein Bild beschreiben" value={prompt} onChange={e => setPrompt(e.target.value)}/>
      <div className="row">
        <button className="icon-btn" aria-label="Bildoptionen" onClick={() => setOptions(true)}><ImageIcon/></button>
        <span className="grow"/>
        <button className="icon-btn" aria-label="Diktieren" onClick={() => dictate().catch(e => shell.notify(errorText(e)))}><Mic/></button>
        {busy ? <span className="send-btn" style={{opacity: .6}}><RefreshCw className="spin"/></span> : <button className="send-btn" disabled={!prompt.trim()} aria-label="Bild erstellen" onClick={generate}><ArrowUp/></button>}
      </div>
    </div>
    <Sheet open={options} title="Bilderstellung" onClose={() => setOptions(false)}>
      <label className="field">Anbieter<select value={provider} onChange={e => {setProvider(e.target.value); setModel("");}}><option value="">Standard auf dem Pi</option>{config.data?.liste?.filter((v: any) => v.verbunden || v.auth === "frei").map((v: any) => <option key={v.id} value={v.id}>{v.label}</option>)}</select></label>
      <label className="field">Modell<select value={model} onChange={e => setModel(e.target.value)}><option value="">Standard</option>{config.data?.liste?.find((v: any) => v.id === provider)?.bild_modelle?.map((v: string) => <option key={v}>{v}</option>)}</select></label>
      <label className="field">Format<select value={size} onChange={e => setSize(e.target.value)}>{(config.data?.groessen || ["1024x1024", "1024x1536", "1536x1024"]).map((s: string) => <option key={s}>{s}</option>)}</select></label>
      <button className="btn primary" onClick={() => setOptions(false)}>Fertig</button>
    </Sheet>
    <Sheet open={!!selected} title="Dein Bild" onClose={() => setSelected(null)}>
      {selected && <>
        <div className="gen-image"><PiImage zoom path={`/api/studio/file/${enc(selected.datei)}`} alt={selected.prompt}/></div>
        <p className="muted small">{selected.prompt}</p>
        <div style={{display: "flex", flexDirection: "column", gap: 10}}>
          <button className="btn primary" onClick={() => {shell.notify("Download beginnt"); saveStudio(selected.datei).then(() => shell.notify("In Downloads/Jon gespeichert.")).catch(e => shell.notify(errorText(e)));}}><Download/>Speichern</button>
          <button className="btn soft" onClick={() => {setPrompt(selected.prompt); setSelected(null);}}>Als Vorlage verwenden</button>
        </div>
      </>}
    </Sheet>
  </>;
}

export function LibraryPage({shell, back}: PageProps) {
  const {state, saveState, notify} = shell;
  const result = useLoad<any[]>(() => Promise.allSettled([api("/api/dateien/liste?limit=200"), api("/api/studio/gallery")]).then(([files, images]) => [
    ...(files.status === "fulfilled" ? files.value.dateien || [] : []),
    ...(images.status === "fulfilled" ? (images.value.galerie || []).map((g: any) => ({...g, name: g.datei, titel: g.prompt, studio: true, id: `studio-${g.id}`})) : [])
  ]));
  const [tab, setTab] = useState("Vorgeschlagen"), [query, setQuery] = useState(""), [file, setFile] = useState<any>(null), [folder, setFolder] = useState(""), [newFolder, setNewFolder] = useState(false), [folderName, setFolderName] = useState(""), [busy, setBusy] = useState(false), [menu, setMenu] = useState(false);
  const [intro, setIntro] = useState(() => {try {return !localStorage.getItem("jon-bibliothek-intro");} catch {return false;}});
  const upload = useRef<HTMLInputElement>(null);
  const favorites: string[] = state.favorites || [];
  const key = (f: any) => String(f.id || filePath(f));
  const isImage = (f: any) => f.studio || /^(bild|image)$/.test(f.art) || /^(png|jpe?g|webp|gif)$/i.test(f.endung || "");
  const files = (result.data || []).filter((f: any) => (tab !== "Favoriten" || favorites.includes(key(f))) && (!folder || state.fileFolders?.[key(f)] === folder) && `${f.titel} ${f.name}`.toLowerCase().includes(query.toLowerCase()));
  async function favorite(f: any) {const id = key(f); await saveState({favorites: favorites.includes(id) ? favorites.filter(v => v !== id) : [...favorites, id]}); haptic("success");}
  async function uploadFile(f: File) {
    setBusy(true);
    try {await api("/api/mobile/upload", "POST", {name: f.name, data: await readUpload(f)}); await result.refresh(); notify("Datei in deiner Bibliothek gespeichert.");}
    catch (e) {notify(errorText(e));} finally {setBusy(false);}
  }
  const closeIntro = () => {setIntro(false); try {localStorage.setItem("jon-bibliothek-intro", "1");} catch {}};
  return <>
    <PageHeader title={folder || "Bibliothek"} onBack={folder ? () => setFolder("") : back} right={<Circle label="Mehr" onClick={() => setMenu(true)}><MoreVertical/></Circle>}/>
    <div className="tabs">{["Vorgeschlagen", "Favoriten", "Ordner"].map(t => <button className={tab === t ? "on" : ""} key={t} onClick={() => {haptic("tick"); setTab(t); setFolder("");}}>{tab === t && <motion.span layoutId="libtab" className="tab-bg" transition={spring}/>}<span>{t}</span></button>)}</div>
    <div className="page-scroll">
      {busy || result.busy ? <Busy/> : result.error ? <p className="error-text">{result.error}</p> : tab === "Ordner" && !folder ? <>
        <div className="masonry">{(state.folders || []).map((f: string) => <button className="tile" key={f} onClick={() => setFolder(f)}><strong>{f}</strong><small>{Object.values(state.fileFolders || {}).filter(v => v === f).length} Dateien</small><span className="foot"><Folder/></span></button>)}</div>
        <button className="btn soft" onClick={() => setNewFolder(true)}><Plus/>Neuer Ordner</button>
      </> : files.length ? <div className="masonry">{files.map((f: any, i: number) => <motion.button key={key(f)} className={`tile ${isImage(f) ? "image" : ""}`} initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: Math.min(i, 12) * .025}} onClick={() => isImage(f) ? setFile(f) : openFile(f)}>
        {isImage(f) ? <PiImage path={f.studio ? `/api/studio/file/${enc(f.datei)}` : filePath(f)} alt={f.titel}/> : <><strong>{f.titel || f.name}</strong><small>{fileExt(f)} · {f.groesse_text || ""}</small><span className="foot"><FileText/></span></>}
        {favorites.includes(key(f)) && <span className="heart"><Heart fill="currentColor"/></span>}
      </motion.button>)}</div> : <Empty icon={<BookOpen/>} title={tab === "Favoriten" ? "Noch keine Favoriten" : "Deine Bibliothek"} text="Dateien aus Work, Uploads und erstellte Bilder werden hier gesammelt."/>}
    </div>
    <div className="bottom-bar"><label className="search-pill"><Search/><input aria-label="Bibliothek durchsuchen" placeholder="Suche" value={query} onChange={e => setQuery(e.target.value)}/></label><Circle label="Datei hinzufügen" onClick={() => upload.current?.click()}><Plus/></Circle></div>
    <input ref={upload} type="file" hidden onChange={e => {const f = e.target.files?.[0]; if (f) uploadFile(f); e.target.value = "";}}/>
    <Modal open={intro} onClose={closeIntro} className="onboard">
      <div className="hero"><span className="ic"><Code color="#e8e8e8"/></span><span className="ic"><FileText color="#ff4f4f"/></span><span className="ic"><ImageIcon color="#7bd4ff"/></span></div>
      <button className="x" onClick={closeIntro} style={{background: "rgba(40,60,80,.6)"}}><X/></button>
      <div className="body"><h2>Einmal hochladen, jederzeit nutzen</h2><p>Frag Jon zu Dateien, die du früher hochgeladen hast – ohne sie erneut hochzuladen.</p><button className="btn primary" style={{marginTop: 22}} onClick={closeIntro}>Verstanden</button></div>
    </Modal>
    <Sheet open={menu} title="Bibliothek" onClose={() => setMenu(false)}>
      <button className="list-row" onClick={() => {setMenu(false); result.refresh();}}><RefreshCw/><span>Aktualisieren</span></button>
      <button className="list-row" onClick={() => {setMenu(false); setNewFolder(true);}}><Folder/><span>Neuer Ordner</span></button>
      <button className="list-row" onClick={() => {setMenu(false); upload.current?.click();}}><Plus/><span>Datei hochladen</span></button>
    </Sheet>
    <Sheet open={newFolder} title="Neuer Ordner" onClose={() => setNewFolder(false)}>
      <Field label="Name" value={folderName} onChange={setFolderName} autoFocus/>
      <button className="btn primary" disabled={!folderName.trim()} onClick={async () => {await saveState({folders: [...new Set([...(state.folders || []), folderName.trim()])]}); setNewFolder(false); setFolderName("");}}>Erstellen</button>
    </Sheet>
    <Sheet open={!!file} title={file ? file.titel || file.name : ""} onClose={() => setFile(null)}>
      {file && <>
        {isImage(file) ? <div className="gen-image"><PiImage zoom path={file.studio ? `/api/studio/file/${enc(file.datei)}` : filePath(file)}/></div> : <FilePill file={file} notify={notify}/>}
        <p className="muted small">{file.beschreibung || fileName(file)}</p>
        <div style={{display: "flex", flexDirection: "column", gap: 10}}>
          <button className="btn primary" onClick={async () => {notify("Download beginnt"); try {if (file.studio) await saveStudio(file.datei); else await saveFile(filePath(file)); notify("In Downloads/Jon gespeichert.");} catch (e) {notify(errorText(e));}}}><Download/>Herunterladen</button>
          <button className="btn soft" onClick={() => favorite(file).catch(e => notify(errorText(e)))}><Heart/>{favorites.includes(key(file)) ? "Favorit entfernen" : "Zu Favoriten"}</button>
          {!file.studio && <button className="btn soft" onClick={() => {setFile(null); shell.chats.create("coding"); setTimeout(() => shell.chats.send(`Lies die Datei ${filePath(file)} und hilf mir damit.`), 50); back();}}><Sparkles/>Mit Jon verwenden</button>}
        </div>
        <label className="field">Ordner<select value={state.fileFolders?.[key(file)] || ""} onChange={e => saveState({fileFolders: {[key(file)]: e.target.value}})}><option value="">Kein Ordner</option>{(state.folders || []).map((f: string) => <option key={f}>{f}</option>)}</select></label>
      </>}
    </Sheet>
  </>;
}

export function ProjectsPage({shell, back}: PageProps) {
  const result = useLoad<any[]>(() => api("/api/projects"));
  const [create, setCreate] = useState(false), [name, setName] = useState(""), [note, setNote] = useState(""), [busy, setBusy] = useState(false), [selected, setSelected] = useState<any>(null);
  function work(root: string, prompt = "") {const thread = shell.chats.create("coding", root); if (prompt) shell.chats.send(prompt, "", thread); back();}
  return <>
    <PageHeader title="Projekte" onBack={back} right={<Circle label="Neues Projekt" onClick={() => setCreate(true)}><Plus/></Circle>}/>
    <div className="page-scroll">
      {result.busy ? <Busy/> : result.error ? <p className="error-text">{result.error}</p> : result.data?.length ? <div className="group">{result.data.map(p => <button key={p.id} className="row-btn" onClick={() => {setSelected(p); setNote(p.note || "");}}><Folder/><span>{p.name}<small>{p.note || p.root}</small></span><ChevronRight className="chev"/></button>)}</div>
        : <Empty icon={<Folder/>} title="Alles für ein Projekt" text="Bündele Chats, Dateien und Anweisungen an einem Ort auf deinem Pi."/>}
    </div>
    <div className="stack-buttons"><button className="btn primary" onClick={() => setCreate(true)}><Plus/>Projekt erstellen</button></div>
    <Sheet open={create} title="Neues Projekt" onClose={() => setCreate(false)}>
      <Field label="Projektname" value={name} onChange={setName} autoFocus/>
      <Field label="Anweisungen für Jon" value={note} onChange={setNote} multiline/>
      <button className="btn primary" disabled={!name.trim() || busy} onClick={async () => {setBusy(true); try {await api("/api/mobile/projects", "POST", {name, note}); await result.refresh(); setCreate(false); setName(""); setNote(""); haptic("success");} catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}}}>Erstellen</button>
    </Sheet>
    <Sheet open={!!selected} title={selected?.name || ""} onClose={() => setSelected(null)}>
      {selected && <>
        <p className="muted small">{selected.root}</p>
        <div style={{display: "flex", flexDirection: "column", gap: 10}}>
          <button className="btn primary" onClick={() => work(selected.root)}><Code/>In Work öffnen</button>
          <button className="btn soft" onClick={() => work(selected.root, `Analysiere dieses Projekt und fasse den Stand zusammen: ${selected.root}`)}><Sparkles/>Projekt analysieren</button>
        </div>
        <Field label="Anweisungen für Jon" value={note} onChange={setNote} multiline/>
        <button className="btn soft" onClick={async () => {try {setSelected(await api(`/api/projects/${selected.id}/note`, "POST", {note})); result.refresh(); shell.notify("Gespeichert.");} catch (e) {shell.notify(errorText(e));}}}>Anweisungen speichern</button>
      </>}
    </Sheet>
  </>;
}

const repeatNames: Record<string, string> = {daily: "Täglich", once: "Einmalig", mo: "Montags", di: "Dienstags", mi: "Mittwochs", do: "Donnerstags", fr: "Freitags", sa: "Samstags", so: "Sonntags"};
const dayPart = (time: string) => {const h = Number(time?.split(":")[0] || 0); return h < 11 ? "Morgens" : h < 14 ? "Mittags" : h < 18 ? "Nachmittags" : "Abends";};

export function TasksPage({shell, back}: PageProps) {
  const result = useLoad<any[]>(() => api("/api/tasks"));
  const [create, setCreate] = useState(false), [task, setTask] = useState(""), [time, setTime] = useState("18:00"), [repeat, setRepeat] = useState("daily"), [selected, setSelected] = useState<any>(null), [busy, setBusy] = useState(false), [filter, setFilter] = useState("alle"), [filterSheet, setFilterSheet] = useState(false);
  const dictate = useDictation("tasks", shell.voice, t => {setTask(p => p ? `${p} ${t}` : t); setCreate(true);});
  const filters: Record<string, string> = {alle: "Alle", daily: "Täglich", weekly: "Wöchentlich", once: "Einmalig"};
  const list = (result.data || []).filter(t => filter === "alle" || (filter === "weekly" ? !["daily", "once"].includes(t.repeat) : t.repeat === filter));
  const starters = [
    {title: "Täglicher Überblick", text: "Personalisierter Überblick mit Neuigkeiten zu meinen wichtigsten Themen", time: "07:30"},
    {title: "KI-Briefing", text: "Recherchiere die spannendsten KI-Neuigkeiten des Tages und fasse sie kurz auf Deutsch zusammen", time: "19:00"},
    {title: "Projektfortschritt prüfen", text: "Prüfe meine Projekte auf dem Pi und fasse zusammen, was sich getan hat", time: "18:00"}
  ];
  return <>
    <PageHeader title="Aufgaben" onBack={back} subtitle={<button onClick={() => setFilterSheet(true)}>{filters[filter]}<ChevronDown/></button>} right={<Circle label="Filter" onClick={() => setFilterSheet(true)}><SlidersHorizontal/></Circle>}/>
    <div className="page-scroll">
      {result.busy ? <Busy/> : result.error ? <p className="error-text">{result.error}</p> : list.map((t, i) => <motion.button className="task" key={t.id} initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={{delay: i * .04}} onClick={() => setSelected(t)}>
        <small>{["daily", "once"].includes(t.repeat) ? repeatNames[t.repeat] : `Wöchentlich`}</small>
        <h2>{t.task.split(/[.!?\n]/)[0].slice(0, 70)}</h2>
        <p>{t.task}</p>
        <footer><b>{t.repeat && !["daily", "once"].includes(t.repeat) ? `${repeatNames[t.repeat]} · ` : ""}{dayPart(t.time)} · {t.time}</b><span>Pi</span></footer>
      </motion.button>)}
      <div className="section-title">Erste Schritte</div>
      {starters.map(s => <button className="suggest-card" key={s.title} onClick={() => {setTask(s.text); setTime(s.time); setRepeat("daily"); setCreate(true);}}><div><strong>{s.title}</strong><span>{s.text}</span></div><Plus/></button>)}
    </div>
    <div className="bottom-bar"><button className="search-pill" style={{textAlign: "left"}} onClick={() => setCreate(true)}><span style={{flex: 1, fontSize: 18, color: "#a9a9a9", fontWeight: 500}}>Eine Aufgabe erstellen</span><span className="icon-btn" onClick={e => {e.stopPropagation(); dictate().catch(err => shell.notify(errorText(err)));}}><Mic/></span></button></div>
    <Sheet open={filterSheet} title="Anzeigen" onClose={() => setFilterSheet(false)}>{Object.entries(filters).map(([id, label]) => <button key={id} className="list-row" onClick={() => {setFilter(id); setFilterSheet(false);}}><span>{label}</span>{filter === id && <Check className="check"/>}</button>)}</Sheet>
    <Sheet open={create} title="Aufgabe planen" onClose={() => setCreate(false)}>
      <Field label="Was soll Jon erledigen?" value={task} onChange={setTask} multiline/>
      <Field label="Uhrzeit auf dem Pi" value={time} onChange={setTime} type="time"/>
      <label className="field">Wiederholen<select value={repeat} onChange={e => setRepeat(e.target.value)}>{Object.entries(repeatNames).map(([id, label]) => <option value={id} key={id}>{label}</option>)}</select></label>
      <button className="btn primary" disabled={!task.trim() || busy} onClick={async () => {setBusy(true); try {await api("/api/tasks", "POST", {task, time, repeat}); await result.refresh(); setCreate(false); setTask(""); haptic("success"); shell.notify("Aufgabe auf dem Pi geplant.");} catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}}}>Auf dem Pi planen</button>
    </Sheet>
    <Sheet open={!!selected} title="Geplante Aufgabe" onClose={() => setSelected(null)}>
      {selected && <>
        <p>{selected.task}</p>
        <p className="muted small">{repeatNames[selected.repeat] || selected.repeat} · {selected.time}{selected.last_run_at ? ` · zuletzt ${new Date(selected.last_run_at).toLocaleString("de-DE")}` : ""}</p>
        {selected.last_result && <div className="card"><Markdown text={selected.last_result} notify={shell.notify}/></div>}
        <div style={{display: "flex", flexDirection: "column", gap: 10}}>
          <button className="btn primary" disabled={busy} onClick={async () => {setBusy(true); try {await api(`/api/tasks/${selected.id}/run`, "POST"); await result.refresh(); shell.notify("Aufgabe ausgeführt."); setSelected(null);} catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}}}>{busy ? <RefreshCw className="spin"/> : <Play/>}{busy ? "Wird ausgeführt …" : "Jetzt ausführen"}</button>
          <button className="btn danger" onClick={async () => {try {await api(`/api/tasks/${selected.id}`, "DELETE"); setSelected(null); result.refresh();} catch (e) {shell.notify(errorText(e));}}}>Aufgabe löschen</button>
        </div>
      </>}
    </Sheet>
  </>;
}

export function RemotePage({shell, back}: PageProps) {
  const status = useLoad<any>(() => api("/api/mobile/status"));
  const [ready, setReady] = useState(() => {try {return !!localStorage.getItem("jon-remote");} catch {return false;}});
  const [panel, setPanel] = useState(""), [command, setCommand] = useState(""), [program, setProgram] = useState(""), [output, setOutput] = useState(""), [busy, setBusy] = useState(false), [path, setPath] = useState(""), [files, setFiles] = useState<any[]>([]), [text, setText] = useState(""), [editing, setEditing] = useState(false);
  async function run(endpoint: string, body: any) {
    setBusy(true);
    try {const v = await api(endpoint, "POST", body); setOutput(v.stdout !== undefined ? `${v.stdout}${v.stderr ? `\n${v.stderr}` : ""}\nExit ${v.exit_code}` : JSON.stringify(v, null, 2));}
    catch (e) {setOutput(errorText(e));} finally {setBusy(false);}
  }
  async function browse(next: string) {
    setBusy(true);
    try {const value = await api("/api/system/files/list", "POST", {path: next}); setFiles(Array.isArray(value) ? value : value.eintraege || value.files || []); setPath(next); setEditing(false);}
    catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}
  }
  const tiles = [
    {id: "work", icon: <Code/>, name: "Mit Jon arbeiten", sub: "Code, Dateien und Aufgaben"},
    {id: "terminal", icon: <Terminal/>, name: "Terminal", sub: "Befehle direkt auf dem Pi"},
    {id: "files", icon: <Folder/>, name: "Dateien", sub: "Ordner ansehen und bearbeiten"},
    {id: "program", icon: <Play/>, name: "Programm starten", sub: "Auf deinem Pi"},
    {id: "browser", icon: <Globe/>, name: "Cloud-Browser", sub: "Webaufgaben an Jon übergeben"},
    {id: "status", icon: <Server/>, name: "Systemstatus", sub: "Speicher und Verbindung"}
  ];
  if (!ready) return <>
    <PageHeader title="Fernzugriff" onBack={back}/>
    <div className="remote">
      <Monitor/>
      <h1>Fernzugriff einrichten</h1>
      <p>Nutze die Möglichkeiten deines Pi auch unterwegs.</p>
      <div className="bullets">
        <div><Laptop/><span>Steuere Jon auf deinem Pi, um Software zu entwickeln und anspruchsvollere Aufgaben zu erledigen.</span></div>
        <div><Sparkles/><span>{shell.conn.connected ? `Verbunden mit ${shell.conn.name || "deinem Pi"} – verschlüsselt über LAN oder Tailscale.` : "Verbinde zuerst dein Gerät mit deinem Pi."}</span></div>
      </div>
    </div>
    <div className="stack-buttons">
      <button className="btn primary" disabled={!shell.conn.connected} onClick={() => {setReady(true); try {localStorage.setItem("jon-remote", "1");} catch {}}}>Ich bin mit dem Pi verbunden</button>
      <button className="btn outline" onClick={() => shell.push("pair")}>Pi-Verbindung verwalten</button>
    </div>
  </>;
  return <>
    <PageHeader title="Fernzugriff" onBack={back} right={<Circle label="Aktualisieren" onClick={status.refresh}><RefreshCw/></Circle>}/>
    <div className="page-scroll">
      <div className="remote" style={{padding: "0 0 22px"}}><Laptop/><h1>{status.data?.hostname || shell.conn.name || "Dein Pi"}</h1><p style={{margin: "6px 0 0"}}>{status.data ? `${status.data.system} · ${status.data.machine} · ${(status.data.free / 1073741824).toFixed(1)} GB frei` : status.error || "Verbinde …"}</p></div>
      <div className="tool-grid">{tiles.map((t, i) => <motion.button key={t.id} initial={{opacity: 0, scale: .96}} animate={{opacity: 1, scale: 1}} transition={{delay: i * .04}} onClick={() => {
        haptic("tick");
        setOutput("");
        if (t.id === "work") {shell.chats.create("coding", status.data?.root || ""); back();}
        else if (t.id === "browser") {const thread = shell.chats.create("coding"); shell.chats.send("Öffne eine Browser-Aufgabe auf dem Pi und frag mich, was du im Web erledigen sollst.", "", thread); back();}
        else {setPanel(t.id); if (t.id === "files") browse(status.data?.root || "/home");}
      }}>{t.icon}<strong>{t.name}</strong><span>{t.sub}</span></motion.button>)}</div>
    </div>
    <Sheet open={!!panel} title={tiles.find(t => t.id === panel)?.name || ""} onClose={() => setPanel("")}>
      {panel === "terminal" && <><Field label="Befehl auf dem Pi" value={command} onChange={setCommand} multiline/><button className="btn primary" disabled={!command.trim() || busy} onClick={() => run("/api/system/cmd", {command})}><Play/>Ausführen</button></>}
      {panel === "program" && <><Field label="Programm oder Pfad" value={program} onChange={setProgram}/><button className="btn primary" disabled={!program.trim() || busy} onClick={() => run("/api/system/start-program", {path: program, args: []})}><Play/>Starten</button></>}
      {panel === "status" && status.data && <><div className="stat"><span>Gerät</span><b>{status.data.hostname}</b></div><div className="stat"><span>System</span><b>{status.data.system} · {status.data.machine}</b></div><div className="stat"><span>Freier Speicher</span><b>{(status.data.free / 1073741824).toFixed(1)} von {(status.data.total / 1073741824).toFixed(0)} GB</b></div><div className="stat"><span>Arbeitsordner</span><b>{status.data.root}</b></div></>}
      {panel === "files" && <>
        <div className="search-field"><Folder/><input value={path} onChange={e => setPath(e.target.value)} onKeyDown={e => {if (e.key === "Enter") browse(path);}}/><button onClick={() => browse(path.split("/").slice(0, -1).join("/") || "/")}><ArrowUp/></button></div>
        {editing ? <><textarea className="terminal" style={{width: "100%", minHeight: 260}} value={text} onChange={e => setText(e.target.value)}/><button className="btn primary" onClick={() => run("/api/system/files/write", {path, content: text})}>Datei speichern</button></>
          : files.map(f => {const dir = f.is_dir || f.type === "dir" || f.dir; const next = f.path || `${path.replace(/\/$/, "")}/${f.name}`; return <button className="list-row" key={next} onClick={async () => {if (dir) browse(next); else {try {const content = await api("/api/system/files/read", "POST", {path: next}); setText(content.content ?? ""); setPath(next); setEditing(true);} catch (e) {shell.notify(errorText(e));}}}}>{dir ? <Folder/> : <FileText/>}<span>{f.name}</span><ChevronRight size={18}/></button>;})}
      </>}
      {busy && <Busy text="Pi arbeitet …"/>}
      {output && <pre className="terminal">{output}</pre>}
    </Sheet>
  </>;
}

export function PluginsPage({shell, back}: PageProps) {
  const result = useLoad<any>(() => api("/api/tools"));
  const [query, setQuery] = useState(""), [selected, setSelected] = useState<any>(null), [skill, setSkill] = useState(false), [name, setName] = useState(""), [content, setContent] = useState(""), [view, setView] = useState("Plugins"), [switcher, setSwitcher] = useState(false);
  const groups: any[] = (result.data?.gruppen || []).filter((g: any) => `${g.name} ${JSON.stringify(g.werkzeuge)}`.toLowerCase().includes(query.toLowerCase()));
  const skills: any[] = (result.data?.skills || []).filter((s: any) => s.name.toLowerCase().includes(query.toLowerCase()));
  const popular = [...groups].sort((a, b) => (b.anzahl || 0) - (a.anzahl || 0));
  const tile = (g: any, cls = "") => <span className={`plugin-tile ${cls}`}>{g.symbol || "🧩"}</span>;
  return <>
    <PageHeader title={view} onBack={back} onTitle={() => setSwitcher(true)}/>
    <div className="page-scroll">
      {result.busy ? <Busy/> : result.error ? <p className="error-text">{result.error}</p> : view === "Plugins" ? <>
        <div className="section-title"><button onClick={() => setSelected({name: "Installiert", werkzeuge: groups.flatMap(g => g.werkzeuge || [])})}>Installiert<ChevronRight/></button></div>
        <div className="installed">{groups.slice(0, 5).map(g => <button key={g.id} onClick={() => setSelected(g)}>{tile(g)}</button>)}{groups.length > 5 && <span className="plugin-tile more">+{groups.length - 5}</span>}</div>
        <div className="section-title"><span>Beliebt</span><ChevronRight/></div>
        {popular.map(g => <button className="plugin-row" key={g.id} onClick={() => setSelected(g)}>{tile(g)}<div><strong>{g.name}</strong><small>{g.werkzeuge?.[0]?.beschreibung?.replace(/^GESPERRT:\s*/, "") || `${g.anzahl} Werkzeuge`}</small></div><MoreHorizontal/></button>)}
        <div className="section-title"><span>Neu und bemerkenswert</span><ChevronRight/></div>
        {skills.slice(0, 6).map(s => <button className="plugin-row" key={s.name} onClick={async () => {try {const v = await api(`/api/skills/${enc(s.name)}`); setName(s.name); setContent(v.content || ""); setSkill(true);} catch (e) {shell.notify(errorText(e));}}}><span className="plugin-tile">✨</span><div><strong>{s.name}</strong><small>Eigener Skill auf deinem Pi</small></div><MoreHorizontal/></button>)}
        <button className="plugin-row" onClick={() => {setName(""); setContent(""); setSkill(true);}}><span className="plugin-tile">➕</span><div><strong>Skill hinzufügen</strong><small>Bring Jon eine neue Fähigkeit bei</small></div><Plus/></button>
      </> : <>{skills.map(s => <button className="plugin-row" key={s.name} onClick={async () => {try {const v = await api(`/api/skills/${enc(s.name)}`); setName(s.name); setContent(v.content || ""); setSkill(true);} catch (e) {shell.notify(errorText(e));}}}><span className="plugin-tile">✨</span><div><strong>{s.name}</strong><small>Skill</small></div><ChevronRight/></button>)}<button className="btn soft" onClick={() => {setName(""); setContent(""); setSkill(true);}}><Plus/>Neuer Skill</button></>}
    </div>
    <div className="bottom-bar"><label className="search-pill"><Search/><input placeholder={view === "Plugins" ? "Plugins suchen" : "Skills suchen"} value={query} onChange={e => setQuery(e.target.value)}/></label></div>
    <Sheet open={switcher} title="Ansicht" onClose={() => setSwitcher(false)}>{["Plugins", "Skills"].map(v => <button key={v} className="list-row" onClick={() => {setView(v); setSwitcher(false);}}><span>{v}</span>{view === v && <Check className="check"/>}</button>)}</Sheet>
    <Sheet open={!!selected} title={selected?.name || ""} onClose={() => setSelected(null)}>
      {(selected?.werkzeuge || []).map((t: any) => <button className="list-row" key={t.name} style={{alignItems: "flex-start", padding: "12px 6px"}} onClick={() => {setSelected(null); compose(`${String(t.beschreibung || t.name).replace(/^GESPERRT:\s*/, "").split(/[.:]/)[0]}: `, "coding"); back();}}><span>{t.name.replaceAll("_", " ")}<small>{String(t.beschreibung || "").replace(/^GESPERRT:\s*/, "")}</small>{t.frei === false && <small className="lock">Auf dem Pi noch nicht freigegeben</small>}</span></button>)}
    </Sheet>
    <Sheet open={skill} title={name ? name : "Neuer Skill"} onClose={() => setSkill(false)}>
      <Field label="Name" value={name} onChange={setName}/>
      <Field label="Anweisungen" value={content} onChange={setContent} multiline/>
      <button className="btn primary" disabled={!name.trim() || !content.trim()} onClick={async () => {try {await api(`/api/skills/${enc(name.trim())}`, "PUT", {content}); setSkill(false); result.refresh(); shell.notify("Skill gespeichert.");} catch (e) {shell.notify(errorText(e));}}}>Speichern</button>
    </Sheet>
  </>;
}

export function SearchPage({shell, back}: PageProps) {
  const [query, setQuery] = useState(""), [results, setResults] = useState<any[]>([]), [busy, setBusy] = useState(false);
  useEffect(() => {
    if (query.trim().length < 2) {setResults([]); return;}
    let live = true;
    const timer = setTimeout(() => {
      setBusy(true);
      Promise.allSettled([api(`/api/dateien/suche?frage=${enc(query)}`), api("/api/projects")]).then(([files, projects]) => {
        if (!live) return;
        const q = query.toLowerCase();
        setResults([
          ...(files.status === "fulfilled" ? (files.value.dateien || []).map((f: any) => ({...f, kind: "file"})) : []),
          ...(projects.status === "fulfilled" ? projects.value.filter((p: any) => `${p.name} ${p.note}`.toLowerCase().includes(q)).map((p: any) => ({...p, kind: "project"})) : [])
        ]);
      }).finally(() => {if (live) setBusy(false);});
    }, 260);
    return () => {live = false; clearTimeout(timer);};
  }, [query]);
  const chatHits = query.trim() ? shell.chats.list.filter(item => `${shell.state.chats?.[item.id]?.title || item.title}`.toLowerCase().includes(query.toLowerCase())) : [];
  return <>
    {!query.trim() ? <div className="search-empty"><span className="box"><Search/></span><strong>Chats, Dateien und Projekte suchen</strong></div> : <div className="page-scroll" style={{paddingTop: 16}}>
      {chatHits.length > 0 && <div className="section-title">Chats</div>}
      {chatHits.map(item => <button className="list-row" key={item.id} onClick={() => {shell.chats.open(item.id).then(back).catch(e => shell.notify(errorText(e)));}}><MessageCircle/><span>{shell.state.chats?.[item.id]?.title || item.title}</span></button>)}
      {results.length > 0 && <div className="section-title">Dateien und Projekte</div>}
      {results.map(item => item.kind === "file" ? <FilePill key={item.id || filePath(item)} file={item} notify={shell.notify}/> : <button className="list-row" key={item.id} onClick={() => {shell.chats.create("coding", item.root); back();}}><Folder/><span>{item.name}<small>{item.root}</small></span></button>)}
      {busy && <Busy/>}
      {!busy && !chatHits.length && !results.length && <p className="muted" style={{textAlign: "center", marginTop: 40}}>Nichts gefunden.</p>}
    </div>}
    <div className="bottom-bar"><label className="search-pill"><Search/><input autoFocus aria-label="Suchen" placeholder="Suchen" value={query} onChange={e => setQuery(e.target.value)}/></label><Circle label="Suche schließen" onClick={back}><X/></Circle></div>
  </>;
}

export function ArchivePage({shell, back}: PageProps) {
  const archived = shell.chats.list.filter(item => shell.state.chats?.[item.id]?.archived);
  return <>
    <PageHeader title="Archivierte Chats" onBack={back}/>
    <div className="page-scroll">{archived.length ? <div className="group compact">{archived.map(item => <button className="row-btn" key={item.id} onClick={() => shell.chats.open(item.id).then(back).catch(e => shell.notify(errorText(e)))}><Archive/><span>{shell.state.chats[item.id]?.title || item.title}</span><span className="value" onClick={e => {e.stopPropagation(); shell.saveState({chats: {[item.id]: {...shell.state.chats[item.id], archived: false}}}).then(() => shell.notify("Wiederhergestellt."));}}>Zurückholen</span></button>)}</div> : <Empty icon={<Archive/>} title="Kein Archiv" text="Archivierte Chats erscheinen hier."/>}</div>
  </>;
}

const appMeta: Record<string, {name: string; sub: string; g: string; icon: React.ReactNode}> = {
  whatsapp: {name: "WhatsApp", sub: "Nachrichten und Anrufe", g: "linear-gradient(145deg,#25d366,#0f7a5c)", icon: <MessageCircle/>},
  tiktok: {name: "TikTok", sub: "Videos entdecken", g: "linear-gradient(145deg,#111 30%,#25f4ee 140%),linear-gradient(0deg,#fe2c55,#fe2c55)", icon: <Music2/>},
  amazon: {name: "Amazon Music", sub: "Deine Musik", g: "linear-gradient(120deg,#0b2447 0%,#1466c8 55%,#25d1da 120%)", icon: <Headphones/>}
};

const sperrText: Record<string, string> = {pause: "Pause", nacht: "Schlafenszeit", limit: "Limit erreicht"};

function restText(minuten: number) {
  if (minuten <= 0) return "Keine Zeit mehr";
  const h = Math.floor(minuten / 60), m = minuten % 60;
  return `Noch ${h ? `${h} h ` : ""}${m || !h ? `${m} min` : ""}`.trim();
}

function farbe(text: string) {
  let h = 0;
  for (const z of text) h = (h * 31 + z.charCodeAt(0)) % 360;
  return `linear-gradient(145deg, hsl(${h} 55% 40%), hsl(${(h + 45) % 360} 60% 20%))`;
}

export function AppsPage({shell, back}: PageProps) {
  const apps = useApps();
  const [music, setMusic] = useState<any>(null), [zeit, setZeit] = useState<any>(null), [wahl, setWahl] = useState(false);
  const [anfrage, setAnfrage] = useState<{id: string; name: string; grund?: string} | null>(null);
  const admin = useAdmin(shell.notify);
  const hatMusik = !!apps?.some(a => a.id === "amazon" && a.installiert !== false);
  useEffect(() => {
    const refresh = () => {
      call("zeit").then(setZeit).catch(() => {});
      if (hatMusik) call("music", {aktion: "status"}).then(setMusic).catch(e => setMusic({fehler: errorText(e)}));
    };
    refresh();
    const timer = setInterval(refresh, 4000);
    return () => clearInterval(timer);
  }, [hatMusik]);
  const open = (id: string) => {haptic("tap"); call("app", {app: id}).catch(e => shell.notify(errorText(e)));};
  const control = (aktion: string) => {haptic("tick"); call("music", {aktion}).then(v => setMusic((m: any) => ({...m, ...v}))).catch(e => shell.notify(errorText(e)));};
  const liste = apps || [];
  return <div className="apps-page" style={{display: "contents"}}>
    <PageHeader title="Apps" onBack={back}/>
    <div className="page-scroll">
      <p className="muted" style={{margin: "0 4px 16px"}}>Diese Apps kannst du aus Jon heraus öffnen. Mit Zurück oder Home kommst du immer wieder zu Jon.</p>
      {apps === null ? <Busy/> : <div className="hero-apps">{liste.map((app, i) => {
        const meta = appMeta[app.id];
        const missing = app.installiert === false;
        const grund = zeit?.gesperrt?.[app.id];
        const rest = zeit?.rest?.[app.id];
        const limit = zeit?.limits?.[app.id] || 0;
        const anteil = limit ? Math.min(1, (zeit?.genutzt?.[app.id] || 0) / limit) : 0;
        const breit = liste.length % 2 === 1 && i === liste.length - 1;
        const laeuft = !!grund && zeit?.anfrage?.app === app.id;
        const tippen = () => {
          if (!grund || missing) return open(app.id);
          haptic("tap");
          if (laeuft) return shell.notify("Deine Anfrage läuft noch. Ich sag dir Bescheid, sobald die Antwort da ist.");
          setAnfrage({id: app.id, name: app.name, grund});
        };
        return <motion.button key={app.id} className={`app-card ${breit ? "wide" : ""} ${missing ? "missing" : ""} ${grund ? "gesperrt" : ""}`} style={{"--g": meta?.g || farbe(app.paket)} as React.CSSProperties} initial={{opacity: 0, y: 16, scale: .97}} animate={{opacity: missing ? .55 : 1, y: 0, scale: 1}} whileTap={{scale: .97}} transition={{...spring, delay: Math.min(i, 10) * .05}} onClick={tippen}>
          <span className="logo">{meta ? meta.icon : <AppSymbol paket={app.paket} name={app.name} groesse={30}/>}</span>
          <span><strong>{app.name}</strong><small>{missing ? "Nicht installiert" : laeuft ? "Anfrage läuft …" : grund ? `${sperrText[grund] || "Gesperrt"}${grund === "nacht" && zeit?.nacht_ende ? ` bis ${zeit.nacht_ende}` : grund === "pause" && zeit?.pause_ende ? ` bis ${zeit.pause_ende}` : ""} · Mehr Zeit?` : zeit?.frei_bis?.[app.id] ? `Frei bis ${zeit.frei_bis[app.id]}` : typeof rest === "number" ? restText(rest) : meta?.sub || "Tippen zum Öffnen"}</small></span>
          {grund && <span className="app-schloss"><Lock/></span>}
          {!grund && limit > 0 && <span className="app-balken"><i style={{width: `${Math.round(anteil * 100)}%`}}/></span>}
        </motion.button>;
      })}
        <motion.button className={`app-card neu ${liste.length % 2 === 0 ? "wide" : ""}`} initial={{opacity: 0, y: 16}} animate={{opacity: 1, y: 0}} transition={{...spring, delay: Math.min(liste.length, 10) * .05}} onClick={() => admin.guard(() => setWahl(true))}>
          <span className="logo"><Plus/></span>
          <span><strong>Apps auswählen</strong><small>{liste.length ? "Für Eltern: freigeben oder entfernen" : "Noch keine App freigegeben"}</small></span>
        </motion.button>
      </div>}
      {hatMusik && <div className="player">
        <span className="file-badge" style={{background: appMeta.amazon.g}}><Headphones size={20}/></span>
        <div><strong>{music?.titel || (music?.fehler ? "Amazon Music" : "Keine Wiedergabe")}</strong><small>{music?.fehler || music?.kuenstler || (music?.spielt ? "Spielt gerade" : "Pausiert")}</small></div>
        <button aria-label="Zurück" onClick={() => control("previous")}><SkipBack/></button>
        <button className="main" aria-label={music?.spielt ? "Pause" : "Abspielen"} onClick={() => control(music?.spielt ? "pause" : "play")}>{music?.spielt ? <Pause fill="currentColor"/> : <Play fill="currentColor"/>}</button>
        <button aria-label="Weiter" onClick={() => control("next")}><SkipForward/></button>
      </div>}
      {hatMusik && music?.fehler && <p className="hint" style={{margin: "12px 6px"}}>Für die Steuerung braucht Jon Medienzugriff. Das richtest du unter Einstellungen → Kindersicherung ein.</p>}
      {zeit && <button className="text-link small" style={{margin: "14px 6px"}} onClick={() => shell.push("zeit")}><Hourglass size={15}/>Bildschirmzeit ansehen</button>}
    </div>
    {admin.element}
    <AppWahl open={wahl} onClose={() => setWahl(false)} notify={shell.notify}/>
    <ZeitAnfrage app={anfrage} onClose={() => setAnfrage(null)} onGesendet={setZeit} notify={shell.notify}/>
  </div>;
}
