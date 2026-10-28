import { useEffect, useRef, useState } from "react";
import { useWeicheSchreibmarke } from "../lib/schreibmarke";

type Feld = HTMLInputElement | HTMLTextAreaElement;

const TEXTARTEN = new Set(["text", "search", "email", "url", "tel", "password", ""]);

const UEBERNOMMEN = [
  "padding-top",
  "padding-right",
  "padding-bottom",
  "padding-left",
  "font-family",
  "font-size",
  "font-weight",
  "font-style",
  "font-stretch",
  "font-kerning",
  "font-feature-settings",
  "font-variation-settings",
  "font-optical-sizing",
  "font-size-adjust",
  "font-variant-ligatures",
  "font-variant-caps",
  "font-variant-numeric",
  "font-variant-east-asian",
  "letter-spacing",
  "word-spacing",
  "line-height",
  "text-transform",
  "text-indent",
  "text-align",
  "text-rendering",
  "tab-size",
  "direction",
  "hyphens",
] as const;

const NULLBREITE = "​";

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
      for (const name of UEBERNOMMEN) spiegel.style.setProperty(name, stil.getPropertyValue(name));
      const zahl = (name: string) => parseFloat(stil.getPropertyValue(name)) || 0;
      const randLinks = zahl("border-left-width");
      const randOben = zahl("border-top-width");
      const raender = randLinks + zahl("border-right-width");
      const polster = zahl("padding-left") + zahl("padding-right");
      const leiste = Math.max(0, el.offsetWidth - el.clientWidth - raender);
      const breite = Math.max(0, (parseFloat(stil.width) || el.clientWidth) - leiste - (stil.boxSizing === "border-box" ? polster + raender : 0));
      Object.assign(spiegel.style, {
        position: "fixed",
        visibility: "hidden",
        pointerEvents: "none",
        top: "0",
        left: "-99999px",
        margin: "0",
        border: "0",
        boxSizing: "content-box",
        overflow: "hidden",
        height: "auto",
        width: `${breite}px`,
        whiteSpace: einzeilig ? "pre" : stil.whiteSpace,
        wordBreak: einzeilig ? "normal" : stil.wordBreak,
        overflowWrap: einzeilig ? "normal" : stil.overflowWrap,
      });
      const wert = el instanceof HTMLInputElement && el.type === "password" ? "•".repeat(el.value.length) : el.value;
      const stelle = el.selectionEnd ?? wert.length;
      const marke = document.createElement("span");
      marke.textContent = wert.slice(stelle, stelle + 1) || NULLBREITE;
      spiegel.replaceChildren(wert.slice(0, stelle), marke, wert.slice(stelle + 1) + NULLBREITE);
      const rahmen = el.getBoundingClientRect();
      const spiegelRahmen = spiegel.getBoundingClientRect();
      const teil = marke.getClientRects()[0] ?? marke.getBoundingClientRect();
      const schrift = parseFloat(stil.fontSize) || 15;
      const hoehe = Math.min(teil.height || schrift * 1.3, rahmen.height);
      const x = rahmen.left + randLinks + (teil.left - spiegelRahmen.left) - el.scrollLeft;
      let y: number;
      let verlaesslich = true;
      if (einzeilig) {
        const innenOben = rahmen.top + randOben + zahl("padding-top");
        const innenHoehe = el.clientHeight - zahl("padding-top") - zahl("padding-bottom");
        y = innenOben + (innenHoehe - hoehe) / 2;
      } else {
        y = rahmen.top + randOben + (teil.top - spiegelRahmen.top) - el.scrollTop;
        const inhalt = spiegelRahmen.height;
        verlaesslich =
          el.scrollHeight > el.clientHeight + 1
            ? Math.abs(inhalt - el.scrollHeight) <= 3
            : inhalt <= el.clientHeight + 3;
      }
      const farbe = verlaesslich ? "transparent" : alteFarbe;
      if (el.style.caretColor !== farbe) el.style.caretColor = farbe;
      const sichtbar =
        verlaesslich &&
        document.activeElement === el &&
        el.selectionStart === el.selectionEnd &&
        rahmen.width > 0 &&
        rahmen.height > 0;
      const innerhalb =
        x >= rahmen.left - 1 &&
        x <= rahmen.right + 1 &&
        y >= rahmen.top - hoehe / 2 &&
        y + hoehe <= rahmen.bottom + hoehe / 2;
      const schluessel = `${x.toFixed(1)}|${y.toFixed(1)}|${hoehe.toFixed(1)}|${sichtbar && innerhalb}`;
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
