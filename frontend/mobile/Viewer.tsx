import React, {useEffect, useMemo, useRef, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {BarChart3, ChevronLeft, ChevronRight, Code2, Download, Eye, FileQuestion, Maximize2, MessageSquareText, StickyNote, X} from "lucide-react";
import {api, binary, enc, haptic, saveFile} from "./bridge";
import {compose} from "./Chat";
import {PageProps} from "./Pages";
import {Busy, Circle, Empty, Markdown, PageHeader, PiImage, errorText, spring, useBackHandler} from "./ui";

export function openFile(file: {path?: string; pfad?: string; name?: string; titel?: string}) {
  window.dispatchEvent(new CustomEvent("jon-open", {detail: {path: file.path || file.pfad || "", name: file.name || file.titel || ""}}));
}

const luminanz = (farbe?: string | null) => {
  if (!farbe || !/^#[0-9a-f]{6}$/i.test(farbe)) return 1;
  const [r, g, b] = [1, 3, 5].map(i => parseInt(farbe.slice(i, i + 2), 16) / 255);
  return .2126 * r + .7152 * g + .0722 * b;
};

function FolienBild({path, folie, form}: {path: string; folie: number; form: number}) {
  const [quelle, setQuelle] = useState("");
  useEffect(() => {
    let live = true;
    binary(`/api/mobile/view/bild?path=${enc(path)}&folie=${folie}&form=${form}`).then(r => {if (live) setQuelle(`data:${r.mime};base64,${r.data}`);}).catch(() => {});
    return () => {live = false;};
  }, [path, folie, form]);
  return quelle ? <img src={quelle} alt="" style={{width: "100%", height: "100%", objectFit: "contain"}}/> : <span className="slide-skeleton"/>;
}

function Diagramm({form}: {form: any}) {
  const reihe = form.reihen?.[0];
  if (!reihe) return <div className="slide-chart"><BarChart3/></div>;
  const max = Math.max(1, ...reihe.werte);
  return <div className="slide-chart">
    {form.titel && <b>{form.titel}</b>}
    <div className="bars">{reihe.werte.map((w: number, i: number) => <div key={i} title={reihe.kategorien?.[i]}><i style={{height: `${Math.max(2, w / max * 100)}%`}}/><span>{reihe.kategorien?.[i]}</span></div>)}</div>
  </div>;
}

export function Folie({folie, daten, path}: {folie: any; daten: any; path: string}) {
  const flaeche = folie.formen.find((f: any) => f.b >= 98 && f.h >= 98 && f.fuellung)?.fuellung;
  const hell = luminanz(folie.hintergrund || flaeche || "#ffffff") > .5;
  const hoehe = daten.hoehe_pt || 540;
  return <div className="slide" style={{aspectRatio: String(daten.verhaeltnis || 16 / 9), background: folie.hintergrund || "#ffffff", color: hell ? "#141414" : "#ffffff"}}>
    {folie.formen.map((f: any) => <div key={f.index} className="slide-shape" style={{left: `${f.x}%`, top: `${f.y}%`, width: `${f.b}%`, height: `${f.h}%`, background: f.fuellung || undefined, borderRadius: f.rund ? "50%" : f.ecken ? "9%" : undefined, transform: f.drehung ? `rotate(${f.drehung}deg)` : undefined}}>
      {f.art === "bild" && <FolienBild path={path} folie={folie.nummer} form={f.index}/>}
      {f.art === "diagramm" && <Diagramm form={f}/>}
      {f.art === "tabelle" && <table className="slide-table">{(f.zeilen || []).map((z: string[], i: number) => <tr key={i}>{z.map((zelle, j) => i ? <td key={j}>{zelle}</td> : <th key={j}>{zelle}</th>)}</tr>)}</table>}
      {f.absaetze && <div className="slide-text" style={{color: f.fuellung ? (luminanz(f.fuellung) > .5 ? "#141414" : "#fff") : undefined}}>{f.absaetze.map((a: any, i: number) => <p key={i} style={{fontSize: `calc(${(a.groesse || 18) / hoehe * 100} * 1cqh)`, fontWeight: a.fett ? 700 : undefined, color: a.farbe || undefined, textAlign: a.ausrichtung, paddingLeft: a.ebene ? `${a.ebene * 4}%` : undefined}}>{a.ebene ? "• " : ""}{a.text || " "}</p>)}</div>}
    </div>)}
  </div>;
}

function Folien({daten, path}: {daten: any; path: string}) {
  const [index, setIndex] = useState(0), [notizen, setNotizen] = useState(false), [praesentieren, setPraesentieren] = useState(false);
  const leiste = useRef<HTMLDivElement>(null);
  const folien: any[] = daten.folien || [];
  useBackHandler(praesentieren, () => setPraesentieren(false));
  const gehe = (n: number) => {
    const ziel = Math.max(0, Math.min(folien.length - 1, n));
    setIndex(ziel);
    haptic("tick");
    leiste.current?.children[ziel]?.scrollIntoView({behavior: "smooth", inline: "center", block: "nearest"});
  };
  return <>
    <div className="deck" ref={leiste} onScroll={e => {const el = e.currentTarget; const n = Math.round(el.scrollLeft / el.clientWidth); if (n !== index) setIndex(n);}}>
      {folien.map(f => <div className="deck-page" key={f.nummer}><Folie folie={f} daten={daten} path={path}/></div>)}
    </div>
    <div className="deck-bar">
      <button className="round-btn" onClick={() => gehe(index - 1)} disabled={index === 0}><ChevronLeft/></button>
      <span>{index + 1} / {folien.length}{daten.gesamt > folien.length ? ` (${daten.gesamt})` : ""}</span>
      <button className="round-btn" onClick={() => gehe(index + 1)} disabled={index >= folien.length - 1}><ChevronRight/></button>
      <span className="grow"/>
      <button className={`round-btn ${notizen ? "ok" : ""}`} aria-label="Notizen" onClick={() => setNotizen(!notizen)}><StickyNote/></button>
      <button className="round-btn" aria-label="Präsentieren" onClick={() => {haptic("tap"); setPraesentieren(true);}}><Maximize2/></button>
    </div>
    <AnimatePresence>{notizen && <motion.div className="card" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}}><h4><StickyNote/>Notizen zu Folie {index + 1}</h4><p>{folien[index]?.notizen || "Keine Notizen."}</p></motion.div>}</AnimatePresence>
    <div className="deck-thumbs">{folien.map((f, i) => <button key={f.nummer} className={i === index ? "on" : ""} onClick={() => gehe(i)}><Folie folie={f} daten={daten} path={path}/><span>{i + 1}</span></button>)}</div>
    <AnimatePresence>{praesentieren && <motion.div className="present" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} onClick={e => {const x = e.clientX / window.innerWidth; gehe(x < .33 ? index - 1 : index + 1);}}>
      <motion.div key={index} className="present-slide" initial={{opacity: 0, scale: .96}} animate={{opacity: 1, scale: 1}} transition={spring}><Folie folie={folien[index]} daten={daten} path={path}/></motion.div>
      <button className="present-close" onClick={e => {e.stopPropagation(); setPraesentieren(false);}}><X/></button>
      <span className="present-count">{index + 1} / {folien.length}</span>
    </motion.div>}</AnimatePresence>
  </>;
}

function Tabelle({blaetter}: {blaetter: any[]}) {
  const [aktiv, setAktiv] = useState(0);
  const blatt = blaetter[aktiv] || {zeilen: []};
  const zeilen: string[][] = blatt.zeilen || [];
  return <>
    {blaetter.length > 1 && <div className="tabs" style={{padding: "0 0 12px"}}>{blaetter.map((b, i) => <button key={b.name + i} className={i === aktiv ? "on" : ""} onClick={() => setAktiv(i)}>{i === aktiv && <motion.span layoutId="blatt" className="tab-bg" transition={spring}/>}<span>{b.name}</span></button>)}</div>}
    {zeilen.length ? <div className="sheet-table"><table><thead><tr><th className="nr"/>{zeilen[0].map((z, i) => <th key={i}>{z}</th>)}</tr></thead><tbody>{zeilen.slice(1).map((zeile, i) => <tr key={i}><td className="nr">{i + 2}</td>{zeile.map((z, j) => <td key={j} className={/^-?[\d.,]+%?$/.test(z) ? "num" : ""}>{z}</td>)}</tr>)}</tbody></table></div> : <p className="muted">Dieses Blatt ist leer.</p>}
    {blatt.gekuerzt && <p className="hint" style={{marginTop: 10}}>Gekürzt – die vollständige Tabelle findest du nach dem Herunterladen.</p>}
  </>;
}

function Html({text}: {text: string}) {
  const [code, setCode] = useState(false);
  return <>
    <div className="segmented" style={{width: 210, margin: "0 auto 14px"}}>{[false, true].map(c => <button key={String(c)} onClick={() => setCode(c)}>{code === c && <motion.span layoutId="htmlseg" className="thumb" style={{left: 0, right: 0}} transition={spring}/>}<span style={{position: "relative", display: "inline-flex", gap: 6, alignItems: "center"}}>{c ? <Code2 size={16}/> : <Eye size={16}/>}{c ? "Code" : "Ansicht"}</span></button>)}</div>
    {code ? <pre className="code-view"><code>{text}</code></pre> : <iframe className="html-view" sandbox="" srcDoc={text} title="Vorschau"/>}
  </>;
}

export function ViewerPage({shell, back, arg}: PageProps) {
  const path = String(arg?.path || "");
  const [daten, setDaten] = useState<any>(null), [fehler, setFehler] = useState("");
  useEffect(() => {
    let live = true;
    api(`/api/mobile/view?path=${enc(path)}`).then(v => {if (live) setDaten(v);}).catch(e => {if (live) setFehler(errorText(e));});
    return () => {live = false;};
  }, [path]);
  const name = daten?.name || arg?.name || path.split(/[\\/]/).pop() || "Datei";
  const speichern = () => {haptic("tap"); shell.notify("Download beginnt"); saveFile(path).then(() => shell.notify(`${name} in Downloads/Jon gespeichert.`)).catch(e => shell.notify(errorText(e)));};
  const seiten = useMemo(() => Array.from({length: Math.min(daten?.seiten || 0, 60)}, (_, i) => i + 1), [daten]);
  return <>
    <PageHeader title={name} onBack={back} right={<Circle label="Herunterladen" onClick={speichern}><Download/></Circle>}/>
    <div className="page-scroll viewer">
      {fehler ? <Empty icon={<FileQuestion/>} title="Öffnen nicht möglich" text={fehler}/> : !daten ? <Busy text="Datei wird vom Pi geladen …"/> : <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{duration: .3}}>
        {daten.art === "markdown" && <div className="doc-paper"><Markdown text={daten.text || "*Leer*"} notify={shell.notify}/></div>}
        {daten.art === "code" && <pre className="code-view"><code>{daten.text}</code></pre>}
        {daten.art === "html" && <Html text={daten.text || ""}/>}
        {daten.art === "tabelle" && <Tabelle blaetter={daten.blaetter || []}/>}
        {daten.art === "folien" && <Folien daten={daten} path={path}/>}
        {daten.art === "pdf" && (daten.bilder ? <div className="pdf-pages">{seiten.map(n => <div key={n} className="pdf-page"><PiImage zoom path={`/api/mobile/view/seite?path=${enc(path)}&seite=${n}`} alt={`${name} Seite ${n}`}/><span>{n}</span></div>)}</div>
          : (daten.texte || []).map((t: string, i: number) => <div key={i} className="doc-paper" style={{marginBottom: 12}}><p className="hint">Seite {i + 1}</p><p style={{whiteSpace: "pre-wrap"}}>{t || "Kein Text auf dieser Seite."}</p></div>))}
        {daten.art === "bild" && <div className="gen-image"><PiImage zoom path={path} alt={name}/></div>}
        {(daten.art === "unbekannt" || daten.art === "fehler") && <Empty icon={<FileQuestion/>} title="Keine Vorschau" text={daten.fehler || "Diese Datei kann Jon hier noch nicht anzeigen. Du kannst sie herunterladen."}/>}
        {daten.gekuerzt && <p className="hint" style={{marginTop: 12}}>Die Vorschau ist gekürzt.</p>}
      </motion.div>}
    </div>
    <div className="stack-buttons" style={{flexDirection: "row"}}>
      <button className="btn soft" onClick={() => {compose(`Lies die Datei ${path} und hilf mir damit: `, "coding"); back();}}><MessageSquareText/>Mit Jon</button>
      <button className="btn primary" onClick={speichern}><Download/>Speichern</button>
    </div>
  </>;
}
