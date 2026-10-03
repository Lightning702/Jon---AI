import {AnimatePresence, motion, useReducedMotion} from "framer-motion";
import {Check, ShieldCheck, Sparkles, X, type LucideIcon} from "lucide-react";
import {useId, useMemo} from "react";
import {KernPhase, Knoten, rolle} from "./daten";
import "./agenten.css";

const BREITE = 160;

function positionen(anzahl: number, hoehe: number) {
  const rx = anzahl > 3 ? 60 : 56;
  const ry = hoehe / 2 - 15;
  const basis = anzahl === 1 ? 0 : anzahl === 2 ? 0 : anzahl === 4 ? -45 : -90;
  return Array.from({length: anzahl}, (_, i) => {
    const winkel = ((basis + (360 / anzahl) * i) * Math.PI) / 180;
    return {x: BREITE / 2 + Math.cos(winkel) * rx, y: hoehe / 2 + Math.sin(winkel) * ry};
  });
}

function Funken({pfad, rueckwaerts, farbe, versatz}: {pfad: string; rueckwaerts?: boolean; farbe: string; versatz: number}) {
  return <>{[0, 1, 2].map(n => <circle key={n} r={n === 0 ? 1.35 : 0.9} style={{fill: farbe}} className="ab-funke">
    <animateMotion dur="1.5s" repeatCount="indefinite" path={pfad} begin={`${versatz + n * 0.5}s`} keyPoints={rueckwaerts ? "1;0" : "0;1"} keyTimes="0;1" calcMode="linear"/>
  </circle>)}</>;
}

export interface Satellit {
  icon: LucideIcon;
  text: string;
}

export default function AgentenBuehne({phase, knoten, kernIcon: KernIcon = Sparkles, kernText, satellit, kompakt = false}: {phase: KernPhase; knoten: Knoten[]; kernIcon?: LucideIcon; kernText?: string; satellit?: Satellit | null; kompakt?: boolean}) {
  const ruhig = useReducedMotion();
  const glanz = "ab-glanz-" + useId().replace(/[^a-zA-Z0-9]/g, "");
  const hoehe = kompakt ? 74 : 90;
  const punkte = useMemo(() => positionen(knoten.length, hoehe), [knoten.length, hoehe]);
  const mitte = {x: BREITE / 2, y: hoehe / 2};
  const SatIcon = satellit?.icon;
  return <div className={`ab-buehne ${kompakt ? "kompakt" : ""}`} data-phase={phase} style={{aspectRatio: `${BREITE} / ${hoehe}`}}>
    <div className="ab-raster" aria-hidden="true"/>
    <svg className="ab-netz" viewBox={`0 0 ${BREITE} ${hoehe}`} aria-hidden="true">
      <defs>
        <radialGradient id={glanz} cx="50%" cy="50%" r="50%">
          <stop offset="0%" style={{stopColor: "var(--ab-akzent)", stopOpacity: 0.22}}/>
          <stop offset="100%" style={{stopColor: "var(--ab-akzent)", stopOpacity: 0}}/>
        </radialGradient>
      </defs>
      <ellipse cx={mitte.x} cy={mitte.y} rx={64} ry={hoehe / 2 - 6} fill={`url(#${glanz})`}/>
      <ellipse className="ab-bahn" cx={mitte.x} cy={mitte.y} rx={knoten.length > 3 ? 60 : 56} ry={hoehe / 2 - 15}/>
      {knoten.map((k, i) => {
        const p = punkte[i];
        if (!p) return null;
        const pfad = `M${mitte.x} ${mitte.y} L${p.x.toFixed(2)} ${p.y.toFixed(2)}`;
        const farbe = rolle(k.rolle).farbe;
        const fluss = !ruhig && ((k.status === "working" && (phase === "verteilen" || phase === "denken" || phase === "warten")) || (k.status === "done" && phase === "sammeln"));
        return <g key={k.id}>
          <path d={pfad} className={`ab-linie status-${k.status}`} style={{["--farbe" as string]: farbe}}/>
          {fluss && <Funken pfad={pfad} farbe={farbe} rueckwaerts={phase === "sammeln"} versatz={i * 0.22}/>}
        </g>;
      })}
    </svg>
    {phase === "pruefen" && !ruhig && <div className="ab-scan" aria-hidden="true"/>}
    <div className="ab-kern-anker">
      {phase === "denken" && !ruhig && [0, 1, 2].map(n => <motion.span key={n} className="ab-welle" initial={{scale: 0.6, opacity: 0.55}} animate={{scale: 2.3, opacity: 0}} transition={{duration: 2.4, repeat: Infinity, delay: n * 0.8, ease: "easeOut"}}/>)}
      <AnimatePresence>{phase === "fertig" && !ruhig && <motion.span key="burst" className="ab-burst" initial={{scale: 0.8, opacity: 0.9}} animate={{scale: 3.2, opacity: 0}} exit={{opacity: 0}} transition={{duration: 1.1, ease: "easeOut"}}/>}</AnimatePresence>
      <motion.div className="ab-kern" animate={phase === "fertig" ? {scale: [1, 1.12, 1]} : {scale: 1}} transition={{duration: 0.6}}>
        <span className="ab-kern-ring"/>
        <span className="ab-kern-ring zwei"/>
        <span className="ab-kern-licht"/>
        <AnimatePresence mode="wait" initial={false}>
          <motion.span key={phase === "fertig" ? "ok" : phase === "pruefen" ? "pruefen" : "icon"} className="ab-kern-icon" initial={{scale: 0.4, opacity: 0, rotate: -40}} animate={{scale: 1, opacity: 1, rotate: 0}} exit={{scale: 0.4, opacity: 0}} transition={{type: "spring", stiffness: 260, damping: 18}}>
            {phase === "fertig" ? <Check/> : phase === "pruefen" ? <ShieldCheck/> : <KernIcon/>}
          </motion.span>
        </AnimatePresence>
      </motion.div>
      {kernText && !satellit && <span className="ab-kern-text">{kernText}</span>}
      {SatIcon && satellit && <div className="ab-orbit" aria-hidden="true"><span className="ab-satellit" title={satellit.text}><SatIcon/></span></div>}
    </div>
    {knoten.map((k, i) => {
      const p = punkte[i];
      if (!p) return null;
      const r = rolle(k.rolle);
      const Icon = r.icon;
      return <motion.div key={k.id} className="ab-knoten" data-status={k.status} style={{["--farbe" as string]: r.farbe, x: "-50%", y: "-50%"}} initial={{left: "50%", top: "50%", scale: 0.2, opacity: 0}} animate={{left: `${(p.x / BREITE) * 100}%`, top: `${(p.y / hoehe) * 100}%`, scale: 1, opacity: 1}} transition={{type: "spring", stiffness: 150, damping: 17, delay: i * 0.09}}>
        <motion.span className="ab-knoten-koerper" animate={k.status === "failed" ? {x: [0, -3, 3, -2, 2, 0]} : {x: 0}} transition={{duration: 0.45}}>
          <span className="ab-knoten-ring"/>
          <span className="ab-knoten-icon"><Icon/></span>
          <AnimatePresence>
            {k.status === "done" && <motion.span key="ok" className="ab-abzeichen ok" initial={{scale: 0}} animate={{scale: 1}} exit={{scale: 0}} transition={{type: "spring", stiffness: 420, damping: 15}}><Check/></motion.span>}
            {(k.status === "failed" || k.status === "interrupted" || k.status === "cancelled") && <motion.span key="fail" className="ab-abzeichen fehler" initial={{scale: 0}} animate={{scale: 1}} exit={{scale: 0}}><X/></motion.span>}
          </AnimatePresence>
        </motion.span>
        <span className="ab-knoten-titel">{k.titel}</span>
      </motion.div>;
    })}
  </div>;
}
