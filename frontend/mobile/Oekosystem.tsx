import React, {useEffect, useRef, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {BatteryCharging, BellRing, BookOpen, Check, Copy, Eye, GraduationCap, Home, Laptop, LoaderCircle, LocateFixed, MapPin, Navigation, RefreshCw, RotateCcw, Send, Smartphone, Tablet, Watch, X, type LucideIcon} from "lucide-react";
import {api, binary, call, enc, haptic} from "./bridge";
import {PageProps} from "./Pages";
import {Busy, Circle, PageHeader, PiImage, Row, Switch, errorText, spring} from "./ui";

type Ort = {id: string; name: string; besitzer: string; typ: string; lat: number; lon: number; genau?: number; alter_s: number; frisch: boolean; online: boolean; akku?: number; laedt?: boolean; zuhause?: boolean; jon?: string; fern?: boolean};

const SYMBOL: Record<string, LucideIcon> = {handy: Smartphone, tablet: Tablet, uhr: Watch, pc: Laptop};

export const wannText = (s: number) => s < 90 ? "gerade eben" : s < 3600 ? `vor ${Math.floor(s / 60)} Min.` : s < 86400 ? `vor ${Math.floor(s / 3600)} Std.` : `vor ${Math.floor(s / 86400)} Tagen`;

const stile: Record<string, Promise<any>> = {};
const stil = (theme: string) => stile[theme] ||= api(`/api/maps/styles/${theme}`).catch(e => {delete stile[theme]; throw e;});

function markerElement(ort: Ort, aktiv: boolean) {
  const el = document.createElement("div");
  el.className = `geraet-marker ${ort.frisch ? "" : "alt"} ${aktiv ? "aktiv" : ""}`;
  const name = (ort.besitzer || ort.name || "?").trim();
  el.innerHTML = `<span class="geraet-marker-kreis">${name.slice(0, 1).toUpperCase().replace(/[<>&"]/g, "")}</span><span class="geraet-marker-name">${name.replace(/[<>&"]/g, "")}</span>`;
  return el;
}

export function KartePage({shell, back}: PageProps) {
  const halter = useRef<HTMLDivElement>(null);
  const karte = useRef<maplibregl.Map | null>(null);
  const marker = useRef<maplibregl.Marker[]>([]);
  const ich = useRef<maplibregl.Marker | null>(null);
  const [orte, setOrte] = useState<Ort[] | null>(null);
  const [zuhause, setZuhause] = useState<{lat: number; lon: number; name: string} | null>(null);
  const [auswahl, setAuswahl] = useState<Ort | null>(null);
  const [laedt, setLaedt] = useState(false);
  const [busy, setBusy] = useState("");
  const erstes = useRef(true);

  async function laden() {
    setLaedt(true);
    try {
      const r = await api<any>("/api/oekosystem/standorte");
      setOrte(Array.isArray(r.orte) ? r.orte : []);
      setZuhause(r.zuhause || null);
    } catch (e) {
      shell.notify(errorText(e));
      setOrte(o => o || []);
    } finally {
      setLaedt(false);
    }
  }

  useEffect(() => {
    void laden();
    const takt = setInterval(() => void laden(), 30_000);
    return () => clearInterval(takt);
  }, []);

  useEffect(() => {
    let lebt = true;
    const theme = document.documentElement.dataset.theme === "light" ? "light" : "dark";
    stil(theme).then(style => {
      if (!lebt || !halter.current) return;
      const m = new maplibregl.Map({container: halter.current, style, center: [16.37, 48.2], zoom: 6, attributionControl: {compact: true}, fadeDuration: 180});
      karte.current = m;
      m.on("load", () => setOrte(o => o ? [...o] : o));
    }).catch(() => shell.notify("Kartenstil von Jon nicht erreichbar."));
    return () => {lebt = false; marker.current.forEach(x => x.remove()); ich.current?.remove(); karte.current?.remove(); karte.current = null;};
  }, []);

  useEffect(() => {
    const m = karte.current;
    if (!m || !orte) return;
    marker.current.forEach(x => x.remove());
    marker.current = orte.map(o => {
      const el = markerElement(o, auswahl?.id === o.id);
      el.addEventListener("click", ev => {ev.stopPropagation(); haptic("tick"); setAuswahl(o); m.flyTo({center: [o.lon, o.lat], zoom: Math.max(m.getZoom(), 15), duration: 900});});
      return new maplibregl.Marker({element: el, anchor: "bottom"}).setLngLat([o.lon, o.lat]).addTo(m);
    });
    if (zuhause) {
      const el = document.createElement("div");
      el.className = "geraet-zuhause";
      marker.current.push(new maplibregl.Marker({element: el}).setLngLat([zuhause.lon, zuhause.lat]).addTo(m));
    }
    if (erstes.current && orte.length) {
      erstes.current = false;
      const punkte = orte.map(o => [o.lon, o.lat] as [number, number]);
      const b = punkte.reduce((g, p) => g.extend(p), new maplibregl.LngLatBounds(punkte[0], punkte[0]));
      m.fitBounds(b, {padding: 70, maxZoom: 15, duration: 0});
    }
  }, [orte, auswahl?.id, zuhause]);

  async function meinOrt() {
    setBusy("ich");
    try {
      const r = await call("ortung-jetzt", {}, 30_000);
      const m = karte.current;
      if (m) {
        ich.current?.remove();
        const el = document.createElement("div");
        el.className = "jm-puls";
        ich.current = new maplibregl.Marker({element: el}).setLngLat([r.lon, r.lat]).addTo(m);
        m.flyTo({center: [r.lon, r.lat], zoom: 15, duration: 900});
      }
    } catch (e) {shell.notify(errorText(e));}
    finally {setBusy("");}
  }

  async function aktualisieren(o: Ort) {
    if (o.fern) {shell.notify(`${o.name} gehört zu ${o.jon || "einem anderen Jon"}.`); return;}
    setBusy("ort");
    try {
      await api(`/api/oekosystem/geraete/${enc(o.id)}/standort`, "POST", {});
      haptic("success");
      await laden();
    } catch (e) {shell.notify(errorText(e));}
    finally {setBusy("");}
  }

  async function klingeln(o: Ort) {
    setBusy("klingeln");
    try {
      await api(`/api/oekosystem/klingeln`, "POST", {ziel: o.id, sekunden: 30});
      haptic("success");
      shell.notify(`${o.name} klingelt.`);
    } catch (e) {shell.notify(errorText(e));}
    finally {setBusy("");}
  }

  const aktuell = auswahl && orte?.find(o => o.id === auswahl.id) || auswahl;
  const Icon = SYMBOL[aktuell?.typ || "handy"] || Smartphone;
  return <>
    <PageHeader title="Jon Maps" subtitle={orte ? `${orte.length} Gerät${orte.length === 1 ? "" : "e"} auf der Karte` : "Lädt …"} onBack={back} right={<Circle label="Aktualisieren" onClick={() => {haptic("tick"); void laden();}}><RefreshCw className={laedt ? "spin" : ""}/></Circle>}/>
    <div className="geraete-karte-rahmen">
      <div ref={halter} className="geraete-karte"/>
      <button className="circle glass geraete-ich" aria-label="Mein Standort" onClick={() => void meinOrt()}>{busy === "ich" ? <LoaderCircle className="spin"/> : <LocateFixed/>}</button>
      {orte && !orte.length && <div className="geraete-leer card"><MapPin/><div><strong>Noch keine Geräte auf der Karte</strong><small>Schalte am Handy unter Einstellungen → Uhr & Standort „Standort teilen“ ein und gib in Jon am PC den Standort frei.</small></div></div>}
      <AnimatePresence>{aktuell && <motion.div className="geraete-blatt glass" initial={{y: 40, opacity: 0}} animate={{y: 0, opacity: 1}} exit={{y: 40, opacity: 0}} transition={spring}>
        <div className="geraete-blatt-kopf">
          <span className="chip-icon"><Icon size={20}/></span>
          <div><strong>{aktuell.besitzer || aktuell.name}</strong><small>{aktuell.name}{aktuell.fern && aktuell.jon ? ` · über ${aktuell.jon}` : ""}</small></div>
          <button className="circle" aria-label="Schließen" onClick={() => setAuswahl(null)}><X/></button>
        </div>
        <div className="geraete-blatt-info">
          <span>{aktuell.zuhause ? <><Home size={14}/>Zuhause</> : <><MapPin size={14}/>{wannText(aktuell.alter_s)}</>}</span>
          {typeof aktuell.akku === "number" && aktuell.akku >= 0 && <span>{aktuell.laedt && <BatteryCharging size={14}/>}{aktuell.akku}%</span>}
          {aktuell.genau ? <span>± {Math.round(aktuell.genau)} m</span> : null}
          <span className={aktuell.online ? "an" : ""}>{aktuell.online ? "online" : "offline"}</span>
        </div>
        <div className="geraete-blatt-knoepfe">
          <button className="btn soft" disabled={!!busy} onClick={() => void aktualisieren(aktuell)}>{busy === "ort" ? <LoaderCircle className="spin"/> : <RefreshCw/>}Jetzt orten</button>
          {aktuell.typ !== "pc" && !aktuell.fern && <button className="btn soft" disabled={!!busy} onClick={() => void klingeln(aktuell)}>{busy === "klingeln" ? <LoaderCircle className="spin"/> : <BellRing/>}Klingeln</button>}
          <button className="btn soft" onClick={() => call("route", {lat: aktuell.lat, lon: aktuell.lon, name: aktuell.besitzer || aktuell.name}).catch(e => shell.notify(errorText(e)))}><Navigation/>Route</button>
        </div>
      </motion.div>}</AnimatePresence>
    </div>
  </>;
}

export function UhrStandortPage({shell, back}: PageProps) {
  const [ortung, setOrtung] = useState<any>(null);
  const [uhren, setUhren] = useState<any[] | null>(null);
  const [busy, setBusy] = useState("");
  async function uhrenLaden() {
    try {setUhren((await call("uhren", {}, 30_000)).uhren || []);}
    catch {setUhren([]);}
  }
  useEffect(() => {call("ortung").then(setOrtung).catch(e => shell.notify(errorText(e))); void uhrenLaden();}, []);
  async function teilen(an: boolean) {
    setBusy("ortung");
    try {setOrtung(await call("ortung-setzen", {an}, 120_000)); haptic("success"); shell.notify(an ? "Dein Standort wird jetzt mit Jon geteilt." : "Standort wird nicht mehr geteilt.");}
    catch (e) {shell.notify(errorText(e));}
    finally {setBusy("");}
  }
  async function uhrKoppeln() {
    setBusy("uhr");
    try {
      const r = await call("uhr-koppeln", {}, 150_000);
      haptic("success");
      shell.notify(`${r.uhr || "Die Uhr"} ist jetzt mit ${r.jon || "Jon"} verbunden.`);
      void uhrenLaden();
    } catch (e) {shell.notify(errorText(e));}
    finally {setBusy("");}
  }
  return <>
    <PageHeader title="Uhr & Standort" onBack={back}/>
    <div className="page-scroll">
      <motion.div className="server-held" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={spring}>
        <span className="chip-icon"><Watch/></span>
        <div><strong>Jon am Handgelenk</strong><small>Installiere „Jon“ auf deiner Wear-OS-Uhr und verbinde sie hier mit einem Tipp. Danach reicht ein Druck auf die Uhr und du sprichst mit Jon.</small></div>
      </motion.div>
      <div className="group-title">Smartwatch</div>
      <div className="group">
        {uhren === null ? <Busy text="Suche Uhren …"/> : uhren.length === 0 ? <Row icon={<Watch/>} label="Keine Uhr gefunden" detail="Ist die Uhr mit dem Handy gekoppelt?" chevron={false}/> :
          uhren.map(u => <Row key={u.id} icon={<Watch/>} label={u.name} detail={!u.app ? "Jon ist auf der Uhr noch nicht installiert" : u.gekoppelt ? `Mit Jon verbunden${u.akku >= 0 ? ` · Akku ${u.akku}%` : ""}` : "Noch nicht mit Jon verbunden"} right={u.gekoppelt ? <span className="badge ok"><Check/>Bereit</span> : undefined} chevron={false}/>)}
      </div>
      <button className="btn primary" style={{marginTop: 14}} disabled={!!busy} onClick={() => void uhrKoppeln()}>{busy === "uhr" ? <LoaderCircle className="spin"/> : <Watch/>}Uhr mit Jon verbinden</button>
      <div className="group-title">Standort</div>
      <div className="group">
        <Row icon={<MapPin/>} label="Standort mit Jon teilen" detail={ortung?.teilen ? (ortung?.hintergrund ? "Auch wenn die App geschlossen ist" : "Nur solange Jon im Hintergrund läuft") : "Für Jon Maps und „Wo ist …?“"} right={busy === "ortung" ? <LoaderCircle className="spin"/> : <Switch on={!!ortung?.teilen} onChange={v => void teilen(v)}/>} chevron={false}/>
      </div>
      <p className="hint" style={{margin: "12px 8px 0"}}>Wer in Jon fragt „Wo ist {ortung?.besitzer || "…"}?“, bekommt deinen Standort. Du siehst jedes Mal eine Benachrichtigung. Freigeben muss ihn zusätzlich jemand in Jon am PC unter Geräte → Standort.</p>
    </div>
  </>;
}

export function WebBildMobil({data}: {data: any}) {
  const bilder = (data.bilder || []).filter((b: any) => b.pfad);
  if (!bilder.length) return null;
  const name = (b: any) => String(b.titel || "").replace(/\.(jpe?g|png|webp|gif|tiff?)$/i, "").replace(/_/g, " ");
  const herkunft = (b: any) => [b.quelle, b.lizenz, b.autor ? String(b.autor).split("\n")[0].slice(0, 50) : ""].filter(Boolean).join(" · ");
  return <motion.div className={`webbild-mobil ${bilder.length > 1 ? "mehrere" : ""}`} initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={spring}>
    {bilder.map((b: any) => <figure key={b.pfad}><PiImage zoom path={b.pfad} alt={name(b)}/><figcaption><b>{name(b)}</b>{herkunft(b) ? ` · ${herkunft(b)}` : ""}</figcaption></figure>)}
  </motion.div>;
}

export function KopplungMobil({data, notify}: {data: any; notify: (s: string) => void}) {
  const [qr, setQr] = useState("");
  const [stand, setStand] = useState<string>(data.fertig ? "verbunden" : "offen");
  const [geraet, setGeraet] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!data.nutzlast) return;
    binary(`/api/handy/pairing/qr?text=${enc(data.nutzlast)}`).then(r => setQr(`data:${r.mime};base64,${r.data}`)).catch(() => {});
  }, [data.nutzlast]);
  useEffect(() => {
    if (data.fertig || !data.code) return;
    let lebt = true, zeit: ReturnType<typeof setTimeout>;
    const tick = () => api<any>("/api/handy/pairing/state").then(s => {
      if (!lebt) return;
      if (s.code && s.code !== data.code) {setStand("abgeloest"); return;}
      setStand(s.status); setGeraet(s.geraet || null);
      if (["verbunden", "abgelehnt", "abgelaufen"].includes(s.status)) return;
      zeit = setTimeout(tick, 2000);
    }).catch(() => {if (lebt) zeit = setTimeout(tick, 4000);});
    tick();
    return () => {lebt = false; clearTimeout(zeit);};
  }, [data.code]);
  async function antworten(ja: boolean) {
    setBusy(true);
    try {const r = await api<any>("/api/handy/pairing/answer", "POST", {angenommen: ja}); setStand(r.status === "ok" ? "verbunden" : "abgelehnt"); haptic(ja ? "success" : "tick");}
    catch (e) {notify(errorText(e));}
    finally {setBusy(false);}
  }
  const Icon = SYMBOL[data.art === "jon" ? "pc" : data.art] || Smartphone;
  return <motion.div className="card kopplung-karte" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={spring}>
    <h4><Icon size={18}/>{data.art === "uhr" ? "Smartwatch verbinden" : data.art === "jon" ? "Anderen Jon verbinden" : data.art === "tablet" ? "Tablet verbinden" : "Handy verbinden"}</h4>
    {stand === "verbunden" ? <p className="ok-text"><Check size={15}/>{data.fertig ? data.anleitung : `${geraet?.name || "Das Gerät"} ist verbunden.`}</p> : <>
      {qr && (stand === "offen" || stand === "wartet") && <img className="kopplung-qr" src={qr} alt="QR-Code"/>}
      {data.anleitung && <p>{data.anleitung}</p>}
      {data.code && <button className="kopplung-code" onClick={() => call("copy", {text: data.code_gruppiert || data.code}).then(() => notify("Code kopiert."))}>{data.code_gruppiert || data.code}<Copy size={15}/></button>}
      {stand === "wartet" && <div className="kopplung-frage"><p><b>{geraet?.name || "Ein Gerät"}</b> möchte sich verbinden.</p><div className="row-btns"><button className="btn primary" disabled={busy} onClick={() => void antworten(true)}><Check/>Erlauben</button><button className="btn soft" disabled={busy} onClick={() => void antworten(false)}><X/>Ablehnen</button></div></div>}
      {stand === "abgelaufen" && <p className="muted small">Der Code ist abgelaufen. Frag Jon einfach nochmal.</p>}
      {stand === "abgeloest" && <p className="muted small">Inzwischen läuft eine neuere Kopplung.</p>}
    </>}
  </motion.div>;
}

export function KarteikartenMobil({data, notify}: {data: any; notify: (s: string) => void}) {
  const [deck, setDeck] = useState<{id: string; titel: string; anzahl: number} | null>(data.aktion === "lernen" && data.deck ? {id: data.deck, titel: data.titel, anzahl: data.anzahl} : null);
  const [karte, setKarte] = useState<any>(null);
  const [eingabe, setEingabe] = useState("");
  const [ergebnis, setErgebnis] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  async function naechste(id = deck?.id) {
    if (!id) return;
    setBusy(true);
    try {setKarte(await api(`/api/flashcards/${enc(id)}/next`)); setErgebnis(null); setEingabe("");}
    catch (e) {notify(errorText(e));}
    finally {setBusy(false);}
  }
  useEffect(() => {if (deck) void naechste(deck.id);}, [deck?.id]);
  async function pruefen(text: string) {
    if (!deck || !karte?.id) return;
    setBusy(true);
    try {const r = await api("/api/flashcards/answer", "POST", {deck: deck.id, card: karte.id, answer: text}); setErgebnis(r); haptic(r.richtig ? "success" : "tick");}
    catch (e) {notify(errorText(e));}
    finally {setBusy(false);}
  }
  return <motion.div className="card lern-karte" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={spring}>
    <h4><GraduationCap size={18}/>{deck ? deck.titel : "Deine Kartenstapel"}</h4>
    {!deck ? <>{(data.decks || []).length === 0 && <p>Noch keine Stapel.</p>}{(data.decks || []).map((d: any) => <button key={d.id} className="lern-stapel" onClick={() => setDeck({id: d.id, titel: d.titel, anzahl: d.anzahl})}><BookOpen size={16}/><span>{d.titel}</span><small>{d.faellig ? `${d.faellig} fällig` : `${d.anzahl} Karten`}</small></button>)}</> :
      karte?.done ? <p>Alles gelernt. Jon fragt dich später wieder ab.</p> : <>
        <AnimatePresence mode="wait"><motion.div key={karte?.id || "lade"} className="lern-seite" initial={{rotateY: -70, opacity: 0}} animate={{rotateY: 0, opacity: 1}} exit={{rotateY: 70, opacity: 0}} transition={{duration: .3}}>
          <small>Frage{typeof karte?.offen === "number" ? ` · ${karte.offen} fällig` : ""}</small>
          <strong>{karte?.frage || (busy ? "Lädt …" : "")}</strong>
          {ergebnis && <div className={`lern-loesung ${ergebnis.richtig ? "richtig" : ""}`}><b>{ergebnis.richtig ? "Richtig" : eingabe ? "Noch nicht ganz" : "Lösung"}</b><p>{ergebnis.loesung}</p>{ergebnis.feedback && <small>{ergebnis.feedback}</small>}</div>}
        </motion.div></AnimatePresence>
        {ergebnis ? <button className="btn primary" onClick={() => void naechste()}><RotateCcw/>Nächste Karte</button> :
          <div className="lern-eingabe"><input value={eingabe} placeholder="Deine Antwort …" onChange={e => setEingabe(e.target.value)} onKeyDown={e => {if (e.key === "Enter" && eingabe.trim()) void pruefen(eingabe.trim());}}/><button className="circle" aria-label="Prüfen" disabled={busy || !eingabe.trim()} onClick={() => void pruefen(eingabe.trim())}>{busy ? <LoaderCircle className="spin"/> : <Send/>}</button><button className="circle" aria-label="Aufdecken" disabled={busy} onClick={() => void pruefen("")}><Eye/></button></div>}
      </>}
  </motion.div>;
}
