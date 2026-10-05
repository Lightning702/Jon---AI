import {AnimatePresence, motion} from "framer-motion";
import {AlertTriangle, ChevronDown, FileText, FolderOpen, Loader2, ShieldAlert, ShieldCheck, Square, Trash2, Users} from "lucide-react";
import {useMemo, useState} from "react";
import AgentenBuehne from "./AgentenBuehne";
import AgentenStufen from "./AgentenStufen";
import {Anfrage, dauerText, ENDE, fehlerText, LAUF_STUFEN, LAUF_TEXT, Lauf, laufPhase, laufStufe, quelle, rolle, Teil, TEIL_TEXT} from "./daten";
import {useJetzt, useLive} from "./live";

const statusKlasse = (status: string) => status === "done" ? "ok" : status === "needs_review" ? "offen" : ENDE.has(status) ? "fehler" : "laeuft";

function TeilZeile({teil, jetzt}: {teil: Teil; jetzt: number}) {
  const [offen, setOffen] = useState(false);
  const r = rolle(teil.rolle);
  const Icon = r.icon;
  const laeuft = teil.status === "working";
  const dauer = teil.dauer ?? (laeuft && teil.begonnen ? jetzt - teil.begonnen : 0);
  return <motion.div layout className="ab-zeile" data-status={teil.status} style={{["--farbe" as string]: r.farbe}} initial={{opacity: 0, y: 6}} animate={{opacity: 1, y: 0}}>
    <button type="button" className="ab-zeile-kopf" onClick={() => setOffen(v => !v)} aria-expanded={offen}>
      <span className="ab-zeile-icon"><Icon/></span>
      <span className="ab-zeile-text"><strong>{teil.titel}</strong><small>{teil.rolle_name || r.name}{teil.auftrag ? " · " + teil.auftrag : ""}</small></span>
      <span className="ab-zeile-status">{laeuft && <Loader2 className="ab-dreht"/>}<span className={laeuft ? "ab-schimmer" : ""}>{TEIL_TEXT[teil.status] || teil.status}</span>{dauer > 0 && <span>{dauerText(dauer)}</span>}<ChevronDown className={`ab-zeile-pfeil ${offen ? "offen" : ""}`}/></span>
    </button>
    <AnimatePresence initial={false}>{offen && <motion.div className="ab-zeile-inhalt" initial={{height: 0, opacity: 0}} animate={{height: "auto", opacity: 1}} exit={{height: 0, opacity: 0}} transition={{duration: 0.22}}>
      {teil.auftrag && <><b>Teilauftrag</b>{teil.auftrag}</>}
      <b>{teil.fehler ? "Fehler" : "Ergebnis"}</b>{teil.ergebnis || teil.fehler || "Arbeitet noch an der Teilfrage …"}
    </motion.div>}</AnimatePresence>
  </motion.div>;
}

function Gespeichert({datei, request}: {datei: string; request?: Anfrage}) {
  const [fehler, setFehler] = useState("");
  const oeffnen = async (ordner: boolean) => {
    setFehler("");
    try {await request?.("/dateien/oeffnen", {pfad: datei, ordner});}
    catch (e) {setFehler(fehlerText(e));}
  };
  return <div className="ab-gespeichert">
    <FileText/>
    <span><strong>Im Agenten-Ordner gespeichert</strong><small title={datei}>{datei}</small>{fehler && <small className="ab-gespeichert-fehler">{fehler}</small>}</span>
    {request && <><button type="button" className="ab-knopf" onClick={() => void oeffnen(false)}>Öffnen</button><button type="button" className="ab-knopf" onClick={() => void oeffnen(true)}><FolderOpen/>Ordner</button></>}
  </div>;
}

export function FachteamAnsicht({lauf, kompakt = false, ergebnisOffen = true, onStopp, onLoeschen, beschaeftigt, request}: {lauf: Lauf; kompakt?: boolean; ergebnisOffen?: boolean; onStopp?: () => void; onLoeschen?: () => void; beschaeftigt?: boolean; request?: Anfrage}) {
  const aktiv = !ENDE.has(lauf.status);
  const jetzt = useJetzt(aktiv);
  const [ergebnisZeigen, setErgebnisZeigen] = useState(ergebnisOffen);
  const knoten = useMemo(() => (lauf.teile || []).map((teil, i) => ({id: `${i}-${teil.rolle}`, titel: teil.titel, rolle: teil.rolle, status: teil.status})), [lauf.teile]);
  const dauer = lauf.dauer ?? (lauf.created_at ? (aktiv ? jetzt : lauf.updated_at || jetzt) - lauf.created_at : 0);
  const fertigCount = (lauf.teile || []).filter(t => t.status === "done").length;
  const herkunft = quelle(lauf.source);
  return <div className={`ab ab-karte ${aktiv ? "aktiv" : ""} ${kompakt ? "ab-kompakt" : ""}`}>
    <div className="ab-kopf">
      <span className="ab-kopf-icon"><Users/></span>
      <span className="ab-kopf-text"><strong>{kompakt ? lauf.aufgabe : "Jon Fachteam"}</strong><small>{kompakt ? (LAUF_TEXT[lauf.status] || lauf.status) + " · " : ""}{lauf.teile?.length ? `${fertigCount}/${lauf.teile.length} Agenten fertig` : "Stellt das Team zusammen"}{herkunft ? " · " + herkunft : ""}</small></span>
      {!kompakt && <span className={`ab-status ${statusKlasse(lauf.status)}`}>{LAUF_TEXT[lauf.status] || lauf.status}</span>}
      {dauer > 0 && <span className="ab-zeit">{dauerText(dauer)}</span>}
      {aktiv && onStopp && <button type="button" className="ab-knopf rund gefahr" disabled={beschaeftigt} onClick={onStopp} title="Fachteam stoppen" aria-label="Fachteam stoppen"><Square fill="currentColor"/></button>}
      {!aktiv && onLoeschen && <button type="button" className="ab-knopf rund" disabled={beschaeftigt} onClick={onLoeschen} title="Auftrag löschen" aria-label="Auftrag löschen"><Trash2/></button>}
    </div>
    {!kompakt && <p className="ab-aufgabe">{lauf.aufgabe}</p>}
    <AgentenBuehne phase={laufPhase(lauf.status)} knoten={knoten} kernText="Jon" kompakt={kompakt}/>
    <AgentenStufen stufen={LAUF_STUFEN} aktuell={laufStufe(lauf.status)} fertig={!aktiv}/>
    {!kompakt && !!lauf.teile?.length && <div className="ab-liste">{lauf.teile.map((teil, i) => <TeilZeile key={i} teil={teil} jetzt={jetzt}/>)}</div>}
    {lauf.hinweis && !kompakt && <div className="ab-hinweis"><AlertTriangle/><span>{lauf.hinweis}</span></div>}
    {lauf.fehler && <div className="ab-hinweis fehler"><AlertTriangle/><span>{lauf.fehler}</span></div>}
    {lauf.pruefung && !kompakt && <motion.div initial={{opacity: 0, y: 6}} animate={{opacity: 1, y: 0}} className={`ab-hinweis ${lauf.pruefung.ok ? "ok" : "offen"}`}>{lauf.pruefung.ok ? <ShieldCheck/> : <ShieldAlert/>}<span><strong>Gegenprüfung · {lauf.pruefung.ok ? "keine offenen Punkte" : "offene Punkte"}</strong>{!!lauf.pruefung.probleme.length && <ul>{lauf.pruefung.probleme.map((p, i) => <li key={i}>{p}</li>)}</ul>}{lauf.pruefung.korrektur && <span style={{display: "block", marginTop: 6}}>{lauf.pruefung.korrektur}</span>}</span></motion.div>}
    {lauf.antwort && !kompakt && <>
      {!ergebnisZeigen && <div className="ab-reihe"><button type="button" className="ab-knopf" onClick={() => setErgebnisZeigen(true)}>Ergebnis des Teams anzeigen<ChevronDown/></button></div>}
      <AnimatePresence>{ergebnisZeigen && <motion.div className="ab-ergebnis" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}}><h4>Ergebnis des Teams</h4>{lauf.antwort}</motion.div>}</AnimatePresence>
    </>}
    {lauf.datei && !aktiv && <Gespeichert datei={lauf.datei} request={request}/>}
  </div>;
}

export default function FachteamKarte({id, aufgabe = "", request, kompakt = false}: {id: string; aufgabe?: string; request: Anfrage; kompakt?: boolean}) {
  const pfad = "/agents/runs/" + encodeURIComponent(id);
  const {daten, setDaten, fehler, fehlversuche} = useLive<Lauf>(request, pfad, lauf => ENDE.has(lauf.status), 900);
  const [beschaeftigt, setBeschaeftigt] = useState(false);
  const [aktionsFehler, setAktionsFehler] = useState("");
  const stoppen = async () => {
    setBeschaeftigt(true);
    setAktionsFehler("");
    try {setDaten(await request(pfad + "/cancel", {}));}
    catch (e) {setAktionsFehler(fehlerText(e));}
    finally {setBeschaeftigt(false);}
  };
  if (!daten) {
    const verloren = fehlversuche >= 6;
    return <div className={`ab ab-karte ${verloren ? "" : "aktiv"} ${kompakt ? "ab-kompakt" : ""}`}>
      <div className="ab-kopf"><span className="ab-kopf-icon"><Users/></span><span className="ab-kopf-text"><strong>Jon Fachteam</strong><small>{verloren ? "Dieser Fachauftrag ist nicht mehr verfügbar" : "Jon stellt das Team zusammen"}</small></span></div>
      {aufgabe && !kompakt && <p className="ab-aufgabe">{aufgabe}</p>}
      <AgentenBuehne phase={verloren ? "ruhe" : "denken"} knoten={[]} kernText="Jon" kompakt={kompakt}/>
      {verloren && fehler && <p className="ab-leer">{fehler}</p>}
    </div>;
  }
  return <>
    <FachteamAnsicht lauf={daten} kompakt={kompakt} ergebnisOffen={false} onStopp={() => void stoppen()} beschaeftigt={beschaeftigt} request={request}/>
    {aktionsFehler && <p className="ab-leer" role="alert">{aktionsFehler}</p>}
  </>;
}
