import {useEffect, useRef, useState} from "react";
import {MediaJob, mediaFile, mediaRequest, uploadMedia} from "../lib/media";
import "./agent-team.css";
import MiniJonActivity from "./MiniJonActivity";

const ended = new Set(["done", "failed", "cancelled", "interrupted"]);
export default function MediaPanel({onClose, uploads = [], initialMode = "transcribe", initialText = "", autoStart = false}: {onClose: () => void; uploads?: {id: string; name: string}[]; initialMode?: string; initialText?: string; autoStart?: boolean}) {
  const [mode, setMode] = useState(initialMode);
  const [audio, setAudio] = useState<{id: string; name: string} | null>(uploads[0] || null);
  const started = useRef(false);
  const [text, setText] = useState(initialText);
  const [url, setUrl] = useState("");
  const [voice, setVoice] = useState("de-DE-ConradNeural");
  const [summarize, setSummarize] = useState(false);
  const [jobs, setJobs] = useState<MediaJob[]>([]);
  const [selected, setSelected] = useState("");
  const [job, setJob] = useState<MediaJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        if (!document.hidden) {
          const values = await mediaRequest<MediaJob[]>("/jobs");
          if (!live) return;
          setJobs(values);
          if (!selected && values.length) setSelected(values[0].id);
          if (selected) {const current = await mediaRequest<MediaJob>("/jobs/" + selected); if (live) setJob(current);}
        }
      } catch(e) {if (live) setError(e instanceof Error ? e.message : "Verbindung unterbrochen.");}
      finally {if (live) timer = setTimeout(refresh, 2000);}
    };
    void refresh();
    return () => {live = false; clearTimeout(timer);};
  }, [selected]);
  const action = async (fn: () => Promise<void>) => {setBusy(true); setError(""); try {await fn();} catch(e) {setError(e instanceof Error ? e.message : "Auftrag fehlgeschlagen.");} finally {setBusy(false);}};
  const start = () => action(async () => {
    const value = await mediaRequest<MediaJob>("/jobs", {kind: mode, upload_id: audio?.id || "", url, text, voice, summarize: mode === "youtube" || summarize});
    setJob(value); setSelected(value.id); setJobs(items => [value, ...items]);
  });
  useEffect(() => {if (autoStart && !started.current) {started.current = true; void start();}}, []);
  return <div className="fixed inset-0 z-[75] bg-black/70 flex items-center justify-center p-3"><section className="glass border border-white/15 rounded-2xl w-[820px] max-w-full max-h-[92vh] overflow-auto p-5 agent-team" aria-label="Jon Medien">
    <div className="agent-run-top"><div><h2>Stimmen & Transkripte</h2><p className="agent-note">Audio verstehen. Videos anhand ihrer Untertitel zusammenfassen. Text hörbar machen.</p></div><button aria-label="Medien schließen" onClick={onClose}>✕</button></div>
    <MiniJonActivity activity={mode === "speech" ? "speaking" : mode === "youtube" ? "research" : "writing"} status={job && !ended.has(job.status) ? "working" : "idle"} label={job?.message || "MiniJon hört genau hin"}/>
    <div className="agent-chips">{[["transcribe", "Audio → Text"], ["youtube", "YouTube erklären"], ["speech", "Text → Audio"]].map(([key, label]) => <button key={key} aria-pressed={mode === key} onClick={() => setMode(key)}>{label}</button>)}</div>
    {error && <div role="alert" className="agent-error">{error}</div>}
    {mode === "transcribe" && <><label>Audiodatei · bis 200 MB<input type="file" accept="audio/*,video/*,.mp3,.m4a,.flac,.opus" disabled={busy} onChange={e => {const file = e.target.files?.[0]; if (file) void action(async () => setAudio(await uploadMedia(file)));}}/></label>{uploads.length > 1 && <select aria-label="Angehängte Audiodatei" value={audio?.id} onChange={e => setAudio(uploads.find(item => item.id === e.target.value) || null)}>{uploads.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}{audio && <p>{audio.name} · bereit</p>}<p className="agent-note">Die gesamte Tonspur wird lokal transkribiert. Lange Aufnahmen brauchen Zeit. Du kannst währenddessen mit Jon weiterarbeiten.</p><label className="agent-check"><input type="checkbox" checked={summarize} onChange={e => setSummarize(e.target.checked)}/>Zusätzlich durch mein eingestelltes KI-Modell zusammenfassen</label></>}
    {mode === "youtube" && <><label>YouTube-Link<input className="rounded-lg border border-white/20 bg-black/20 p-3" type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=…"/></label><p className="agent-note">Jon ruft verfügbare Untertitel ab und übergibt sie deinem eingestellten Modell. Ohne zugängliche Untertitel gibt es keine erfundene Zusammenfassung.</p></>}
    {mode === "speech" && <><label>Text oder Podcast-Skript<textarea rows={6} maxLength={80000} value={text} onChange={e => setText(e.target.value)} placeholder="Dein vollständiger Text …"/></label><label>Stimme<select value={voice} onChange={e => setVoice(e.target.value)}><option value="de-DE-ConradNeural">Jon · Deutsch</option><option value="de-DE-KatjaNeural">Katja · Deutsch</option><option value="de-DE-KillianNeural">MiniJon · Deutsch</option><option value="en-US-AriaNeural">Aria · Englisch</option><option value="en-US-GuyNeural">Guy · Englisch</option></select></label><p className="agent-note">Der vollständige Text wird abschnittsweise an Microsofts Sprachausgabe übermittelt und als MP3 gespeichert.</p></>}
    <button className="agent-primary" disabled={busy || (mode === "transcribe" ? !audio : mode === "youtube" ? !url.trim() : !text.trim())} onClick={() => void start()}>{busy ? "Bereitet vor …" : mode === "transcribe" ? "Vollständig transkribieren" : mode === "youtube" ? "Transkript holen & zusammenfassen" : "Audiodatei erstellen"}</button>
    <label>Medienaufträge<select value={selected} onChange={e => {setJob(null); setSelected(e.target.value);}}><option value="">Auftrag auswählen</option>{jobs.map(item => <option value={item.id} key={item.id}>{item.title} · {item.status === "done" ? "Fertig" : item.progress + "%"}</option>)}</select></label>
    {job && <article className="agent-run"><div className="agent-run-top"><strong>{job.message}</strong>{!ended.has(job.status) && <button disabled={busy} onClick={() => void action(async () => setJob(await mediaRequest<MediaJob>("/jobs/" + job.id + "/cancel", {})))}>Stoppen</button>}</div><progress className="w-full accent-amber-300" value={job.progress} max={100}/>{job.error && <p className="agent-error">{job.error}</p>}{job.url && <p className="agent-note">{job.automatic ? "Automatisch erzeugte" : "Vorhandene"} YouTube-Untertitel · können Erkennungsfehler enthalten.</p>}
      <div className="agent-chips">{job.files?.map(file => <a className="rounded-lg border border-white/20 px-3 py-2 text-gold" key={file} href={mediaFile(job.id, file)} download>{file === "audio.mp3" ? "MP3 herunterladen" : "Vollständiges Transkript herunterladen"}</a>)}</div>
      {job.files?.includes("audio.mp3") && <audio className="w-full mt-3" controls preload="metadata" src={mediaFile(job.id, "audio.mp3")}/>}
      {job.summary && <div className="agent-answer"><h3>Zusammenfassung</h3><p>{job.summary}</p></div>}
      {job.preview && <details><summary>{job.preview_truncated ? "Transkript-Vorschau · vollständig im Download" : "Vollständiger Text"}</summary><pre>{job.preview}</pre></details>}
    </article>}
  </section></div>;
}
