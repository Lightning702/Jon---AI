import assert from "node:assert/strict";
import {generateKeyPairSync} from "node:crypto";
import {createServer} from "node:http";
import {after, before, beforeEach, test} from "node:test";

const {privateKey} = generateKeyPairSync("ed25519");
process.env.JON_LIZENZ_SCHLUESSEL = privateKey.export({format: "der", type: "pkcs8"}).toString("base64");
process.env.STRIPE_SECRET_KEY = "sk_test_attrappe";
process.env.JON_ADMIN_PASSWORT = "ein-sehr-langes-passwort";
process.env.JON_SEITE = "https://getjon.example";

const GERAET = "a".repeat(20);
const ANDERES = "b".repeat(20);
let stripe;
let server;

function zustand() {
  return {anfragen: [], produkte: [], preise: [], sitzung: {id: "cs_test_1", url: "https://checkout.stripe.com/c/pay/cs_test_1", status: "open", metadata: {}, customer_details: {name: "Felix"}}, abo: {id: "sub_1", customer: "cus_1", status: "active", metadata: {jon: "premium", geraete: ""}, items: {data: [{current_period_end: Math.floor(Date.now() / 1000) + 30 * 86400}]}}};
}

before(async () => {
  server = createServer((req, res) => {
    let koerper = "";
    req.on("data", teil => koerper += teil);
    req.on("end", () => {
      const url = new URL(req.url, "http://x");
      const werte = Object.fromEntries(new URLSearchParams(req.method === "GET" ? url.search : koerper));
      stripe.anfragen.push({methode: req.method, pfad: url.pathname, werte, idempotenz: req.headers["idempotency-key"] || "", auth: req.headers.authorization});
      const senden = (daten, status = 200) => {res.writeHead(status, {"Content-Type": "application/json"}); res.end(JSON.stringify(daten));};
      const p = url.pathname;
      if (p === "/v1/products" && req.method === "GET") return senden({data: stripe.produkte});
      if (p === "/v1/products") {const neu = {id: "prod_1", metadata: {jon: werte["metadata[jon]"]}}; stripe.produkte.push(neu); return senden(neu);}
      if (p === "/v1/prices" && req.method === "GET") return senden({data: stripe.preise.filter(x => x.lookup_key === werte["lookup_keys[0]"])});
      if (p === "/v1/prices") {const neu = {id: `price_${werte.lookup_key}`, lookup_key: werte.lookup_key}; stripe.preise.push(neu); return senden(neu);}
      if (p === "/v1/checkout/sessions") {Object.assign(stripe.sitzung, {metadata: {jon: werte["metadata[jon]"], geraet: werte["metadata[geraet]"]}}); stripe.abo.metadata.geraete = werte["subscription_data[metadata][geraete]"]; return senden(stripe.sitzung);}
      if (p === "/v1/checkout/sessions/cs_test_1") return senden({...stripe.sitzung, subscription: stripe.sitzung.status === "complete" ? stripe.abo : null});
      if (p === "/v1/subscriptions/sub_1" && req.method === "POST") {stripe.abo.metadata.geraete = werte["metadata[geraete]"]; return senden(stripe.abo);}
      if (p === "/v1/subscriptions/sub_1") return senden(stripe.abo);
      if (p === "/v1/billing_portal/sessions") return senden({url: "https://billing.stripe.com/p/session/test"});
      senden({error: {message: `Unbekannt: ${req.method} ${p}`}}, 404);
    });
  });
  await new Promise(fertig => server.listen(0, "127.0.0.1", fertig));
  process.env.STRIPE_API_BASE = `http://127.0.0.1:${server.address().port}`;
});

after(() => server.close());
beforeEach(() => {stripe = zustand();});

const {verarbeiten: checkout} = await import("../functions/premium-checkout.mjs");
const {verarbeiten: lizenz} = await import("../functions/premium-lizenz.mjs");
const {verarbeiten: portal} = await import("../functions/premium-portal.mjs");
const {verarbeiten: admin} = await import("../functions/premium-admin.mjs");
const {verarbeiten: sicherung} = await import("../functions/premium-sicherung.mjs");
const {lesen, Fehler} = await import("../lib/basis.mjs");
const fehlschlag = async (versprechen, status, text) => {
  await assert.rejects(versprechen, e => e instanceof Fehler && e.status === status && (!text || e.message.includes(text)));
};

async function kaufen(geraet = GERAET) {
  const sitzung = await checkout({plan: "monat", geraet});
  stripe.sitzung.status = "complete";
  return (await lizenz({aktion: "abholen", session_id: sitzung.id, geraet})).token;
}

test("Kauf legt Produkt und Preis mit Steuer an und startet Checkout mit Stripe Tax", async () => {
  const sitzung = await checkout({plan: "jahr", geraet: GERAET});
  assert.equal(sitzung.url, "https://checkout.stripe.com/c/pay/cs_test_1");
  const preis = stripe.anfragen.find(a => a.methode === "POST" && a.pfad === "/v1/prices").werte;
  assert.equal(preis.tax_behavior, "inclusive");
  assert.equal(preis.unit_amount, "5999");
  assert.equal(preis.currency, "eur");
  assert.equal(preis["recurring[interval]"], "year");
  assert.equal(preis.lookup_key, "jon_premium_jahr");
  const produkt = stripe.anfragen.find(a => a.methode === "POST" && a.pfad === "/v1/products");
  assert.ok(produkt.werte.tax_code.startsWith("txcd_") && produkt.idempotenz);
  const werte = stripe.anfragen.find(a => a.pfad === "/v1/checkout/sessions").werte;
  assert.equal(werte.mode, "subscription");
  assert.equal(werte["automatic_tax[enabled]"], "true");
  assert.equal(werte["tax_id_collection[enabled]"], "true");
  assert.equal(werte["subscription_data[metadata][geraete]"], GERAET);
  assert.ok(werte.success_url.includes("{CHECKOUT_SESSION_ID}"));
  assert.ok(stripe.anfragen.every(a => a.auth === "Bearer sk_test_attrappe"));
  await checkout({plan: "monat", geraet: GERAET});
  assert.equal(stripe.anfragen.filter(a => a.methode === "POST" && a.pfad === "/v1/products").length, 1);
});

test("Lizenz kommt erst nach bezahltem Kauf und ist signiert und an das Gerät gebunden", async () => {
  const sitzung = await checkout({plan: "monat", geraet: GERAET});
  assert.deepEqual(await lizenz({aktion: "abholen", session_id: sitzung.id, geraet: GERAET}), {offen: true});
  stripe.sitzung.status = "complete";
  const inhalt = lesen((await lizenz({aktion: "abholen", session_id: sitzung.id, geraet: GERAET})).token);
  assert.equal(inhalt.stufe, "premium");
  assert.deepEqual(inhalt.geraete, [GERAET]);
  assert.equal(inhalt.abo, "sub_1");
  assert.ok(inhalt.exp > Date.now() / 1000 + 30 * 86400);
});

test("Gefälschte oder veränderte Lizenz wird abgelehnt", async () => {
  const token = await kaufen();
  const [kopf, inhalt, signatur] = token.split(".");
  const gefaelscht = Buffer.from(JSON.stringify({...JSON.parse(Buffer.from(inhalt, "base64url")), stufe: "admin"})).toString("base64url");
  await fehlschlag(lizenz({aktion: "erneuern", token: `${kopf}.${gefaelscht}.${signatur}`, geraet: GERAET}), 403, "Signatur");
  const {privateKey: fremd} = generateKeyPairSync("ed25519");
  const alt = process.env.JON_LIZENZ_SCHLUESSEL;
  process.env.JON_LIZENZ_SCHLUESSEL = fremd.export({format: "der", type: "pkcs8"}).toString("base64");
  const {adminToken} = await import("../lib/basis.mjs");
  const fremdToken = adminToken(GERAET);
  process.env.JON_LIZENZ_SCHLUESSEL = alt;
  await fehlschlag(lizenz({aktion: "erneuern", token: fremdToken, geraet: GERAET}), 403, "Signatur");
});

test("Erneuern verlängert aktive Abos und lehnt gekündigte ab", async () => {
  const token = await kaufen();
  assert.equal(lesen((await lizenz({aktion: "erneuern", token, geraet: GERAET})).token).abo, "sub_1");
  await fehlschlag(lizenz({aktion: "erneuern", token, geraet: ANDERES}), 403, "Gerät");
  stripe.abo.status = "canceled";
  await fehlschlag(lizenz({aktion: "erneuern", token, geraet: GERAET}), 402, "nicht mehr aktiv");
});

test("Höchstens drei Geräte pro Abo", async () => {
  const token = await kaufen();
  const ids = ["c", "d", "e"].map(z => z.repeat(20));
  const zweit = lesen((await lizenz({aktion: "geraet", token, geraet: ids[0]})).token);
  assert.deepEqual(zweit.geraete, [GERAET, ids[0]]);
  await lizenz({aktion: "geraet", token, geraet: ids[1]});
  await fehlschlag(lizenz({aktion: "geraet", token, geraet: ids[2]}), 403, "drei Geräten");
  assert.equal(stripe.abo.metadata.geraete.split(",").length, 3);
});

test("Admin nur mit richtigem Passwort, und ein neues Passwort sperrt alte Admin-Lizenzen", async () => {
  let gewartet = 0;
  await fehlschlag(admin({passwort: "falsch", geraet: GERAET}, async ms => {gewartet = ms;}), 403, "Falsches");
  assert.ok(gewartet >= 1000);
  const token = (await admin({passwort: "ein-sehr-langes-passwort", geraet: GERAET})).token;
  const inhalt = lesen(token);
  assert.equal(inhalt.stufe, "admin");
  assert.deepEqual(inhalt.geraete, [GERAET]);
  assert.ok(lesen((await lizenz({aktion: "erneuern", token, geraet: GERAET})).token).stufe === "admin");
  process.env.JON_ADMIN_PASSWORT = "ein-ganz-anderes-passwort";
  await fehlschlag(lizenz({aktion: "erneuern", token, geraet: GERAET}), 403, "Admin");
  process.env.JON_ADMIN_PASSWORT = "kurz";
  await fehlschlag(admin({passwort: "kurz", geraet: GERAET}), 503, "nicht eingerichtet");
  process.env.JON_ADMIN_PASSWORT = "ein-sehr-langes-passwort";
});

test("Abo-Verwaltung öffnet das Stripe-Kundenportal", async () => {
  const token = await kaufen();
  assert.equal((await portal({token})).url, "https://billing.stripe.com/p/session/test");
  assert.equal(stripe.anfragen.at(-1).werte.customer, "cus_1");
});

test("Cloud-Sicherung nur mit gültiger Lizenz und freigeschaltetem Gerät", async () => {
  const token = await kaufen();
  const blobs = new Map();
  const speicher = {set: async (k, v, o) => blobs.set(k, {v, m: o.metadata}), get: async k => blobs.get(k)?.v ?? null, getMetadata: async k => blobs.has(k) ? {metadata: blobs.get(k).m} : null};
  assert.deepEqual(await sicherung({aktion: "info", token, geraet: GERAET}, speicher), {zeit: 0});
  await sicherung({aktion: "hochladen", token, geraet: GERAET, daten: "verschluesselt"}, speicher);
  assert.equal((await sicherung({aktion: "holen", token, geraet: GERAET}, speicher)).daten, "verschluesselt");
  assert.ok(blobs.has("kunde-cus_1"));
  await fehlschlag(sicherung({aktion: "holen", token, geraet: ANDERES}, speicher), 403);
  await fehlschlag(sicherung({aktion: "hochladen", token, geraet: GERAET, daten: "x".repeat(4_000_001)}, speicher), 413);
});
