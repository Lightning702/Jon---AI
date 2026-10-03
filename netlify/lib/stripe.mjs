import {Fehler, jetzt, MAX_GERAETE, signieren, TAG} from "./basis.mjs";

export const PLAENE = {
  monat: {cent: Number(process.env.JON_PREIS_MONAT_CENT || 699), intervall: "month", name: "Jon Premium monatlich"},
  jahr: {cent: Number(process.env.JON_PREIS_JAHR_CENT || 5999), intervall: "year", name: "Jon Premium jährlich"},
};
export const AKTIV = ["active", "trialing", "past_due"];

function formular(werte, vorne = "", ausgabe = new URLSearchParams()) {
  for (const [schluessel, wert] of Object.entries(werte)) {
    if (wert === undefined || wert === null) continue;
    const name = vorne ? `${vorne}[${schluessel}]` : schluessel;
    if (Array.isArray(wert)) wert.forEach((eintrag, i) => eintrag !== null && typeof eintrag === "object" ? formular(eintrag, `${name}[${i}]`, ausgabe) : ausgabe.append(`${name}[${i}]`, String(eintrag)));
    else if (typeof wert === "object") formular(wert, name, ausgabe);
    else ausgabe.append(name, String(wert));
  }
  return ausgabe;
}

function erklaeren(text) {
  const klein = text.toLowerCase();
  if (klein.includes("tax") && (klein.includes("activat") || klein.includes("head office") || klein.includes("origin") || klein.includes("settings"))) return `${text} Richte Stripe Tax im Dashboard ein: Einstellungen → Steuern → Firmenadresse und Registrierungen.`;
  if (klein.includes("portal") || klein.includes("configuration")) return `${text} Speichere im Stripe-Dashboard einmal Einstellungen → Billing → Kundenportal.`;
  return text;
}

export async function stripe(methode, pfad, werte = {}, idempotenz = "") {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) throw new Fehler(503, "STRIPE_SECRET_KEY fehlt in den Netlify-Umgebungsvariablen.");
  const basis = (process.env.STRIPE_API_BASE || "https://api.stripe.com").replace(/\/$/, "");
  const koerper = formular(werte).toString();
  const kopf = {Authorization: `Bearer ${key}`};
  if (methode !== "GET") kopf["Content-Type"] = "application/x-www-form-urlencoded";
  if (idempotenz) kopf["Idempotency-Key"] = idempotenz;
  let r;
  try {
    r = await fetch(`${basis}/v1/${pfad}${methode === "GET" && koerper ? `?${koerper}` : ""}`, {method: methode, headers: kopf, body: methode === "GET" ? undefined : koerper});
  } catch {
    throw new Fehler(502, "Stripe ist gerade nicht erreichbar. Bitte versuche es gleich noch einmal.");
  }
  const daten = await r.json().catch(() => ({}));
  if (!r.ok) throw new Fehler(r.status >= 500 ? 502 : r.status === 404 ? 404 : 400, erklaeren(daten?.error?.message || `Stripe antwortet mit Fehler ${r.status}.`));
  return daten;
}

export async function produkt() {
  const liste = await stripe("GET", "products", {active: true, limit: 100});
  const vorhanden = (liste.data || []).find(p => p.metadata?.jon === "premium");
  if (vorhanden) return vorhanden.id;
  const neu = await stripe("POST", "products", {name: "Jon Premium", description: "Alle Premium-Funktionen von Jon: Harness Pro, Fachteam, Funke, Fernsteuerung, Studio, Recherche und mehr.", tax_code: process.env.JON_TAX_CODE || "txcd_10103000", metadata: {jon: "premium"}}, "jon-premium-produkt-v1");
  return neu.id;
}

export async function preis(plan) {
  const daten = PLAENE[plan];
  if (!daten) throw new Fehler(400, "Unbekannter Tarif.");
  const lookup = `jon_premium_${plan}`;
  const liste = await stripe("GET", "prices", {lookup_keys: [lookup], active: true, limit: 1});
  if (liste.data?.[0]) return liste.data[0].id;
  const neu = await stripe("POST", "prices", {product: await produkt(), currency: "eur", unit_amount: daten.cent, recurring: {interval: daten.intervall}, tax_behavior: "inclusive", lookup_key: lookup, transfer_lookup_key: true, nickname: daten.name}, `jon-premium-preis-${plan}-${daten.cent}-v1`);
  return neu.id;
}

export const geraeteListe = abo => String(abo?.metadata?.geraete || "").split(",").filter(g => /^[a-f0-9]{20}$/.test(g));

export function periodenende(abo) {
  const posten = (abo?.items?.data || []).map(i => i.current_period_end).filter(Boolean);
  return Number(abo?.current_period_end || Math.max(0, ...posten) || jetzt() + 31 * TAG);
}

export function premiumToken(abo, geraete, name = "") {
  const kunde = typeof abo.customer === "string" ? abo.customer : abo.customer?.id;
  return signieren({stufe: "premium", name: String(name || "").slice(0, 80), kunde, abo: abo.id, geraete, exp: periodenende(abo) + 7 * TAG});
}

export async function geraetHinzufuegen(abo, geraete, geraet) {
  if (!geraet || geraete.includes(geraet)) return geraete;
  if (geraete.length >= MAX_GERAETE) throw new Fehler(403, "Diese Lizenz ist schon auf drei Geräten aktiv. Entferne ein Gerät über die Abo-Verwaltung oder schreib uns.");
  const neu = [...geraete, geraet];
  await stripe("POST", `subscriptions/${abo.id}`, {metadata: {geraete: neu.join(",")}});
  return neu;
}
