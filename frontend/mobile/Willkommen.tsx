import React, {useState} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {ArrowRight, Cloud, Cpu, Laptop} from "lucide-react";
import {call, haptic} from "./bridge";
import {JonMark, Orb, spring} from "./ui";

export function Willkommen({fertig, oeffnen}: {fertig: (name: string) => void; oeffnen: (seite: string) => void}) {
  const [schritt, setSchritt] = useState(0), [name, setName] = useState("");
  const weiter = () => {haptic("tap"); setSchritt(s => s + 1);};
  const wahl = (seite: string) => {
    haptic("success");
    try {localStorage.setItem("jon-willkommen", "1");} catch {}
    fertig(name.trim());
    if (seite) setTimeout(() => oeffnen(seite), 250);
  };
  return <motion.div className="willkommen" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}}>
    <AnimatePresence mode="wait">
      {schritt === 0 && <motion.div key="a" className="w-seite" initial={{opacity: 0, y: 24}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -24}} transition={spring}>
        <Orb size={Math.min(230, Math.round(window.innerWidth * .6))} phase="idle"/>
        <h1>Hallo, ich bin Jon.</h1>
        <p>Dein persönlicher KI-Assistent – zum Reden, Lernen, Arbeiten und Organisieren.</p>
        <button className="btn primary" onClick={weiter}>Los geht's<ArrowRight/></button>
      </motion.div>}
      {schritt === 1 && <motion.div key="b" className="w-seite" initial={{opacity: 0, y: 24}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -24}} transition={spring}>
        <span className="w-logo"><JonMark/></span>
        <h1>Wie heißt du?</h1>
        <p>So spricht dich Jon an. Du kannst es jederzeit ändern.</p>
        <input className="w-eingabe" autoFocus placeholder="Dein Vorname" value={name} onChange={e => setName(e.target.value)} onKeyDown={e => {if (e.key === "Enter" && name.trim()) {call("profil-setzen", {name: name.trim()}).catch(() => {}); weiter();}}}/>
        <button className="btn primary" disabled={!name.trim()} onClick={() => {call("profil-setzen", {name: name.trim()}).catch(() => {}); weiter();}}>Weiter<ArrowRight/></button>
      </motion.div>}
      {schritt === 2 && <motion.div key="c" className="w-seite" initial={{opacity: 0, y: 24}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -24}} transition={spring}>
        <h1>Wie soll Jon laufen{name.trim() ? `, ${name.trim()}` : ""}?</h1>
        <p>Du kannst das später in den Einstellungen ändern.</p>
        <div className="w-wahl">
          {[
            {id: "pair", icon: <Laptop/>, titel: "Mit Jon am PC oder Pi", text: "Voller Funktionsumfang: Dateien, Programme, Fernsteuerung, Jon Chat."},
            {id: "solo", icon: <Cloud/>, titel: "Mit eigenem API-Schlüssel", text: "Ohne PC: OpenAI, Claude, Gemini und mehr – direkt vom Handy."},
            {id: "offline", icon: <Cpu/>, titel: "Offline auf dem Handy", text: "Gemma 4 und Co. laufen ganz ohne Internet auf deinem Gerät."}
          ].map((w, i) => <motion.button key={w.id} initial={{opacity: 0, y: 14}} animate={{opacity: 1, y: 0}} transition={{...spring, delay: .08 * i}} onClick={() => wahl(w.id)}><span className="w-icon">{w.icon}</span><span><strong>{w.titel}</strong><small>{w.text}</small></span><ArrowRight/></motion.button>)}
        </div>
        <button className="text-link" onClick={() => wahl("")}>Später</button>
      </motion.div>}
    </AnimatePresence>
    <div className="w-punkte">{[0, 1, 2].map(i => <i key={i} className={i === schritt ? "an" : ""}/>)}</div>
  </motion.div>;
}
