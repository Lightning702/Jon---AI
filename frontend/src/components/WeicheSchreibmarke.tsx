import { useEffect, useRef, useState } from "react";
import { useWeicheSchreibmarke } from "../lib/schreibmarke";

type Feld = HTMLInputElement | HTMLTextAreaElement;

const TEXTARTEN = new Set(["text", "search", "email", "url", "tel", "password", ""]);

const UEBERNOMMEN = [
  "boxSizing",
  "width",
  "paddingTop",
  "paddingRight",
  "paddingBottom",
  "paddingLeft",
  "borderTopWidth",
  "borderRightWidth",
  "borderBottomWidth",
  "borderLeftWidth",
  "borderStyle",
  "fontFamily",
  "fontSize",
  "fontWeight",
  "fontStyle",
  "letterSpacing",
  "lineHeight",
  "textTransform",
  "wordSpacing",
  "textIndent",
  "tabSize",
] as const;

function passt(el: Element | null): el is Feld {
  if (!el) return false;
  if (el instanceof HTMLTextAreaElement) return !el.readOnly && !el.disabled && el.dataset.keineMarke === undefined;
  if (el instanceof HTMLInputElement) return TEXTARTEN.has(el.type) && !el.readOnly && !el.disabled && el.dataset.keineMarke === undefined;
  return false;
}

type Lage = { x: number; y: number; hoehe: number; sichtbar: boolean };

export default function WeicheSchreibmarke() {
  const aktiv = useWeicheSchreibmarke();
  const [feld, setFeld] = useState<Feld | null>(null);
  const [lage, setLage] = useState<Lage>({ x: 0, y: 0, hoehe: 18, sichtbar: false });
  const [tippt, setTippt] = useState(false);
  const ruhe = useRef(0);
  const bild = useRef(0);

  useEffect(() => {
    if (!aktiv) {
      setFeld(null);
      return;
    }
    const rein = (e: FocusEvent) => {
      const ziel = e.target as Element | null;
      if (passt(ziel)) setFeld(ziel);
    };
    const raus = () => {
      window.setTimeout(() => {
        const jetzt = document.activeElement;
        setFeld(passt(jetzt) ? jetzt : null);
      }, 0);
    };
    const pruefen = () => {
      const jetzt = document.activeElement;
      setFeld(passt(jetzt) ? jetzt : null);
    };
    document.addEventListener("focusin", rein);
    document.addEventListener("focusout", raus);
    window.addEventListener("focus", pruefen);
    document.addEventListener("pointerup", pruefen);
    pruefen();
    return () => {
      document.removeEventListener("focusin", rein);
      document.removeEventListener("focusout", raus);
      window.removeEventListener("focus", pruefen);
      document.removeEventListener("pointerup", pruefen);
    };
  }, [aktiv]);

  useEffect(() => {
    const el = feld;
    if (!el || !aktiv) return;
    const alteFarbe = el.style.caretColor;
    el.style.caretColor = "transparent";
    const spiegel = document.createElement("div");
    spiegel.setAttribute("aria-hidden", "true");
    document.body.appendChild(spiegel);
    const einzeilig = el instanceof HTMLInputElement;
    let letzte = "";

    const messen = () => {
      bild.current = 0;
      if (!el.isConnected) return;
      const stil = getComputedStyle(el);
      const s = spiegel.style as unknown as Record<string, string>;
      for (const name of UEBERNOMMEN) s[name] = stil[name] as string;
      Object.assign(spiegel.style, {
        position: "absolute",
        visibility: "hidden",
        top: "0",
        left: "-99999px",
        whiteSpace: einzeilig ? "pre" : "pre-wrap",
        overflowWrap: einzeilig ? "normal" : "break-word",
        wordBreak: einzeilig ? "normal" : "break-word",
        overflow: "hidden",
        height: "auto",
        width: einzeilig ? "auto" : stil.width,
      });
      const wert = el instanceof HTMLInputElement && el.type === "password" ? "•".repeat(el.value.length) : el.value;
      const stelle = el.selectionEnd ?? wert.length;
      spiegel.textContent = wert.slice(0, stelle);
      const marke = document.createElement("span");
      marke.textContent = wert.slice(stelle, stelle + 1) || "​";
      spiegel.appendChild(marke);
      const rahmen = el.getBoundingClientRect();
      const schrift = parseFloat(stil.fontSize) || 15;
      const zeile = parseFloat(stil.lineHeight) || schrift * 1.3;
      const hoehe = Math.min(einzeilig ? schrift * 1.3 : zeile, rahmen.height);
      const rand = parseFloat(stil.borderLeftWidth) || 0;
      const oben = parseFloat(stil.borderTopWidth) || 0;
      const sichtbar =
        document.activeElement === el &&
        el.selectionStart === el.selectionEnd &&
        rahmen.width > 0 &&
        rahmen.height > 0;
      const x = rahmen.left + rand + marke.offsetLeft - el.scrollLeft;
      const y = einzeilig
        ? rahmen.top + (rahmen.height - hoehe) / 2
        : rahmen.top + oben + marke.offsetTop - el.scrollTop + Math.max(0, (marke.offsetHeight - zeile) / 2);
      const innerhalb = x >= rahmen.left - 1 && x <= rahmen.right + 1 && y >= rahmen.top - hoehe && y <= rahmen.bottom;
      const schluessel = `${Math.round(x)}|${Math.round(y)}|${Math.round(hoehe)}|${sichtbar && innerhalb}`;
      if (schluessel === letzte) return;
      letzte = schluessel;
      setLage({ x, y, hoehe, sichtbar: sichtbar && innerhalb });
    };

    const planen = () => {
      if (!bild.current) bild.current = requestAnimationFrame(messen);
    };

    const getippt = () => {
      setTippt(true);
      window.clearTimeout(ruhe.current);
      ruhe.current = window.setTimeout(() => setTippt(false), 550);
      planen();
    };

    for (const name of ["focus", "blur", "click", "mouseup", "scroll", "select"]) el.addEventListener(name, planen);
    el.addEventListener("input", getippt);
    el.addEventListener("keydown", getippt);
    document.addEventListener("selectionchange", planen);
    document.addEventListener("scroll", planen, true);
    window.addEventListener("resize", planen);
    const beobachter = new ResizeObserver(planen);
    beobachter.observe(el);
    const takt = window.setInterval(planen, 250);
    planen();

    return () => {
      el.style.caretColor = alteFarbe;
      spiegel.remove();
      beobachter.disconnect();
      window.clearInterval(takt);
      for (const name of ["focus", "blur", "click", "mouseup", "scroll", "select"]) el.removeEventListener(name, planen);
      el.removeEventListener("input", getippt);
      el.removeEventListener("keydown", getippt);
      document.removeEventListener("selectionchange", planen);
      document.removeEventListener("scroll", planen, true);
      window.removeEventListener("resize", planen);
      window.clearTimeout(ruhe.current);
      if (bild.current) cancelAnimationFrame(bild.current);
      bild.current = 0;
      setLage((l) => ({ ...l, sichtbar: false }));
    };
  }, [feld, aktiv]);

  if (!aktiv || !feld || !lage.sichtbar) return null;
  return (
    <span
      aria-hidden="true"
      className={`weiche-marke${tippt ? " tippt" : ""}`}
      style={{ transform: `translate3d(${lage.x}px, ${lage.y}px, 0)`, height: lage.hoehe }}
    />
  );
}
