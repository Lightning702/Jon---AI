import {Fehler, funktion, lesen, seite} from "../lib/basis.mjs";
import {stripe} from "../lib/stripe.mjs";

export async function verarbeiten({token}) {
  const inhalt = lesen(token);
  if (inhalt.stufe !== "premium" || !inhalt.kunde) throw new Fehler(400, "Die Abo-Verwaltung gibt es nur für Premium-Abos.");
  const sitzung = await stripe("POST", "billing_portal/sessions", {customer: inhalt.kunde, return_url: `${seite()}/premium/`, locale: "de"});
  return {url: sitzung.url};
}

export default funktion(verarbeiten);
