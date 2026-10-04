import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Activity, Bug, Check, ChevronDown, Cpu, Download, Eye, FlaskConical, Gauge, HardDrive, Image, KeyRound, Lightbulb, Loader2, Megaphone, MessageSquare, MessagesSquare, Plus, Power, RefreshCw, Reply, ScrollText, Send, Server, Settings2, Share2, Sparkles, ThumbsUp, ToggleLeft, Trash2, Users, Wrench, X } from "lucide-react";
import { BASE, getSkill, getSkills, SkillSummary } from "../lib/api";
import { premiumAnfrage, PremiumStatus, teamAnfrage, TeamNachricht, TeamStand } from "../lib/premium";
import EntwicklerCodes from "./EntwicklerCodes";
import "./team.css";

type Bereich = "codes" | "team" | "fehler" | "geraete" | "schalter" | "pi" | "skills" | "inspektor" | "einstellungen";

const ART: Record<string, { text: string; icon: typeof Lightbulb }> = {
  idee: { text: "Idee", icon: Lightbulb },
  fehler: { text: "Fehler", icon: Bug },
  nachricht: { text: "Nachricht", icon: MessageSquare },
  rundschreiben: { text: "Rundschreiben", icon: Megaphone },
};

function zeit(sekunden?: number) {
  if (!sekunden) return "";
  const datum = new Date(sekunden * 1000);
  const heute = new Date().toDateString() === datum.toDateString();
  return heute ? datum.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" }) : datum.toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit" }) + " " + datum.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });
}

function zahl(wert?: number) {
  return (wert || 0).toLocaleString("de-AT");
}

function fehlerText(e: unknown) {
  return e instanceof Error ? e.message : "Das hat nicht geklappt.";
}

function TeamChat({ admin, onFehler, onGelesen }: { admin: boolean; onFehler: (text: string) => void; onGelesen: () => void }) {
  const [stand, setStand] = useState<TeamStand | null>(null);
  const [filter, setFilter] = useState("alle");
  const [art, setArt] = useState(admin ? "rundschreiben" : "idee");
  const [an, setAn] = useState(admin ? "team" : "admin");
  const [text, setText] = useState("");
  const [antwort, setAntwort] = useState<TeamNachricht | null>(null);
  const [bild, setBild] = useState<{ id: string; daten: string } | null>(null);
  const [busy, setBusy] = useState("");
  const liste = useRef<HTMLDivElement>(null);
  const gelesen = useRef(false);

  const laden = async () => {
    try {
      const neu = await teamAnfrage<TeamStand>("team/liste");
      setStand(alt => JSON.stringify(alt) === JSON.stringify(neu) ? alt : neu);
      if (neu.ungelesen && !gelesen.current) {
        gelesen.current = true;
        await teamAnfrage("team/gelesen");
        onGelesen();
        gelesen.current = false;
      }
    } catch (e) {
      onFehler(fehlerText(e));
    }
  };

  useEffect(() => {
    void laden();
    const takt = setInterval(() => {if (!document.hidden) void laden();}, 10000);
    return () => clearInterval(takt);
  }, []);

  useEffect(() => {
    const el = liste.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [stand?.nachrichten.length, filter]);

  const handeln = async (kennung: string, fn: () => Promise<TeamStand | void>) => {
    setBusy(kennung);
    onFehler("");
    try {
      const neu = await fn();
      if (neu) setStand(neu);
    } catch (e) {
      onFehler(fehlerText(e));
    } finally {
      setBusy("");
    }
  };

  const senden = () => handeln("senden", async () => {
    const ziel = art === "rundschreiben" ? "team" : antwort && admin ? (antwort.von.id === "admin" ? "team" : antwort.von.id) : an;
    const neu = await teamAnfrage<TeamStand>("team/senden", { art, text: text.trim(), an: ziel, antwort_auf: antwort?.id || "" });
    setText("");
    setAntwort(null);
    return neu;
  });

  const bildZeigen = (n: TeamNachricht) => handeln("bild" + n.id, async () => {
    const { bild: daten } = await teamAnfrage<{ bild: string }>("team/anhang", { id: n.id });
    setBild({ id: n.id, daten });
  });

  const namen = useMemo(() => Object.fromEntries((stand?.mitglieder || []).map(m => [m.id, m.name])), [stand?.mitglieder]);
  const nachrichten = (stand?.nachrichten || []).filter(n => filter === "alle" || n.art === filter);
  const ziele = admin ? [{ id: "team", name: "Ganzes Team" }, ...(stand?.mitglieder || []).map(m => ({ id: m.id, name: m.name }))] : [{ id: "admin", name: "Nur an den Admin" }, { id: "team", name: "Ans ganze Team" }];
  const anText = (n: TeamNachricht) => n.an === "team" ? "an alle" : n.an === "admin" ? "an den Admin" : n.an === stand?.ich.id ? "an dich" : "an " + (namen[n.an] || "ein Mitglied");

  return <div className="tz-chat">
    <div className="tz-filter" role="tablist" aria-label="Nachrichten filtern">
      {["alle", "idee", "fehler", "nachricht", "rundschreiben"].map(f => <button key={f} role="tab" aria-selected={filter === f} className={filter === f ? "an" : ""} onClick={() => setFilter(f)}>{f === "alle" ? "Alle" : ART[f].text}<em>{(stand?.nachrichten || []).filter(n => f === "alle" || n.art === f).length}</em></button>)}
    </div>
    <div className="tz-nachrichten" ref={liste}>
      {!stand && <div className="tz-leer"><Loader2 size={14} className="tz-dreh" />Lade Team-Nachrichten …</div>}
      {stand && !nachrichten.length && <div className="tz-leer tz-leer-gross"><MessagesSquare size={20} /><b>Noch nichts hier</b><span>{admin ? "Schreib deinem Team ein Rundschreiben oder warte auf Ideen und Fehlerberichte." : "Schick dem Admin deine erste Idee, einen Fehler oder eine Nachricht."}</span></div>}
      {nachrichten.map(n => {
        const Icon = ART[n.art]?.icon || MessageSquare;
        const bezug = n.antwort_auf ? stand?.nachrichten.find(x => x.id === n.antwort_auf) : null;
        return <motion.div key={n.id} layout="position" className={"tz-nachricht " + (n.von_mir ? "mir " : "") + "tz-n-" + n.art + (n.gelesen ? "" : " neu")} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
          <div className="tz-n-kopf">
            <span className={"tz-n-art tz-n-art-" + n.art}><Icon size={11} />{ART[n.art]?.text}</span>
            <b>{n.von_mir ? "Du" : n.von.name}</b>
            <span className="tz-n-rolle">{n.von.rolle === "admin" ? "Admin" : "Entwickler"} · {anText(n)}</span>
            <time>{zeit(n.zeit)}</time>
          </div>
          {bezug && <div className="tz-n-bezug"><Reply size={11} />{bezug.text.slice(0, 120)}</div>}
          <p>{n.text}</p>
          {n.anhang && <div className="tz-n-anhang">
            {n.anhang.system && <span className="tz-n-system"><Cpu size={11} />{n.anhang.system}</span>}
            {n.anhang.log && <details><summary><ScrollText size={11} />Log ansehen</summary><pre>{n.anhang.log}</pre></details>}
            {n.anhang.bild && <button type="button" className="tz-klein" onClick={() => void bildZeigen(n)}>{busy === "bild" + n.id ? <Loader2 size={12} className="tz-dreh" /> : <Image size={12} />}Bildschirmfoto</button>}
          </div>}
          <div className="tz-n-fuss">
            {n.art === "idee" && <button type="button" className={"tz-stimme " + (n.meine_stimme ? "an" : "")} onClick={() => void handeln("s" + n.id, () => teamAnfrage<TeamStand>("team/stimme", { id: n.id }))}><ThumbsUp size={11} />{n.stimmen}</button>}
            {n.art === "idee" && (admin ? <select className={"tz-idee-status s-" + n.status} value={n.status} onChange={e => void handeln("st" + n.id, () => teamAnfrage<TeamStand>("team/status", { id: n.id, status: e.target.value }))} aria-label="Status der Idee">{Object.entries(stand?.status || {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select> : <span className={"tz-idee-status s-" + n.status}>{stand?.status[n.status || "neu"]}</span>)}
            {!n.von_mir && <button type="button" className="tz-link" onClick={() => {setAntwort(n); if (!admin) setArt("nachricht");}}><Reply size={11} />Antworten</button>}
            {(admin || n.von_mir) && <button type="button" className="tz-link tz-gefahr" onClick={() => void handeln("l" + n.id, () => teamAnfrage<TeamStand>("team/loeschen", { id: n.id }))}><Trash2 size={11} />Entfernen</button>}
          </div>
        </motion.div>;
      })}
    </div>
    <form className="tz-schreiben" onSubmit={e => {e.preventDefault(); if (text.trim() && !busy) void senden();}}>
      {antwort && <div className="tz-antwort-auf"><Reply size={12} />Antwort an {antwort.von.name}: „{antwort.text.slice(0, 80)}“<button type="button" aria-label="Antwort abbrechen" onClick={() => setAntwort(null)}><X size={12} /></button></div>}
      <div className="tz-schreiben-optionen">
        <div className="tz-chips" role="radiogroup" aria-label="Art">
          {(admin ? ["rundschreiben", "nachricht", "idee"] : ["idee", "fehler", "nachricht"]).map(a => {
            const Icon = ART[a].icon;
            return <button key={a} type="button" role="radio" aria-checked={art === a} className={art === a ? "an" : ""} onClick={() => setArt(a)}><Icon size={12} />{ART[a].text}</button>;
          })}
        </div>
        {art !== "rundschreiben" && !(antwort && admin) && <select aria-label="Empfänger" value={an} onChange={e => setAn(e.target.value)}>{ziele.map(z => <option key={z.id} value={z.id}>{z.name}</option>)}</select>}
      </div>
      <div className="tz-schreiben-zeile">
        <textarea rows={2} maxLength={8000} value={text} onChange={e => setText(e.target.value)} onKeyDown={e => {if (e.key === "Enter" && !e.shiftKey) {e.preventDefault(); if (text.trim() && !busy) void senden();}}} placeholder={art === "idee" ? "Deine Idee für Jon …" : art === "fehler" ? "Was ist passiert, und wie kann man es nachstellen?" : art === "rundschreiben" ? "Nachricht an alle Entwickler …" : "Deine Nachricht …"} aria-label="Nachricht" />
        <button type="submit" className="tz-gold" disabled={!text.trim() || !!busy}>{busy === "senden" ? <Loader2 size={15} className="tz-dreh" /> : <Send size={15} />}</button>
      </div>
    </form>
    <AnimatePresence>{bild && <motion.div className="tz-bild" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setBild(null)}><img src={bild.daten} alt="Bildschirmfoto zum Fehlerbericht" /><button type="button" aria-label="Schließen"><X size={16} /></button></motion.div>}</AnimatePresence>
  </div>;
}

function FehlerMelden({ onFehler }: { onFehler: (text: string) => void }) {
  const [text, setText] = useState("");
  const [bild, setBild] = useState(true);
  const [busy, setBusy] = useState(false);
  const [fertig, setFertig] = useState(false);
  const senden = async () => {
    setBusy(true);
    onFehler("");
    try {
      await premiumAnfrage("/premium/fehlerbericht", { text, bild });
      setFertig(true);
      setText("");
    } catch (e) {
      onFehler(fehlerText(e));
    } finally {
      setBusy(false);
    }
  };
  if (fertig) return <div className="tz-erfolg"><span><Check size={20} /></span><b>Fehlerbericht ist beim Admin.</b><p>Version, System, das Protokoll ohne Passwörter{bild ? " und ein Bildschirmfoto" : ""} sind dabei. Die Antwort siehst du im Team-Chat.</p><button type="button" onClick={() => setFertig(false)}>Noch einen Fehler melden</button></div>;
  return <div className="tz-fehler-melden">
    <div className="tz-abschnitt-kopf"><div><h4>Fehler mit einem Klick melden</h4><p>Jon schickt dem Admin automatisch Version, System und die letzten Protokollzeilen mit. Passwörter, Schlüssel und Tokens werden vorher entfernt.</p></div></div>
    <textarea rows={5} maxLength={8000} value={text} onChange={e => setText(e.target.value)} placeholder="Was ist passiert? Was hast du davor gemacht? Was hättest du erwartet?" aria-label="Fehlerbeschreibung" />
    <label className="tz-schalter"><input type="checkbox" checked={bild} onChange={e => setBild(e.target.checked)} /><span className="tz-schalter-bahn"><i /></span><span><b>Bildschirmfoto mitschicken</b><small>So sieht der Admin genau, was du siehst</small></span></label>
    <button type="button" className="tz-gold tz-breit" disabled={busy} onClick={() => void senden()}>{busy ? <Loader2 size={15} className="tz-dreh" /> : <Bug size={15} />}Fehlerbericht senden</button>
  </div>;
}

interface Statistik {
  geraete: { geraet: string; kurz: string; name: string; rolle: string; version: string; system: string; zuletzt: number; anfragen: number; tokens: number; felworks_heute: number }[];
  summe: { geraete: number; anfragen: number; tokens: number; fehler: number; modelle: [string, number][]; werkzeuge: [string, number][]; anbieter: [string, number][] };
  felworks: { kontingent: number; heute: number; gesamt: number };
}

function Geraete({ onFehler }: { onFehler: (text: string) => void }) {
  const [daten, setDaten] = useState<Statistik | null>(null);
  const [kontingent, setKontingent] = useState("");
  const laden = async () => {
    try {
      const neu = await teamAnfrage<Statistik>("statistik");
      setDaten(neu);
      setKontingent(String(neu.felworks.kontingent));
    } catch (e) {
      onFehler(fehlerText(e));
    }
  };
  useEffect(() => {void laden();}, []);
  const speichern = async () => {
    try {
      await teamAnfrage("llm/kontingent", { wert: Number(kontingent) || 0 });
      await laden();
    } catch (e) {
      onFehler(fehlerText(e));
    }
  };
  if (!daten) return <div className="tz-leer"><Loader2 size={14} className="tz-dreh" />Lade Statistik vom Pi …</div>;
  const balken = (liste: [string, number][]) => {
    const max = Math.max(1, ...liste.map(([, n]) => n));
    return liste.length ? liste.map(([name, n]) => <div key={name} className="tz-balken"><span>{name}</span><i style={{ width: `${(n / max) * 100}%` }} /><b>{zahl(n)}</b></div>) : <p className="tz-hinweis">Noch keine Daten.</p>;
  };
  return <div className="tz-geraete">
    <div className="tz-kacheln">
      <div className="tz-kachel"><Users size={15} /><b>{zahl(daten.summe.geraete)}</b><span>Team-Geräte</span></div>
      <div className="tz-kachel"><Activity size={15} /><b>{zahl(daten.summe.anfragen)}</b><span>Modellanfragen heute</span></div>
      <div className="tz-kachel"><Gauge size={15} /><b>{zahl(daten.summe.tokens)}</b><span>Tokens heute</span></div>
      <div className="tz-kachel"><Server size={15} /><b>{zahl(daten.felworks.heute)}</b><span>über FelWorks heute</span></div>
    </div>
    <div className="tz-karte">
      <div className="tz-karte-kopf"><Server size={14} /><b>Modellzugang über FelWorks</b></div>
      <p className="tz-hinweis">Entwickler können Cloud-Modelle über deinen NVIDIA-Schlüssel auf dem Pi nutzen. Hier legst du fest, wie viele Anfragen jedes Gerät pro Tag stellen darf. Admins haben kein Limit. Insgesamt bisher: {zahl(daten.felworks.gesamt)} Anfragen.</p>
      <div className="tz-zeile"><input type="number" min={0} max={100000} value={kontingent} onChange={e => setKontingent(e.target.value)} aria-label="Anfragen pro Gerät und Tag" /><span>Anfragen pro Gerät und Tag</span><button type="button" className="tz-klein" onClick={() => void speichern()}><Check size={12} />Speichern</button></div>
    </div>
    <div className="tz-zwei">
      <div className="tz-karte"><div className="tz-karte-kopf"><Cpu size={14} /><b>Modelle</b></div>{balken(daten.summe.modelle)}</div>
      <div className="tz-karte"><div className="tz-karte-kopf"><Wrench size={14} /><b>Werkzeuge</b></div>{balken(daten.summe.werkzeuge)}</div>
    </div>
    <div className="tz-karte">
      <div className="tz-karte-kopf"><Users size={14} /><b>Geräte im Team</b><button type="button" className="tz-klein" onClick={() => void laden()}><RefreshCw size={12} />Neu laden</button></div>
      {!daten.geraete.length && <p className="tz-hinweis">Geräte melden sich hier, sobald Jon dort einmal beim Pi nachgefragt hat (alle 6 Stunden und beim Start).</p>}
      {daten.geraete.map(g => <div key={g.geraet} className="tz-geraet">
        <span className={"tz-punkt " + (Date.now() / 1000 - g.zuletzt < 7 * 3600 ? "an" : "")} />
        <span><b>{g.name}<em className={"tz-marke tz-art-" + g.rolle}>{g.rolle === "admin" ? "Admin" : "Entwickler"}</em></b><small>Gerät {g.kurz} · Jon {g.version || "?"} · {g.system || "?"} · zuletzt {zeit(g.zuletzt)}</small></span>
        <span className="tz-geraet-zahlen"><b>{zahl(g.anfragen)}</b> Anfragen · <b>{zahl(g.felworks_heute)}</b> FelWorks</span>
      </div>)}
    </div>
  </div>;
}

interface FlagEintrag { name: string; beschreibung: string; an: boolean; fuer: "alle" | "auswahl"; codes: string[]; eigen: boolean }

function Schalter({ onFehler }: { onFehler: (text: string) => void }) {
  const [flags, setFlags] = useState<Record<string, FlagEintrag> | null>(null);
  const [mitglieder, setMitglieder] = useState<{ id: string; name: string }[]>([]);
  const [neu, setNeu] = useState({ schluessel: "", name: "" });
  const laden = async () => {
    try {
      setFlags((await teamAnfrage<{ flags: Record<string, FlagEintrag> }>("flags/liste")).flags);
      setMitglieder((await teamAnfrage<TeamStand>("team/liste")).mitglieder);
    } catch (e) {
      onFehler(fehlerText(e));
    }
  };
  useEffect(() => {void laden();}, []);
  const setzen = async (schluessel: string, werte: Record<string, unknown>) => {
    try {
      setFlags((await teamAnfrage<{ flags: Record<string, FlagEintrag> }>("flags/setzen", { schluessel, ...werte })).flags);
    } catch (e) {
      onFehler(fehlerText(e));
    }
  };
  if (!flags) return <div className="tz-leer"><Loader2 size={14} className="tz-dreh" />Lade Schalter …</div>;
  return <div className="tz-schalter-liste">
    <div className="tz-abschnitt-kopf"><div><h4>Beta-Schalter</h4><p>Schalte Funktionen für alle Entwickler oder nur für ausgewählte frei. Admins haben immer alles. Eigene Schalter kannst du für neue Funktionen anlegen und später im Code abfragen.</p></div></div>
    {Object.entries(flags).map(([schluessel, f]) => <div key={schluessel} className={"tz-flag " + (f.an ? "an" : "")}>
      <label className="tz-schalter"><input type="checkbox" checked={f.an} onChange={e => void setzen(schluessel, { an: e.target.checked })} /><span className="tz-schalter-bahn"><i /></span><span><b>{f.name}</b><small>{f.beschreibung || schluessel}</small></span></label>
      <div className="tz-flag-ziel">
        <select value={f.fuer} onChange={e => void setzen(schluessel, { fuer: e.target.value })} disabled={!f.an} aria-label="Für wen"><option value="alle">Alle Entwickler</option><option value="auswahl">Nur ausgewählte</option></select>
        {f.eigen && <button type="button" className="tz-klein tz-gefahr" title="Schalter löschen" onClick={() => void setzen(schluessel, { loeschen: true })}><Trash2 size={12} /></button>}
      </div>
      {f.an && f.fuer === "auswahl" && <div className="tz-chips">{mitglieder.map(m => <button key={m.id} type="button" className={f.codes.includes(m.id) ? "an" : ""} onClick={() => void setzen(schluessel, { codes: f.codes.includes(m.id) ? f.codes.filter(c => c !== m.id) : [...f.codes, m.id] })}>{f.codes.includes(m.id) ? <Check size={11} /> : <Plus size={11} />}{m.name}</button>)}{!mitglieder.length && <span className="tz-hinweis">Noch keine Entwickler im Team.</span>}</div>}
    </div>)}
    <form className="tz-zeile tz-flag-neu" onSubmit={e => {e.preventDefault(); if (neu.schluessel && neu.name) void setzen(neu.schluessel, { name: neu.name, an: false }).then(() => setNeu({ schluessel: "", name: "" }));}}>
      <input placeholder="schluessel_wie_so" value={neu.schluessel} onChange={e => setNeu({ ...neu, schluessel: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "") })} aria-label="Schlüssel des neuen Schalters" maxLength={31} />
      <input placeholder="Name, z. B. Neues Menü" value={neu.name} onChange={e => setNeu({ ...neu, name: e.target.value })} aria-label="Name des neuen Schalters" maxLength={80} />
      <button type="submit" className="tz-klein" disabled={!neu.schluessel || !neu.name}><Plus size={12} />Schalter anlegen</button>
    </form>
  </div>;
}

interface PiStand { dienste: Record<string, string>; version: string; git: string; funnel: string; laufzeit: string; platte: { frei_gb?: number; gesamt_gb?: number }; ram: { frei_mb?: number; gesamt_mb?: number }; temperatur: number | null }

const DIENST_NAME: Record<string, string> = { jon: "Jon auf dem Pi", "jon-codes": "Codeserver", "jon-demo": "Website-Demo" };

function Pi({ onFehler }: { onFehler: (text: string) => void }) {
  const [stand, setStand] = useState<PiStand | null>(null);
  const [busy, setBusy] = useState("");
  const [meldung, setMeldung] = useState("");
  const [log, setLog] = useState<{ dienst: string; text: string } | null>(null);
  const laden = async () => {
    try {
      setStand(await teamAnfrage<PiStand>("pi/status"));
    } catch (e) {
      onFehler(fehlerText(e));
    }
  };
  useEffect(() => {void laden();}, []);
  const handeln = async (kennung: string, fn: () => Promise<void>) => {
    setBusy(kennung);
    onFehler("");
    setMeldung("");
    try {
      await fn();
    } catch (e) {
      onFehler(fehlerText(e));
    } finally {
      setBusy("");
    }
  };
  if (!stand) return <div className="tz-leer"><Loader2 size={14} className="tz-dreh" />Frage den Pi …</div>;
  return <div className="tz-pi">
    <div className="tz-kacheln">
      <div className="tz-kachel"><Sparkles size={15} /><b>{stand.version || "?"}</b><span>Jon-Version</span></div>
      <div className="tz-kachel"><Cpu size={15} /><b>{stand.ram.frei_mb !== undefined ? `${zahl(stand.ram.frei_mb)} MB` : "?"}</b><span>RAM frei von {zahl(stand.ram.gesamt_mb)} MB</span></div>
      <div className="tz-kachel"><HardDrive size={15} /><b>{stand.platte.frei_gb ?? "?"} GB</b><span>Platte frei von {stand.platte.gesamt_gb ?? "?"} GB</span></div>
      <div className="tz-kachel"><Activity size={15} /><b>{stand.temperatur !== null ? `${stand.temperatur} °C` : "?"}</b><span>{stand.laufzeit || "Laufzeit unbekannt"}</span></div>
    </div>
    {meldung && <div className="tz-ok"><Check size={13} />{meldung}</div>}
    <div className="tz-karte">
      <div className="tz-karte-kopf"><Server size={14} /><b>Dienste</b><button type="button" className="tz-klein" onClick={() => void laden()}><RefreshCw size={12} />Neu laden</button></div>
      {Object.entries(stand.dienste).map(([dienst, zustand]) => <div key={dienst} className="tz-dienst">
        <span className={"tz-punkt " + (zustand === "active" ? "an" : "aus")} />
        <span><b>{DIENST_NAME[dienst] || dienst}</b><small>{zustand === "active" ? "läuft" : zustand}</small></span>
        <button type="button" className="tz-klein" onClick={() => void handeln("log" + dienst, async () => setLog({ dienst, text: (await teamAnfrage<{ log: string }>("pi/log", { dienst })).log }))}>{busy === "log" + dienst ? <Loader2 size={12} className="tz-dreh" /> : <ScrollText size={12} />}Log</button>
        <button type="button" className="tz-klein" onClick={() => void handeln("neu" + dienst, async () => {setMeldung((await teamAnfrage<{ text: string }>("pi/neustart", { dienst })).text); setTimeout(() => void laden(), 8000);})}>{busy === "neu" + dienst ? <Loader2 size={12} className="tz-dreh" /> : <Power size={12} />}Neu starten</button>
      </div>)}
    </div>
    <div className="tz-karte">
      <div className="tz-karte-kopf"><Download size={14} /><b>Pi aktualisieren</b></div>
      <p className="tz-hinweis">Holt den neuesten Stand von GitHub (<code>{stand.git || "?"}</code>) und aktualisiert die Bibliotheken. Danach Jon, Demo und Codeserver neu starten.</p>
      <button type="button" className="tz-klein" disabled={!!busy} onClick={() => {if (confirm("Jon auf dem Pi jetzt aus GitHub aktualisieren?")) void handeln("update", async () => {const r = await teamAnfrage<{ text: string; hinweis: string }>("pi/aktualisieren"); setMeldung(r.hinweis); setLog({ dienst: "Aktualisierung", text: r.text }); void laden();});}}>{busy === "update" ? <Loader2 size={12} className="tz-dreh" /> : <Download size={12} />}Jetzt aktualisieren</button>
    </div>
    <details className="tz-karte tz-funnel"><summary><Share2 size={14} /><b>Tailscale Funnel</b><ChevronDown size={13} /></summary><pre>{stand.funnel || "Keine Angaben"}</pre></details>
    <AnimatePresence>{log && <motion.div className="tz-log" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}><div className="tz-karte-kopf"><ScrollText size={14} /><b>{DIENST_NAME[log.dienst] || log.dienst}</b><button type="button" className="tz-klein" onClick={() => setLog(null)}><X size={12} /></button></div><pre>{log.text}</pre></motion.div>}</AnimatePresence>
  </div>;
}

interface GeteilterSkill { id: string; name: string; titel: string; beschreibung: string; autor: { id: string; name: string }; zeit: number; downloads: number; zeichen: number }

function Skills({ ich, admin, onFehler }: { ich: string; admin: boolean; onFehler: (text: string) => void }) {
  const [skills, setSkills] = useState<GeteilterSkill[] | null>(null);
  const [eigene, setEigene] = useState<SkillSummary[]>([]);
  const [wahl, setWahl] = useState("");
  const [beschreibung, setBeschreibung] = useState("");
  const [busy, setBusy] = useState("");
  const [meldung, setMeldung] = useState("");
  const laden = async () => {
    try {
      setSkills((await teamAnfrage<{ skills: GeteilterSkill[] }>("skills/liste")).skills);
    } catch (e) {
      setSkills([]);
      onFehler(fehlerText(e));
    }
  };
  useEffect(() => {void laden(); void getSkills().then(setEigene);}, []);
  const handeln = async (kennung: string, fn: () => Promise<void>) => {
    setBusy(kennung);
    onFehler("");
    setMeldung("");
    try {
      await fn();
    } catch (e) {
      onFehler(fehlerText(e));
    } finally {
      setBusy("");
    }
  };
  const teilen = () => handeln("teilen", async () => {
    const skill = eigene.find(s => s.name === wahl);
    if (!skill) return;
    const { content } = await getSkill(skill.name);
    setSkills((await teamAnfrage<{ skills: GeteilterSkill[] }>("skills/teilen", { name: skill.name, titel: skill.title || skill.name, beschreibung, inhalt: content })).skills);
    setMeldung(`„${skill.title || skill.name}“ ist jetzt fürs Team verfügbar.`);
    setWahl("");
    setBeschreibung("");
  });
  return <div className="tz-skills">
    <div className="tz-karte">
      <div className="tz-karte-kopf"><Share2 size={14} /><b>Eigenen Skill teilen</b></div>
      <div className="tz-zeile">
        <select value={wahl} onChange={e => setWahl(e.target.value)} aria-label="Skill auswählen"><option value="">Skill aus deinem Jon wählen …</option>{eigene.map(s => <option key={s.name} value={s.name}>{s.title || s.name}</option>)}</select>
        <input value={beschreibung} onChange={e => setBeschreibung(e.target.value)} maxLength={300} placeholder="Wofür ist er gut? (optional)" aria-label="Beschreibung" />
        <button type="button" className="tz-klein" disabled={!wahl || !!busy} onClick={() => void teilen()}>{busy === "teilen" ? <Loader2 size={12} className="tz-dreh" /> : <Share2 size={12} />}Teilen</button>
      </div>
    </div>
    {meldung && <div className="tz-ok"><Check size={13} />{meldung}</div>}
    {skills === null && <div className="tz-leer"><Loader2 size={14} className="tz-dreh" />Lade Skills …</div>}
    {skills && !skills.length && <div className="tz-leer tz-leer-gross"><Share2 size={20} /><b>Noch keine geteilten Skills</b><span>Teile oben deinen ersten Skill mit dem Team.</span></div>}
    {skills?.map(s => <div key={s.id} className="tz-skill">
      <span className="tz-skill-icon"><ScrollText size={14} /></span>
      <span className="tz-skill-text"><b>{s.titel}</b><small>{s.beschreibung || s.name} · von {s.autor.id === ich ? "dir" : s.autor.name} · {zahl(s.zeichen)} Zeichen · {zahl(s.downloads)}× installiert</small></span>
      <button type="button" className="tz-klein" disabled={!!busy} onClick={() => void handeln("i" + s.id, async () => {const r = await premiumAnfrage<{ titel: string }>("/premium/skill-installieren", { id: s.id }); setMeldung(`„${r.titel}“ ist installiert. Jon kennt den Skill ab der nächsten Nachricht.`); void laden();})}>{busy === "i" + s.id ? <Loader2 size={12} className="tz-dreh" /> : <Download size={12} />}Installieren</button>
      {(admin || s.autor.id === ich) && <button type="button" className="tz-klein tz-gefahr" title="Entfernen" onClick={() => void handeln("e" + s.id, async () => setSkills((await teamAnfrage<{ skills: GeteilterSkill[] }>("skills/entfernen", { id: s.id })).skills))}><Trash2 size={12} /></button>}
    </div>)}
  </div>;
}

interface InspektorEintrag { id: number; zeit: number; anbieter: string; modell: string; slot: string; nachrichten: number; zeichen: number; werkzeuge_angeboten: number; frage: string; antwort: string; denken: number; erstes_token: number | null; dauer: number | null; prompt_tokens: number; antwort_tokens: number; werkzeuge: { name: string; ok: boolean | null }[]; fehler: string; laeuft: boolean }

function Inspektor({ onFehler }: { onFehler: (text: string) => void }) {
  const [daten, setDaten] = useState<{ eintraege: InspektorEintrag[]; nutzung: { anfragen: number; tokens: number; fehler: number } } | null>(null);
  const [live, setLive] = useState(true);
  const [offen, setOffen] = useState<number | null>(null);
  const laden = async () => {
    try {
      const antwort = await fetch(BASE + "/inspektor");
      const neu = await antwort.json();
      if (!antwort.ok) throw new Error(typeof neu.detail === "string" ? neu.detail : "Der Inspektor ist nicht erreichbar.");
      setDaten(neu);
    } catch (e) {
      onFehler(fehlerText(e));
      setLive(false);
    }
  };
  useEffect(() => {
    void laden();
    if (!live) return;
    const takt = setInterval(() => {if (!document.hidden) void laden();}, 2500);
    return () => clearInterval(takt);
  }, [live]);
  if (!daten) return <div className="tz-leer"><Loader2 size={14} className="tz-dreh" />Lade Inspektor …</div>;
  return <div className="tz-inspektor">
    <div className="tz-zeile tz-inspektor-kopf">
      <span><b>{zahl(daten.nutzung.anfragen)}</b> Anfragen heute · <b>{zahl(daten.nutzung.tokens)}</b> Tokens · <b>{zahl(daten.nutzung.fehler)}</b> Fehler</span>
      <label className="tz-mini-schalter"><input type="checkbox" checked={live} onChange={e => setLive(e.target.checked)} />Live</label>
      <button type="button" className="tz-klein" onClick={() => void fetch(BASE + "/inspektor/leeren", { method: "POST" }).then(() => laden())}><Trash2 size={12} />Leeren</button>
    </div>
    {!daten.eintraege.length && <div className="tz-leer tz-leer-gross"><Eye size={20} /><b>Noch keine Anfragen</b><span>Schreib Jon etwas. Jede Modellanfrage erscheint hier mit Anbieter, Modell, Dauer, Tokens und Werkzeugen.</span></div>}
    {daten.eintraege.map(e => <div key={e.id} className={"tz-anfrage " + (e.fehler ? "fehler " : "") + (e.laeuft ? "laeuft" : "")}>
      <button type="button" className="tz-anfrage-zeile" onClick={() => setOffen(o => o === e.id ? null : e.id)} aria-expanded={offen === e.id}>
        <span className="tz-anfrage-zeit">{new Date(e.zeit * 1000).toLocaleTimeString("de-AT")}</span>
        <span className="tz-anfrage-modell"><b>{e.modell}</b><small>{e.anbieter} · {e.slot}</small></span>
        <span className="tz-anfrage-zahlen">{e.laeuft ? <Loader2 size={12} className="tz-dreh" /> : `${e.dauer?.toFixed(1)} s`}{e.erstes_token !== null && <small>erstes Token {e.erstes_token.toFixed(1)} s</small>}</span>
        <span className="tz-anfrage-zahlen"><b>{zahl(e.prompt_tokens + e.antwort_tokens)}</b><small>Tokens</small></span>
        <span className="tz-anfrage-werkzeuge">{e.werkzeuge.slice(0, 3).map((w, i) => <em key={i} className={w.ok === false ? "nein" : ""}>{w.name}</em>)}{e.werkzeuge.length > 3 && <em>+{e.werkzeuge.length - 3}</em>}</span>
        <ChevronDown size={13} className="tz-pfeil" />
      </button>
      <AnimatePresence initial={false}>{offen === e.id && <motion.div className="tz-anfrage-details" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
        <dl>
          <dt>Nachrichten</dt><dd>{e.nachrichten} · {zahl(e.zeichen)} Zeichen · {e.werkzeuge_angeboten} Werkzeuge angeboten</dd>
          <dt>Tokens</dt><dd>{zahl(e.prompt_tokens)} Eingabe · {zahl(e.antwort_tokens)} Antwort · {zahl(e.denken)} Zeichen Nachdenken</dd>
          {e.frage && <><dt>Frage</dt><dd>{e.frage}</dd></>}
          {e.antwort && <><dt>Antwort</dt><dd>{e.antwort}</dd></>}
          {!!e.werkzeuge.length && <><dt>Werkzeuge</dt><dd className="tz-anfrage-werkzeuge">{e.werkzeuge.map((w, i) => <em key={i} className={w.ok === false ? "nein" : ""}>{w.name}{w.ok === null ? "" : w.ok ? " ✓" : " ✗"}</em>)}</dd></>}
          {e.fehler && <><dt>Fehler</dt><dd className="tz-fehlertext">{e.fehler}</dd></>}
        </dl>
      </motion.div>}</AnimatePresence>
    </div>)}
  </div>;
}

function Einstellungen({ status, onFehler }: { status: PremiumStatus; onFehler: (text: string) => void }) {
  const [beta, setBeta] = useState(status.beta);
  const umschalten = async (an: boolean) => {
    try {
      const neu = await premiumAnfrage<PremiumStatus>("/premium/beta", { an });
      setBeta(neu.beta);
    } catch (e) {
      onFehler(fehlerText(e));
    }
  };
  const VORTEILE: [string, string, typeof FlaskConical][] = [["beta", "Beta-Versionen", FlaskConical], ["inspektor", "Jon-Inspektor", Eye], ["modell", "Modellzugang über FelWorks", Server], ["skills", "Skills teilen", Share2], ["fehlerbericht", "Fehler mit einem Klick", Bug]];
  return <div className="tz-einstellungen">
    <div className="tz-karte">
      <label className="tz-schalter"><input type="checkbox" checked={beta} disabled={!status.flags.beta} onChange={e => void umschalten(e.target.checked)} /><span className="tz-schalter-bahn"><i /></span><span><b>Beta-Versionen früher bekommen</b><small>Jon aktualisiert sich dann auch auf Vorabversionen, bevor sie für alle erscheinen.</small></span></label>
    </div>
    <div className="tz-karte">
      <div className="tz-karte-kopf"><Server size={14} /><b>Modellzugang über FelWorks</b></div>
      <p className="tz-hinweis">{status.flags.modell ? "Wähle oben im Chat beim Anbieter „FelWorks · über den Pi“. Dann laufen die Anfragen über den FelWorks-Zugang, ohne eigenen API-Schlüssel." : "Der Admin hat den Modellzugang für dich noch nicht freigegeben."}</p>
    </div>
    <div className="tz-karte">
      <div className="tz-karte-kopf"><ToggleLeft size={14} /><b>Deine Vorteile</b></div>
      <div className="tz-vorteile">{VORTEILE.map(([key, name, Icon]) => <span key={key} className={status.flags[key] ? "an" : ""}><Icon size={13} />{name}{status.flags[key] ? <Check size={12} /> : <X size={12} />}</span>)}</div>
      {Object.keys(status.flags).filter(k => !VORTEILE.some(([v]) => v === k)).length > 0 && <p className="tz-hinweis">Weitere Beta-Schalter: {Object.entries(status.flags).filter(([k]) => !VORTEILE.some(([v]) => v === k)).map(([k, v]) => `${k} ${v ? "an" : "aus"}`).join(" · ")}</p>}
    </div>
  </div>;
}

export default function TeamZentrale({ status, onFehler, onNeuLaden }: { status: PremiumStatus; onFehler: (text: string) => void; onNeuLaden: () => void }) {
  const admin = status.stufe === "admin";
  const bereiche = useMemo(() => {
    const liste: { key: Bereich; name: string; icon: typeof Users; zeigen: boolean }[] = [
      { key: "codes", name: "Codes", icon: KeyRound, zeigen: admin },
      { key: "team", name: "Team", icon: MessagesSquare, zeigen: true },
      { key: "fehler", name: "Fehler melden", icon: Bug, zeigen: !admin && !!status.flags.fehlerbericht },
      { key: "geraete", name: "Geräte & Nutzung", icon: Activity, zeigen: admin },
      { key: "schalter", name: "Beta-Schalter", icon: ToggleLeft, zeigen: admin },
      { key: "pi", name: "Pi", icon: Server, zeigen: admin },
      { key: "skills", name: "Skills", icon: Share2, zeigen: !!status.flags.skills },
      { key: "inspektor", name: "Inspektor", icon: Eye, zeigen: !!status.flags.inspektor },
      { key: "einstellungen", name: "Einstellungen", icon: Settings2, zeigen: true },
    ];
    return liste.filter(b => b.zeigen);
  }, [admin, status.flags]);
  const [bereich, setBereich] = useState<Bereich>(admin ? "codes" : "team");
  const [ich, setIch] = useState("");
  useEffect(() => {void teamAnfrage<TeamStand>("team/ungelesen").then(() => onNeuLaden()).catch(() => {}); void teamAnfrage<TeamStand>("team/liste").then(s => setIch(s.ich.id)).catch(() => {});}, []);
  return <section className="tz pm-ein" aria-label="Team-Zentrale">
    <div className="tz-kopf">
      <span className={"tz-emblem " + (admin ? "admin" : "entwickler")}>{admin ? <Users size={17} /> : <Wrench size={17} />}</span>
      <div><h3>Team-Zentrale</h3><p>{admin ? "Codes, Team, Beta-Schalter, Statistik und dein Pi an einem Ort." : "Schreib dem Admin, melde Fehler, teile Skills und schau Jon unter die Haube."}</p></div>
    </div>
    <nav className="tz-reiter" role="tablist" aria-label="Bereiche der Team-Zentrale">
      {bereiche.map(b => <button key={b.key} role="tab" aria-selected={bereich === b.key} className={bereich === b.key ? "an" : ""} onClick={() => setBereich(b.key)}>
        {bereich === b.key && <motion.span layoutId="tz-reiter-hinten" className="tz-reiter-hinten" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
        <b.icon size={13} /><span>{b.name}</span>{b.key === "team" && status.ungelesen > 0 && <em>{status.ungelesen}</em>}
      </button>)}
    </nav>
    <AnimatePresence mode="wait" initial={false}>
      <motion.div key={bereich} className="tz-inhalt" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.16 }}>
        {bereich === "codes" && <EntwicklerCodes onFehler={onFehler} />}
        {bereich === "team" && <TeamChat admin={admin} onFehler={onFehler} onGelesen={onNeuLaden} />}
        {bereich === "fehler" && <FehlerMelden onFehler={onFehler} />}
        {bereich === "geraete" && <Geraete onFehler={onFehler} />}
        {bereich === "schalter" && <Schalter onFehler={onFehler} />}
        {bereich === "pi" && <Pi onFehler={onFehler} />}
        {bereich === "skills" && <Skills ich={ich} admin={admin} onFehler={onFehler} />}
        {bereich === "inspektor" && <Inspektor onFehler={onFehler} />}
        {bereich === "einstellungen" && <Einstellungen status={status} onFehler={onFehler} />}
      </motion.div>
    </AnimatePresence>
  </section>;
}
