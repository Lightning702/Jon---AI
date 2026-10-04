export const STANDARD = "https://felworks.tail661828.ts.net";

export const adresse = () => (process.env.JON_DEMO_URL || STANDARD).trim().replace(/\/+$/, "");

export default async () => new Response(JSON.stringify({url: adresse()}), {headers: {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=60"}});
