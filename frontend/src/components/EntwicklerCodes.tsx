import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Ban, Check, ChevronDown, Copy, Crown, Gem, KeyRound, Loader2, Monitor, Pencil, Plus, RotateCcw, ShieldCheck, Trash2, Wrench, X } from "lucide-react";
import { CodeArt, EntwicklerCode, teamAnfrage } from "../lib/premium";

const GERAETE = [1, 2, 3, 5, 10, 25];
const LAUFZEITEN = [{ tage: 7, text: "7 Tage" }, { tage: 30, text: "30 Tage" }, { tage: 90, text: "3 Monate" }, { tage: 365, text: "1 Jahr" }, { tage: 0, text: "Für immer" }];
const ARTEN: { key: CodeArt; name: string; text: string; icon: typeof Wrench }[] = [
  { key: "entwickler", name: "Entwickler", text: "Alles unbegrenzt, Team-Zentrale, keine Codes", icon: Wrench },
  { key: "premium", name: "Premium", text: "Alle Premium-Funktionen, mit Laufzeit", icon: Gem },
  { key: "admin", name: "Admin", text: "Volle Rechte wie du, auch Codes erzeugen", icon: Crown },
];

function wann(sekunden?: number) {
  if (!sekunden) return "";
  return new Date(sekunden * 1000).toLocaleDateString("de-AT", { day: "2-digit", month: "short", year: "numeric" });
}

function laufzeit(tage: number) {
  return LAUFZEITEN.find(l => l.tage === tage)?.text || `${tage} Tage`;
}

export default function EntwicklerCodes({ onFehler }: { onFehler: (text: string) => void }) {
  const [codes, setCodes] = useState<EntwicklerCode[] | null>(null);
  const [art, setArt] = useState<CodeArt>("entwickler");
  const [name, setName] = useState("");
  const [geraete, setGeraete] = useState(3);
  const [tage, setTage] = useState(30);
  const [neu, setNeu] = useState<{ code: string; art: CodeArt } | null>(null);
  const [kopiert, setKopiert] = useState(false);
  const [busy, setBusy] = useState("");
  const [offen, setOffen] = useState("");
  const [umbenennen, setUmbenennen] = useState<{ id: string; name: string } | null>(null);
  const [filter, setFilter] = useState<"alle" | CodeArt>("alle");

  const laden = async () => {
    try {
      setCodes((await teamAnfrage<{ codes: EntwicklerCode[] }>("liste")).codes);
    } catch (e) {
      setCodes([]);
      onFehler(e instanceof Error ? e.message : "Die Codes konnten nicht geladen werden.");
    }
  };

  useEffect(() => {void laden();}, []);

  const handeln = async (kennung: string, fn: () => Promise<void>) => {
    setBusy(kennung);
    onFehler("");
    try {
      await fn();
    } catch (e) {
      onFehler(e instanceof Error ? e.message : "Das hat nicht geklappt.");
    } finally {
      setBusy("");
    }
  };

  const erzeugen = () => handeln("neu", async () => {
    const antwort = await teamAnfrage<{ code: string; codes: EntwicklerCode[] }>("erstellen", { name: name.trim(), geraete, art, tage: art === "premium" ? tage : 0 });
    setNeu({ code: antwort.code, art });
    setCodes(antwort.codes);
    setName("");
    setKopiert(false);
  });

  const aendern = (aktion: string, daten: Record<string, unknown>, kennung: string) => handeln(kennung, async () => {
    setCodes((await teamAnfrage<{ codes: EntwicklerCode[] }>(aktion, daten)).codes);
  });

  const kopieren = () => neu && void navigator.clipboard?.writeText(neu.code).then(() => {setKopiert(true); setTimeout(() => setKopiert(false), 2200);});
  const sichtbar = (codes || []).filter(c => filter === "alle" || c.art === filter);
  const aktiv = (codes || []).filter(c => !c.gesperrt).length;
  const gewaehlt = ARTEN.find(a => a.key === art)!;

  return <div className="tz-codes">
    <div className="tz-abschnitt-kopf">
      <div><h4>Codes erzeugen</h4><p>Wähle, was der Code freischaltet. Jeder Code wird genau einmal angezeigt und lässt sich jederzeit sperren.</p></div>
      {codes && <span className="tz-zahl"><b>{aktiv}</b> aktiv</span>}
    </div>

    <div className="tz-arten" role="radiogroup" aria-label="Code-Art">
      {ARTEN.map(a => <button key={a.key} type="button" role="radio" aria-checked={art === a.key} className={"tz-art tz-art-" + a.key + (art === a.key ? " an" : "")} onClick={() => setArt(a.key)}>
        <span className="tz-art-icon"><a.icon size={15} /></span>
        <span><b>{a.name}</b><small>{a.text}</small></span>
      </button>)}
    </div>

    <form className="tz-codes-neu" onSubmit={e => {e.preventDefault(); if (!busy) void erzeugen();}}>
      <input aria-label="Für wen ist der Code?" placeholder={art === "premium" ? "Für wen? z. B. Gewinnspiel Oktober" : "Für wen? z. B. Anna oder Testgerät"} value={name} maxLength={60} onChange={e => setName(e.target.value)} />
      <label className="tz-wahl" title="Auf wie vielen Geräten der Code funktioniert"><Monitor size={13} /><select aria-label="Geräte pro Code" value={geraete} onChange={e => setGeraete(Number(e.target.value))}>{GERAETE.map(n => <option key={n} value={n}>{n} {n === 1 ? "Gerät" : "Geräte"}</option>)}</select></label>
      {art === "premium" && <label className="tz-wahl" title="Wie lange Premium ab dem Einlösen gilt"><Gem size={13} /><select aria-label="Laufzeit" value={tage} onChange={e => setTage(Number(e.target.value))}>{LAUFZEITEN.map(l => <option key={l.tage} value={l.tage}>{l.text}</option>)}</select></label>}
      <button type="submit" className="tz-gold" disabled={!!busy}>{busy === "neu" ? <Loader2 size={14} className="tz-dreh" /> : <Plus size={14} />}{gewaehlt.name}-Code erzeugen</button>
    </form>

    <AnimatePresence>{neu && <motion.div className="tz-neuer-code" initial={{ opacity: 0, y: 8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.22 }}>
      <span className="tz-etikett">Neuer {ARTEN.find(a => a.key === neu.art)?.name}-Code · wird nur jetzt angezeigt</span>
      <div className="tz-neuer-code-zeile">
        <code>{neu.code}</code>
        <button type="button" onClick={kopieren}>{kopiert ? <Check size={14} /> : <Copy size={14} />}{kopiert ? "Kopiert" : "Kopieren"}</button>
      </div>
      <small>In Jon oben links auf die Stufe klicken, „Lizenz oder Code eingeben“ und einfügen. Gespeichert wird nur ein Fingerabdruck auf deinem Pi.</small>
      <button type="button" className="tz-neuer-code-zu" onClick={() => setNeu(null)}>Fertig</button>
    </motion.div>}</AnimatePresence>

    <div className="tz-filter" role="tablist" aria-label="Codes filtern">
      {(["alle", "entwickler", "premium", "admin"] as const).map(f => <button key={f} role="tab" aria-selected={filter === f} className={filter === f ? "an" : ""} onClick={() => setFilter(f)}>{f === "alle" ? "Alle" : ARTEN.find(a => a.key === f)!.name}<em>{f === "alle" ? (codes || []).length : (codes || []).filter(c => c.art === f).length}</em></button>)}
    </div>

    <div className="tz-liste">
      {codes === null && <div className="tz-leer"><Loader2 size={14} className="tz-dreh" />Lade Codes vom Pi …</div>}
      {codes && !sichtbar.length && <div className="tz-leer"><KeyRound size={14} />Noch keine Codes in dieser Auswahl.</div>}
      {sichtbar.map((c, i) => {
        const Icon = ARTEN.find(a => a.key === c.art)?.icon || Wrench;
        return <div key={c.id} className={"tz-code " + (c.gesperrt ? "gesperrt " : "") + (offen === c.id ? "offen" : "")} style={{ ["--i" as string]: i }}>
          <div className="tz-code-zeile">
            <span className={"tz-code-icon tz-art-" + c.art}><Icon size={13} /></span>
            {umbenennen?.id === c.id ? <form className="tz-umbenennen" onSubmit={e => {e.preventDefault(); void aendern("bearbeiten", { id: c.id, name: umbenennen.name }, c.id).then(() => setUmbenennen(null));}}>
              <input autoFocus value={umbenennen.name} maxLength={60} onChange={e => setUmbenennen({ id: c.id, name: e.target.value })} aria-label="Neuer Name" />
              <button type="submit" aria-label="Speichern"><Check size={13} /></button>
              <button type="button" aria-label="Abbrechen" onClick={() => setUmbenennen(null)}><X size={13} /></button>
            </form> : <button type="button" className="tz-code-text" onClick={() => setOffen(o => o === c.id ? "" : c.id)} aria-expanded={offen === c.id}>
              <b>{c.name || "Ohne Namen"}<span className={"tz-marke tz-art-" + c.art}>{ARTEN.find(a => a.key === c.art)?.name}{c.art === "premium" ? " · " + laufzeit(c.tage) : ""}</span></b>
              <small>{c.ende ? `endet auf ${c.ende} · ` : ""}{c.geraete}/{c.max_geraete} {c.max_geraete === 1 ? "Gerät" : "Geräte"} · seit {wann(c.erstellt)}{c.zuletzt ? ` · zuletzt ${wann(c.zuletzt)}` : " · noch nicht benutzt"}</small>
            </button>}
            <span className={"tz-status " + (c.gesperrt ? "aus" : "an")}>{c.gesperrt ? "Gesperrt" : "Aktiv"}</span>
            <button type="button" className="tz-klein" title="Umbenennen" aria-label="Umbenennen" onClick={() => setUmbenennen({ id: c.id, name: c.name })}><Pencil size={12} /></button>
            <button type="button" className="tz-klein tz-gefahr" disabled={!!busy} onClick={() => void aendern("sperren", { id: c.id, gesperrt: !c.gesperrt }, c.id)} title={c.gesperrt ? "Wieder freigeben" : "Sperren: das Gerät fällt bei der nächsten Prüfung auf Standard zurück"}>{busy === c.id ? <Loader2 size={12} className="tz-dreh" /> : c.gesperrt ? <RotateCcw size={12} /> : <Ban size={12} />}{c.gesperrt ? "Freigeben" : "Sperren"}</button>
            <ChevronDown size={14} className="tz-pfeil" onClick={() => setOffen(o => o === c.id ? "" : c.id)} />
          </div>
          <AnimatePresence initial={false}>{offen === c.id && <motion.div className="tz-code-details" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
            <div className="tz-code-optionen">
              <label>Art<select value={c.art} onChange={e => void aendern("bearbeiten", { id: c.id, art: e.target.value }, c.id)}>{ARTEN.map(a => <option key={a.key} value={a.key}>{a.name}</option>)}</select></label>
              {c.art === "premium" && <label>Laufzeit<select value={c.tage} onChange={e => void aendern("bearbeiten", { id: c.id, tage: Number(e.target.value) }, c.id)}>{LAUFZEITEN.map(l => <option key={l.tage} value={l.tage}>{l.text}</option>)}</select></label>}
              <label>Geräte<select value={c.max_geraete} onChange={e => void aendern("bearbeiten", { id: c.id, max_geraete: Number(e.target.value) }, c.id)}>{[...new Set([...GERAETE, c.max_geraete])].sort((a, b) => a - b).map(n => <option key={n} value={n}>{n}</option>)}</select></label>
            </div>
            {!c.geraete_liste.length && <p className="tz-hinweis">Noch auf keinem Gerät eingelöst.</p>}
            {c.geraete_liste.map(g => <div key={g.geraet} className="tz-geraet">
              <Monitor size={13} />
              <span><b>Gerät {g.kurz}</b><small>{g.version ? `Jon ${g.version} · ` : ""}{g.system || "System unbekannt"} · seit {wann(g.seit) || "?"}{g.zuletzt ? ` · zuletzt ${wann(g.zuletzt)}` : ""}{g.ablauf ? ` · Premium bis ${wann(g.ablauf)}` : ""}</small></span>
              <button type="button" className="tz-klein tz-gefahr" disabled={!!busy} title="Gerät entfernen, damit der Platz frei wird" onClick={() => void aendern("geraet-entfernen", { id: c.id, entfernen: g.geraet }, c.id)}><Trash2 size={12} />Entfernen</button>
            </div>)}
          </motion.div>}</AnimatePresence>
        </div>;
      })}
    </div>
    <p className="tz-fuss"><ShieldCheck size={12} />Codes prüft dein FelWorks-Codeserver auf dem Raspberry Pi. Er speichert nur Fingerabdrücke und stellt signierte Lizenzen für einzelne Geräte aus.</p>
  </div>;
}
