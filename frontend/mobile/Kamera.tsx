import React, {useEffect, useState} from "react";
import {motion} from "framer-motion";
import {Camera, ImageOff, MessageSquareText, Trash2} from "lucide-react";
import {call, haptic} from "./bridge";
import {PageProps} from "./Pages";
import {LANG} from "./useChats";
import {Busy, Circle, Empty, PageHeader, Sheet, errorText, showImage, spring} from "./ui";

export function anhangSenden(anhang: any) {
  window.dispatchEvent(new CustomEvent("jon-anhang", {detail: anhang}));
}

export function KameraPage({shell, back}: PageProps) {
  const [fotos, setFotos] = useState<any[] | null>(null), [gewaehlt, setGewaehlt] = useState<any>(null), [gross, setGross] = useState(""), [busy, setBusy] = useState(false);
  const laden = () => call("fotos").then(v => setFotos(v.fotos || [])).catch(e => {setFotos([]); shell.notify(errorText(e));});
  useEffect(() => {laden();}, []);
  async function aufnehmen() {
    haptic("tap");
    try {const r = await call("kamera", {ziel: "galerie"}, LANG); if (r?.gespeichert) shell.notify(r.gespeichert === 1 ? "1 Foto gespeichert." : `${r.gespeichert} Fotos gespeichert.`); laden();}
    catch (e) {if (errorText(e) !== "Abgebrochen") shell.notify(errorText(e));}
  }
  async function oeffnen(foto: any) {
    setGewaehlt(foto);
    setGross("");
    try {const r = await call("foto", {foto: foto.id}); setGross(`data:${r.mime};base64,${r.data}`);} catch (e) {shell.notify(errorText(e));}
  }
  return <>
    <PageHeader title="Kamera" onBack={back} right={<Circle label="Foto machen" onClick={aufnehmen}><Camera/></Circle>}/>
    <div className="page-scroll">
      <motion.button className="kamera-start" onClick={aufnehmen} initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={spring}>
        <span className="linse"><Camera/></span><span><strong>Foto machen</strong><small>Fotos landen in deiner Galerie unter „Jon“.</small></span>
      </motion.button>
      {fotos === null ? <Busy/> : !fotos.length ? <Empty icon={<ImageOff/>} title="Noch keine Fotos" text="Mach dein erstes Foto – Jon kann es dir auch erklären."/> :
        <div className="foto-raster">{fotos.map((f, i) => <motion.button key={f.id} initial={{opacity: 0, scale: .92}} animate={{opacity: 1, scale: 1}} transition={{delay: Math.min(i, 18) * .02}} onClick={() => oeffnen(f)}><img src={`data:image/jpeg;base64,${f.vorschau}`} alt={f.name}/></motion.button>)}</div>}
    </div>
    <Sheet open={!!gewaehlt} title={gewaehlt ? new Date(gewaehlt.zeit).toLocaleString("de-DE", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"}) : ""} onClose={() => setGewaehlt(null)}>
      {gewaehlt && <>
        <div className="gen-image" onClick={() => gross && showImage(gross, gewaehlt.name)}>{gross ? <img src={gross} alt=""/> : <img src={`data:image/jpeg;base64,${gewaehlt.vorschau}`} alt="" style={{filter: "blur(6px)"}}/>}</div>
        <div style={{display: "flex", flexDirection: "column", gap: 10}}>
          <button className="btn primary" disabled={!gross} onClick={() => {anhangSenden({name: gewaehlt.name, bilder: [gross.split(",")[1]], anhang: `Datei: ${gewaehlt.name}`, vorschau: gross.split(",")[1]}); setGewaehlt(null); back();}}><MessageSquareText/>Jon fragen</button>
          <button className="btn danger" disabled={busy} onClick={async () => {setBusy(true); try {await call("foto-loeschen", {foto: gewaehlt.id}); setGewaehlt(null); laden(); shell.notify("Foto gelöscht.");} catch (e) {shell.notify(errorText(e));} finally {setBusy(false);}}}><Trash2/>Löschen</button>
        </div>
      </>}
    </Sheet>
  </>;
}
