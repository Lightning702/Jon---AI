import {useEffect, useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {Check, Crown, Gem, Lock, Sparkles} from "lucide-react";
import {api} from "./bridge";
import {Sheet} from "./ui";
import "./premium.css";

export interface MobilPremium {
  stufe: "standard" | "premium" | "admin";
  name: string;
  features: {key: string; name: string; beschreibung: string; frei: boolean}[];
}

let stand: MobilPremium | null = null;

export function useMobilPremium() {
  const [wert, setWert] = useState<MobilPremium | null>(stand);
  useEffect(() => {
    let aktiv = true;
    api<MobilPremium>("/api/premium").then(daten => {
      if (aktiv && daten?.stufe) {stand = daten; setWert(daten);}
    }).catch(() => {});
    return () => {aktiv = false;};
  }, []);
  return wert;
}

const ICON = {standard: Sparkles, premium: Gem, admin: Crown};

export function PremiumMarke() {
  const status = useMobilPremium();
  const [offen, setOffen] = useState(false);
  if (!status) return null;
  const Icon = ICON[status.stufe] || Sparkles;
  return <>
    <button className={`pm-marke pm-marke-${status.stufe}`} onClick={() => setOffen(true)} aria-label={`Stufe: ${status.name}`}><Icon size={12}/>{status.name}</button>
    <Sheet open={offen} title={status.stufe === "standard" ? "Jon Standard" : status.stufe === "admin" ? "Admin · alles unbegrenzt" : "Jon Premium ist aktiv"} onClose={() => setOffen(false)}>
      <PremiumListe status={status}/>
    </Sheet>
  </>;
}

export function PremiumListe({status}: {status: MobilPremium}) {
  return <div className="pm-mobil">
    {status.stufe === "standard" && <p className="pm-mobil-text">Premium schaltest du in Jon am PC frei: oben links neben „JON“ auf „Standard“ tippen. Danach gilt alles automatisch auch hier am Handy.</p>}
    <div className="pm-mobil-liste">{status.features.map(f => <div key={f.key} className={f.frei ? "frei" : ""}>
      {f.frei ? <Check size={15}/> : <Lock size={14}/>}<span><b>{f.name}</b><small>{f.beschreibung}</small></span>
    </div>)}</div>
  </div>;
}

export function FunkeGesperrt({status}: {status: MobilPremium}) {
  return <AnimatePresence><motion.section className="pm-funke" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}}>
    <div className="pm-funke-icon"><Lock size={22}/></div>
    <h2>Funke gibt es mit Jon Premium</h2>
    <p>Funke übernimmt am Handy ganze Aufgaben mit Jons vollem Modell und allen Werkzeugen, auch über allen Apps. Der normale Jon-Chat bleibt kostenlos.</p>
    <PremiumListe status={status}/>
  </motion.section></AnimatePresence>;
}
