import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Clapperboard, CloudDownload, CloudUpload, Code2, Copy, Crown, ExternalLink, Flame, Gamepad2, Gem, Globe, GraduationCap, HeartHandshake, KeyRound, Loader2, Lock, Mic, Palette, ScanEye, ShieldCheck, Smartphone, Sparkles, Users, Workflow, X } from "lucide-react";
import { istPremium, premiumAnfrage, PremiumAnlass, PremiumStatus } from "../lib/premium";
import "./premium.css";

const ICONS: Record<string, typeof Code2> = { harness: Code2, fachteam: Users, funke: Flame, fernsteuerung: Smartphone, recherche: GraduationCap, studio: Clapperboard, stimmen: Mic, bildschirm: ScanEye, browser: Globe, aussehen: Palette, familie: HeartHandshake, sync: CloudUpload, automatik: Workflow, spiele: Gamepad2 };
const KOPF: Record<string, { titel: string; text: string; icon: typeof Code2 }> = {
  standard: { titel: "Jon Standard", text: "Kostenlos: Chat mit deinen Modellen, Werkzeuge, Gedächtnis, Kalender und MiniJon. Mit Premium schaltest du alles frei.", icon: Sparkles },
  premium: { titel: "Jon Premium", text: "Alle Premium-Funktionen sind freigeschaltet. Danke, dass du Jon unterstützt!", icon: Gem },
  admin: { titel: "Admin", text: "Alles ist unbegrenzt freigeschaltet. Deine Admin-Lizenz ist signiert und an dieses Gerät gebunden.", icon: Crown },
};

function datum(sekunden: number) {
  return sekunden ? new Date(sekunden * 1000).toLocaleDateString("de-AT", { day: "2-digit", month: "long", year: "numeric" }) : "";
}

export default function PremiumDialog({ status, anlass, onClose }: { status: PremiumStatus | null; anlass: PremiumAnlass | null; onClose: () => void }) {
  const [plan, setPlan] = useState("jahr");
  const [busy, setBusy] = useState("");
  const [fehler, setFehler] = useState("");
  const [meldung, setMeldung] = useState("");
  const [warten, setWarten] = useState(false);
  const [mehr, setMehr] = useState(false);
  const [token, setToken] = useState("");
  const [passwort, setPasswort] = useState("");
  const [syncPasswort, setSyncPasswort] = useState("");
  const [sync, setSync] = useState<{ zeit: number; verfuegbar?: boolean } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const stufe = status?.stufe || "standard";
  const kopf = KOPF[stufe];
  const premium = istPremium(status);
  const anlassFeature = status?.features.find(f => f.key === anlass?.feature);

  useEffect(() => {
    const taste = (e: KeyboardEvent) => {if (e.key === "Escape") onClose();};
    window.addEventListener("keydown", taste);
    return () => {window.removeEventListener("keydown", taste); clearTimeout(timer.current);};
  }, [onClose]);

  useEffect(() => {
    if (premium) void premiumAnfrage<{ zeit: number; verfuegbar: boolean }>("/premium/sync").then(setSync).catch(() => setSync(null));
  }, [premium]);

  const handeln = async (name: string, fn: () => Promise<unknown>, erfolg = "") => {
    setBusy(name);
    setFehler("");
    setMeldung("");
    try {
      await fn();
      if (erfolg) setMeldung(erfolg);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Das hat nicht geklappt.");
    } finally {
      setBusy("");
    }
  };

  const abholen = (versuche: number) => {
    timer.current = setTimeout(async () => {
      try {
        const antwort = await premiumAnfrage<{ fertig: boolean }>("/premium/abholen", {});
        if (antwort.fertig) {setWarten(false); setMeldung("Willkommen bei Jon Premium! Alles ist freigeschaltet."); return;}
      } catch (e) {
        setFehler(e instanceof Error ? e.message : "Verbindung zum Lizenzserver unterbrochen.");
      }
      if (versuche < 400) abholen(versuche + 1);
      else setWarten(false);
    }, 3000);
  };

  const kaufen = () => handeln("kaufen", async () => {
    const { url } = await premiumAnfrage<{ url: string }>("/premium/kaufen", { plan });
    window.open(url, "_blank");
    setWarten(true);
    abholen(0);
  });

  const oeffnen = (pfad: string) => handeln(pfad, async () => {
    const { url } = await premiumAnfrage<{ url: string }>(pfad, {});
    window.open(url, "_blank");
  });

  return createPortal(<motion.div className="pm-schleier" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={e => {if (e.target === e.currentTarget) onClose();}}>
    <motion.div role="dialog" aria-modal="true" aria-label="Jon Premium" className={"pm-fenster pm-" + stufe} initial={{ opacity: 0, y: 18, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12, scale: 0.98 }} transition={{ type: "spring", stiffness: 260, damping: 26 }}>
      <button className="pm-zu" aria-label="Schließen" onClick={onClose}><X size={18} /></button>
      <header className="pm-kopf">
        <div className="pm-emblem"><kopf.icon size={30} /><span className="pm-ring" /></div>
        <div>
          <span className="pm-etikett">Deine Stufe</span>
          <h2>{kopf.titel}</h2>
          <p>{kopf.text}</p>
          {premium && <small>{status?.inhaber ? status.inhaber + " · " : ""}{status?.gueltig_bis ? "gültig bis " + datum(status.gueltig_bis) + (status.abo ? ", verlängert sich automatisch" : "") : "unbegrenzt"}</small>}
        </div>
      </header>
      <AnimatePresence>{anlass?.feature && !premium && <motion.div className="pm-anlass" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}><Lock size={15} /><span>{anlass.text || `${anlassFeature?.name || "Diese Funktion"} gibt es mit Jon Premium.`}</span></motion.div>}</AnimatePresence>
      {status?.hinweis && <div className="pm-hinweis">{status.hinweis}</div>}
      <AnimatePresence>{fehler && <motion.div className="pm-fehler" role="alert" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>{fehler}</motion.div>}</AnimatePresence>
      <AnimatePresence>{meldung && <motion.div className="pm-ok" role="status" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><Check size={15} />{meldung}</motion.div>}</AnimatePresence>
      {!premium && <section className="pm-plaene">
        {status?.plaene.map(p => <button key={p.key} className={"pm-plan " + (plan === p.key ? "an" : "")} onClick={() => setPlan(p.key)} aria-pressed={plan === p.key}>
          {p.hinweis && <em>{p.hinweis}</em>}
          <span>{p.name}</span>
          <strong>{p.preis}</strong>
          <small>{p.zeitraum} · inkl. MwSt.</small>
        </button>)}
        <button className="pm-kaufen" disabled={!!busy || warten} onClick={() => void kaufen()}>{warten || busy === "kaufen" ? <Loader2 size={17} className="pm-dreh" /> : <Gem size={17} />}{warten ? "Warte auf deine Zahlung …" : "Premium holen"}</button>
        {warten && <p className="pm-klein">Stripe ist in deinem Browser geöffnet. Sobald die Zahlung durch ist, schaltet sich Jon hier von selbst frei. <button onClick={() => {clearTimeout(timer.current); setWarten(false);}}>Abbrechen</button></p>}
      </section>}
      <section className="pm-features">
        {status?.features.map((f, i) => {
          const Icon = ICONS[f.key] || Sparkles;
          return <motion.div key={f.key} className={"pm-feature " + (f.frei ? "frei " : "") + (anlass?.feature === f.key ? "markiert" : "")} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.02 * i }}>
            <span className="pm-feature-icon"><Icon size={16} /></span>
            <span className="pm-feature-text"><b>{f.name}</b><small>{f.beschreibung}</small>{!f.frei && f.kontingent > 0 && <small className="pm-kontingent">Kostenlos: {f.kontingent} pro Tag · heute {Math.min(f.verbraucht, f.kontingent)} genutzt</small>}</span>
            {f.frei ? <Check size={15} className="pm-check" /> : <Lock size={14} className="pm-schloss" />}
          </motion.div>;
        })}
      </section>
      {premium && <section className="pm-block">
        <h3><CloudUpload size={15} />Cloud-Sync</h3>
        <p className="pm-klein">Gedächtnis, Persona und Einstellungen werden auf diesem Gerät mit deinem Sicherungspasswort verschlüsselt. FelWorks kann sie nicht lesen. {sync?.zeit ? "Letzte Sicherung: " + new Date(sync.zeit * 1000).toLocaleString("de-AT") : "Noch keine Sicherung in der Cloud."}</p>
        <div className="pm-zeile">
          <input type="password" placeholder="Sicherungspasswort (mind. 8 Zeichen)" aria-label="Sicherungspasswort" value={syncPasswort} onChange={e => setSyncPasswort(e.target.value)} />
          <button disabled={!!busy || syncPasswort.length < 8} onClick={() => void handeln("hoch", async () => {setSync(await premiumAnfrage("/premium/sync/hochladen", { passwort: syncPasswort }));}, "Gesichert. Auf einem anderen Gerät holst du alles mit demselben Passwort zurück.")}>{busy === "hoch" ? <Loader2 size={14} className="pm-dreh" /> : <CloudUpload size={14} />}Sichern</button>
          <button disabled={!!busy || syncPasswort.length < 8 || !sync?.zeit} onClick={() => void handeln("runter", async () => {const r = await premiumAnfrage<{ erinnerungen: number }>("/premium/sync/holen", { passwort: syncPasswort }); setMeldung(`Wiederhergestellt: ${r.erinnerungen} neue Erinnerungen und deine Einstellungen.`);})}>{busy === "runter" ? <Loader2 size={14} className="pm-dreh" /> : <CloudDownload size={14} />}Holen</button>
        </div>
      </section>}
      <section className="pm-aktionen">
        {stufe === "premium" && <button disabled={!!busy} onClick={() => void oeffnen("/premium/portal")}><ExternalLink size={14} />Abo, Rechnungen & Zahlungsart</button>}
        {premium && status?.token && <button onClick={() => void navigator.clipboard?.writeText(status.token).then(() => setMeldung("Lizenzschlüssel kopiert. Auf einem weiteren Gerät unter „Lizenzschlüssel eingeben“ einfügen (bis zu drei Geräte)."))}><Copy size={14} />Lizenzschlüssel kopieren</button>}
        <button onClick={() => setMehr(v => !v)} aria-expanded={mehr}><KeyRound size={14} />{mehr ? "Weniger" : "Lizenz eingeben oder Admin"}</button>
        {premium && <button className="pm-leise" disabled={!!busy} onClick={() => void handeln("ab", () => premiumAnfrage("/premium/abmelden", {}), "Abgemeldet. Jon läuft jetzt als Standard.")}>Abmelden</button>}
      </section>
      <AnimatePresence>{mehr && <motion.section className="pm-block" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
        <h3><KeyRound size={15} />Lizenzschlüssel eingeben</h3>
        <div className="pm-zeile"><input placeholder="JON1.…" aria-label="Lizenzschlüssel" value={token} onChange={e => setToken(e.target.value.trim())} /><button disabled={!!busy || token.length < 20} onClick={() => void handeln("token", async () => {await premiumAnfrage("/premium/lizenz", { token }); setToken("");}, "Lizenz übernommen.")}>{busy === "token" ? <Loader2 size={14} className="pm-dreh" /> : <Check size={14} />}Übernehmen</button></div>
        <h3><ShieldCheck size={15} />Als Admin anmelden</h3>
        <div className="pm-zeile"><input type="password" placeholder="Admin-Passwort" aria-label="Admin-Passwort" value={passwort} onChange={e => setPasswort(e.target.value)} onKeyDown={e => {if (e.key === "Enter" && passwort) void handeln("admin", async () => {await premiumAnfrage("/premium/admin", { passwort }); setPasswort("");}, "Willkommen, Admin. Alles ist unbegrenzt freigeschaltet.");}} /><button disabled={!!busy || !passwort} onClick={() => void handeln("admin", async () => {await premiumAnfrage("/premium/admin", { passwort }); setPasswort("");}, "Willkommen, Admin. Alles ist unbegrenzt freigeschaltet.")}>{busy === "admin" ? <Loader2 size={14} className="pm-dreh" /> : <Crown size={14} />}Anmelden</button></div>
        <p className="pm-klein">Das Passwort wird nur an den FelWorks-Lizenzserver geschickt, nie gespeichert. Der Server stellt eine signierte Admin-Lizenz für genau dieses Gerät aus. Geräte-ID: <code>{status?.geraet}</code></p>
      </motion.section>}</AnimatePresence>
      <footer className="pm-fuss"><ShieldCheck size={13} />Zahlung, Rechnung und Steuer laufen sicher über Stripe. Jon speichert keine Zahlungsdaten und keinen geheimen Schlüssel.</footer>
    </motion.div>
  </motion.div>, document.body);
}
