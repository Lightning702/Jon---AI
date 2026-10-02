import React, {useEffect, useRef} from "react";
import {AnimatePresence, motion} from "framer-motion";
import {Mic, MicOff, ShieldAlert, X} from "lucide-react";
import {api, call, haptic} from "./bridge";
import {JonMark, Orb, useBackHandler} from "./ui";

const labels: Record<string, string> = {
  LISTENING: "Ich höre zu",
  THINKING: "Einen Moment …",
  SPEAKING: "Jon spricht",
  CONNECTING: "Verbinde mit deinem Pi …",
  ERROR: "Das hat nicht geklappt",
  OFFLINE: "Pi nicht erreichbar",
  IDLE: "Sprich mit Jon"
};

export function VoiceMode({voice, model, notify}: {voice: any; model: string; notify: (s: string) => void}) {
  const open = !!voice?.open && voice?.mode !== "dictate";
  const lines = useRef<HTMLDivElement>(null);
  const close = () => {haptic("tap"); call("voice-cancel").catch(() => {});};
  useBackHandler(open, close);
  useEffect(() => {const el = lines.current; if (el) el.scrollTop = el.scrollHeight;}, [voice?.text, voice?.user, voice?.partial]);
  const phase = String(voice?.phase || "IDLE");
  const size = Math.min(300, Math.round(window.innerWidth * .74));
  const hint = phase === "SPEAKING" ? "Tippe auf Jon, um zu unterbrechen" : phase === "LISTENING" && voice?.muted ? "Mikrofon stumm" : phase === "LISTENING" && voice?.partial ? "Tippe auf Jon, wenn du fertig bist" : "";
  return <AnimatePresence>{open && <motion.div className="voice" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} transition={{duration: .3}}>
    <header>
      <strong><span style={{color: "#fff", display: "flex"}}><JonMark/></span>Jon</strong>
      <small>{model}</small>
    </header>
    <motion.div className="orb-zone" initial={{scale: .6, opacity: 0}} animate={{scale: 1, opacity: 1}} transition={{type: "spring", stiffness: 180, damping: 20}}>
      <Orb size={size} level={voice?.level || 0} phase={phase.toLowerCase()} onClick={() => {haptic("tap"); if (phase === "SPEAKING" || phase === "THINKING") call("voice-interrupt").catch(() => {}); else if (phase === "LISTENING") call("voice-finish").catch(() => {});}}/>
    </motion.div>
    <AnimatePresence mode="wait"><motion.div key={phase} className="state" initial={{opacity: 0, y: 6}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -6}} transition={{duration: .2}}>{voice?.error && (phase === "ERROR" || phase === "OFFLINE") ? voice.error : labels[phase] || labels.IDLE}</motion.div></AnimatePresence>
    <div className="lines" ref={lines}>
      {voice?.user && <div className="me">{voice.user}</div>}
      {phase === "LISTENING" && voice?.partial && <div className="me">{voice.partial}</div>}
      {voice?.text && phase !== "LISTENING" && <div>{voice.text}</div>}
      {hint && <div className="small">{hint}</div>}
    </div>
    {voice?.approval && <div className="approval"><strong><ShieldAlert/>Jon möchte eine Aktion ausführen</strong><p>{voice.approvalText || "Bitte bestätige die Aktion."}</p><div className="row">
      <button onClick={() => api("/api/chat/approve", "POST", {id: voice.approval, approved: false}).catch(e => notify(String(e)))}>Ablehnen</button>
      <button className="yes" onClick={() => api("/api/chat/approve", "POST", {id: voice.approval, approved: true}).catch(e => notify(String(e)))}>Erlauben</button>
    </div></div>}
    <footer>
      <button aria-label={voice?.muted ? "Mikrofon an" : "Mikrofon stumm"} className={voice?.muted ? "off" : ""} onClick={() => {haptic("tick"); call("voice-mute", {muted: !voice?.muted}).catch(() => {});}}>{voice?.muted ? <MicOff/> : <Mic/>}</button>
      <button aria-label="Sprachmodus beenden" className="end" onClick={close}><X/></button>
    </footer>
  </motion.div>}</AnimatePresence>;
}
