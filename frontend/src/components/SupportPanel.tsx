import { useEffect, useState } from "react";
import { Bug, Check, Copy, Gem, HelpCircle, Lightbulb, Loader2, Mail, Send, Sparkles, TriangleAlert } from "lucide-react";
import { BASE } from "../lib/api";
import "./beobachten.css";

const ARTEN = [
  { key: "problem", label: "Problem", icon: TriangleAlert },
  { key: "fehler", label: "Fehler melden", icon: Bug },
  { key: "vorschlag", label: "Vorschlag", icon: Lightbulb },
  { key: "standard", label: "Neue Standard-Funktion", icon: Sparkles },
  { key: "premium", label: "Neue Premium-Funktion", icon: Gem },
  { key: "frage", label: "Frage", icon: HelpCircle },
] as const;
const EMAIL = "felix.heinisch12@gmail.com";

export default function SupportPanel() {
  const [art, setArt] = useState<(typeof ARTEN)[number]["key"]>("problem");
  const [betreff, setBetreff] = useState("");
  const [nachricht, setNachricht] = useState("");
  const [email, setEmail] = useState("");
  const [infos, setInfos] = useState(true);
  const [system, setSystem] = useState<{ version: string; stufe: string; system: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [fehler, setFehler] = useState("");
  const [fertig, setFertig] = useState(false);
  const [kopiert, setKopiert] = useState(false);
  const label = ARTEN.find(a => a.key === art)?.label || "Support";
  const gueltig = betreff.trim().length >= 3 && nachricht.trim().length >= 10 && (!email || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email));

  useEffect(() => {
    void fetch(BASE + "/support").then(r => r.ok ? r.json() : null).then(setSystem).catch(() => setSystem(null));
  }, []);

  const mailto = () => {
    const text = `${nachricht.trim()}\n\n${infos && system ? `Jon ${system.version} · ${system.stufe} · ${system.system}` : ""}`;
    return `mailto:${EMAIL}?subject=${encodeURIComponent(`[Jon · ${label}] ${betreff.trim()}`)}&body=${encodeURIComponent(text)}`;
  };

  const senden = async () => {
    setBusy(true);
    setFehler("");
    try {
      const antwort = await fetch(BASE + "/support", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ art, betreff: betreff.trim(), nachricht: nachricht.trim(), email: email.trim(), infos }) });
      const daten = await antwort.json().catch(() => ({}));
      if (!antwort.ok) throw new Error(typeof daten.detail === "string" ? daten.detail : "Die Nachricht konnte nicht gesendet werden.");
      setFertig(true);
      setBetreff("");
      setNachricht("");
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Die Nachricht konnte nicht gesendet werden.");
    } finally {
      setBusy(false);
    }
  };

  return <div className="bo">
    <div className="bo-kopf">
      <span className="bo-icon"><Mail size={18} /></span>
      <div>
        <strong>Support</strong>
        <p>Probleme, Fehler, Vorschläge oder Ideen für neue Standard- oder Premium-Funktionen gehen direkt an FelWorks: <b className="text-gold/90">{EMAIL}</b></p>
      </div>
    </div>
    {fertig ? <div key="fertig" className="bo-treffer bo-ein" style={{ marginLeft: 0 }}>
        <Check size={16} /><div><p>Danke! Deine Nachricht ist angekommen. Wenn du eine E-Mail angegeben hast, bekommst du dorthin eine Antwort.</p><button className="text-[11.5px] text-emerald-200 underline" onClick={() => setFertig(false)}>Noch eine Nachricht schreiben</button></div>
      </div> : <form key="form" className="bo-neu bo-ein" onSubmit={e => {e.preventDefault(); if (gueltig && !busy) void senden();}}>
        <div className="sp-arten" role="radiogroup" aria-label="Worum geht es?">{ARTEN.map(a => <button type="button" role="radio" aria-checked={art === a.key} key={a.key} className={art === a.key ? "an" : ""} onClick={() => setArt(a.key)}><a.icon size={13} />{a.label}</button>)}</div>
        <input aria-label="Betreff" placeholder="Betreff" value={betreff} maxLength={160} onChange={e => setBetreff(e.target.value)} />
        <textarea className="sp-text" aria-label="Nachricht" placeholder={art === "fehler" ? "Was ist passiert? Was hast du davor gemacht? Was hättest du erwartet?" : art === "premium" || art === "standard" ? "Welche Funktion wünschst du dir und wofür würdest du sie nutzen?" : "Deine Nachricht …"} value={nachricht} maxLength={8000} onChange={e => setNachricht(e.target.value)} />
        <input aria-label="Deine E-Mail für die Antwort" placeholder="Deine E-Mail für die Antwort (optional)" value={email} maxLength={200} onChange={e => setEmail(e.target.value.trim())} />
        <label className="sp-infos"><input type="checkbox" checked={infos} onChange={e => setInfos(e.target.checked)} />Version und System mitsenden{system ? `: Jon ${system.version} · ${system.stufe} · ${system.system}` : ""}</label>
        {fehler && <div className="bo-fehler bo-ein" role="alert"><TriangleAlert size={14} />{fehler}</div>}
        <div className="bo-zeile sp-knoepfe">
          <a className={"sp-mail " + (gueltig ? "" : "aus")} href={gueltig ? mailto() : undefined} aria-disabled={!gueltig}><Mail size={13} />Mit E-Mail-Programm</a>
          <button type="button" className="sp-kopieren" onClick={() => void navigator.clipboard?.writeText(EMAIL).then(() => {setKopiert(true); setTimeout(() => setKopiert(false), 2000);})}>{kopiert ? <Check size={13} /> : <Copy size={13} />}{kopiert ? "Kopiert" : "Adresse kopieren"}</button>
          <button type="submit" disabled={!gueltig || busy}>{busy ? <Loader2 size={14} className="bo-dreh" /> : <Send size={14} />}Senden</button>
        </div>
      </form>}
  </div>;
}
