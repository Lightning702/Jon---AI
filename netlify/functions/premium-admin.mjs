import {adminToken, Fehler, funktion, geraetPruefen, gleich} from "../lib/basis.mjs";

export const warten = ms => new Promise(fertig => setTimeout(fertig, ms));

export async function verarbeiten({passwort, geraet}, pause = warten) {
  const id = geraetPruefen(geraet);
  const soll = process.env.JON_ADMIN_PASSWORT || "";
  if (soll.length < 12) throw new Fehler(503, "Die Admin-Anmeldung ist nicht eingerichtet. Setze JON_ADMIN_PASSWORT (mindestens 12 Zeichen) in Netlify.");
  if (typeof passwort !== "string" || !gleich(passwort, soll)) {
    await pause(1500);
    throw new Fehler(403, "Falsches Admin-Passwort.");
  }
  return {token: adminToken(id)};
}

export default funktion(daten => verarbeiten(daten));
