import {motion} from "framer-motion";
import {Code2, Compass, Lightbulb, Map, Sparkles, Users} from "lucide-react";
import AgentenBuehne from "./agenten/AgentenBuehne";

const VORSCHLAEGE = [
  {icon: Users, text: "Lass dein Fachteam einen Lernplan für meine Prüfungswoche erstellen und gegenprüfen", label: "Fachteam", farbe: "#79d0ff"},
  {icon: Code2, text: "Starte den Harness in meinem Projekt und behebe den letzten Fehler", label: "Harness", farbe: "#7fe0a4"},
  {icon: Lightbulb, text: "Was kannst du alles für mich tun?", label: "Entdecken", farbe: "#e5c889"},
  {icon: Map, text: "/maps Cafés in meiner Nähe", label: "Jon Maps", farbe: "#ffad74"},
];

const DEKO = [
  {id: "a", titel: "Recherche", rolle: "research", status: "queued"},
  {id: "b", titel: "Code", rolle: "coding", status: "queued"},
  {id: "c", titel: "Planung", rolle: "planning", status: "queued"},
];

export default function StartHero({titel, hinweis, onVorschlag}: {titel: string; hinweis: string; onVorschlag: (text: string) => void}) {
  return <div className="h-full flex flex-col items-center justify-center text-center px-2">
    <motion.div className="ab w-full max-w-[360px] -mb-2" initial={{opacity: 0, scale: 0.9}} animate={{opacity: 1, scale: 1}} transition={{type: "spring", stiffness: 140, damping: 18}}>
      <AgentenBuehne phase="bereit" knoten={DEKO} kernIcon={Sparkles} kompakt/>
    </motion.div>
    <motion.h1 className="text-4xl font-bold gold-text mb-3" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 0.12}}>{titel}</motion.h1>
    <motion.p className="text-white/40 max-w-md" initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} transition={{delay: 0.2}}>{hinweis}</motion.p>
    <div className="mt-7 grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-[640px]">
      {VORSCHLAEGE.map((v, i) => {
        const Icon = v.icon;
        return <motion.button key={v.text} type="button" onClick={() => onVorschlag(v.text)} initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={{delay: 0.26 + i * 0.07, type: "spring", stiffness: 260, damping: 24}} whileHover={{y: -2}} whileTap={{scale: 0.98}} className="group text-left glass rounded-2xl px-4 py-3 flex items-start gap-3 hover:border-gold/35 transition-colors">
          <span className="mt-0.5 w-8 h-8 rounded-xl grid place-items-center shrink-0" style={{background: `${v.farbe}1f`, color: v.farbe}}><Icon size={16}/></span>
          <span className="min-w-0">
            <span className="block text-[11px] font-semibold uppercase tracking-wider text-white/40 group-hover:text-gold/80 transition-colors">{v.label}</span>
            <span className="block text-[13px] text-white/80 leading-snug mt-0.5">{v.text}</span>
          </span>
          <Compass size={14} className="ml-auto mt-1 text-white/20 group-hover:text-gold/70 transition-colors shrink-0"/>
        </motion.button>;
      })}
    </div>
  </div>;
}
