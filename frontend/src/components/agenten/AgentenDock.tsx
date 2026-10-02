import {AnimatePresence, motion} from "framer-motion";
import {ChevronDown} from "lucide-react";
import {useEffect, useState} from "react";
import FachteamKarte from "./FachteamKarte";
import HarnessKarte from "./HarnessKarte";
import {Anfrage, ENDE, rolle} from "./daten";
import "./agenten.css";

interface LiveTeam {id: string; aufgabe: string; source: string; status: string; teile: {rolle: string; status: string}[]}
interface LiveHarness {id: string; goal: string; source: string; status: string; pending: boolean; specialists: {profil: string; status: string}[]}
interface LiveDaten {teams: LiveTeam[]; harness: LiveHarness[]}

export default function AgentenDock({request, onHarness, ausblenden}: {request: Anfrage; onHarness?: (id: string) => void; ausblenden?: Set<string>}) {
  const [daten, setDaten] = useState<LiveDaten>({teams: [], harness: []});
  const [offen, setOffen] = useState(false);
  useEffect(() => {
    let aktiv = true;
    let timer: ReturnType<typeof setTimeout>;
    let laeuft = false;
    const laden = async () => {
      try {
        if (!document.hidden) {
          const wert: LiveDaten = await request("/agents/live");
          if (!aktiv) return;
          setDaten({teams: wert.teams || [], harness: wert.harness || []});
          laeuft = [...(wert.teams || []), ...(wert.harness || [])].some(e => !ENDE.has(e.status));
        }
      } catch {
        laeuft = false;
      } finally {
        if (aktiv) timer = setTimeout(laden, laeuft ? 1500 : 4000);
      }
    };
    void laden();
    return () => {aktiv = false; clearTimeout(timer);};
  }, [request]);
  const teams = daten.teams.filter(t => !ausblenden?.has(t.id));
  const harness = daten.harness.filter(h => !ausblenden?.has(h.id));
  const aktiveTeams = teams.filter(t => !ENDE.has(t.status));
  const aktiveHarness = harness.filter(h => !ENDE.has(h.status));
  const sichtbar = teams.length + harness.length > 0;
  useEffect(() => {if (!sichtbar) setOffen(false);}, [sichtbar]);
  const agenten = aktiveTeams.reduce((n, t) => n + Math.max(1, t.teile.filter(p => p.status === "working").length), 0) + aktiveHarness.reduce((n, h) => n + 1 + h.specialists.filter(s => s.status === "working").length, 0);
  const wartet = harness.some(h => h.pending);
  const farben = [...aktiveTeams.flatMap(t => t.teile.map(p => rolle(p.rolle).farbe)), ...aktiveHarness.flatMap(h => [rolle("coding").farbe, ...h.specialists.map(s => rolle(s.profil).farbe)])].slice(0, 5);
  const text = wartet ? "Freigabe nötig" : agenten > 0 ? `${agenten} ${agenten === 1 ? "Agent arbeitet" : "Agenten arbeiten"}` : "Agenten fertig";
  return <div className="ab ab-dock">
    <AnimatePresence>{sichtbar && offen && <motion.div className="ab-dock-panel" initial={{opacity: 0, y: 14, scale: 0.97}} animate={{opacity: 1, y: 0, scale: 1}} exit={{opacity: 0, y: 14, scale: 0.97}} transition={{type: "spring", stiffness: 260, damping: 24}}>
      {harness.map(h => <HarnessKarte key={h.id} id={h.id} request={request} kompakt onOeffnen={onHarness}/>)}
      {teams.map(t => <FachteamKarte key={t.id} id={t.id} aufgabe={t.aufgabe} request={request} kompakt/>)}
    </motion.div>}</AnimatePresence>
    <AnimatePresence>{sichtbar && <motion.button type="button" className="ab-dock-pille" onClick={() => setOffen(v => !v)} initial={{opacity: 0, y: 20, scale: 0.8}} animate={{opacity: 1, y: 0, scale: 1}} exit={{opacity: 0, y: 20, scale: 0.8}} transition={{type: "spring", stiffness: 320, damping: 22}} aria-expanded={offen} title="Laufende Agenten anzeigen">
      <span className="ab-dock-orbit"><span/>{(farben.length ? farben : ["var(--ab-ok)"]).map((farbe, i) => <i key={i} style={{["--farbe" as string]: farbe, animationDelay: `${-i * 0.48}s`, animationPlayState: agenten ? "running" : "paused"}}/>)}</span>
      <span>{text}</span>
      <ChevronDown style={{width: 14, height: 14, transform: offen ? "rotate(180deg)" : "none", transition: "transform .25s"}}/>
    </motion.button>}</AnimatePresence>
  </div>;
}
