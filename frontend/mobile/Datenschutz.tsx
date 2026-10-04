import React, {useState} from "react";
import {motion} from "framer-motion";
import {Bell, Camera, Cloud, Copy, Footprints, Hourglass, Lock, MapPin, Mic, Phone, Server, ShieldCheck, Smartphone, Trash2, Users} from "lucide-react";
import {call, haptic} from "./bridge";
import {PageProps} from "./Pages";
import {useAdmin} from "./Settings";
import {PageHeader, Sheet, Switch, errorText, spring} from "./ui";

const abschnitte: {icon: React.ReactNode; titel: string; text: string}[] = [
  {icon: <ShieldCheck/>, titel: "Das Wichtigste", text: "Kein Konto bei FelWorks, keine Werbung, kein Tracking, keine Analyse-Dienste. FelWorks betreibt keinen Server, über den deine Daten laufen."},
  {icon: <Smartphone/>, titel: "Auf diesem Handy", text: "Offline-Chats, Erinnerungen, Fitness, Wecker, Bildschirmzeit-Regeln, Jons Arbeitsordner und Offline-Modelle bleiben im geschützten App-Speicher. API-Schlüssel und Zugangsdaten sind mit dem Android-Schlüsselspeicher verschlüsselt."},
  {icon: <Server/>, titel: "Zu deinem Jon am PC oder Pi", text: "Chats, Dateien, Sicherungen und für die Eltern-Übersicht der Gerätestatus gehen nur an deinen eigenen Jon – Ende-zu-Ende verschlüsselt über WLAN oder Tailscale."},
  {icon: <Cloud/>, titel: "KI-Anbieter und Dienste", text: "Nur wenn du sie nutzt: deine Nachrichten an den gewählten KI-Anbieter, Suchanfragen an DuckDuckGo und Wikipedia, Orte an Open-Meteo, Modell-Downloads über Hugging Face und das Sprachmodell für Live-Text von alphacephei.com. Offline-Modelle senden nichts."},
  {icon: <Users/>, titel: "Familie", text: "Kindersicherung, SOS und Anfragen nach mehr Zeit gehen nur an den Jon deiner Familie und, falls eingerichtet, an euren Telegram-Bot."}
];

const rechte: {icon: React.ReactNode; name: string; grund: string}[] = [
  {icon: <Mic/>, name: "Mikrofon", grund: "Sprechen und Diktieren – nur wenn du auf den Knopf tippst"},
  {icon: <Camera/>, name: "Kamera", grund: "Fotos für Jon und QR-Codes zum Koppeln"},
  {icon: <Bell/>, name: "Benachrichtigungen", grund: "Wecker, Timer, Jon Chat und Durchsagen"},
  {icon: <Footprints/>, name: "Körperliche Aktivität", grund: "Schrittzähler"},
  {icon: <Hourglass/>, name: "Nutzungszugriff", grund: "Bildschirmzeit der freigegebenen Apps"},
  {icon: <MapPin/>, name: "Standort", grund: "Nur beim SOS, wenn du es einschaltest"},
  {icon: <Phone/>, name: "Telefon", grund: "Nur für den Anruf nach einem SOS"},
  {icon: <Lock/>, name: "Gerätemodus", grund: "Nur für den Kiosk der Kindersicherung"}
];

export function DatenschutzPage({shell, back}: PageProps) {
  const [loeschen, setLoeschen] = useState(false), [medien, setMedien] = useState(false), [busy, setBusy] = useState(false);
  const admin = useAdmin(shell.notify);
  async function allesLoeschen() {
    setBusy(true);
    haptic("error");
    try {await call("alle-daten-loeschen", {medien}, 60_000);}
    catch (e) {shell.notify(errorText(e)); setBusy(false);}
  }
  return <>
    <PageHeader title="Datenschutz" onBack={back}/>
    <div className="page-scroll">
      {abschnitte.map((a, i) => <motion.div key={a.titel} className="card datenschutz" initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={{...spring, delay: i * .05}}>
        <h4>{a.icon}{a.titel}</h4>
        <p>{a.text}</p>
      </motion.div>)}
      <div className="group-title">Berechtigungen</div>
      <div className="card">{rechte.map(r => <div className="stat recht" key={r.name}><span>{r.icon}<b>{r.name}</b></span><small>{r.grund}</small></div>)}</div>
      <button className="text-link small" style={{margin: "12px 6px", display: "inline-flex", alignItems: "center", gap: 6}} onClick={() => call("copy", {text: "https://getjon.info/datenschutz-app"}).then(() => shell.notify("Link zur Datenschutzerklärung kopiert.")).catch(() => {})}><Copy size={15}/>getjon.info/datenschutz-app</button>
      <div className="gap"/>
      <div className="group compact"><button className="row-btn danger" onClick={() => admin.guard(() => setLoeschen(true))}><Trash2/><span>Alle Daten löschen<small>Setzt Jon auf diesem Handy komplett zurück</small></span></button></div>
    </div>
    {admin.element}
    <Sheet open={loeschen} title="Alle Daten löschen?" onClose={() => !busy && setLoeschen(false)}>
      <p>Jon vergisst auf diesem Handy alles: Chats, Erinnerungen, Fitness, Wecker, Regeln, Schlüssel und Offline-Modelle. Die Kopplung mit deinem PC oder Pi wird aufgehoben, der Kiosk beendet. Danach startet Jon neu wie am ersten Tag.</p>
      <div className="row-btn" style={{borderRadius: 18}}><Camera/><span>Auch Fotos und Downloads von Jon<small>Galerie „Jon“ und Download/Jon</small></span><Switch on={medien} onChange={setMedien}/></div>
      <button className="btn danger" style={{marginTop: 14}} disabled={busy} onClick={allesLoeschen}><Trash2/>{busy ? "Wird gelöscht …" : "Endgültig löschen"}</button>
    </Sheet>
  </>;
}
