const ZEICHEN = ["❤️", "\u{1F497}", "\u{1F496}", "❤️", "\u{1F339}"];

let ebene: HTMLDivElement | null = null;

function ebeneHolen(): HTMLDivElement {
  if (ebene && ebene.isConnected) return ebene;
  ebene = document.createElement("div");
  ebene.className = "jd-herzflug-ebene";
  ebene.setAttribute("aria-hidden", "true");
  document.body.appendChild(ebene);
  return ebene;
}

export function herzenSteigen(x: number, y: number, anzahl = 8, weit = 1): void {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const ziel = ebeneHolen();
  for (let i = 0; i < anzahl; i++) {
    const herz = document.createElement("span");
    herz.className = "jd-herzflug";
    herz.textContent = ZEICHEN[Math.floor(Math.random() * ZEICHEN.length)];
    const dauer = 1.1 + Math.random() * 0.9;
    herz.style.left = `${x}px`;
    herz.style.top = `${y}px`;
    herz.style.fontSize = `${12 + Math.random() * 14}px`;
    herz.style.setProperty("--dx", `${(Math.random() - 0.5) * 140 * weit}px`);
    herz.style.setProperty("--dy", `${-(80 + Math.random() * 120) * weit}px`);
    herz.style.setProperty("--dreh", `${(Math.random() - 0.5) * 50}deg`);
    herz.style.animationDuration = `${dauer}s`;
    herz.style.animationDelay = `${Math.random() * 0.18}s`;
    herz.addEventListener("animationend", () => herz.remove());
    ziel.appendChild(herz);
    window.setTimeout(() => herz.remove(), (dauer + 0.5) * 1000);
  }
}

function herzenAktiv(): boolean {
  return document.documentElement.classList.contains("jd-herzen");
}

function ausKnopf(element: Element | null): void {
  if (!element) return;
  const rahmen = element.getBoundingClientRect();
  herzenSteigen(rahmen.left + rahmen.width / 2, rahmen.top + rahmen.height / 3, 9);
}

export function herzenStarten(): void {
  document.addEventListener(
    "click",
    (ereignis) => {
      if (!herzenAktiv()) return;
      const knopf = (ereignis.target as Element | null)?.closest?.("button.jon-senden");
      if (knopf && !(knopf as HTMLButtonElement).disabled) ausKnopf(knopf);
    },
    true
  );
  document.addEventListener(
    "keydown",
    (ereignis) => {
      if (!herzenAktiv() || ereignis.key !== "Enter" || ereignis.shiftKey || ereignis.isComposing) return;
      const feld = ereignis.target as HTMLTextAreaElement | null;
      if (!feld || feld.tagName !== "TEXTAREA" || !feld.closest(".jon-eingabe") || !feld.value.trim()) return;
      ausKnopf(feld.closest(".jon-eingabe")?.querySelector("button.jon-senden") ?? feld);
    },
    true
  );
}
