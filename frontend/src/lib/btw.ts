import { BASE } from "./api";

export type BtwQuelle = "chat" | "code" | "harness";

export interface BtwKontext {
  quelle: BtwQuelle;
  verlauf?: { role: string; content: string }[];
  taskId?: string;
  nebenbei?: string;
  arbeitet?: boolean;
  nachauftrag?: (text: string) => void;
}

export interface BtwAntwort {
  art: "frage" | "nachauftrag" | "fehler" | "leer" | string;
  antwort: string;
  auftrag?: string;
  nachauftraege?: string[];
}

type Hoerer = (frage: string | null) => void;

const stapel: { id: number; holen: () => BtwKontext }[] = [];
const hoerer = new Set<Hoerer>();
let zaehler = 0;

export const QUELLEN_NAME: Record<BtwQuelle, string> = { chat: "Chat", code: "Jon Code", harness: "Harness" };

export function btwKontextAnmelden(holen: () => BtwKontext): () => void {
  const id = ++zaehler;
  stapel.push({ id, holen });
  return () => {
    const stelle = stapel.findIndex((eintrag) => eintrag.id === id);
    if (stelle >= 0) stapel.splice(stelle, 1);
  };
}

export function btwKontext(): BtwKontext {
  const oben = stapel[stapel.length - 1];
  return oben ? oben.holen() : { quelle: "chat" };
}

export function btwHoeren(neu: Hoerer): () => void {
  hoerer.add(neu);
  return () => {
    hoerer.delete(neu);
  };
}

export function btwOeffnen(frage: string | null = null): void {
  hoerer.forEach((h) => h(frage));
}

export function istBtw(text: string): boolean {
  return /^\/(btw|nebenbei)(\s|$)/i.test(text.trim());
}

export function btwRest(text: string): string {
  return text.trim().replace(/^\/(btw|nebenbei)\s*[:,-]?\s*/i, "");
}

export async function btwFragen(frage: string, kontext: BtwKontext): Promise<BtwAntwort> {
  const antwort = await fetch(`${BASE}/btw`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      frage,
      verlauf: (kontext.verlauf || []).slice(-12).map((e) => ({ role: e.role, content: String(e.content || "").slice(0, 2000) })),
      task_id: kontext.taskId || "",
      nebenbei: String(kontext.nebenbei || "").slice(0, 5000),
    }),
  });
  if (!antwort.ok) throw new Error(`Jon antwortet gerade nicht (${antwort.status}).`);
  return antwort.json();
}
