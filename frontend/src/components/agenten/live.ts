import {useCallback, useEffect, useRef, useState} from "react";
import {Anfrage, fehlerText} from "./daten";

export function useLive<T>(request: Anfrage, pfad: string | null, fertig: (wert: T) => boolean, takt = 1000) {
  const [daten, setDaten] = useState<T | null>(null);
  const [fehler, setFehler] = useState("");
  const [fehlversuche, setFehlversuche] = useState(0);
  const [runde, setRunde] = useState(0);
  const fertigRef = useRef(fertig);
  fertigRef.current = fertig;
  useEffect(() => {
    if (!pfad) return;
    let aktiv = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let fehlschlaege = 0;
    const laden = async () => {
      if (!aktiv) return;
      if (typeof document !== "undefined" && document.hidden) {
        timer = setTimeout(laden, takt * 3);
        return;
      }
      let weiter = true;
      try {
        const wert: T = await request(pfad);
        if (!aktiv) return;
        fehlschlaege = 0;
        setDaten(wert);
        setFehler("");
        setFehlversuche(0);
        weiter = !fertigRef.current(wert);
      } catch (e) {
        if (!aktiv) return;
        fehlschlaege += 1;
        setFehlversuche(fehlschlaege);
        setFehler(fehlerText(e));
        weiter = fehlschlaege < 14;
      }
      if (aktiv && weiter) timer = setTimeout(laden, fehlschlaege ? Math.min(takt * (1 + fehlschlaege), 6000) : takt);
    };
    void laden();
    return () => {
      aktiv = false;
      if (timer) clearTimeout(timer);
    };
  }, [request, pfad, takt, runde]);
  const neu = useCallback(() => setRunde(n => n + 1), []);
  return {daten, setDaten, fehler, fehlversuche, neu};
}

export function useJetzt(aktiv: boolean) {
  const [jetzt, setJetzt] = useState(() => Date.now() / 1000);
  useEffect(() => {
    if (!aktiv) return;
    setJetzt(Date.now() / 1000);
    const timer = setInterval(() => setJetzt(Date.now() / 1000), 1000);
    return () => clearInterval(timer);
  }, [aktiv]);
  return jetzt;
}
