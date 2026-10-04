import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Crown, Gem, Sparkles, Wrench } from "lucide-react";
import { premiumLaden, PremiumAnlass, teamAnfrage, usePremium } from "../lib/premium";
import PremiumDialog from "./PremiumDialog";
import "./premium.css";

const ICON = { standard: Sparkles, premium: Gem, admin: Crown, entwickler: Wrench };
const TITEL = { standard: "Jon Standard · Premium ansehen", premium: "Jon Premium ist aktiv", admin: "Admin · alles unbegrenzt · hier erzeugst du Entwickler-Codes", entwickler: "Entwickler · alles unbegrenzt" };

export default function PremiumAbzeichen() {
  const status = usePremium();
  const [offen, setOffen] = useState(false);
  const [anlass, setAnlass] = useState<PremiumAnlass | null>(null);
  const [toast, setToast] = useState<PremiumAnlass | null>(null);
  const eingabe = useRef(0);
  const zuletzt = useRef<Record<string, number>>({});
  const stufe = status?.stufe || "standard";
  const Icon = ICON[stufe];
  const team = !!status?.team;

  useEffect(() => {
    if (!team) return;
    const pruefen = () => {if (!document.hidden) void teamAnfrage("team/ungelesen").then(() => premiumLaden()).catch(() => {});};
    pruefen();
    const takt = setInterval(pruefen, 120000);
    return () => clearInterval(takt);
  }, [team]);

  useEffect(() => {
    const merken = () => {eingabe.current = Date.now();};
    const melden = (e: Event) => {
      const wert = (e as CustomEvent<PremiumAnlass>).detail || { feature: "", text: "" };
      void premiumLaden();
      if (Date.now() - eingabe.current < 5000) {
        setAnlass(wert);
        setOffen(true);
        return;
      }
      if (Date.now() - (zuletzt.current[wert.feature] || 0) < 600000) return;
      zuletzt.current[wert.feature] = Date.now();
      setToast(wert);
      setTimeout(() => setToast(t => t === wert ? null : t), 7000);
    };
    const takt = setInterval(() => void premiumLaden(), 15 * 60000);
    window.addEventListener("pointerdown", merken, true);
    window.addEventListener("keydown", merken, true);
    window.addEventListener("jon-premium", melden);
    return () => {
      clearInterval(takt);
      window.removeEventListener("pointerdown", merken, true);
      window.removeEventListener("keydown", merken, true);
      window.removeEventListener("jon-premium", melden);
    };
  }, []);

  return <>
    <button type="button" className={"no-drag pm-abzeichen pm-abzeichen-" + stufe} title={TITEL[stufe]} onClick={() => {setAnlass(null); setOffen(true); void premiumLaden();}}>
      <Icon size={11} />
      <span>{status?.name || "Standard"}</span>
      {team && !!status?.ungelesen && <em className="pm-abzeichen-neu" aria-label={`${status.ungelesen} neue Team-Nachrichten`}>{status.ungelesen > 9 ? "9+" : status.ungelesen}</em>}
    </button>
    <AnimatePresence>{toast && !offen && <motion.button type="button" className="no-drag pm-toast" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} onClick={() => {setAnlass(toast); setToast(null); setOffen(true);}}>
      <Gem size={14} /><span>{toast.text || "Das ist eine Premium-Funktion."}</span><b>Ansehen</b>
    </motion.button>}</AnimatePresence>
    <AnimatePresence>{offen && <PremiumDialog status={status} anlass={anlass} onClose={() => setOffen(false)} />}</AnimatePresence>
  </>;
}
