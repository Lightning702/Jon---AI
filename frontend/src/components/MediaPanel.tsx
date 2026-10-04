import {useEffect, useRef, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {AudioLines, AudioWaveform, Captions, Check, Copy, Download, FileAudio, FileText, Link2, Loader2, Mic, Sparkles, Square, Upload, Volume2, X} from "lucide-react";
import {MediaJob, mediaFile, mediaRequest, uploadMedia} from "../lib/media";
import "./media.css";

const ended = new Set(["done", "failed", "cancelled", "interrupted"]);
const MODI = [
  {key: "transcribe", label: "Audio → Text", text: "Aufnahmen vollständig abtippen", icon: FileAudio},
  {key: "youtube", label: "YouTube erklären", text: "Video über Untertitel zusammenfassen", icon: Captions},
  {key: "speech", label: "Text → Audio", text: "Text als MP3 vorlesen lassen", icon: Volume2},
] as const;
const STIMMEN = [
  {key: "de-DE-ConradNeural", name: "Jon", sprache: "Deutsch", ton: "ruhig"},
  {key: "de-DE-KatjaNeural", name: "Katja", sprache: "Deutsch", ton: "klar"},
  {key: "de-DE-KillianNeural", name: "MiniJon", sprache: "Deutsch", ton: "jung"},
  {key: "en-US-AriaNeural", name: "Aria", sprache: "Englisch", ton: "warm"},
  {key: "en-US-GuyNeural", name: "Guy", sprache: "Englisch", ton: "tief"},
];
const STATUS: Record<string, {text: string; art: string}> = {queued: {text: "Wartet", art: "laeuft"}, working: {text: "Läuft", art: "laeuft"}, cancelling: {text: "Stoppt", art: "laeuft"}, done: {text: "Fertig", art: "ok"}, failed: {text: "Fehlgeschlagen", art: "fehler"}, cancelled: {text: "Gestoppt", art: "aus"}, interrupted: {text: "Unterbrochen", art: "aus"}};
const ICON: Record<string, typeof Mic> = {transcribe: FileAudio, youtube: Captions, speech: Volume2};

function groesse(bytes?: number) {
  if (!bytes) return "";
  return bytes > 1048576 ? `${(bytes / 1048576).toFixed(1).replace(".", ",")} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function zeit(sekunden?: number) {
  if (!sekunden) return "";
  return new Date(sekunden * 1000).toLocaleString("de-AT", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"});
}

export default function MediaPanel({onClose, uploads = [], initialMode = "transcribe", initialText = "", autoStart = false, eingebettet = false}: {onClose?: () => void; uploads?: {id: string; name: string; size?: number}[]; initialMode?: string; initialText?: string; autoStart?: boolean; eingebettet?: boolean}) {
  const [mode, setMode] = useState(initialMode);
  const [audio, setAudio] = useState<{id: string; name: string; size?: number} | null>(uploads[0] || null);
  const [weitere, setWeitere] = useState(uploads);
  const started = useRef(false);
  const datei = useRef<HTMLInputElement>(null);
  const [text, setText] = useState(initialText);
  const [url, setUrl] = useState("");
  const [voice, setVoice] = useState("de-DE-ConradNeural");
  const [summarize, setSummarize] = useState(false);
  const [jobs, setJobs] = useState<(MediaJob & {created_at?: number})[]>([]);
  const [selected, setSelected] = useState("");
  const [job, setJob] = useState<MediaJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [laedt, setLaedt] = useState(false);
  const [ziehen, setZiehen] = useState(false);
  const [error, setError] = useState("");
  const [kopiert, setKopiert] = useState(false);

  useEffect(() => {
    if (eingebettet || !onClose) return;
    const taste = (e: KeyboardEvent) => {if (e.key === "Escape") onClose();};
    window.addEventListener("keydown", taste);
    return () => window.removeEventListener("keydown", taste);
  }, [eingebettet, onClose]);

  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      let schnell = false;
      try {
        if (!document.hidden) {
          const values = await mediaRequest<MediaJob[]>("/jobs");
          if (!live) return;
          setJobs(values);
          schnell = values.some(v => !ended.has(v.status));
          if (!selected && values.length) setSelected(values[0].id);
          if (selected) {const current = await mediaRequest<MediaJob>("/jobs/" + selected); if (live) setJob(current);}
        }
      } catch (e) {if (live) setError(e instanceof Error ? e.message : "Verbindung unterbrochen.");}
      finally {if (live) timer = setTimeout(refresh, schnell ? 1500 : 4000);}
    };
    void refresh();
    return () => {live = false; clearTimeout(timer);};
  }, [selected]);

  const action = async (fn: () => Promise<void>) => {setBusy(true); setError(""); try {await fn();} catch (e) {setError(e instanceof Error ? e.message : "Auftrag fehlgeschlagen.");} finally {setBusy(false);}};
  const hochladen = (file?: File) => {
    if (!file) return;
    setLaedt(true);
    setError("");
    void uploadMedia(file).then(neu => {const eintrag = {...neu, size: file.size}; setAudio(eintrag); setWeitere(items => [eintrag, ...items.filter(i => i.id !== neu.id)]);}).catch(e => setError(e instanceof Error ? e.message : "Audio konnte nicht hochgeladen werden.")).finally(() => setLaedt(false));
  };
  const start = () => action(async () => {
    const value = await mediaRequest<MediaJob>("/jobs", {kind: mode, upload_id: audio?.id || "", url, text, voice, summarize: mode === "youtube" || summarize});
    setJob(value); setSelected(value.id); setJobs(items => [value, ...items.filter(i => i.id !== value.id)]);
  });
  useEffect(() => {if (autoStart && !started.current) {started.current = true; void start();}}, []);

  const bereit = mode === "transcribe" ? !!audio : mode === "youtube" ? /^https?:\/\/\S+/.test(url.trim()) : !!text.trim();
  const laeuft = !!job && !ended.has(job.status);
  const status = job ? STATUS[job.status] || {text: job.status, art: "aus"} : null;
  const knopf = mode === "transcribe" ? "Vollständig transkribieren" : mode === "youtube" ? "Transkript holen & zusammenfassen" : "Audiodatei erstellen";

  const inhalt = <section className={"md " + (eingebettet ? "md-eingebettet" : "md-fenster")} role={eingebettet ? undefined : "dialog"} aria-modal={eingebettet ? undefined : true} aria-label="Stimmen & Transkripte" onMouseDown={e => e.stopPropagation()}>
    <header className="md-kopf">
      <span className={"md-emblem " + (laeuft ? "aktiv" : "")}><AudioLines size={20}/></span>
      <div className="md-kopf-text">
        <h2>Stimmen & Transkripte</h2>
        <p>Audio verstehen, Videos über ihre Untertitel zusammenfassen und Text hörbar machen.</p>
      </div>
      {!eingebettet && onClose && <button className="md-zu" aria-label="Schließen" onClick={onClose}><X size={18}/></button>}
    </header>

    <div className="md-modi" role="tablist" aria-label="Was möchtest du tun?">
      {MODI.map(m => <button key={m.key} role="tab" aria-selected={mode === m.key} className={mode === m.key ? "an" : ""} onClick={() => setMode(m.key)}>
        {mode === m.key && <motion.span layoutId={eingebettet ? "md-modus-e" : "md-modus"} className="md-modus-hinten" transition={{type: "spring", stiffness: 420, damping: 34}}/>}
        <m.icon size={16}/><span><b>{m.label}</b><small>{m.text}</small></span>
      </button>)}
    </div>

    <AnimatePresence>{error && <motion.div className="md-fehler" role="alert" initial={{opacity: 0, height: 0}} animate={{opacity: 1, height: "auto"}} exit={{opacity: 0, height: 0}}><span>{error}</span><button aria-label="Fehler schließen" onClick={() => setError("")}><X size={14}/></button></motion.div>}</AnimatePresence>

    <div className="md-raster">
      <div className="md-eingabe">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={mode} className="md-karte" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -6}} transition={{duration: 0.18}}>
            {mode === "transcribe" && <>
              <div className={"md-ablage " + (ziehen ? "ziehen " : "") + (audio ? "voll" : "")} role="button" tabIndex={0} aria-label="Audiodatei auswählen" onClick={() => datei.current?.click()} onKeyDown={e => {if (e.key === "Enter" || e.key === " ") {e.preventDefault(); datei.current?.click();}}} onDragOver={e => {e.preventDefault(); setZiehen(true);}} onDragLeave={() => setZiehen(false)} onDrop={e => {e.preventDefault(); setZiehen(false); hochladen(e.dataTransfer.files?.[0]);}}>
                <input ref={datei} type="file" hidden accept="audio/*,video/*,.mp3,.m4a,.flac,.opus,.wav,.ogg" onChange={e => {hochladen(e.target.files?.[0]); e.target.value = "";}}/>
                {laedt ? <><Loader2 size={24} className="md-dreh"/><b>Wird hochgeladen …</b><small>Große Dateien brauchen einen Moment.</small></> : audio ? <><span className="md-datei-icon"><FileAudio size={20}/></span><b>{audio.name}</b><small>{groesse(audio.size) ? groesse(audio.size) + " · " : ""}bereit · zum Ändern klicken oder neue Datei hierher ziehen</small></> : <><span className="md-ablage-icon"><Upload size={20}/></span><b>Audio- oder Videodatei hierher ziehen</b><small>oder klicken zum Auswählen · MP3, M4A, WAV, FLAC, OPUS · bis 200 MB</small></>}
              </div>
              {weitere.length > 1 && <div className="md-chips" aria-label="Angehängte Dateien">{weitere.map(item => <button key={item.id} className={audio?.id === item.id ? "an" : ""} onClick={() => setAudio(item)}><FileAudio size={12}/>{item.name}</button>)}</div>}
              <label className="md-schalter"><input type="checkbox" checked={summarize} onChange={e => setSummarize(e.target.checked)}/><span className="md-schalter-bahn"><i/></span><span><b>Zusätzlich zusammenfassen</b><small>mit deinem eingestellten KI-Modell, nachdem alles abgetippt ist</small></span></label>
              <p className="md-notiz">Die gesamte Tonspur wird lokal auf deinem Gerät transkribiert. Lange Aufnahmen brauchen Zeit, du kannst währenddessen mit Jon weiterarbeiten.</p>
            </>}
            {mode === "youtube" && <>
              <label className="md-feld"><span>YouTube-Link</span><div className="md-feld-zeile"><Link2 size={15}/><input type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=…" spellCheck={false}/></div></label>
              <p className="md-notiz">Jon ruft die verfügbaren Untertitel ab und übergibt sie deinem eingestellten Modell. Gibt es keine zugänglichen Untertitel, bekommst du keine erfundene Zusammenfassung.</p>
            </>}
            {mode === "speech" && <>
              <label className="md-feld"><span>Text oder Podcast-Skript<em>{text.length.toLocaleString("de-AT")} / 80.000</em></span><textarea rows={7} maxLength={80000} value={text} onChange={e => setText(e.target.value)} placeholder="Dein vollständiger Text …"/></label>
              <div className="md-feld"><span>Stimme</span><div className="md-stimmen" role="radiogroup" aria-label="Stimme">{STIMMEN.map(s => <button key={s.key} role="radio" aria-checked={voice === s.key} className={voice === s.key ? "an" : ""} onClick={() => setVoice(s.key)}><span className="md-stimme-icon"><Mic size={13}/></span><b>{s.name}</b><small>{s.sprache} · {s.ton}</small></button>)}</div></div>
              <p className="md-notiz">Der Text wird abschnittsweise an Microsofts Sprachausgabe übermittelt und als MP3 gespeichert.</p>
            </>}
          </motion.div>
        </AnimatePresence>
        <button className="md-start" disabled={busy || laedt || !bereit} onClick={() => void start()}>{busy ? <Loader2 size={17} className="md-dreh"/> : <Sparkles size={17}/>}{busy ? "Bereitet vor …" : knopf}</button>
      </div>

      <aside className="md-auftraege" aria-label="Medienaufträge">
        <div className="md-abschnitt"><span>Aufträge</span>{jobs.length > 0 && <em>{jobs.length}</em>}</div>
        <div className="md-liste">
          {!jobs.length && <div className="md-leer"><AudioWaveform size={18}/><span>Hier erscheinen deine Transkripte und Audiodateien.</span></div>}
          {jobs.map((item, i) => {
            const Icon = ICON[item.kind] || Mic;
            const st = STATUS[item.status] || {text: item.status, art: "aus"};
            return <button key={item.id} className={"md-auftrag " + (selected === item.id ? "an " : "") + st.art} style={{["--i" as string]: i}} onClick={() => {if (item.id !== selected) {setJob(null); setSelected(item.id);}}}>
              <span className="md-auftrag-icon"><Icon size={14}/></span>
              <span className="md-auftrag-text"><b>{item.title}</b><small>{st.art === "laeuft" ? `${item.progress}% · ${item.message || st.text}` : `${st.text}${item.created_at ? " · " + zeit(item.created_at) : ""}`}</small>{st.art === "laeuft" && <span className="md-balken klein"><i style={{width: `${item.progress}%`}}/></span>}</span>
            </button>;
          })}
        </div>
      </aside>
    </div>

    <AnimatePresence mode="wait">{job && <motion.article key={job.id} className={"md-ergebnis " + (status?.art || "")} initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}} transition={{duration: 0.2}}>
      <div className="md-ergebnis-kopf">
        <span className={"md-status " + (status?.art || "")}>{laeuft ? <span className="md-eq" aria-hidden><i/><i/><i/><i/></span> : status?.art === "ok" ? <Check size={12}/> : null}{status?.text}</span>
        <strong>{job.title}</strong>
        {laeuft && <button className="md-stopp" disabled={busy} onClick={() => void action(async () => setJob(await mediaRequest<MediaJob>("/jobs/" + job.id + "/cancel", {})))}><Square size={11} fill="currentColor"/>Stoppen</button>}
      </div>
      {laeuft && <><p className="md-meldung">{job.message}</p><div className="md-balken"><i style={{width: `${job.progress}%`}}/></div></>}
      {job.error && <p className="md-ergebnis-fehler">{job.error}</p>}
      {job.url && <p className="md-notiz">{job.automatic ? "Automatisch erzeugte" : "Vorhandene"} YouTube-Untertitel · können Erkennungsfehler enthalten.</p>}
      {job.files?.includes("audio.mp3") && <audio className="md-player" controls preload="metadata" src={mediaFile(job.id, "audio.mp3")}/>}
      {!!job.files?.length && <div className="md-downloads">{job.files.map(file => <a key={file} href={mediaFile(job.id, file)} download>{file === "audio.mp3" ? <Volume2 size={14}/> : <FileText size={14}/>}{file === "audio.mp3" ? "MP3 herunterladen" : "Vollständiges Transkript"}<Download size={13}/></a>)}</div>}
      {job.summary && <div className="md-zusammenfassung"><h3><Sparkles size={14}/>Zusammenfassung</h3><p>{job.summary}</p></div>}
      {job.preview && <details className="md-vorschau" open={!job.summary}>
        <summary><FileText size={14}/>{job.preview_truncated ? "Transkript-Vorschau · vollständig im Download" : "Vollständiger Text"}<button type="button" onClick={e => {e.preventDefault(); void navigator.clipboard?.writeText(job.preview || "").then(() => {setKopiert(true); setTimeout(() => setKopiert(false), 1800);});}}>{kopiert ? <Check size={12}/> : <Copy size={12}/>}{kopiert ? "Kopiert" : "Kopieren"}</button></summary>
        <pre>{job.preview}</pre>
      </details>}
    </motion.article>}</AnimatePresence>
  </section>;

  if (eingebettet) return inhalt;
  return <motion.div className="md-schleier" initial={{opacity: 0}} animate={{opacity: 1}} onMouseDown={() => onClose?.()}>{inhalt}</motion.div>;
}
