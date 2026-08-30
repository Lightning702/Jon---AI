const ZELLEN_TRENNER = /^:?-{2,}:?$/;

function istZeile(zeile: string): boolean {
  const roh = zeile.trim();
  return roh.startsWith("|") && (roh.match(/\|/g)?.length ?? 0) >= 2;
}

function zellen(zeile: string): string[] {
  return zeile
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((teil) => teil.trim());
}

function istTrenner(zeile: string): boolean {
  if (!istZeile(zeile)) return false;
  const felder = zellen(zeile);
  return felder.length > 0 && felder.every((feld) => ZELLEN_TRENNER.test(feld));
}

function schmuckLos(text: string): string {
  return text.replace(/\*+/g, "").replace(/^_+|_+$/g, "").trim();
}

function zeileAlsListe(kopf: string[], werte: string[]): string[] {
  const gefuellt = werte.map((wert) => wert.trim());
  if (gefuellt.every((wert) => !wert)) return [];
  if (gefuellt.length <= 2) {
    const [links, rechts] = gefuellt;
    return [rechts ? `- ${links}: ${rechts}` : `- ${links}`];
  }
  const zeilen = [`- ${gefuellt[0]}`];
  for (let i = 1; i < gefuellt.length; i += 1) {
    if (!gefuellt[i]) continue;
    const label = schmuckLos(kopf[i] ?? "");
    zeilen.push(label ? `   ${label}: ${gefuellt[i]}` : `   ${gefuellt[i]}`);
  }
  return zeilen;
}

function wandleBlock(block: string): string {
  const zeilen = block.split("\n");
  const raus: string[] = [];
  let i = 0;
  while (i < zeilen.length) {
    if (
      istZeile(zeilen[i]) &&
      i + 1 < zeilen.length &&
      istTrenner(zeilen[i + 1])
    ) {
      const kopf = zellen(zeilen[i]);
      i += 2;
      while (i < zeilen.length && istZeile(zeilen[i]) && !istTrenner(zeilen[i])) {
        raus.push(...zeileAlsListe(kopf, zellen(zeilen[i])));
        i += 1;
      }
      continue;
    }
    raus.push(zeilen[i]);
    i += 1;
  }
  return raus.join("\n");
}

export function ohneTabellen(text: string): string {
  if (!text.includes("|")) return text;
  const teile = text.split("```");
  for (let i = 0; i < teile.length; i += 2) {
    teile[i] = wandleBlock(teile[i]);
  }
  return teile.join("```");
}
