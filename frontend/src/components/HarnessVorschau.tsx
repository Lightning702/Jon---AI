import {useEffect, useRef, useState} from "react";
import {ExternalLink, Loader2, Monitor, Play, Power, RotateCw, Smartphone, Tablet, TriangleAlert, X} from "lucide-react";
import {harnessRequest, VorschauZustand} from "../lib/harness";

const GERAETE = [{key: "desktop", icon: Monitor, breite: "100%", label: "Desktop"}, {key: "tablet", icon: Tablet, breite: "820px", label: "Tablet"}, {key: "handy", icon: Smartphone, breite: "390px", label: "Handy"}] as const;

export default function HarnessVorschau({root, neuLaden, onClose}: {root: string; neuLaden: number; onClose: () => void}) {
  const [zustand, setZustand] = useState<VorschauZustand | null>(null);
  const [fehler, setFehler] = useState("");
  const [busy, setBusy] = useState(false);
  const [geraet, setGeraet] = useState<(typeof GERAETE)[number]["key"]>("desktop");
  const [runde, setRunde] = useState(0);
  const protokoll = useRef<HTMLPreElement>(null);
  const pfad = "/harness/preview?root=" + encodeURIComponent(root);

  useEffect(() => {
    if (!root) return;
    let aktiv = true;
    let timer: ReturnType<typeof setTimeout>;
    const laden = async () => {
      let takt = 5000;
      try {
        const wert = await harnessRequest<VorschauZustand>(pfad);
        if (!aktiv) return;
        setZustand(wert);
        takt = wert.status === "startet" ? 1200 : wert.status === "laeuft" ? 5000 : 8000;
      } catch (e) {
        if (aktiv) setFehler(e instanceof Error ? e.message : "Vorschau nicht erreichbar");
      } finally {
        if (aktiv) timer = setTimeout(laden, takt);
      }
    };
    void laden();
    return () => {aktiv = false; clearTimeout(timer);};
  }, [pfad, root]);

  useEffect(() => {if (neuLaden) setRunde(n => n + 1);}, [neuLaden]);
  useEffect(() => {protokoll.current?.scrollTo({top: protokoll.current.scrollHeight});}, [zustand?.log?.length]);

  const handeln = async (fn: () => Promise<VorschauZustand>) => {
    setBusy(true);
    setFehler("");
    try {setZustand(await fn());}
    catch (e) {setFehler(e instanceof Error ? e.message : "Aktion fehlgeschlagen");}
    finally {setBusy(false);}
  };
  const starten = () => handeln(() => harnessRequest<VorschauZustand>("/harness/preview", {root}));
  const stoppen = () => handeln(() => harnessRequest<VorschauZustand>("/harness/preview/stop", {root}));
  const erkannt = zustand?.erkannt;
  const laeuft = zustand?.status === "laeuft" && !!zustand.url;
  const breite = GERAETE.find(g => g.key === geraet)?.breite || "100%";

  return <aside className="harness-review harness-vorschau" aria-label="Projektvorschau">
    <header>
      <Monitor size={16}/><strong>Vorschau</strong>
      {laeuft && <div className="harness-geraete" role="group" aria-label="Bildschirmgröße">{GERAETE.map(g => <button key={g.key} className={geraet === g.key ? "an" : ""} title={g.label} aria-label={g.label} onClick={() => setGeraet(g.key)}><g.icon size={14}/></button>)}</div>}
      <button aria-label="Vorschau schließen" title="Schließen" onClick={onClose}><X size={17}/></button>
    </header>
    {laeuft && zustand?.url && <div className="harness-vorschau-leiste">
      <input readOnly value={zustand.url} aria-label="Adresse der Vorschau" onFocus={e => e.currentTarget.select()}/>
      <button title="Neu laden" aria-label="Neu laden" onClick={() => setRunde(n => n + 1)}><RotateCw size={15}/></button>
      <button title="Im Browser öffnen" aria-label="Im Browser öffnen" onClick={() => window.open(zustand.url, "_blank")}><ExternalLink size={15}/></button>
      <button title="Vorschau stoppen" aria-label="Vorschau stoppen" disabled={busy} onClick={() => void stoppen()}><Power size={15}/></button>
    </div>}
    {fehler && <p className="harness-vorschau-fehler" role="alert"><TriangleAlert size={14}/>{fehler}</p>}
    {laeuft && zustand?.url ? <div className="harness-vorschau-buehne">
      <div key={geraet} className="harness-vorschau-rahmen" style={{width: breite}}>
        <iframe key={runde} title="Projektvorschau" src={zustand.url} sandbox="allow-scripts allow-forms allow-same-origin allow-modals allow-popups allow-downloads"/>
      </div>
    </div> : <div className="harness-vorschau-start">
      {!zustand && <p className="harness-muted"><Loader2 size={14} className="harness-spin"/> Prüfe das Projekt …</p>}
      {zustand?.status === "startet" && <>
        <div className="harness-vorschau-lade"><Loader2 size={22} className="harness-spin"/><strong>Vorschau startet …</strong><span>{zustand.befehl}</span></div>
        {zustand.hinweis && <p className="harness-muted">{zustand.hinweis}</p>}
      </>}
      {zustand && zustand.status !== "startet" && <>
        {(zustand.status === "beendet" || zustand.status === "fehler") && <p className="harness-vorschau-fehler"><TriangleAlert size={14}/>Der Vorschau-Server wurde beendet. Sieh dir das Protokoll an und starte ihn erneut.</p>}
        {erkannt?.art === "statisch" && <div className="harness-vorschau-karte"><Monitor size={22}/><strong>Webseite gefunden</strong><span>{erkannt.datei} in {erkannt.ordner?.split(/[\\/]/).filter(Boolean).at(-1)}</span><button className="harness-vorschau-knopf" disabled={busy} onClick={() => void starten()}><Play size={15}/>Vorschau öffnen</button></div>}
        {erkannt?.art === "npm" && <div className="harness-vorschau-karte"><Play size={22}/><strong>Entwicklungsserver starten</strong><code>{erkannt.befehl}</code><span>Startet den Server deines Projekts mit deinen Benutzerrechten. Stoppen kannst du ihn jederzeit hier.</span><button className="harness-vorschau-knopf" disabled={busy} onClick={() => void starten()}>{busy ? <Loader2 size={15} className="harness-spin"/> : <Play size={15}/>}Server starten</button></div>}
        {erkannt && !erkannt.art && <div className="harness-vorschau-karte"><TriangleAlert size={22}/><strong>Keine Vorschau gefunden</strong><span>Lege eine index.html an oder ergänze in package.json ein dev-Skript. Du kannst Jon auch bitten: „Baue mir eine Startseite“.</span></div>}
      </>}
      {!!zustand?.log?.length && <pre className="harness-vorschau-log" ref={protokoll}>{zustand.log.join("\n")}</pre>}
    </div>}
  </aside>;
}
