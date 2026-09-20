export const MIKROFON_FEHLT =
  "Dieser Browser gibt kein Mikrofon frei. Über eine Netzwerkadresse wie " +
  "http://192.168.x.x erlauben Browser den Mikrofonzugriff nicht — nur über " +
  "localhost oder https.";

export function unsichereHerkunft(): boolean {
  if (typeof window === "undefined") return false;
  if (window.isSecureContext) return false;
  return window.location.protocol === "http:";
}

export function medienGeraete(): MediaDevices | null {
  if (typeof navigator === "undefined") return null;
  const geraete = navigator.mediaDevices;
  if (!geraete || typeof geraete.getUserMedia !== "function") return null;
  return geraete;
}

export function mikrofonMoeglich(): boolean {
  return medienGeraete() !== null;
}

export async function mikrofonOeffnen(
  vorgabe: MediaStreamConstraints
): Promise<MediaStream> {
  const geraete = medienGeraete();
  if (!geraete) throw new Error(MIKROFON_FEHLT);
  return geraete.getUserMedia(vorgabe);
}

export async function geraeteListe(): Promise<MediaDeviceInfo[]> {
  const geraete = medienGeraete();
  if (!geraete || typeof geraete.enumerateDevices !== "function") return [];
  try {
    return await geraete.enumerateDevices();
  } catch {
    return [];
  }
}

export function aufGeraetewechsel(hoerer: () => void): () => void {
  const geraete = medienGeraete();
  if (!geraete || typeof geraete.addEventListener !== "function") {
    return () => undefined;
  }
  geraete.addEventListener("devicechange", hoerer);
  return () => {
    try {
      geraete.removeEventListener("devicechange", hoerer);
    } catch {
      return;
    }
  };
}

async function ueberFeld(text: string): Promise<boolean> {
  if (typeof document === "undefined") return false;
  const feld = document.createElement("textarea");
  feld.value = text;
  feld.setAttribute("readonly", "");
  feld.style.position = "fixed";
  feld.style.top = "-1000px";
  feld.style.opacity = "0";
  document.body.appendChild(feld);
  feld.select();
  feld.setSelectionRange(0, feld.value.length);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  feld.remove();
  return ok;
}

export async function inZwischenablage(text: string): Promise<boolean> {
  const ablage = typeof navigator !== "undefined" ? navigator.clipboard : null;
  if (ablage && typeof ablage.writeText === "function") {
    try {
      await ablage.writeText(text);
      return true;
    } catch {
      return ueberFeld(text);
    }
  }
  return ueberFeld(text);
}
