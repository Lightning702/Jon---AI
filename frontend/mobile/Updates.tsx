import React, {useEffect, useRef, useState} from "react";
import {motion} from "framer-motion";
import {CheckCircle2, Download, RefreshCw, Server, Smartphone} from "lucide-react";
import {api, haptic, native} from "./bridge";
import {PageProps} from "./Pages";
import {useAdmin} from "./Settings";
import {Busy, PageHeader, errorText, spring} from "./ui";

const mb = (bytes: number) => `${Math.max(1, Math.round((bytes || 0) / 1_048_576))} MB`;

export function UpdatesPage({shell, back}: PageProps) {
  const [app, setApp] = useState<any>(null), [fortschritt, setFortschritt] = useState(""), [laedt, setLaedt] = useState(false);
  const [jon, setJon] = useState<any>(null), [piStand, setPiStand] = useState<any>(null), [neustart, setNeustart] = useState(false);
  const admin = useAdmin(shell.notify);
  const vorher = useRef("");
  const rechner = jon?.system === "linux" ? "Pi" : "PC";
  const pruefen = () => native("update-pruefen").promise.then(setApp).catch(e => setApp({fehler: errorText(e)}));
  const jonLaden = () => api("/api/health").then(h => {setJon(h); return h;}).catch(() => null);
  useEffect(() => {
    pruefen();
    if (shell.conn.connected) {jonLaden().then(h => {if (h) vorher.current = h.version;}); api("/api/system/pi-update").then(setPiStand).catch(() => {});}
  }, []);
  useEffect(() => {
    if (!neustart) return;
    const timer = setInterval(async () => {
      const h = await jonLaden();
      if (h && h.version) {
        setNeustart(false);
        haptic("success");
        shell.notify(h.version !== vorher.current ? `Jon ist jetzt auf Version ${h.version}.` : "Jon ist wieder da.");
        api("/api/system/pi-update").then(setPiStand).catch(() => {});
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [neustart]);
  async function aktualisieren() {
    setLaedt(true);
    setFortschritt("Starte …");
    try {
      await native("update-installieren", {}, teil => setFortschritt(teil?.fortschritt || ""), 30 * 60_000).promise;
      setFortschritt("Bestätige die Installation, falls Android fragt.");
    } catch (e) {shell.notify(errorText(e)); setFortschritt("");} finally {setLaedt(false);}
  }
  async function piAktualisieren() {
    try {
      const stand = await api("/api/system/pi-update", "POST");
      setPiStand(stand);
      haptic("success");
      const timer = setInterval(async () => {
        try {
          const s = await api("/api/system/pi-update");
          setPiStand(s);
          if (s.fertig || !s.laeuft) {clearInterval(timer); if (s.fertig) setNeustart(true); if (s.fehler) shell.notify(s.fehler);}
        } catch {clearInterval(timer); setNeustart(true);}
      }, 2000);
    } catch (e) {shell.notify(errorText(e));}
  }
  return <>
    <PageHeader title="Updates" onBack={back}/>
    <div className="page-scroll">
      <motion.div className="card update-karte" initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={spring}>
        <h4><Smartphone/>Jon Gerät auf diesem Handy</h4>
        {!app ? <Busy/> : <>
          <div className="stat"><span>Installiert</span><b>{app.version || "?"}</b></div>
          {app.neu ? <div className="stat"><span>Neu verfügbar</span><b className="gut">{app.neue_version} · {mb(app.groesse)}</b></div>
            : app.verfuegbar ? <p className="hint ok-text"><CheckCircle2 size={15}/> Jon ist auf dem neuesten Stand.</p> : null}
          {app.hinweis && <p className="hint">{app.hinweis}</p>}
          {app.fehler && <p className="error-text small">{app.fehler}</p>}
          {fortschritt && <p className="small muted" style={{margin: "8px 0 0"}}>{fortschritt}</p>}
          {app.neu && <button className="btn primary" style={{marginTop: 14}} disabled={laedt} onClick={() => admin.guard(aktualisieren)}>{laedt ? <RefreshCw className="spin"/> : <Download/>}Jetzt aktualisieren</button>}
          {!app.neu && app.moeglich && <button className="btn soft" style={{marginTop: 14}} onClick={() => {setApp(null); pruefen();}}><RefreshCw/>Nochmal prüfen</button>}
        </>}
      </motion.div>
      {shell.conn.paired && <motion.div className="card update-karte" initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={{...spring, delay: .06}}>
        <h4><Server/>Jon auf deinem {rechner}</h4>
        {!shell.conn.connected ? <p className="hint">Gerade nicht erreichbar.</p> : !jon ? <Busy/> : <>
          <div className="stat"><span>Version</span><b>{jon.version}</b></div>
          {neustart ? <p className="small muted"><RefreshCw className="spin" size={14}/> Jon startet neu …</p>
            : piStand?.laeuft ? <p className="small muted"><RefreshCw className="spin" size={14}/> {piStand.schritt || "Läuft …"}</p>
            : piStand?.moeglich ? <button className="btn soft" style={{marginTop: 12}} onClick={() => admin.guard(piAktualisieren)}><RefreshCw/>{`${rechner} aktualisieren`}</button>
            : <p className="hint">{piStand?.grund || "Am PC aktualisiert sich Jon über sein Setup."}</p>}
          {piStand?.fehler && <p className="error-text small">{piStand.fehler}</p>}
        </>}
      </motion.div>}
    </div>
    {admin.element}
  </>;
}
