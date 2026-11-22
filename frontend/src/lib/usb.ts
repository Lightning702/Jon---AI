import { BASE } from "./api";

export interface UsbLaufwerk {
  pfad: string;
  name: string;
  art: string;
  frei: number;
  gesamt: number;
  system: boolean;
}

export interface UsbModell {
  name: string;
  id: string;
  groesse: number;
  familie: string;
  parameter: string;
  quantisierung: string;
  vollstaendig: boolean;
}

export interface UsbSpeicher {
  pfad: string;
  modelle: UsbModell[];
  groesse: number;
}

export interface UsbGguf {
  pfad: string;
  datei: string;
  groesse: number;
  vorschlag: string;
}

export interface UsbFund {
  pfad: string;
  speicher: UsbSpeicher[];
  gguf: UsbGguf[];
  programme: string[];
  abgebrochen: boolean;
}

export interface UsbAufgabe {
  laeuft?: boolean;
  name?: string;
  datei?: string;
  text?: string;
  fehler?: string;
  fertig?: boolean;
}

export interface UsbStand {
  aktiv: boolean;
  speicher: string;
  eingesteckt: boolean;
  laeuft: boolean;
  port: number;
  programm: string;
  modelle: UsbModell[];
  fehler: string;
  aufgabe: UsbAufgabe;
  laufwerke?: UsbLaufwerk[];
}

async function lesen<T>(res: Response, ersatz: string): Promise<T> {
  if (!res.ok) {
    let text = ersatz;
    try {
      const daten = await res.json();
      if (daten && typeof daten.detail === "string") text = daten.detail;
    } catch {
      text = ersatz;
    }
    throw new Error(text);
  }
  return res.json() as Promise<T>;
}

function senden(pfad: string, daten: unknown): Promise<Response> {
  return fetch(`${BASE}/ollama/usb${pfad}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(daten ?? {}),
  });
}

export async function usbStand(): Promise<UsbStand> {
  return lesen<UsbStand>(await fetch(`${BASE}/ollama/usb`), "Der USB-Bereich ist gerade nicht erreichbar.");
}

export async function usbSuchen(pfad: string): Promise<UsbFund> {
  return lesen<UsbFund>(await senden("/suchen", { pfad }), "Die Suche hat nicht geklappt.");
}

export async function usbVerbinden(pfad: string, programme: string[] = []): Promise<UsbStand> {
  return lesen<UsbStand>(await senden("/verbinden", { pfad, programme }), "Der Stick ließ sich nicht verbinden.");
}

export async function usbTrennen(): Promise<UsbStand> {
  return lesen<UsbStand>(await senden("/trennen", {}), "Trennen hat nicht geklappt.");
}

export async function usbEinbinden(datei: string, name: string): Promise<UsbStand> {
  return lesen<UsbStand>(await senden("/einbinden", { datei, name }), "Die Datei ließ sich nicht einbinden.");
}

export function groesseText(bytes: number): string {
  if (!bytes) return "–";
  if (bytes >= 1e9) return `${(bytes / 1e9).toLocaleString("de-DE", { maximumFractionDigits: 1 })} GB`;
  return `${Math.max(1, Math.round(bytes / 1e6)).toLocaleString("de-DE")} MB`;
}

export function modellWaehlen(provider: string, model: string): void {
  window.dispatchEvent(new CustomEvent("jon-modell-waehlen", { detail: { provider, model } }));
}

export function anbieterNeuLaden(): void {
  window.dispatchEvent(new Event("jon-anbieter-neu"));
}
