import {Fehler, funktion, geraetPruefen, seite} from "../lib/basis.mjs";
import {preis, stripe} from "../lib/stripe.mjs";

export async function verarbeiten({plan = "monat", geraet = ""}) {
  const id = geraetPruefen(geraet, false);
  if (!["monat", "jahr"].includes(plan)) throw new Fehler(400, "Unbekannter Tarif.");
  const werte = {
    mode: "subscription",
    line_items: [{price: await preis(plan), quantity: 1}],
    success_url: `${seite()}/premium/danke.html?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${seite()}/premium/?abgebrochen=1`,
    locale: "de",
    allow_promotion_codes: true,
    billing_address_collection: "required",
    tax_id_collection: {enabled: true},
    metadata: {jon: "premium", geraet: id},
    subscription_data: {metadata: {jon: "premium", geraete: id}},
  };
  if (process.env.STRIPE_TAX !== "aus") werte.automatic_tax = {enabled: true};
  const sitzung = await stripe("POST", "checkout/sessions", werte);
  return {id: sitzung.id, url: sitzung.url};
}

export default funktion(verarbeiten);
