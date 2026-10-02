import React, {Suspense, lazy, useEffect, useState} from "react";
import {motion} from "framer-motion";
import {AlarmClock, ChevronRight, Download, Film, Globe, LoaderCircle, Play, Telescope, Timer} from "lucide-react";
import {api, binary, call, enc, saveFile} from "./bridge";
import {Markdown, PiImage, errorText, saveStudio, showImage, spring} from "./ui";
import {openFile} from "./Viewer";

const MapCard = lazy(() => import("./MapCard"));

export const fileName = (f: any) => String(f.name || f.titel || f.title || String(f.path || f.pfad || "Datei").split(/[\\/]/).pop());
export const filePath = (f: any) => String(f.path || f.pfad || "");
export const fileExt = (f: any) => String(f.endung || fileName(f).split(".").pop() || "").toUpperCase().slice(0, 4);

export function FilePill({file, notify}: {file: any; notify: (s: string) => void}) {
  const [busy, setBusy] = useState(false);
  return <div className="file-pill" role="button" onClick={() => openFile({path: filePath(file), name: fileName(file)})}>
    <span className="file-badge">{fileExt(file)}</span>
    <span>{fileName(file)}<small>{file.sizeText || file.groesse_text || "Auf deinem Pi"}{busy ? " · wird geladen …" : " · Tippen zum Öffnen"}</small></span>
    <button className="pill-save" aria-label="Herunterladen" disabled={busy} onClick={async e => {
      e.stopPropagation();
      setBusy(true);
      notify("Download beginnt");
      try {await saveFile(filePath(file)); notify(`${fileName(file)} in Downloads/Jon gespeichert.`);}
      catch (err) {notify(errorText(err));}
      finally {setBusy(false);}
    }}><Download/></button>
    <ChevronRight/>
  </div>;
}

function Clocks({data}: {data: any}) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => {const timer = setInterval(() => setNow(Date.now() / 1000), 500); return () => clearInterval(timer);}, []);
  const format = (s: number) => {const v = Math.max(0, Math.round(s)); const h = Math.floor(v / 3600), m = Math.floor(v % 3600 / 60), sec = v % 60; return `${h ? `${h}:` : ""}${String(m).padStart(h ? 2 : 1, "0")}:${String(sec).padStart(2, "0")}`;};
  return <div className="card"><h4><Timer/>Uhren auf deinem Pi</h4>{(data.uhren || []).map((u: any) => {
    const offset = u.laeuft ? Math.max(0, now - (u.gemessen ?? now)) : 0;
    const passed = (u.verstrichen || 0) + offset;
    const rest = u.art === "wecker" ? Math.max(0, (u.ziel || 0) - now) : Math.max(0, (u.dauer || 0) - passed);
    const value = u.art === "stoppuhr" ? passed : rest;
    const ringing = u.art !== "stoppuhr" && rest <= 0;
    return <div key={u.id} className={`clock-row ${ringing ? "ring" : ""}`}><div><small>{u.titel || (u.art === "wecker" ? "Wecker" : u.art === "stoppuhr" ? "Stoppuhr" : "Timer")}</small><strong>{u.art === "wecker" ? new Date((u.ziel || 0) * 1000).toLocaleTimeString("de-DE", {hour: "2-digit", minute: "2-digit"}) : format(value)}</strong></div>{u.art === "wecker" ? <AlarmClock/> : <small>{u.laeuft ? (ringing ? "Fertig" : "Läuft") : "Pausiert"}</small>}</div>;
  })}</div>;
}

function Research({data, notify}: {data: any; notify: (s: string) => void}) {
  const [task, setTask] = useState<any>(data.task || {});
  const id = data.id || data.task?.id;
  useEffect(() => {
    if (!id) return;
    let live = true, timer: ReturnType<typeof setTimeout>;
    const tick = () => api(`/api/research/tasks/${enc(id)}`).then(v => {if (live) setTask(v);}).catch(() => {}).finally(() => {if (live) timer = setTimeout(tick, 4000);});
    tick();
    return () => {live = false; clearTimeout(timer);};
  }, [id]);
  const done = ["fertig", "abgeschlossen", "done"].includes(String(task.status));
  const progress = Math.round((done ? 1 : task.fortschritt || .03) * 100);
  const files: string[] = Array.isArray(task.dateien) ? task.dateien : [];
  return <div className="card">
    <h4><Telescope/>{task.titel || task.thema || "Deep Research"}</h4>
    <div className="progress"><i style={{width: `${progress}%`}}/></div>
    <p className="small muted" style={{margin: 0}}>{done ? `Fertig · ${(task.quellen || []).length || 0} Quellen` : `${task.phase || task.status || "Startet"}${task.aktuelles_thema ? ` · ${task.aktuelles_thema}` : ""} · ${progress}%`}</p>
    {done && task.zusammenfassung && <div style={{marginTop: 12}}><Markdown text={task.zusammenfassung} notify={notify}/></div>}
    {files.map(name => <button key={name} className="file-pill" onClick={() => {notify("Download beginnt"); binary(`/api/research/tasks/${enc(id)}/files/${enc(name)}`).then(f => call("save", {...f, name})).then(() => notify(`${name} in Downloads/Jon gespeichert.`)).catch(e => notify(errorText(e)));}}><span className="file-badge">{name.split(".").pop()?.toUpperCase().slice(0, 4)}</span><span>{name}</span><Download/></button>)}
    {task.fehler && <p className="error-text">{task.fehler}</p>}
  </div>;
}

export const groesseText = (bytes: number) => bytes >= 1_048_576 ? `${(bytes / 1_048_576).toFixed(1).replace(".", ",")} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;

function VideoKarte({data, notify}: {data: any; notify: (s: string) => void}) {
  const [quelle, setQuelle] = useState(""), [laedt, setLaedt] = useState(false), [anteil, setAnteil] = useState(0), [sichert, setSichert] = useState(false);
  useEffect(() => () => {if (quelle.startsWith("blob:")) URL.revokeObjectURL(quelle);}, [quelle]);
  async function laden() {
    setLaedt(true);
    try {
      const teile: Uint8Array[] = [];
      let offset = 0, groesse = 1, mime = "video/mp4";
      while (offset < groesse) {
        const t = await api<any>(`/api/mobile/file?path=${enc(data.pfad)}&offset=${offset}`);
        teile.push(Uint8Array.from(atob(t.data || ""), z => z.charCodeAt(0)));
        if (!t.size || t.offset <= offset) break;
        offset = t.offset; groesse = t.size; mime = t.mime || mime;
        setAnteil(Math.min(100, Math.round(offset / groesse * 100)));
      }
      setQuelle(URL.createObjectURL(new Blob(teile as BlobPart[], {type: mime})));
    } catch (e) {notify(errorText(e));} finally {setLaedt(false);}
  }
  async function speichern() {
    setSichert(true);
    notify("Download beginnt");
    try {await saveFile(data.pfad); notify(`${data.name || "Video"} in Downloads/Jon gespeichert.`);}
    catch (e) {notify(errorText(e));} finally {setSichert(false);}
  }
  return <motion.div className="video-karte" initial={{opacity: 0, y: 10, scale: .98}} animate={{opacity: 1, y: 0, scale: 1}} transition={spring}>
    <div className="buehne">
      {quelle ? <video src={quelle} controls autoPlay playsInline/> : <button className="video-start" aria-label="Video abspielen" disabled={laedt} onClick={laden}>
        {laedt ? <><LoaderCircle className="spin"/><small>{anteil}%</small></> : <Play/>}
      </button>}
    </div>
    <div className="unten">
      <span className="symbol"><Film/></span>
      <span className="titel"><strong>{data.name || "Bildschirmvideo"}</strong><small>{[data.sekunden ? `${data.sekunden} s` : "", data.groesse ? groesseText(data.groesse) : "", "Auf dem PC"].filter(Boolean).join(" · ")}</small></span>
      <button className="mini" disabled={sichert} onClick={speichern}><Download/>Aufs Handy</button>
    </div>
  </motion.div>;
}

function HandyBild({data, notify}: {data: any; notify: (s: string) => void}) {
  const [quelle, setQuelle] = useState("");
  const name = String(data.pfad || "Jon-Bild.png").split("/").pop() || "Jon-Bild.png";
  useEffect(() => {
    let live = true;
    call("arbeit-datei", {pfad: data.pfad}, 60_000).then((r: any) => {if (live) setQuelle(`data:${r.mime};base64,${r.data}`);}).catch(() => {});
    return () => {live = false;};
  }, [data.pfad]);
  return <motion.div className="gen-image" initial={{opacity: 0, scale: .97}} animate={{opacity: 1, scale: 1}} transition={spring}>
    {quelle ? <img className="handy-bild" src={quelle} alt={data.prompt || ""} onClick={() => showImage(quelle, name)}/> : <div className="handy-bild leer"><span className="slide-skeleton"/></div>}
    <button className="over" aria-label="Bild speichern" onClick={() => {notify("Download beginnt"); call("arbeit-export", {pfad: data.pfad}, 60_000).then((r: any) => notify(`${r.saved} in Downloads/Jon gespeichert.`)).catch(e => notify(errorText(e)));}}><Download/></button>
  </motion.div>;
}

export function ResultCards({cards, notify, ohneDateien = false}: {cards: any[]; notify: (s: string) => void; ohneDateien?: boolean}) {
  return <>{cards.map((card, i) => {
    const data = card?.data || {};
    if (card.kind === "datei") return ohneDateien ? null : <div key={i}>{(data.dateien || []).map((f: any) => <FilePill key={filePath(f) || fileName(f)} file={f} notify={notify}/>)}</div>;
    if (card.kind === "video" && data.pfad) return <VideoKarte key={i} data={data} notify={notify}/>;
    if (card.kind === "handy-bild" && data.pfad) return <HandyBild key={i} data={data} notify={notify}/>;
    if (card.kind === "bild" && data.datei) return <div className="gen-image" key={i}><PiImage zoom path={`/api/studio/file/${encodeURIComponent(data.datei)}`} alt={data.prompt}/><button className="over" aria-label="Bild speichern" onClick={() => {notify("Download beginnt"); saveStudio(data.datei).then(() => notify("Bild in Downloads/Jon gespeichert.")).catch(e => notify(errorText(e)));}}><Download/></button></div>;
    if (card.kind === "zeit") return <Clocks key={i} data={data}/>;
    if (card.kind === "maps") return <Suspense key={i} fallback={<div className="map-slot"><div className="map-card"><div className="map-mini"><span className="slide-skeleton"/></div></div></div>}><MapCard data={data}/></Suspense>;
    if (card.kind === "browser") return <div className="card" key={i}><h4><Globe/>{data.titel || "Browser-Aufgabe"}</h4>{data.auftrag && <p>{data.auftrag}</p>}{(data.schritte || []).slice(-4).map((s: any, n: number) => <p key={n} className="small muted">{typeof s === "string" ? s : s.text || s.beschreibung || s.aktion}</p>)}{data.url && <button className="text-link small" onClick={() => call("copy", {text: data.url}).then(() => notify("Link kopiert."))}>{data.url}</button>}</div>;
    if (card.kind === "deep_learning") return <Research key={i} data={data} notify={notify}/>;
    return null;
  })}</>;
}
