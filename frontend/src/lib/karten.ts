import type { ChatCard } from "../components/MessageBubble";

export const KARTEN_ARTEN = ["maps", "deep_learning", "bild", "browser"] as const;

export type KartenArt = (typeof KARTEN_ARTEN)[number];

export function istKarte(art: string | undefined | null): art is KartenArt {
  return !!art && (KARTEN_ARTEN as readonly string[]).includes(art);
}

export function karteBauen(
  art: string,
  daten: Record<string, unknown>,
  laufend: number,
  kennung: () => number | string
): ChatCard | null {
  if (!istKarte(art)) return null;
  return {
    id: `${art}-${laufend}-${kennung()}`,
    kind: art,
    data: daten,
  } as unknown as ChatCard;
}

export function karteAnhaengen(
  vorhandene: ChatCard[] | undefined,
  karte: { kind: string; data: Record<string, unknown> } | undefined,
  kennung: () => number | string
): ChatCard[] {
  const liste = [...(vorhandene ?? [])];
  if (!karte) return liste;
  const neu = karteBauen(karte.kind, karte.data, liste.length, kennung);
  if (neu) liste.push(neu);
  return liste;
}

export function kartenLesen(
  roh: string | null | undefined,
  kennung: () => number | string
): ChatCard[] {
  if (!roh) return [];
  try {
    const daten = JSON.parse(roh);
    if (!Array.isArray(daten)) return [];
    const liste: ChatCard[] = [];
    for (const eintrag of daten) {
      const karte = karteBauen(
        String(eintrag?.kind ?? ""),
        (eintrag?.data ?? {}) as Record<string, unknown>,
        liste.length,
        kennung
      );
      if (karte) liste.push(karte);
    }
    return liste;
  } catch {
    return [];
  }
}
