import {getStore} from "@netlify/blobs";
import {Fehler, funktion, geraetPruefen, jetzt, lesen} from "../lib/basis.mjs";

export const MAX_ZEICHEN = 4_000_000;

export async function verarbeiten({aktion, token, geraet, daten}, speicher) {
  const id = geraetPruefen(geraet);
  const inhalt = lesen(token);
  if (inhalt.exp && inhalt.exp < jetzt()) throw new Fehler(402, "Deine Lizenz ist abgelaufen. Jon erneuert sie automatisch, sobald dein Abo aktiv ist.");
  if (!(inhalt.geraete || []).includes(id)) throw new Fehler(403, "Dieses Gerät ist für die Lizenz nicht freigeschaltet.");
  const schluessel = inhalt.quelle === "codes" ? (inhalt.pk ? `admin-${inhalt.pk}` : inhalt.stufe === "entwickler" ? `entwickler-${inhalt.code}` : `code-${inhalt.code}`) : inhalt.stufe === "admin" ? `admin-${inhalt.pk}` : `kunde-${inhalt.kunde}`;
  if (aktion === "hochladen") {
    if (typeof daten !== "string" || !daten.length) throw new Fehler(400, "Keine Sicherung übergeben.");
    if (daten.length > MAX_ZEICHEN) throw new Fehler(413, "Die Sicherung ist größer als 4 MB.");
    const zeit = jetzt();
    await speicher.set(schluessel, daten, {metadata: {zeit, geraet: id, groesse: daten.length}});
    return {zeit, groesse: daten.length};
  }
  if (aktion === "info") {
    const eintrag = await speicher.getMetadata(schluessel);
    return eintrag ? {zeit: eintrag.metadata?.zeit || 0, groesse: eintrag.metadata?.groesse || 0, geraet: eintrag.metadata?.geraet || ""} : {zeit: 0};
  }
  if (aktion === "holen") {
    const wert = await speicher.get(schluessel, {type: "text"});
    if (!wert) throw new Fehler(404, "Es gibt noch keine Cloud-Sicherung.");
    return {daten: wert};
  }
  throw new Fehler(400, "Unbekannte Aktion.");
}

export default funktion(daten => verarbeiten(daten, getStore({name: "jon-sicherung", consistency: "strong"})));
