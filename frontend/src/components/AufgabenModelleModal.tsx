import { useEffect, useState } from "react";
import Symbol from "./Symbol";
import {
  Aufgabe,
  AufgabenZuordnung,
  ProviderStatus,
  StudioProvider,
  aufgabenModelle,
  aufgabenModelleErkennen,
  aufgabenModelleSpeichern,
  getProviders,
  getStudioConfig,
  getUserSettings,
  saveUserSettings,
} from "../lib/api";

interface Props {
  onClose: () => void;
}

const field =
  "w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50";

const AUFGABEN: { id: Aufgabe; titel: string; hinweis: string }[] = [
  { id: "text", titel: "Antworten", hinweis: "Normale Fragen und Gespräche, z. B. GPT-OSS 120B." },
  { id: "code", titel: "Code", hinweis: "Programmieren im Code-Modus. Leer = wie Antworten." },
  { id: "bild", titel: "Bilder", hinweis: "Bilder malen, z. B. Z-Image auf dem lokalen Server." },
  { id: "sehen", titel: "Sehen", hinweis: "Bilder, Fotos und den Bildschirm verstehen." },
];

function Schalter({ an, onClick, titel, hinweis }: { an: boolean; onClick: () => void; titel: string; hinweis: string }) {
  return (
    <button onClick={onClick} className="w-full flex items-start justify-between gap-3 px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-left">
      <span className="flex flex-col gap-0.5">
        <span className="text-[12px] text-white/90">{titel}</span>
        <span className="text-[10.5px] leading-snug text-white/45">{hinweis}</span>
      </span>
      <span className={`mt-0.5 w-9 h-5 shrink-0 rounded-full flex items-center px-0.5 transition-colors ${an ? "bg-gold/70" : "bg-white/15"}`}>
        <span className={`w-4 h-4 rounded-full bg-white transition-transform ${an ? "translate-x-4" : ""}`} />
      </span>
    </button>
  );
}

export default function AufgabenModelleModal({ onClose }: Props) {
  const [offline, setOffline] = useState(false);
  const [aktiv, setAktiv] = useState(true);
  const [zuordnung, setZuordnung] = useState<Partial<Record<Aufgabe, AufgabenZuordnung>>>({});
  const [anbieter, setAnbieter] = useState<ProviderStatus[]>([]);
  const [studio, setStudio] = useState<StudioProvider[]>([]);
  const [url, setUrl] = useState("");
  const [schluessel, setSchluessel] = useState("");
  const [meldung, setMeldung] = useState("");
  const [sucht, setSucht] = useState(false);

  const anbieterLaden = () => {
    void getProviders().then(setAnbieter).catch(() => setAnbieter([]));
    void getStudioConfig().then((c) => setStudio(c.liste)).catch(() => setStudio([]));
  };

  useEffect(() => {
    void aufgabenModelle().then((s) => {
      setAktiv(s.aktiv);
      setZuordnung(s.zuordnung);
      setOffline(s.offline);
    }).catch(() => undefined);
    void getUserSettings().then((s) => {
      setUrl(s.lokaler_server_url ?? "");
      setSchluessel(s.lokaler_server_key ?? "");
    });
    anbieterLaden();
  }, []);

  const offlineUmschalten = () => {
    const neu = !offline;
    setOffline(neu);
    void saveUserSettings({ offline_modus: neu }).then(anbieterLaden);
  };

  const aktivUmschalten = () => {
    const neu = !aktiv;
    setAktiv(neu);
    void aufgabenModelleSpeichern({ aktiv: neu });
  };

  const setzen = (aufgabe: Aufgabe, teil: Partial<AufgabenZuordnung>) => {
    setZuordnung((z) => {
      const alt = z[aufgabe] ?? { provider: "", model: "" };
      const neu = { ...alt, ...teil };
      if (teil.provider !== undefined && teil.provider !== alt.provider) neu.model = "";
      return { ...z, [aufgabe]: neu };
    });
    setMeldung("");
  };

  const serverSpeichern = async () => {
    await saveUserSettings({ lokaler_server_url: url.trim(), lokaler_server_key: schluessel.trim() });
    setMeldung("Lokaler Server gespeichert.");
    anbieterLaden();
  };

  const erkennen = async () => {
    setSucht(true);
    setMeldung("");
    try {
      await saveUserSettings({ lokaler_server_url: url.trim(), lokaler_server_key: schluessel.trim() });
      const ergebnis = await aufgabenModelleErkennen();
      const anzahl = Object.values(ergebnis.modelle).reduce((summe, liste) => summe + liste.length, 0);
      if (!anzahl && !ergebnis.vorschlag.bild) {
        setMeldung("Keine lokalen Modelle gefunden. Läuft der Server und stimmt die Adresse?");
      } else {
        setZuordnung((z) => ({ ...z, ...ergebnis.vorschlag }));
        setMeldung(`${anzahl} lokale Modelle gefunden und zugeordnet. Prüfen und speichern.`);
      }
      anbieterLaden();
    } catch (fehler) {
      setMeldung(`Erkennen fehlgeschlagen: ${String((fehler as Error).message || fehler)}`);
    } finally {
      setSucht(false);
    }
  };

  const speichern = async () => {
    const sauber: Partial<Record<Aufgabe, AufgabenZuordnung>> = {};
    for (const { id } of AUFGABEN) {
      const eintrag = zuordnung[id];
      if (eintrag?.provider) sauber[id] = { provider: eintrag.provider, model: eintrag.model.trim() };
    }
    await aufgabenModelleSpeichern({ aktiv, zuordnung: sauber });
    setMeldung("Gespeichert. Jon nimmt ab der nächsten Nachricht diese Modelle.");
  };

  const wahl = (aufgabe: Aufgabe) => {
    if (aufgabe === "bild") {
      return studio
        .filter((s) => !offline || s.id === "lokal" || s.id === "lokalserver")
        .map((s) => ({ id: s.id, label: s.label, modelle: s.bild_modelle }));
    }
    const liste = anbieter.filter((a) => a.configured).map((a) => ({ id: a.provider, label: a.label || a.provider, modelle: a.models }));
    if (!liste.some((a) => a.id === "lokalserver") && url.trim()) liste.unshift({ id: "lokalserver", label: "Lokaler Server", modelle: [] });
    return liste;
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[600px] max-w-[94vw] max-h-[88vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div className="text-[14px] text-white/90 flex items-center gap-2">
            <Symbol zeichen="🧠" /> Modelle je Aufgabe & Offline
          </div>
          <button onClick={onClose} className="text-white/50 hover:text-white text-[18px] leading-none" aria-label="Schließen">
            ×
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-4 space-y-4">
          <Schalter
            an={offline}
            onClick={offlineUmschalten}
            titel="Offline-Modus"
            hinweis="Jon arbeitet nur mit lokalen Modellen (Ollama, LM Studio, lokaler Server) und nutzt kein Internet - keine Websuche, kein Browser, keine Cloud-Anbieter."
          />
          <Schalter
            an={aktiv}
            onClick={aktivUmschalten}
            titel="Jon wählt das Modell je Aufgabe"
            hinweis="Für Antworten, Code, Bilder und Sehen nimmt Jon jeweils das unten eingetragene Modell. Aus = immer das Modell aus der Modellwahl."
          />
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-gold/70">Lokaler Server</div>
            <p className="text-[11px] text-white/45 leading-relaxed">
              Ein Gerät in deinem Netz mit OpenAI-kompatibler Schnittstelle, zum Beispiel das Tiiny AI Pocket Lab,
              llama.cpp, vLLM oder LocalAI. Adresse wie <code>http://192.168.1.50:8000</code>.
            </p>
            <input className={field} placeholder="Adresse des lokalen Servers" value={url} onChange={(e) => setUrl(e.target.value)} />
            <input className={field} type="password" placeholder="Schlüssel (falls der Server einen verlangt)" value={schluessel} onChange={(e) => setSchluessel(e.target.value)} />
            <div className="flex gap-2">
              <button onClick={() => void serverSpeichern()} className="px-3 py-1.5 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-[12px] text-white/85">
                Speichern
              </button>
              <button disabled={sucht} onClick={() => void erkennen()} className="px-3 py-1.5 rounded-lg border border-gold/30 bg-gold/10 hover:bg-gold/20 text-[12px] text-gold/90 disabled:opacity-50">
                {sucht ? "Suche Modelle …" : "Modelle erkennen und zuordnen"}
              </button>
            </div>
          </div>
          <div className={`space-y-3 ${aktiv ? "" : "opacity-50"}`}>
            <div className="text-[11px] uppercase tracking-wide text-gold/70">Zuordnung</div>
            {AUFGABEN.map(({ id, titel, hinweis }) => {
              const eintrag = zuordnung[id] ?? { provider: "", model: "" };
              const optionen = wahl(id);
              const modelle = optionen.find((o) => o.id === eintrag.provider)?.modelle ?? [];
              return (
                <div key={id} className="space-y-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-[12px] text-white/85">{titel}</span>
                    <span className="text-[10.5px] text-white/40 text-right">{hinweis}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <select className={field} value={eintrag.provider} onChange={(e) => setzen(id, { provider: e.target.value })}>
                      <option value="">Wie in der Modellwahl</option>
                      {eintrag.provider && !optionen.some((o) => o.id === eintrag.provider) && (
                        <option value={eintrag.provider}>{eintrag.provider}</option>
                      )}
                      {optionen.map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                    <input
                      className={field}
                      list={`aufgabe-${id}`}
                      placeholder={id === "bild" ? "Bildmodell, z. B. z-image-turbo" : "Modell"}
                      value={eintrag.model}
                      disabled={!eintrag.provider}
                      onChange={(e) => setzen(id, { model: e.target.value })}
                    />
                    <datalist id={`aufgabe-${id}`}>
                      {modelle.map((m) => (
                        <option key={m} value={m} />
                      ))}
                    </datalist>
                  </div>
                </div>
              );
            })}
          </div>
          {meldung && <div className="text-[11.5px] text-gold/80">{meldung}</div>}
        </div>
        <div className="flex justify-end gap-2 px-5 py-3 border-t border-white/10">
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-[12px] text-white/60 hover:text-white">
            Schließen
          </button>
          <button onClick={() => void speichern()} className="px-4 py-1.5 rounded-lg bg-gold/80 hover:bg-gold text-black text-[12px] font-medium">
            Zuordnung speichern
          </button>
        </div>
      </div>
    </div>
  );
}
