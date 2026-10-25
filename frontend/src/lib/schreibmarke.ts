import { useEffect, useState } from "react";

const SCHLUESSEL = "jon_weiche_schreibmarke";
const EREIGNIS = "jon-schreibmarke";

export function weicheSchreibmarke(): boolean {
  try {
    return localStorage.getItem(SCHLUESSEL) !== "aus";
  } catch {
    return true;
  }
}

export function weicheSchreibmarkeSetzen(an: boolean): void {
  try {
    localStorage.setItem(SCHLUESSEL, an ? "an" : "aus");
  } catch {
    return;
  } finally {
    window.dispatchEvent(new CustomEvent(EREIGNIS));
  }
}

export function useWeicheSchreibmarke(): boolean {
  const [an, setAn] = useState(weicheSchreibmarke);
  useEffect(() => {
    const neu = () => setAn(weicheSchreibmarke());
    window.addEventListener(EREIGNIS, neu);
    window.addEventListener("storage", neu);
    return () => {
      window.removeEventListener(EREIGNIS, neu);
      window.removeEventListener("storage", neu);
    };
  }, []);
  return an;
}
