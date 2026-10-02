import React, {useEffect, useRef, useState} from "react";
import {createPortal} from "react-dom";
import {AnimatePresence, motion} from "framer-motion";
import {RefreshCw, X} from "lucide-react";
import {api, call, enc, haptic} from "./bridge";
import {Shell} from "./Chat";
import {errorText, overlayHost, spring, useBackHandler} from "./ui";

export type Befehl = {name: string; args?: string; text: string; pi?: boolean};

export const befehle: Befehl[] = [
  {name: "/hilfe", text: "Alle Befehle anzeigen"},
  {name: "/neu", text: "Neuen Chat starten"},
  {name: "/work", text: "Zu Work wechseln"},
  {name: "/chat", text: "Zu Chat wechseln"},
  {name: "/website", args: "<Idee>", text: "Website bauen und ansehen"},
  {name: "/podcast", args: "<Thema>", text: "Podcast mit zwei Stimmen"},
  {name: "/bild", args: "<Beschreibung>", text: "Bild erstellen"},
  {name: "/suche", args: "<Frage>", text: "Im Web suchen"},
  {name: "/wetter", args: "[Ort]", text: "Wetter anzeigen"},
  {name: "/datei", text: "Datei hochladen und auswerten"},
  {name: "/foto", text: "Foto machen und Jon fragen"},
  {name: "/wecker", args: "<Uhrzeit>", text: "Wecker stellen"},
  {name: "/timer", args: "<Minuten>", text: "Timer starten"},
  {name: "/fokus", args: "[Minuten]", text: "Fokuszeit starten"},
  {name: "/schritte", text: "Schritte von heute"},
  {name: "/gym", args: "<Training>", text: "Training eintragen"},
  {name: "/zeit", text: "Bildschirmzeit öffnen"},
  {name: "/video", args: "[Sekunden]", text: "Video vom Bildschirm deines PCs", pi: true},
  {name: "/live", args: "[1|2|alle]", text: "Bildschirm live ansehen", pi: true},
  {name: "/livestop", text: "Live-Ansicht beenden", pi: true},
  {name: "/geraete", text: "Alle verbundenen Jon-Geräte", pi: true},
  {name: "/lernen", args: "<Thema>", text: "Tiefenrecherche starten", pi: true},
  {name: "/lernstatus", text: "Stand der Recherche", pi: true},
  {name: "/lernstop", text: "Recherche abbrechen", pi: true},
  {name: "/lernweiter", text: "Recherche fortsetzen", pi: true},
  {name: "/modell", args: "[Name]", text: "Modell anzeigen oder wechseln"},
  {name: "/anbieter", args: "[Name]", text: "KI-Anbieter wechseln"},
  {name: "/stimme", text: "Jon liest Antworten vor"},
  {name: "/endstimme", text: "Nur noch Text"},
  {name: "/offline", text: "Offline-KI verwalten"},
  {name: "/sos", text: "Notruf an deine Familie"},
  {name: "/stopp", text: "Laufende Antwort abbrechen"},
  {name: "/reset", text: "Gespräch neu beginnen"}
];

export function passende(text: string): Befehl[] {
  if (!text.startsWith("/") || /\s/.test(text.trim()) && text.trim().split(/\s+/).length > 1) return [];
  const suche = text.trim().toLowerCase();
  return befehle.filter(b => b.name.startsWith(suche));
}

export function BefehlsListe({text, waehlen}: {text: string; waehlen: (b: Befehl) => void}) {
  const liste = passende(text);
  return <AnimatePresence>{liste.length > 0 && <motion.div className="befehle" initial={{opacity: 0, y: 10, scale: .98}} animate={{opacity: 1, y: 0, scale: 1}} exit={{opacity: 0, y: 8}} transition={spring}>
    {liste.map((b, i) => <motion.button key={b.name} initial={{opacity: 0, x: -8}} animate={{opacity: 1, x: 0}} transition={{delay: i * .025}} onClick={() => {haptic("tick"); waehlen(b);}}>
      <b>{b.name}</b>{b.args && <i>{b.args}</i>}<span>{b.text}</span>
    </motion.button>)}
  </motion.div>}</AnimatePresence>;
}

export type BefehlsKontext = {
  shell: Shell;
  senden: (text: string, force?: string) => void;
  melden: (text: string, karte?: any) => void;
  hochladen: () => void;
  fotografieren: () => void;
  vorlesenSetzen: (an: boolean) => void;
};

function arbeitsModus(k: BefehlsKontext) {
  const c = k.shell.chats.current;
  if (c.mode !== "coding") {
    if (c.messages.length) k.shell.chats.create("coding");
    else k.shell.chats.update({mode: "coding"});
  }
}

export async function ausfuehren(roh: string, k: BefehlsKontext): Promise<boolean> {
  const text = roh.trim();
  const [kopf, ...teile] = text.split(/\s+/);
  const befehl = kopf.toLowerCase().split("@")[0];
  const rest = teile.join(" ").trim();
  const {shell} = k;
  const piWeg = shell.conn.connected;
  const bekannt = befehle.find(b => b.name === befehl);
  if (!bekannt && !["/start", "/befehle", "/help", "/geräte", "/lerne"].includes(befehl)) return false;
  if (bekannt?.pi && !piWeg) {
    k.melden(`**${befehl}** braucht Jon am PC oder Pi. Gerade ist keiner verbunden.`);
    return true;
  }
  try {
    switch (befehl) {
      case "/hilfe": case "/help": case "/start": case "/befehle":
        k.melden(["**Befehle**", "", ...befehle.filter(b => !b.pi || piWeg).map(b => `- **${b.name}${b.args ? ` ${b.args}` : ""}** – ${b.text}`)].join("\n"));
        return true;
      case "/neu": case "/reset":
        shell.chats.create(shell.chats.current.mode);
        return true;
      case "/work": case "/chat": {
        const modus = befehl === "/work" ? "coding" : "chat";
        if (shell.chats.current.messages.length) shell.chats.create(modus); else shell.chats.update({mode: modus});
        return true;
      }
      case "/website":
        if (!rest) {k.melden("Beschreib die Website, zum Beispiel: **/website** Portfolio für meine Fotos"); return true;}
        arbeitsModus(k);
        setTimeout(() => k.senden(`Baue mir eine vollständige Website: ${rest}. Lege sie als eigenen Ordner an (index.html, style.css, script.js) – modern, schön, responsiv fürs Handy und ohne Build-Werkzeuge. Nenne am Ende den Pfad der index.html.`), 60);
        return true;
      case "/podcast":
        if (!rest) {k.melden("Sag mir das Thema, zum Beispiel: **/podcast** Wie funktionieren schwarze Löcher?"); return true;}
        arbeitsModus(k);
        setTimeout(() => k.senden(`Erstelle einen Podcast über: ${rest}. Schreib ein lebendiges Gespräch zwischen zwei Sprechern (A moderiert, B ist Gast), etwa drei Minuten lang, und nimm es danach mit dem Werkzeug podcast_erstellen auf.`), 60);
        return true;
      case "/bild":
        if (!rest) {shell.push("images"); return true;}
        k.senden(`Erstelle ein Bild: ${rest}`, piWeg ? "create_image" : "");
        return true;
      case "/suche":
        if (!rest) {k.melden("Wonach soll ich suchen? Zum Beispiel: **/suche** Öffnungszeiten Tiergarten Schönbrunn"); return true;}
        k.senden(rest, piWeg ? "web_search" : "");
        return true;
      case "/wetter":
        k.senden(rest ? `Wie wird das Wetter in ${rest}?` : "Wie wird das Wetter heute?", piWeg ? "get_weather" : "");
        return true;
      case "/datei":
        k.hochladen();
        return true;
      case "/foto":
        k.fotografieren();
        return true;
      case "/wecker": {
        if (!rest) {shell.push("uhr"); return true;}
        const r = await call("uhr-befehl", {text: /^\d/.test(rest) ? `weck mich um ${rest}` : `weck mich ${rest}`});
        k.melden(r.antwort ? `⏰ ${r.antwort}` : "Die Uhrzeit habe ich nicht verstanden. Beispiel: **/wecker** 6:30");
        return true;
      }
      case "/timer": {
        if (!rest) {shell.push("uhr"); return true;}
        const r = await call("uhr-befehl", {text: /^\d+([.,]\d+)?$/.test(rest) ? `timer ${rest.replace(",", ".")} minuten` : `timer ${rest}`});
        k.melden(r.antwort ? `⏱️ ${r.antwort}` : "Die Dauer habe ich nicht verstanden. Beispiel: **/timer** 10");
        return true;
      }
      case "/fokus": {
        const minuten = Math.max(5, Math.min(240, parseInt(rest || "25", 10) || 25));
        await call("fokus", {minuten});
        k.melden(`🎯 Fokuszeit läuft ${minuten} Minuten. So lange ist Ruhe.`);
        return true;
      }
      case "/schritte": {
        const s = await call("schritte");
        k.melden(s.erlaubt ? `👣 Heute **${(s.heute || 0).toLocaleString("de-DE")}** Schritte – Ziel ${(s.ziel || 8000).toLocaleString("de-DE")}.` : "👣 Erlaube „Körperliche Aktivität“ unter Fitness, dann zähle ich deine Schritte.");
        return true;
      }
      case "/gym": {
        if (!rest) {shell.push("fitness"); return true;}
        const t = await call("fitness-eintragen", {training: {art: "gym", text: rest}});
        k.melden(`💪 **${t.titel}** eingetragen: ${(t.uebungen || []).map((u: any) => u.name).join(", ") || rest}${t.volumen ? ` · ${Math.round(t.volumen)} kg bewegt` : ""}.`);
        return true;
      }
      case "/zeit":
        shell.push("zeit");
        return true;
      case "/offline":
        shell.push("offline");
        return true;
      case "/sos":
        await call("sos", {text: rest}, 40_000);
        k.melden("🆘 SOS ist gesendet. Deine Familie wurde benachrichtigt.");
        return true;
      case "/stopp":
        shell.chats.stop();
        return true;
      case "/stimme":
        k.vorlesenSetzen(true);
        k.melden("🔊 Ich lese dir meine Antworten ab jetzt vor.");
        return true;
      case "/endstimme":
        k.vorlesenSetzen(false);
        k.melden("💬 Okay, nur noch Text.");
        return true;
      case "/modell": case "/anbieter": {
        if (!rest) {shell.openModel(); return true;}
        const suche = rest.toLowerCase();
        const lokal = await call("ki-katalog").catch(() => ({modelle: []}));
        const offline = (lokal.modelle || []).find((m: any) => m.status === "fertig" && (m.name.toLowerCase().includes(suche) || m.titel.toLowerCase().includes(suche)));
        if (offline || ["offline", "handy", "lokal"].includes(suche)) {
          const name = offline?.name || lokal.standard;
          if (!name) {k.melden("Lade zuerst ein Offline-Modell (**/offline**)."); return true;}
          shell.chats.update({provider: "handy", model: name});
          k.melden(`📱 Dieser Chat läuft jetzt offline mit **${offline?.titel || name}**.`);
          return true;
        }
        for (const p of shell.providers) {
          const modelle: string[] = Array.from(new Set([...(p.default_model ? [p.default_model] : []), ...(p.models || [])]));
          const treffer = befehl === "/anbieter" ? (p.provider.toLowerCase().startsWith(suche) || String(p.label).toLowerCase().includes(suche) ? p.default_model || modelle[0] || "" : null) : modelle.find(m => m.toLowerCase().includes(suche));
          if (treffer !== null && treffer !== undefined && (befehl === "/anbieter" || treffer)) {
            shell.chats.update({provider: p.provider, model: treffer});
            k.melden(`✅ ${p.label}${treffer ? ` · ${treffer.split("/").pop()}` : ""}`);
            return true;
          }
        }
        k.melden(`Das finde ich nicht: ${rest}. Tippe **/modell** ohne Namen, dann siehst du alle.`);
        return true;
      }
      case "/live": case "/livestop":
        window.dispatchEvent(new CustomEvent("jon-live", {detail: befehl === "/livestop" ? null : {welcher: rest || "alle"}}));
        return true;
      default: {
        const antwort = await api<any>("/api/mobile/befehl", "POST", {text});
        k.melden(antwort.text || "Erledigt.", antwort.video ? {kind: "video", data: antwort.video} : undefined);
        return true;
      }
    }
  } catch (e) {
    k.melden(`⚠️ ${errorText(e)}`);
    return true;
  }
}

export function LiveAnsicht({piName}: {piName: string}) {
  const [live, setLive] = useState<{welcher: string} | null>(null), [bild, setBild] = useState(""), [fehler, setFehler] = useState("");
  const laeuft = useRef(false);
  useEffect(() => {
    const h = (e: Event) => setLive((e as CustomEvent).detail);
    window.addEventListener("jon-live", h);
    return () => window.removeEventListener("jon-live", h);
  }, []);
  useBackHandler(!!live, () => setLive(null));
  useEffect(() => {
    if (!live) {setBild(""); setFehler(""); return;}
    let aktiv = true;
    laeuft.current = true;
    const holen = async () => {
      while (aktiv) {
        try {
          const r = await api<any>(`/api/live/bild64?welcher=${enc(live.welcher)}&breite=1100&qualitaet=55`);
          if (!aktiv) return;
          if (r.ok) {setBild(`data:${r.typ};base64,${r.bild}`); setFehler("");} else setFehler(r.fehler || "Kein Bild.");
        } catch (e) {if (aktiv) setFehler(errorText(e));}
        await new Promise(res => setTimeout(res, 1100));
      }
    };
    holen();
    return () => {aktiv = false; laeuft.current = false;};
  }, [live?.welcher]);
  return createPortal(<AnimatePresence>{live && <motion.div className="live-ansicht" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}}>
    <header><span className="punkt"/><strong>Live · {piName || "PC"}</strong><span className="grow"/>
      {["1", "2", "alle"].map(w => <button key={w} className={live.welcher === w ? "on" : ""} onClick={() => setLive({welcher: w})}>{w === "alle" ? "Alle" : w}</button>)}
      <button aria-label="Schließen" onClick={() => setLive(null)}><X/></button>
    </header>
    <div className="live-bild">{bild ? <img src={bild} alt="Bildschirm"/> : <div className="live-warten">{fehler ? <p>{fehler}</p> : <RefreshCw className="spin"/>}</div>}</div>
    {fehler && bild && <p className="live-fehler">{fehler}</p>}
  </motion.div>}</AnimatePresence>, overlayHost());
}
