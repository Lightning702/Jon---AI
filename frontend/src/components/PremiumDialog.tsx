import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion } from "framer-motion";
import { Check, ChevronDown, Clapperboard, CloudDownload, CloudUpload, Code2, Copy, Crown, ExternalLink, Flame, Gamepad2, Gem, Globe, GraduationCap, HeartHandshake, KeyRound, Loader2, Lock, LogOut, Mic, Palette, ScanEye, ShieldCheck, Smartphone, Sparkles, Users, Workflow, Wrench, X } from "lucide-react";
import { istPremium, premiumAnfrage, PremiumAnlass, premiumLaden, PremiumStatus } from "../lib/premium";
import TeamZentrale from "./TeamZentrale";
import "./premium.css";

const ICONS: Record<string, typeof Code2> = { harness: Code2, fachteam: Users, funke: Flame, fernsteuerung: Smartphone, recherche: GraduationCap, studio: Clapperboard, stimmen: Mic, bildschirm: ScanEye, browser: Globe, aussehen: Palette, familie: HeartHandshake, sync: CloudUpload, automatik: Workflow, spiele: Gamepad2 };
const KOPF: Record<string, { titel: string; text: string; icon: typeof Code2 }> = {
  standard: { titel: "Jon Standard", text: "Kostenlos: Chat mit deinen Modellen, Werkzeuge, Gedächtnis, Kalender und MiniJon. Mit Premium schaltest du alles frei.", icon: Sparkles },
  premium: { titel: "Jon Premium", text: "Alle Premium-Funktionen sind freigeschaltet. Danke, dass du Jon unterstützt!", icon: Gem },
  admin: { titel: "Admin", text: "Alles ist unbegrenzt freigeschaltet. In der Team-Zentrale steuerst du Codes, Team, Beta-Schalter, Nutzung und deinen Pi.", icon: Crown },
  entwickler: { titel: "Entwickler", text: "Alles ist unbegrenzt freigeschaltet und gilt für immer. In der Team-Zentrale schreibst du dem Admin, meldest Fehler, teilst Skills und siehst Jon unter die Haube.", icon: Wrench },
};
const SANFT = { duration: 0.2, ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number] };

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
  const [eingabe, setEingabe] = useState("");
  const [syncPasswort, setSyncPasswort] = useState("");
  const [sync, setSync] = useState<{ zeit: number; verfuegbar?: boolean } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const fenster = useRef<HTMLDivElement>(null);
  const inhalt = useRef<HTMLDivElement>(null);
  const mehrBereich = useRef<HTMLElement>(null);
  const stufe = status?.stufe || "standard";
  const kopf = KOPF[stufe];
  const premium = istPremium(status);
  const anlassFeature = status?.features.find(f => f.key === anlass?.feature);
  const gewaehlt = status?.plaene.find(p => p.key === plan);

  useEffect(() => {
    const taste = (e: KeyboardEvent) => {if (e.key === "Escape") onClose();};
    window.addEventListener("keydown", taste);
    return () => {window.removeEventListener("keydown", taste); clearTimeout(timer.current);};
  }, [onClose]);

  useEffect(() => {
    const el = inhalt.current;
    const rahmen = fenster.current;
    if (!el || !rahmen) return;
    let bild = 0;
    const messen = () => {
      bild = 0;
      rahmen.dataset.oben = el.scrollTop > 2 ? "1" : "";
      rahmen.dataset.unten = el.scrollTop + el.clientHeight < el.scrollHeight - 2 ? "1" : "";
    };
    const planen = () => {if (!bild) bild = requestAnimationFrame(messen);};
    messen();
    el.addEventListener("scroll", planen, { passive: true });
    const beobachter = new ResizeObserver(planen);
    beobachter.observe(el);
    return () => {el.removeEventListener("scroll", planen); beobachter.disconnect(); cancelAnimationFrame(bild);};
  }, []);

  useEffect(() => {
    if (premium) void premiumAnfrage<{ zeit: number; verfuegbar: boolean }>("/premium/sync").then(setSync).catch(() => setSync(null));
  }, [premium]);

  useEffect(() => {
    if (mehr) requestAnimationFrame(() => mehrBereich.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }));
  }, [mehr]);

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

  const einloesen = () => handeln("einloesen", async () => {
    const wert = eingabe.trim();
    const neu = await premiumAnfrage<PremiumStatus>(wert.startsWith("JON1.") ? "/premium/lizenz" : "/premium/code", wert.startsWith("JON1.") ? { token: wert } : { code: wert });
    setEingabe("");
    setMehr(false);
    setMeldung(neu.stufe === "admin" ? "Willkommen, Admin. Alles ist unbegrenzt freigeschaltet, und du kannst jetzt Entwickler-Codes erzeugen." : neu.stufe === "entwickler" ? "Willkommen, Entwickler. Alles ist unbegrenzt freigeschaltet." : "Lizenz übernommen.");
  });

  return createPortal(<motion.div className="pm-schleier" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={SANFT} onMouseDown={e => {if (e.target === e.currentTarget) onClose();}}>
    <motion.div ref={fenster} role="dialog" aria-modal="true" aria-label="Jon Premium" className={"pm-fenster pm-" + stufe + (status?.team ? " pm-team" : "")} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }} transition={SANFT}>
      <header className="pm-kopf">
        <div className="pm-emblem"><kopf.icon size={26} /><span className="pm-ring" /></div>
        <div className="pm-kopf-text">
          <span className="pm-etikett">Deine Stufe</span>
          <h2>{kopf.titel}</h2>
          <p>{kopf.text}</p>
          {premium && <small>{status?.inhaber ? status.inhaber + " · " : ""}{status?.gueltig_bis ? "gültig bis " + datum(status.gueltig_bis) + (status.abo ? ", verlängert sich automatisch" : "") : "unbegrenzt"}</small>}
        </div>
        <button className="pm-zu" aria-label="Schließen" onClick={onClose}><X size={18} /></button>
      </header>

      <div className="pm-inhalt" ref={inhalt}>
        {anlass?.feature && !premium && <div className="pm-anlass pm-ein"><Lock size={15} /><span>{anlass.text || `${anlassFeature?.name || "Diese Funktion"} gibt es mit Jon Premium.`}</span></div>}
        {status?.hinweis && <div className="pm-hinweis pm-ein">{status.hinweis}</div>}
        {fehler && <div className="pm-fehler pm-ein" role="alert">{fehler}</div>}
        {meldung && <div className="pm-ok pm-ein" role="status"><Check size={15} />{meldung}</div>}

        {status?.team ? <TeamZentrale status={status} onFehler={setFehler} onNeuLaden={() => void premiumLaden()} /> : stufe === "admin" && <div className="pm-hinweis pm-ein">Codes erzeugst du mit einer Admin-Lizenz von deinem Pi. Melde dich dafür einmal unten unter „Lizenz oder Code eingeben“ mit dem Admin-Code an.</div>}

        <section className="pm-features" aria-label="Funktionen">
          {status?.features.map((f, i) => {
            const Icon = ICONS[f.key] || Sparkles;
            return <div key={f.key} className={"pm-feature " + (f.frei ? "frei " : "") + (anlass?.feature === f.key ? "markiert" : "")} style={{ ["--i" as string]: i }}>
              <span className="pm-feature-icon"><Icon size={16} /></span>
              <span className="pm-feature-text"><b>{f.name}</b><small>{f.beschreibung}</small>{!f.frei && f.kontingent > 0 && <small className="pm-kontingent">Kostenlos: {f.kontingent} pro Tag · heute {Math.min(f.verbraucht, f.kontingent)} genutzt</small>}</span>
              {f.frei ? <Check size={15} className="pm-check" /> : <Lock size={14} className="pm-schloss" />}
            </div>;
          })}
        </section>

        {premium && <section className="pm-block pm-ein">
          <h3><CloudUpload size={15} />Cloud-Sync</h3>
          <p className="pm-klein">Gedächtnis, Persona und Einstellungen werden auf diesem Gerät mit deinem Sicherungspasswort verschlüsselt. FelWorks kann sie nicht lesen. {sync?.zeit ? "Letzte Sicherung: " + new Date(sync.zeit * 1000).toLocaleString("de-AT") : "Noch keine Sicherung in der Cloud."}</p>
          <div className="pm-zeile">
            <input type="password" placeholder="Sicherungspasswort (mind. 8 Zeichen)" aria-label="Sicherungspasswort" value={syncPasswort} onChange={e => setSyncPasswort(e.target.value)} />
            <button disabled={!!busy || syncPasswort.length < 8} onClick={() => void handeln("hoch", async () => {setSync(await premiumAnfrage("/premium/sync/hochladen", { passwort: syncPasswort }));}, "Gesichert. Auf einem anderen Gerät holst du alles mit demselben Passwort zurück.")}>{busy === "hoch" ? <Loader2 size={14} className="pm-dreh" /> : <CloudUpload size={14} />}Sichern</button>
            <button disabled={!!busy || syncPasswort.length < 8 || !sync?.zeit} onClick={() => void handeln("runter", async () => {const r = await premiumAnfrage<{ erinnerungen: number }>("/premium/sync/holen", { passwort: syncPasswort }); setMeldung(`Wiederhergestellt: ${r.erinnerungen} neue Erinnerungen und deine Einstellungen.`);})}>{busy === "runter" ? <Loader2 size={14} className="pm-dreh" /> : <CloudDownload size={14} />}Holen</button>
          </div>
        </section>}

        <button className={"pm-mehr " + (mehr ? "offen" : "")} onClick={() => setMehr(v => !v)} aria-expanded={mehr}><KeyRound size={14} />{premium ? "Lizenz oder Code eingeben" : "Schon einen Lizenzschlüssel, Entwickler- oder Admin-Code?"}<ChevronDown size={14} className="pm-pfeil" /></button>
        {mehr && <section className="pm-block pm-ein" ref={mehrBereich}>
          <h3><KeyRound size={15} />Lizenz oder Code eingeben</h3>
          <form className="pm-zeile" onSubmit={e => {e.preventDefault(); if (eingabe.trim().length >= 8 && !busy) void einloesen();}}>
            <input type="password" autoComplete="off" spellCheck={false} placeholder="JON1.… · ENT-… · Admin-Code" aria-label="Lizenzschlüssel, Entwickler- oder Admin-Code" value={eingabe} onChange={e => setEingabe(e.target.value)} />
            <button type="submit" disabled={!!busy || eingabe.trim().length < 8}>{busy === "einloesen" ? <Loader2 size={14} className="pm-dreh" /> : <Check size={14} />}Einlösen</button>
          </form>
          <p className="pm-klein">Lizenzschlüssel prüft Jon selbst. Entwickler- und Admin-Codes prüft der FelWorks-Codeserver. Er stellt eine signierte Lizenz für genau dieses Gerät aus, der Code selbst wird nicht gespeichert. Geräte-ID: <code>{status?.geraet}</code></p>
        </section>}

        <p className="pm-fuss"><ShieldCheck size={13} />Zahlung, Rechnung und Steuer laufen sicher über Stripe. Jon speichert keine Zahlungsdaten und keinen geheimen Schlüssel.</p>
      </div>

      <footer className="pm-leiste">
        {!premium ? <>
          <div className="pm-tarife" role="radiogroup" aria-label="Tarif">
            {status?.plaene.map(p => <button key={p.key} role="radio" aria-checked={plan === p.key} className={plan === p.key ? "an" : ""} onClick={() => setPlan(p.key)} disabled={warten}>
              <span className="pm-tarif-text"><span>{p.name}</span><b>{p.preis}</b></span>
              {p.hinweis && <em>{p.hinweis}</em>}
            </button>)}
          </div>
          <button className="pm-kaufen" disabled={!!busy || warten} onClick={() => void kaufen()}>{warten || busy === "kaufen" ? <Loader2 size={17} className="pm-dreh" /> : <Gem size={17} />}{warten ? "Warte auf Zahlung …" : "Premium holen"}</button>
          <p className="pm-leiste-text">{warten ? <>Stripe ist im Browser geöffnet. Nach der Zahlung schaltet sich Jon von selbst frei. <button onClick={() => {clearTimeout(timer.current); setWarten(false);}}>Abbrechen</button></> : <>{gewaehlt ? `${gewaehlt.preis} ${gewaehlt.zeitraum}` : ""} inkl. MwSt. · jederzeit kündbar</>}</p>
        </> : <div className="pm-aktionen">
          {stufe === "premium" && <button disabled={!!busy} onClick={() => void oeffnen("/premium/portal")}>{busy === "/premium/portal" ? <Loader2 size={14} className="pm-dreh" /> : <ExternalLink size={14} />}Abo, Rechnungen & Zahlungsart</button>}
          {status?.token && status.abo && <button onClick={() => void navigator.clipboard?.writeText(status.token).then(() => setMeldung("Lizenzschlüssel kopiert. Auf einem weiteren Gerät unter „Lizenz eingeben“ einfügen (bis zu drei Geräte)."))}><Copy size={14} />Lizenzschlüssel kopieren</button>}
          <button className="pm-leise" disabled={!!busy} onClick={() => void handeln("ab", () => premiumAnfrage("/premium/abmelden", {}), "Abgemeldet. Jon läuft jetzt als Standard.")}><LogOut size={14} />Abmelden</button>
        </div>}
      </footer>
    </motion.div>
  </motion.div>, document.body);
}
