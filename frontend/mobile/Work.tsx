import React, {useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {Check, CircleDot, Code2, Copy, Download, Eye, FileText, Globe, ListChecks, Music2, Play, Server, Smartphone, Upload, X} from "lucide-react";
import {api, call, haptic, saveFile} from "./bridge";
import {Shell} from "./Chat";
import {openFile} from "./Viewer";
import {LANG, Message, Step} from "./useChats";
import {Busy, Markdown, Sheet, errorText, spring} from "./ui";

export type Plan = {ziel: string; schritte: {text: string; status: "offen" | "laeuft" | "fertig" | "fehler"}[]; phase: "planen" | "bereit" | "laeuft" | "fertig" | "abgebrochen"};

const schreibWerkzeuge = new Set(["write_file", "edit_file", "append_file", "datei_schreiben", "datei_erstellen", "create_pptx", "podcast_erstellen"]);

export type Ergebnis = {pfad: string; name: string; quelle: "pi" | "handy"};

export function ergebnisse(m: Message): Ergebnis[] {
  const liste: Ergebnis[] = [];
  const sehen = new Set<string>();
  const add = (pfad: string, quelle: "pi" | "handy") => {
    const sauber = String(pfad || "").trim();
    if (!sauber || sehen.has(quelle + sauber)) return;
    sehen.add(quelle + sauber);
    liste.push({pfad: sauber, name: sauber.split(/[\\/]/).pop() || sauber, quelle});
  };
  for (const s of (m.steps || []) as Step[]) {
    if (!s.name || !schreibWerkzeuge.has(s.name) || s.ok === false) continue;
    const pfad = s.args?.path || s.args?.pfad;
    if (pfad && !["datei_erstellen", "create_pptx", "podcast_erstellen"].includes(s.name)) add(pfad, s.name === "datei_schreiben" ? "handy" : "pi");
  }
  for (const karte of m.cards || []) {
    if (karte?.kind === "datei") for (const f of karte.data?.dateien || []) add(f.path || f.pfad, "pi");
    if (karte?.kind === "handy-datei") for (const f of karte.data?.dateien || []) add(f.pfad, "handy");
  }
  const text = m.content || "";
  for (const treffer of text.matchAll(/`((?:[A-Za-z]:\\|\/)[^`\n]+\.(?:html?|py|js|md|pdf|docx|pptx|xlsx|csv|mp3|wav|zip))`/g)) add(treffer[1], m.lokal ? "handy" : "pi");
  return liste.slice(0, 12);
}

const endung = (name: string) => name.split(".").pop()?.toLowerCase() || "";

function DateiIcon({name}: {name: string}) {
  const e = endung(name);
  if (["html", "htm"].includes(e)) return <Globe/>;
  if (["py", "js", "sh", "ts", "css", "json"].includes(e)) return <Code2/>;
  if (["mp3", "wav", "m4a"].includes(e)) return <Music2/>;
  return <FileText/>;
}

function AudioSpieler({e, notify}: {e: Ergebnis; notify: (s: string) => void}) {
  const [quelle, setQuelle] = useState("");
  const laden = async () => {
    try {
      if (e.quelle === "handy") {const r = await call("arbeit-datei", {pfad: e.pfad}, 120_000); setQuelle(`data:${r.mime};base64,${r.data}`);}
      else {
        const teile: Uint8Array[] = [];
        let offset = 0, groesse = 1, mime = "audio/mpeg";
        while (offset < groesse) {
          const t = await api<any>(`/api/mobile/file?path=${encodeURIComponent(e.pfad)}&offset=${offset}`);
          teile.push(Uint8Array.from(atob(t.data), z => z.charCodeAt(0)));
          offset = t.offset; groesse = t.size; mime = t.mime || mime;
          if (!t.size) break;
        }
        setQuelle(URL.createObjectURL(new Blob(teile as BlobPart[], {type: mime})));
      }
    } catch (err) {notify(errorText(err));}
  };
  return quelle ? <audio src={quelle} controls autoPlay style={{width: "100%", marginTop: 8}}/> : <button className="mini" onClick={laden}><Play/>Anhören</button>;
}

export function ErgebnisKarten({m, shell}: {m: Message; shell: Shell}) {
  const liste = ergebnisse(m);
  const [ausgabe, setAusgabe] = useState<any>(null), [busy, setBusy] = useState("");
  if (!liste.length) return null;
  const notify = shell.notify;
  const piDa = shell.conn.connected;
  async function aufsHandy(e: Ergebnis, ordner = false) {
    setBusy(e.pfad);
    notify("Download beginnt");
    try {
      if (e.quelle === "handy") {const r = await call("arbeit-export", {pfad: ordner ? e.pfad.split("/").slice(0, -1).join("/") : e.pfad}, 120_000); notify(`${r.saved} in Downloads/Jon gespeichert.`);}
      else if (ordner) {const z = await api<any>("/api/mobile/zip", "POST", {path: e.pfad}); await saveFile(z.pfad); notify(`${z.name} in Downloads/Jon gespeichert.`);}
      else {await saveFile(e.pfad); notify(`${e.name} in Downloads/Jon gespeichert.`);}
    } catch (err) {notify(errorText(err));} finally {setBusy("");}
  }
  async function aufDenPi(e: Ergebnis) {
    setBusy(e.pfad);
    try {const r = await call("arbeit-zum-pi", {pfad: e.pfad}, LANG); haptic("success"); notify(`Liegt jetzt auf dem Pi: ${r.pfad}`);}
    catch (err) {notify(errorText(err));} finally {setBusy("");}
  }
  async function ausfuehren(e: Ergebnis) {
    setAusgabe({name: e.name, laeuft: true});
    try {setAusgabe({name: e.name, ...(await api<any>("/api/mobile/ausfuehren", "POST", {path: e.pfad}))});}
    catch (err) {setAusgabe({name: e.name, stderr: errorText(err), exit_code: -1});}
  }
  return <div className="ergebnisse">
    {liste.map((e, i) => {
      const art = endung(e.name);
      const web = ["html", "htm"].includes(art);
      const lauf = ["py", "sh", "js", "mjs"].includes(art) && e.quelle === "pi";
      const ton = ["mp3", "wav", "m4a"].includes(art);
      return <motion.div key={e.quelle + e.pfad} className="ergebnis" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={{...spring, delay: i * .05}}>
        <div className="kopf"><span className="symbol"><DateiIcon name={e.name}/></span><div><strong>{e.name}</strong><small>{e.quelle === "pi" ? <><Server size={12}/> Auf dem Pi</> : <><Smartphone size={12}/> Auf dem Handy</>}</small></div></div>
        <div className="aktionen">
          {web && <button className="mini haupt" onClick={() => call("site", {quelle: e.quelle, pfad: e.pfad, titel: e.name}, LANG).catch(err => notify(errorText(err)))}><Eye/>Ansehen</button>}
          {lauf && <button className="mini haupt" onClick={() => ausfuehren(e)}><Play/>Ausführen</button>}
          {!web && !lauf && !ton && e.quelle === "pi" && <button className="mini haupt" onClick={() => openFile({path: e.pfad, name: e.name})}><Eye/>Öffnen</button>}
          {ton && <AudioSpieler e={e} notify={notify}/>}
          <button className="mini" disabled={busy === e.pfad} onClick={() => aufsHandy(e)}><Download/>Aufs Handy</button>
          {web && <button className="mini" disabled={busy === e.pfad} onClick={() => aufsHandy(e, true)}><Download/>Ordner als ZIP</button>}
          {e.quelle === "handy" && piDa && <button className="mini" disabled={busy === e.pfad} onClick={() => aufDenPi(e)}><Upload/>Auf den Pi</button>}
          {e.quelle === "pi" && <button className="mini" onClick={() => call("copy", {text: e.pfad}).then(() => notify("Pfad auf dem Pi kopiert."))}><Copy/>Pfad</button>}
        </div>
      </motion.div>;
    })}
    <Sheet open={!!ausgabe} title={ausgabe ? `Ausgabe · ${ausgabe.name}` : ""} onClose={() => setAusgabe(null)}>
      {ausgabe?.laeuft ? <Busy text="Läuft auf dem Pi …"/> : ausgabe && <>
        <p className="small muted">{ausgabe.befehl || ""}{ausgabe.dauer !== undefined ? ` · ${ausgabe.dauer} s · Code ${ausgabe.exit_code}` : ""}</p>
        {ausgabe.stdout && <pre className="terminal">{ausgabe.stdout}</pre>}
        {ausgabe.stderr && <pre className="terminal" style={{color: "#ffb3b3"}}>{ausgabe.stderr}</pre>}
        {!ausgabe.stdout && !ausgabe.stderr && <p className="muted">Keine Ausgabe.</p>}
      </>}
    </Sheet>
  </div>;
}

export function planErkennen(text: string): string[] {
  const start = text.indexOf("{"), ende = text.lastIndexOf("}");
  if (start >= 0 && ende > start) {
    try {
      const daten = JSON.parse(text.slice(start, ende + 1));
      const liste = daten.schritte || daten.steps;
      if (Array.isArray(liste)) return liste.map((s: any) => String(typeof s === "string" ? s : s.text || s.titel || s.schritt || "")).filter(Boolean).slice(0, 12);
    } catch {}
  }
  return text.split("\n").map(z => z.replace(/^\s*(\d+[.)]|[-*•])\s*/, "").trim()).filter(z => z.length > 3 && z.length < 300).slice(0, 12);
}

export function PlanKarte({plan, starten, abbrechen, entfernen}: {plan: Plan; starten: () => void; abbrechen: () => void; entfernen: (i: number) => void}) {
  const fertig = plan.schritte.filter(s => s.status === "fertig").length;
  return <motion.div className="plan-karte" initial={{opacity: 0, y: 14}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: 10}} transition={spring}>
    <div className="kopf"><ListChecks/><div><strong>{plan.phase === "planen" ? "Jon plant …" : plan.phase === "fertig" ? "Erledigt" : "Plan"}</strong><small>{plan.ziel}</small></div>{plan.phase !== "planen" && <span className="zaehler">{fertig}/{plan.schritte.length}</span>}</div>
    {plan.phase === "planen" ? <div className="plan-laden"><span className="shimmer">Zerlege die Aufgabe in Schritte …</span></div> :
      <div className="plan-schritte"><AnimatePresence initial={false}>{plan.schritte.map((s, i) => <motion.div key={i + s.text} layout className={`plan-schritt ${s.status}`} initial={{opacity: 0, x: -10}} animate={{opacity: 1, x: 0}} exit={{opacity: 0, height: 0}} transition={{delay: i * .03}}>
        <span className="marke">{s.status === "fertig" ? <Check/> : s.status === "laeuft" ? <CircleDot className="spin-langsam"/> : s.status === "fehler" ? <X/> : <i>{i + 1}</i>}</span>
        <span className="text">{s.text}</span>
        {plan.phase === "bereit" && <button aria-label="Schritt entfernen" onClick={() => entfernen(i)}><X/></button>}
      </motion.div>)}</AnimatePresence></div>}
    {plan.phase === "bereit" && <div className="plan-knoepfe"><button className="btn soft" onClick={abbrechen}>Verwerfen</button><button className="btn primary" onClick={starten} disabled={!plan.schritte.length}><Play/>Los geht's</button></div>}
    {plan.phase === "laeuft" && <div className="plan-knoepfe"><button className="btn soft" onClick={abbrechen}><X/>Stopp</button></div>}
  </motion.div>;
}

export function PlanHinweis({text, notify}: {text: string; notify: (s: string) => void}) {
  return <div className="card"><Markdown text={text} notify={notify}/></div>;
}
