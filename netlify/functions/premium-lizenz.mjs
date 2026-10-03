import {adminKennung, adminToken, Fehler, funktion, geraetPruefen, lesen} from "../lib/basis.mjs";
import {AKTIV, geraeteListe, geraetHinzufuegen, premiumToken, stripe} from "../lib/stripe.mjs";

async function aboLaden(id) {
  const abo = await stripe("GET", `subscriptions/${encodeURIComponent(id)}`);
  if (abo.metadata?.jon !== "premium") throw new Fehler(404, "Dieses Abo gehört nicht zu Jon Premium.");
  if (!AKTIV.includes(abo.status)) throw new Fehler(402, "Dein Jon-Premium-Abo ist nicht mehr aktiv. Du kannst es jederzeit neu abschließen.");
  return abo;
}

export async function verarbeiten({aktion, session_id, token, geraet}) {
  if (aktion === "abholen") {
    if (typeof session_id !== "string" || !/^cs_[A-Za-z0-9_]+$/.test(session_id)) throw new Fehler(400, "Ungültige Kauf-ID.");
    const id = geraetPruefen(geraet, false);
    const sitzung = await stripe("GET", `checkout/sessions/${session_id}`, {expand: ["subscription"]});
    if (sitzung.metadata?.jon !== "premium") throw new Fehler(404, "Dieser Kauf gehört nicht zu Jon Premium.");
    if (sitzung.status !== "complete" || !sitzung.subscription) return {offen: true};
    const abo = typeof sitzung.subscription === "string" ? await aboLaden(sitzung.subscription) : sitzung.subscription;
    if (!AKTIV.includes(abo.status)) return {offen: true};
    const geraete = await geraetHinzufuegen(abo, geraeteListe(abo), id);
    return {token: premiumToken(abo, geraete, sitzung.customer_details?.name), geraete: geraete.length};
  }
  const id = geraetPruefen(geraet);
  const inhalt = lesen(token);
  if (aktion === "erneuern" && inhalt.stufe === "admin") {
    if (inhalt.pk !== adminKennung() || !(inhalt.geraete || []).includes(id)) throw new Fehler(403, "Die Admin-Lizenz ist nicht mehr gültig. Melde dich erneut als Admin an.");
    return {token: adminToken(id)};
  }
  if (inhalt.stufe !== "premium" || !inhalt.abo) throw new Fehler(400, "Dieser Lizenzschlüssel gehört zu keinem Abo.");
  const abo = await aboLaden(inhalt.abo);
  let geraete = geraeteListe(abo);
  if (aktion === "geraet") geraete = await geraetHinzufuegen(abo, geraete, id);
  else if (aktion !== "erneuern") throw new Fehler(400, "Unbekannte Aktion.");
  if (!geraete.includes(id)) throw new Fehler(403, "Dieses Gerät ist für die Lizenz nicht freigeschaltet.");
  return {token: premiumToken(abo, geraete, inhalt.name)};
}

export default funktion(verarbeiten);
