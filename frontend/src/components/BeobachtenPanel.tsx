import { useEffect, useRef, useState } from "react";
import { BellRing, Check, ExternalLink, Eye, Loader2, Plus, RotateCw, Square, Trash2, TriangleAlert } from "lucide-react";
import { BASE } from "../lib/api";
import "./beobachten.css";

export interface Beobachtung {
  id: string;
  frage: string;
  bedingung: string;
  intervall_stunden: number;
  letzter_check: number;
  status: "aktiv" | "erfuellt" | "gestoppt";
  treffer: null | { beweis: string; quelle: string; titel: string; zeit: number };
  letzter_fehler?: string;
  pruefungen?: number;
}

async function anfrage<T>(pfad: string, methode = "GET", body?: unknown): Promise<T> {
  const antwort = await fetch(BASE + pfad, { method: methode, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  const daten = await antwort.json().catch(() => ({}));
  if (!antwort.ok) throw new Error(typeof daten.detail === "string" ? daten.detail : "Das hat nicht geklappt.");
  return daten as T;
}

export const beobachtungsMeldungen = () => anfrage<Beobachtung[]>("/beobachten/meldungen").catch(() => [] as Beobachtung[]);

const STATUS = { aktiv: "Beobachtet", erfuellt: "Eingetreten", gestoppt: "Gestoppt" };
const BEISPIELE = ["Tiiny AI Pocket Lab Release", "Neue Jon-Version auf getjon.info", "Tickets für mein Lieblingskonzert", "Preis der neuen Grafikkarte unter 500 €"];

function wann(sekunden: number) {
  if (!sekunden) return "noch nicht geprüft";
  const minuten = Math.round((Date.now() / 1000 - sekunden) / 60);
  if (minuten < 1) return "gerade eben geprüft";
  if (minuten < 60) return `vor ${minuten} Min. geprüft`;
  if (minuten < 48 * 60) return `vor ${Math.round(minuten / 60)} Std. geprüft`;
  return `zuletzt am ${new Date(sekunden * 1000).toLocaleDateString("de-AT")} geprüft`;
}

export default function BeobachtenPanel() {
  const [liste, setListe] = useState<Beobachtung[]>([]);
  const [frage, setFrage] = useState("");
  const [bedingung, setBedingung] = useState("");
  const [intervall, setIntervall] = useState(24);
  const [busy, setBusy] = useState("");
  const [fehler, setFehler] = useState("");
  const [laedt, setLaedt] = useState(true);

  const zuletzt = useRef("");
  const laden = async () => {
    try {
      const neu = await anfrage<Beobachtung[]>("/beobachten");
      const text = JSON.stringify(neu);
      if (text !== zuletzt.current) {zuletzt.current = text; setListe(neu);}
      setFehler("");
    }
    catch (e) {setFehler(e instanceof Error ? e.message : "Liste nicht erreichbar");}
    finally {setLaedt(false);}
  };

  useEffect(() => {
    void laden();
    const takt = setInterval(() => void laden(), 15000);
    return () => clearInterval(takt);
  }, []);

  const handeln = async (name: string, fn: () => Promise<unknown>) => {
    setBusy(name);
    setFehler("");
    try {await fn(); await laden();}
    catch (e) {setFehler(e instanceof Error ? e.message : "Das hat nicht geklappt.");}
    finally {setBusy("");}
  };

  const anlegen = () => handeln("neu", async () => {
    await anfrage("/beobachten", "POST", { frage: frage.trim(), bedingung: bedingung.trim(), intervall_stunden: intervall });
    setFrage("");
    setBedingung("");
  });

  const aktiv = liste.filter(b => b.status === "aktiv").length;
  return <div className="bo bo-seite">
    <div className="bo-kopf">
      <span className="bo-icon"><Eye size={18} /></span>
      <div>
        <strong>Beobachten</strong>
        <p>Jon prüft regelmäßig im Internet, ob etwas eingetreten ist, und meldet sich hier und über Telegram. Sag im Chat einfach: „Erinnere mich, wenn das Tiiny AI Pocket Lab rauskommt.“</p>
      </div>
    </div>
    <div className="bo-spalten">
      <div className="bo-links">
        <form className="bo-neu bo-karte" onSubmit={e => {e.preventDefault(); if (frage.trim().length >= 3) void anlegen();}}>
          <span className="bo-feld-titel">Neue Beobachtung</span>
          <input aria-label="Was soll Jon beobachten?" placeholder="Was soll Jon beobachten? z. B. Tiiny AI Pocket Lab Release" value={frage} maxLength={300} onChange={e => setFrage(e.target.value)} />
          <input aria-label="Wann ist es so weit?" placeholder="Wann ist es so weit? (optional) z. B. offiziell erhältlich" value={bedingung} maxLength={500} onChange={e => setBedingung(e.target.value)} />
          <div className="bo-zeile">
            <label>Prüfen alle<select value={intervall} onChange={e => setIntervall(Number(e.target.value))}>{[6, 12, 24, 48, 168].map(h => <option key={h} value={h}>{h === 168 ? "7 Tage" : h + " Stunden"}</option>)}</select></label>
            <button type="submit" disabled={busy === "neu" || frage.trim().length < 3}>{busy === "neu" ? <Loader2 size={14} className="bo-dreh" /> : <Plus size={14} />}Beobachten</button>
          </div>
        </form>
        <p className="bo-hinweis"><RotateCw size={12} />Jon prüft nur, solange er läuft, auf deinem PC oder deinem Pi.</p>
        {fehler && <div className="bo-fehler bo-ein" role="alert"><TriangleAlert size={14} />{fehler}</div>}
      </div>
      <div className="bo-rechts">
        <div className="bo-abschnitt"><span>Deine Beobachtungen</span>{liste.length > 0 && <em>{aktiv} aktiv</em>}</div>
        {laedt && <p className="bo-leer"><Loader2 size={14} className="bo-dreh" />Lädt …</p>}
        {!laedt && !liste.length && <div className="bo-leer-karte">
          <span className="bo-leer-icon"><Eye size={20} /></span>
          <strong>Noch nichts beobachtet</strong>
          <p>Zum Beispiel:</p>
          <div className="bo-beispiele">{BEISPIELE.map(text => <button key={text} type="button" onClick={() => setFrage(text)}>{text}</button>)}</div>
        </div>}
        <div className="bo-liste">
          {liste.map((b, i) => <article key={b.id} className={"bo-eintrag bo-" + b.status} style={{ ["--i" as string]: i }}>
            <div className="bo-eintrag-kopf">
              <span className="bo-punkt" />
              <strong title={b.bedingung}>{b.frage}</strong>
              <span className="bo-status">{b.status === "erfuellt" ? <BellRing size={12} /> : b.status === "aktiv" ? <Eye size={12} /> : <Square size={11} />}{STATUS[b.status]}</span>
            </div>
            <small className="bo-meta">{b.bedingung !== b.frage ? `Wenn: ${b.bedingung} · ` : ""}alle {b.intervall_stunden >= 168 ? `${Math.round(b.intervall_stunden / 24)} Tage` : `${b.intervall_stunden} Std.`} · {wann(b.letzter_check)}</small>
            {b.letzter_fehler && b.status === "aktiv" && <small className="bo-warn"><TriangleAlert size={11} />Letzter Versuch: {b.letzter_fehler}. Jon versucht es beim nächsten Intervall erneut.</small>}
            {b.treffer && <div className="bo-treffer"><Check size={14} /><div><p>{b.treffer.beweis}</p><a href={b.treffer.quelle} target="_blank" rel="noreferrer">{b.treffer.titel || b.treffer.quelle}<ExternalLink size={11} /></a></div></div>}
            <div className="bo-knoepfe">
              {b.status === "aktiv" && <button disabled={!!busy} onClick={() => void handeln("p" + b.id, () => anfrage(`/beobachten/${b.id}/pruefen`, "POST"))}>{busy === "p" + b.id ? <Loader2 size={12} className="bo-dreh" /> : <RotateCw size={12} />}Jetzt prüfen</button>}
              {b.status === "aktiv" && <button disabled={!!busy} onClick={() => void handeln("s" + b.id, () => anfrage(`/beobachten/${b.id}/stoppen`, "POST"))}><Square size={11} />Stoppen</button>}
              <button className="bo-weg" disabled={!!busy} aria-label="Beobachtung löschen" onClick={() => void handeln("l" + b.id, () => anfrage(`/beobachten/${b.id}`, "DELETE"))}><Trash2 size={12} /></button>
            </div>
          </article>)}
        </div>
      </div>
    </div>
  </div>;
}
