import {native} from "./bridge";

export async function agentenAnfrage(pfad: string, body?: unknown, method?: string) {
  const result = await native("api", {path: "/api" + pfad, method: method || (body === undefined ? "GET" : "POST"), body}, undefined, 20000).promise;
  const daten = JSON.parse(result?.text || "{}");
  if (Number(result?.status) >= 400 || (daten && !Array.isArray(daten) && typeof daten.detail === "string" && !("id" in daten))) throw new Error(typeof daten?.detail === "string" ? daten.detail : "Jon antwortet mit einem Fehler.");
  return daten;
}
