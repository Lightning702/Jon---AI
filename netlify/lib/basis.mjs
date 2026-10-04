import {createHash, createPrivateKey, createPublicKey, sign, timingSafeEqual, verify} from "node:crypto";

export class Fehler extends Error {
  constructor(status, text) {
    super(text);
    this.status = status;
  }
}

export const CODE_OEFFENTLICH = "dkdz3y9XOspsQOQdubK5s2rqZ0L4+hkwqWzq1EuWuyQ=";
export const TAG = 86400;
export const MAX_GERAETE = 3;
export const jetzt = () => Math.floor(Date.now() / 1000);
export const seite = () => (process.env.JON_SEITE || process.env.URL || "https://getjon.netlify.app").replace(/\/$/, "");

const b64url = daten => Buffer.from(daten).toString("base64url");

export function antwort(daten, status = 200) {
  return new Response(JSON.stringify(daten), {status, headers: {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}});
}

export function funktion(verarbeiten) {
  return async (req, context) => {
    if (req.method !== "POST") return antwort({fehler: "Nur POST ist erlaubt."}, 405);
    let daten;
    try {
      daten = await req.json();
    } catch {
      return antwort({fehler: "Ungültige Anfrage."}, 400);
    }
    if (!daten || typeof daten !== "object" || Array.isArray(daten)) return antwort({fehler: "Ungültige Anfrage."}, 400);
    try {
      return antwort(await verarbeiten(daten, context));
    } catch (e) {
      if (e instanceof Fehler) return antwort({fehler: e.message}, e.status);
      console.error(e);
      return antwort({fehler: "Interner Fehler im Lizenzserver."}, 500);
    }
  };
}

export function geraetPruefen(geraet, pflicht = true) {
  if (!geraet && !pflicht) return "";
  if (typeof geraet !== "string" || !/^[a-f0-9]{20}$/.test(geraet)) throw new Fehler(400, "Ungültige Geräte-ID.");
  return geraet;
}

function privat() {
  const wert = process.env.JON_LIZENZ_SCHLUESSEL;
  if (!wert) throw new Fehler(503, "JON_LIZENZ_SCHLUESSEL fehlt in den Netlify-Umgebungsvariablen.");
  try {
    return createPrivateKey({key: Buffer.from(wert, "base64"), format: "der", type: "pkcs8"});
  } catch {
    throw new Fehler(503, "JON_LIZENZ_SCHLUESSEL ist kein gültiger Schlüssel.");
  }
}

export function signieren(inhalt) {
  const kopf = `JON1.${b64url(JSON.stringify({...inhalt, iat: jetzt()}))}`;
  return `${kopf}.${b64url(sign(null, Buffer.from(kopf), privat()))}`;
}

export function codeSchluessel() {
  const wert = process.env.JON_CODE_OEFFENTLICH || CODE_OEFFENTLICH;
  if (!wert) return null;
  return createPublicKey({key: Buffer.concat([Buffer.from("302a300506032b6570032100", "hex"), Buffer.from(wert, "base64")]), format: "der", type: "spki"});
}

export function lesen(token) {
  const teile = typeof token === "string" ? token.trim().split(".") : [];
  if (teile.length !== 3 || teile[0] !== "JON1") throw new Fehler(400, "Das ist kein gültiger Jon-Lizenzschlüssel.");
  const kopf = `${teile[0]}.${teile[1]}`;
  let inhalt;
  try {
    inhalt = JSON.parse(Buffer.from(teile[1], "base64url").toString("utf8"));
  } catch {
    throw new Fehler(400, "Das ist kein gültiger Jon-Lizenzschlüssel.");
  }
  const vomCodeserver = inhalt?.quelle === "codes";
  let gueltig = false;
  try {
    const schluessel = vomCodeserver ? codeSchluessel() : createPublicKey(privat());
    gueltig = !!schluessel && verify(null, Buffer.from(kopf), schluessel, Buffer.from(teile[2], "base64url"));
  } catch (e) {
    if (e instanceof Fehler) throw e;
  }
  if (!gueltig) throw new Fehler(403, "Die Signatur des Lizenzschlüssels ist ungültig.");
  if (!(vomCodeserver ? ["admin", "entwickler"] : ["premium", "admin"]).includes(inhalt.stufe)) throw new Fehler(400, "Der Lizenzschlüssel enthält keine gültige Stufe.");
  return inhalt;
}

export function gleich(a, b) {
  const x = createHash("sha256").update(String(a)).digest();
  const y = createHash("sha256").update(String(b)).digest();
  return timingSafeEqual(x, y);
}

export function adminKennung() {
  const passwort = process.env.JON_ADMIN_PASSWORT || "";
  if (passwort.length < 12) throw new Fehler(503, "Die Admin-Anmeldung ist nicht eingerichtet. Setze JON_ADMIN_PASSWORT (mindestens 12 Zeichen) in Netlify.");
  return createHash("sha256").update(`jon-admin:${passwort}`).digest("hex").slice(0, 16);
}

export function adminToken(geraet) {
  return signieren({stufe: "admin", name: "Admin", geraete: [geraet], exp: jetzt() + 90 * TAG, pk: adminKennung()});
}
