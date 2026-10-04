import { useEffect, useRef, useState } from "react";
import { Loader2, Mic, Square } from "lucide-react";
import { alsWav, sprachText } from "../lib/diktat";
import { mikrofonOeffnen } from "../lib/umgebung";
import "./diktat.css";

export type DiktatZustand = "aus" | "hoert" | "wandelt";

const MAX_SEKUNDEN = 120;

export default function DiktatKnopf({ disabled, onText, onZustand, onFehler }: { disabled?: boolean; onText: (text: string) => void; onZustand?: (zustand: DiktatZustand) => void; onFehler?: (text: string) => void }) {
  const [zustand, setZustand] = useState<DiktatZustand>("aus");
  const [sekunden, setSekunden] = useState(0);
  const [pegel, setPegel] = useState([0, 0, 0, 0, 0]);
  const rekorder = useRef<MediaRecorder | null>(null);
  const stuecke = useRef<Blob[]>([]);
  const strom = useRef<MediaStream | null>(null);
  const kontext = useRef<AudioContext | null>(null);
  const bild = useRef(0);
  const uhr = useRef<ReturnType<typeof setInterval>>();
  const verwerfen = useRef(false);

  const setzen = (wert: DiktatZustand) => {
    setZustand(wert);
    onZustand?.(wert);
  };

  const aufraeumen = () => {
    cancelAnimationFrame(bild.current);
    clearInterval(uhr.current);
    strom.current?.getTracks().forEach(spur => spur.stop());
    strom.current = null;
    void kontext.current?.close().catch(() => {});
    kontext.current = null;
    setPegel([0, 0, 0, 0, 0]);
  };

  useEffect(() => () => {
    verwerfen.current = true;
    if (rekorder.current?.state === "recording") rekorder.current.stop();
    aufraeumen();
  }, []);

  const auswerten = async () => {
    const aufnahme = new Blob(stuecke.current, { type: rekorder.current?.mimeType || "audio/webm" });
    rekorder.current = null;
    if (verwerfen.current || aufnahme.size < 800) {
      setzen("aus");
      return;
    }
    setzen("wandelt");
    try {
      const text = await sprachText(await alsWav(aufnahme));
      if (text) onText(text);
      else onFehler?.("Ich habe nichts verstanden. Sprich etwas lauter oder näher am Mikrofon.");
    } catch (e) {
      onFehler?.(e instanceof Error ? e.message : "Die Spracherkennung hat nicht geklappt.");
    } finally {
      setzen("aus");
    }
  };

  const starten = async () => {
    onFehler?.("");
    try {
      const neu = await mikrofonOeffnen({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 } });
      strom.current = neu;
      const ton = new AudioContext();
      kontext.current = ton;
      const analyse = ton.createAnalyser();
      analyse.fftSize = 256;
      ton.createMediaStreamSource(neu).connect(analyse);
      const werte = new Uint8Array(analyse.frequencyBinCount);
      const zeichnen = () => {
        analyse.getByteFrequencyData(werte);
        const breite = Math.floor(werte.length / 5);
        setPegel(Array.from({ length: 5 }, (_, i) => {
          let summe = 0;
          for (let j = i * breite; j < (i + 1) * breite; j++) summe += werte[j];
          return Math.min(1, summe / breite / 140);
        }));
        bild.current = requestAnimationFrame(zeichnen);
      };
      zeichnen();
      const aufnahme = new MediaRecorder(neu);
      stuecke.current = [];
      verwerfen.current = false;
      aufnahme.ondataavailable = ereignis => {if (ereignis.data.size) stuecke.current.push(ereignis.data);};
      aufnahme.onstop = () => {aufraeumen(); void auswerten();};
      rekorder.current = aufnahme;
      aufnahme.start(250);
      setSekunden(0);
      const beginn = Date.now();
      uhr.current = setInterval(() => {
        const vergangen = Math.floor((Date.now() - beginn) / 1000);
        setSekunden(vergangen);
        if (vergangen >= MAX_SEKUNDEN) stoppen();
      }, 250);
      setzen("hoert");
    } catch (e) {
      aufraeumen();
      setzen("aus");
      onFehler?.(e instanceof Error && e.message && !/permission|denied|NotAllowed/i.test(e.name + e.message) ? e.message : "Kein Zugriff auf das Mikrofon. Erlaube das Mikrofon und versuch es noch einmal.");
    }
  };

  const stoppen = (abbrechen = false) => {
    verwerfen.current = abbrechen;
    if (rekorder.current?.state === "recording") rekorder.current.stop();
  };

  useEffect(() => {
    if (zustand !== "hoert") return;
    const taste = (e: KeyboardEvent) => {if (e.key === "Escape") {e.preventDefault(); stoppen(true);}};
    window.addEventListener("keydown", taste, true);
    return () => window.removeEventListener("keydown", taste, true);
  }, [zustand]);

  const zeit = `${Math.floor(sekunden / 60)}:${String(sekunden % 60).padStart(2, "0")}`;

  if (zustand === "hoert") return <div className="dk-aufnahme" role="group" aria-label="Sprachaufnahme läuft">
    <span className="dk-pegel" aria-hidden>{pegel.map((wert, i) => <i key={i} style={{ transform: `scaleY(${0.18 + wert * 0.82})` }} />)}</span>
    <span className="dk-zeit">{zeit}</span>
    <button type="button" className="dk-stopp" onClick={() => stoppen()} title="Aufnahme beenden und in Text umwandeln" aria-label="Aufnahme beenden und in Text umwandeln"><Square size={12} fill="currentColor" /></button>
  </div>;

  return <button type="button" className={"dk-knopf " + (zustand === "wandelt" ? "wandelt" : "")} disabled={disabled || zustand === "wandelt"} onClick={() => void starten()} title="Sprechen statt tippen: Jon schreibt mit, was du sagst" aria-label={zustand === "wandelt" ? "Sprache wird in Text umgewandelt" : "Sprachnachricht als Text aufnehmen"}>
    {zustand === "wandelt" ? <Loader2 size={16} className="dk-dreh" /> : <Mic size={16} />}
  </button>;
}
