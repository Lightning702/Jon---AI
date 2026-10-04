import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Ban, Check, Copy, KeyRound, Loader2, Monitor, Plus, RotateCcw, ShieldCheck, Wrench } from "lucide-react";
import { EntwicklerCode, premiumAnfrage } from "../lib/premium";

const GERAETE = [1, 2, 3, 5, 10];

function wann(sekunden: number) {
  if (!sekunden) return "";
  return new Date(sekunden * 1000).toLocaleDateString("de-AT", { day: "2-digit", month: "short", year: "numeric" });
}

export default function EntwicklerCodes({ onFehler }: { onFehler: (text: string) => void }) {
  const [codes, setCodes] = useState<EntwicklerCode[] | null>(null);
  const [name, setName] = useState("");
  const [geraete, setGeraete] = useState(3);
  const [neu, setNeu] = useState("");
  const [kopiert, setKopiert] = useState(false);
  const [busy, setBusy] = useState("");

  const laden = async () => {
    try {
      setCodes((await premiumAnfrage<{ codes: EntwicklerCode[] }>("/premium/codes")).codes);
    } catch (e) {
      setCodes([]);
      onFehler(e instanceof Error ? e.message : "Die Codes konnten nicht geladen werden.");
    }
  };

  useEffect(() => {void laden();}, []);

  const handeln = async (art: string, fn: () => Promise<void>) => {
    setBusy(art);
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
    const antwort = await premiumAnfrage<{ code: string; codes: EntwicklerCode[] }>("/premium/codes", { name: name.trim(), geraete });
    setNeu(antwort.code);
    setCodes(antwort.codes);
    setName("");
    setKopiert(false);
  });

  const sperren = (code: EntwicklerCode) => handeln(code.id, async () => {
    setCodes((await premiumAnfrage<{ codes: EntwicklerCode[] }>("/premium/codes/sperren", { id: code.id, gesperrt: !code.gesperrt })).codes);
  });

  const kopieren = () => void navigator.clipboard?.writeText(neu).then(() => {setKopiert(true); setTimeout(() => setKopiert(false), 2200);});
  const aktiv = (codes || []).filter(c => !c.gesperrt).length;

  return <section className="pm-block pm-codes pm-ein" aria-label="Entwickler-Codes">
    <div className="pm-codes-kopf">
      <span className="pm-codes-icon"><Wrench size={17} /></span>
      <div>
        <h3>Entwickler-Codes</h3>
        <p>Wer einen Code einlöst, bekommt alles unbegrenzt wie du und heißt in Jon „Entwickler“. Neue Codes erzeugen kann nur der Admin.</p>
      </div>
      {codes && <span className="pm-codes-zahl"><b>{aktiv}</b> aktiv</span>}
    </div>

    <form className="pm-codes-neu" onSubmit={e => {e.preventDefault(); if (!busy) void erzeugen();}}>
      <input aria-label="Für wen ist der Code?" placeholder="Für wen? z. B. Anna oder Testgerät" value={name} maxLength={60} onChange={e => setName(e.target.value)} />
      <label className="pm-codes-geraete" title="Auf wie vielen Geräten der Code funktioniert">
        <Monitor size={13} />
        <select aria-label="Geräte pro Code" value={geraete} onChange={e => setGeraete(Number(e.target.value))}>{GERAETE.map(n => <option key={n} value={n}>{n} {n === 1 ? "Gerät" : "Geräte"}</option>)}</select>
      </label>
      <button type="submit" className="pm-codes-erzeugen" disabled={!!busy}>{busy === "neu" ? <Loader2 size={14} className="pm-dreh" /> : <Plus size={14} />}Code erzeugen</button>
    </form>

    <AnimatePresence>{neu && <motion.div className="pm-neuer-code" initial={{ opacity: 0, y: 8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.22 }}>
      <span className="pm-etikett">Neuer Code · wird nur jetzt angezeigt</span>
      <div className="pm-neuer-code-zeile">
        <code>{neu}</code>
        <button type="button" onClick={kopieren}>{kopiert ? <Check size={14} /> : <Copy size={14} />}{kopiert ? "Kopiert" : "Kopieren"}</button>
      </div>
      <small>In Jon oben links auf „Standard“ klicken, „Lizenz oder Code eingeben“ und einfügen. Gespeichert wird nur ein Fingerabdruck auf deinem Pi, nicht der Code selbst.</small>
      <button type="button" className="pm-neuer-code-zu" onClick={() => setNeu("")}>Fertig</button>
    </motion.div>}</AnimatePresence>

    <div className="pm-codes-liste">
      {codes === null && <div className="pm-codes-leer"><Loader2 size={14} className="pm-dreh" />Lade Codes vom Pi …</div>}
      {codes && !codes.length && <div className="pm-codes-leer"><KeyRound size={14} />Noch keine Entwickler-Codes.</div>}
      {codes?.map((c, i) => <div key={c.id} className={"pm-code " + (c.gesperrt ? "gesperrt" : "")} style={{ ["--i" as string]: i }}>
        <span className="pm-code-punkt" />
        <span className="pm-code-text">
          <b>{c.name || "Ohne Namen"}</b>
          <small>{c.ende ? `endet auf ${c.ende} · ` : ""}{c.geraete}/{c.max_geraete} {c.max_geraete === 1 ? "Gerät" : "Geräte"} · seit {wann(c.erstellt)}{c.zuletzt ? ` · zuletzt ${wann(c.zuletzt)}` : " · noch nicht benutzt"}</small>
        </span>
        <span className={"pm-code-status " + (c.gesperrt ? "aus" : "an")}>{c.gesperrt ? "Gesperrt" : "Aktiv"}</span>
        <button type="button" className="pm-code-knopf" disabled={!!busy} onClick={() => void sperren(c)} title={c.gesperrt ? "Wieder freigeben" : "Sperren: Jon fällt dort spätestens nach 14 Tagen auf Standard zurück"}>{busy === c.id ? <Loader2 size={13} className="pm-dreh" /> : c.gesperrt ? <RotateCcw size={13} /> : <Ban size={13} />}{c.gesperrt ? "Freigeben" : "Sperren"}</button>
      </div>)}
    </div>
    <p className="pm-klein pm-codes-fuss"><ShieldCheck size={12} />Codes prüft dein FelWorks-Codeserver auf dem Raspberry Pi. Er speichert nur Fingerabdrücke und stellt signierte Lizenzen für einzelne Geräte aus.</p>
  </section>;
}
