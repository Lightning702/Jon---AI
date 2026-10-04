import { BASE } from "./api";

const RATE = 16000;

function wavKodieren(samples: Float32Array, rate: number): Blob {
  const puffer = new ArrayBuffer(44 + samples.length * 2);
  const sicht = new DataView(puffer);
  const text = (stelle: number, wert: string) => {for (let i = 0; i < wert.length; i++) sicht.setUint8(stelle + i, wert.charCodeAt(i));};
  text(0, "RIFF");
  sicht.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  sicht.setUint32(16, 16, true);
  sicht.setUint16(20, 1, true);
  sicht.setUint16(22, 1, true);
  sicht.setUint32(24, rate, true);
  sicht.setUint32(28, rate * 2, true);
  sicht.setUint16(32, 2, true);
  sicht.setUint16(34, 16, true);
  text(36, "data");
  sicht.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const wert = Math.max(-1, Math.min(1, samples[i]));
    sicht.setInt16(44 + i * 2, wert < 0 ? wert * 0x8000 : wert * 0x7fff, true);
  }
  return new Blob([puffer], { type: "audio/wav" });
}

export async function alsWav(aufnahme: Blob): Promise<Blob> {
  const kontext = new AudioContext();
  try {
    const roh = await kontext.decodeAudioData(await aufnahme.arrayBuffer());
    const laenge = Math.max(1, Math.ceil(roh.duration * RATE));
    const offline = new OfflineAudioContext(1, laenge, RATE);
    const quelle = offline.createBufferSource();
    quelle.buffer = roh;
    quelle.connect(offline.destination);
    quelle.start();
    const fertig = await offline.startRendering();
    return wavKodieren(fertig.getChannelData(0), RATE);
  } finally {
    void kontext.close();
  }
}

export async function sprachText(wav: Blob): Promise<string> {
  const antwort = await fetch(`${BASE}/system/transcribe`, { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: wav, signal: AbortSignal.timeout(120000) });
  const daten = await antwort.json().catch(() => ({}));
  if (!antwort.ok) throw new Error(typeof daten.detail === "string" ? `Die Spracherkennung hat nicht geklappt: ${daten.detail}` : "Die Spracherkennung hat nicht geklappt.");
  return typeof daten.text === "string" ? daten.text.trim() : "";
}
