import type maplibregl from "maplibre-gl";
import { BASE } from "../lib/api";

export const HEUTE = new Date().getFullYear();

const GEBAEUDE = "jon-3d-gebaeude";
const OHM_QUELLE = "jon-ohm";
const OHM_SCHICHT = "jon-ohm-gebaeude";
const OHM_KACHELN = "https://vtiles.openhistoricalmap.org/maps/ohm/{z}/{x}/{y}.pbf";
const LADE_ABSTAND = 650;
const LADE_RAND = 0.009;

export interface Luftbild {
  jahr: number;
  datum: string;
  url: string;
}

export function hoeheBis(jahr: number): number {
  if (jahr >= HEUTE) return Infinity;
  if (jahr < 1850) return 42;
  if (jahr < 1890) return 55;
  if (jahr < 1925) return 75;
  if (jahr < 1950) return 110;
  if (jahr < 1970) return 160;
  if (jahr < 1990) return 240;
  if (jahr < 2005) return 320;
  return 900;
}

export function epochenFilter(jahr: number): string {
  if (jahr >= 1995) return "";
  if (jahr < 1880) return "sepia(0.62) saturate(0.7) contrast(0.96) brightness(1.02)";
  if (jahr < 1930) return "sepia(0.5) saturate(0.72) contrast(0.97)";
  if (jahr < 1960) return "sepia(0.32) saturate(0.82)";
  return "sepia(0.14) saturate(0.92)";
}

export function epochenName(jahr: number): string {
  if (jahr >= HEUTE) return "Heute";
  if (jahr < 1000) return "Antike";
  if (jahr < 1500) return "Mittelalter";
  if (jahr < 1800) return "Frühe Neuzeit";
  if (jahr < 1870) return "Biedermeier und Industrialisierung";
  if (jahr < 1914) return "Kaiserzeit und Belle Époque";
  if (jahr < 1945) return "Zwischenkriegszeit";
  if (jahr < 1970) return "Wiederaufbau und Wirtschaftswunder";
  if (jahr < 2000) return "Spätes 20. Jahrhundert";
  return "Gegenwart";
}

function abstand(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const dLat = (b.lat - a.lat) * 111320;
  const dLon = (b.lon - a.lon) * 111320 * Math.cos((a.lat * Math.PI) / 180);
  return Math.hypot(dLat, dLon);
}

export class Zeitreise {
  private map: maplibregl.Map;
  private jahr = HEUTE;
  private baujahre = new Map<number, number>();
  private geladen: { lat: number; lon: number }[] = [];
  private laedt = false;
  private luftbilder: Luftbild[] = [];
  private ursprungFarbe: unknown;
  private ursprungFilter: unknown;
  private ursprungKacheln: string[] | null = null;
  private ursprungCanvas = "";
  private aktiv = true;
  private gewuenscht = "";
  private wache = () => {
    if (!this.aktiv) return;
    try {
      if (!this.map.getLayer(GEBAEUDE)) return;
      if (JSON.stringify(this.map.getPaintProperty(GEBAEUDE, "fill-extrusion-color")) !== this.gewuenscht) this.map.setPaintProperty(GEBAEUDE, "fill-extrusion-color", this.farbe());
    } catch {
      return;
    }
  };
  onAenderung?: () => void;

  constructor(map: maplibregl.Map) {
    this.map = map;
    this.ursprungCanvas = map.getCanvas().style.filter;
    try {
      this.ursprungFarbe = map.getPaintProperty(GEBAEUDE, "fill-extrusion-color");
      this.ursprungFilter = map.getFilter(GEBAEUDE);
    } catch {
      this.ursprungFarbe = undefined;
    }
    const satellit = map.getSource("jon-satellit") as (maplibregl.RasterTileSource & { tiles?: string[] }) | undefined;
    this.ursprungKacheln = satellit?.tiles ? [...satellit.tiles] : null;
    this.ohmAnlegen();
    map.on("styledata", this.wache);
    void fetch(`${BASE}/maps/zeitreise/luftbilder`)
      .then((r) => (r.ok ? r.json() : { luftbilder: [] }))
      .then((d: { luftbilder?: Luftbild[] }) => {
        this.luftbilder = d.luftbilder ?? [];
        if (this.aktiv) this.anwenden();
      })
      .catch(() => undefined);
  }

  get bekannte(): number {
    return this.baujahre.size;
  }

  get ausgeblendet(): number {
    let n = 0;
    this.baujahre.forEach((jahr) => {
      if (jahr > this.jahr) n += 1;
    });
    return n;
  }

  get luftbildJahr(): string {
    const bild = this.luftbildFuer(this.jahr);
    return bild ? bild.datum : "";
  }

  setJahr(jahr: number): void {
    this.jahr = Math.round(jahr);
    this.anwenden();
  }

  sichtbar(id: string | number | undefined, hoehe: number): boolean {
    if (this.jahr >= HEUTE) return true;
    const roh = typeof id === "number" ? id : Number(id);
    const kennung = Number.isFinite(roh) && roh % 10 !== 3 ? Math.floor(roh / 10) : NaN;
    const bekannt = Number.isFinite(kennung) ? this.baujahre.get(kennung) : undefined;
    if (bekannt !== undefined) return bekannt <= this.jahr;
    return hoehe <= hoeheBis(this.jahr);
  }

  async nachladen(lat: number, lon: number): Promise<void> {
    if (this.laedt || this.geladen.some((p) => abstand(p, { lat, lon }) < LADE_ABSTAND)) return;
    this.laedt = true;
    try {
      const params = new URLSearchParams({
        sued: String(lat - LADE_RAND),
        west: String(lon - LADE_RAND / Math.max(0.2, Math.cos((lat * Math.PI) / 180))),
        nord: String(lat + LADE_RAND),
        ost: String(lon + LADE_RAND / Math.max(0.2, Math.cos((lat * Math.PI) / 180))),
      });
      const antwort = await fetch(`${BASE}/maps/zeitreise/baujahre?${params.toString()}`);
      const daten = (await antwort.json()) as { gebaeude?: [number, number][]; fehler?: string };
      if (!daten.fehler) this.geladen.push({ lat, lon });
      for (const [id, jahr] of daten.gebaeude ?? []) this.baujahre.set(id, jahr);
      if (this.aktiv) this.anwenden();
    } catch {
      return;
    } finally {
      this.laedt = false;
    }
  }

  private ohmAnlegen(): void {
    const map = this.map;
    try {
      if (!map.getSource(OHM_QUELLE)) {
        map.addSource(OHM_QUELLE, {
          type: "vector",
          tiles: [OHM_KACHELN],
          minzoom: 0,
          maxzoom: 15,
          attribution: "© OpenHistoricalMap",
        });
      }
      if (!map.getLayer(OHM_SCHICHT)) {
        map.addLayer({
          id: OHM_SCHICHT,
          type: "fill-extrusion",
          source: OHM_QUELLE,
          "source-layer": "buildings",
          minzoom: 13,
          layout: { visibility: "none" },
          paint: {
            "fill-extrusion-color": "#cdb791",
            "fill-extrusion-height": 13,
            "fill-extrusion-base": 0,
            "fill-extrusion-opacity": 0.96,
            "fill-extrusion-vertical-gradient": true,
          },
        });
      }
    } catch {
      return;
    }
  }

  private luftbildFuer(jahr: number): Luftbild | null {
    if (!this.luftbilder.length || jahr >= HEUTE) return null;
    const passend = this.luftbilder.filter((b) => b.jahr <= jahr);
    return passend.length ? passend[passend.length - 1] : this.luftbilder[0];
  }

  private farbe(): maplibregl.ExpressionSpecification {
    const alt = this.jahr < 1900;
    const ersatz = alt ? "#c9b48e" : this.jahr < 1960 ? "#cbbfa8" : "#cfcac0";
    return [
      "case",
      ["has", "colour"],
      ["to-color", ["get", "colour"], ersatz],
      [
        "interpolate",
        ["linear"],
        ["coalesce", ["get", "render_height"], 6],
        0,
        alt ? "#bfa57d" : "#bcb5a6",
        40,
        alt ? "#c9b48e" : "#cdc8bc",
        140,
        "#e3dfd4",
      ],
    ] as unknown as maplibregl.ExpressionSpecification;
  }

  anwenden(): void {
    const map = this.map;
    const jahr = this.jahr;
    const frueher = jahr < HEUTE;
    try {
      if (map.getLayer(GEBAEUDE)) {
        const farbe = this.farbe();
        this.gewuenscht = JSON.stringify(farbe);
        map.setPaintProperty(GEBAEUDE, "fill-extrusion-color", farbe);
        const neuer: number[] = [];
        const alt: number[] = [];
        this.baujahre.forEach((baujahr, id) => (baujahr > jahr ? neuer : alt).push(id));
        const osm = ["floor", ["/", ["id"], 10]];
        const weg = ["!=", ["%", ["id"], 10], 3];
        const teile: unknown[] = frueher
          ? [
              ["!", ["all", weg, ["in", osm, ["literal", neuer]]]],
              ["any", ["all", weg, ["in", osm, ["literal", alt]]], ["<=", ["coalesce", ["get", "render_height"], 0], hoeheBis(jahr)]],
            ]
          : [];
        const ursprung = this.ursprungFilter ? [this.ursprungFilter] : [];
        const filter = teile.length || ursprung.length ? ["all", ...ursprung, ...teile] : null;
        map.setFilter(GEBAEUDE, filter as maplibregl.FilterSpecification | null);
      }
      if (map.getLayer(OHM_SCHICHT)) {
        map.setLayoutProperty(OHM_SCHICHT, "visibility", frueher ? "visible" : "none");
        const zeit = jahr + 0.5;
        map.setFilter(OHM_SCHICHT, [
          "all",
          ["has", "end_decdate"],
          ["<=", ["coalesce", ["get", "start_decdate"], -9999], zeit],
          [">", ["get", "end_decdate"], zeit],
          ["<", ["get", "end_decdate"], HEUTE - 0.5],
        ] as unknown as maplibregl.FilterSpecification);
      }
      const satellit = map.getSource("jon-satellit") as (maplibregl.RasterTileSource & { setTiles?: (t: string[]) => void }) | undefined;
      if (satellit?.setTiles && this.ursprungKacheln) {
        const bild = this.luftbildFuer(jahr);
        satellit.setTiles(bild ? [bild.url] : this.ursprungKacheln);
      }
      map.getCanvas().style.filter = epochenFilter(jahr);
    } catch {
      return;
    }
    this.onAenderung?.();
  }

  entfernen(): void {
    this.aktiv = false;
    const map = this.map;
    map.off("styledata", this.wache);
    try {
      if (map.getLayer(GEBAEUDE)) {
        if (this.ursprungFarbe !== undefined) map.setPaintProperty(GEBAEUDE, "fill-extrusion-color", this.ursprungFarbe);
        map.setFilter(GEBAEUDE, (this.ursprungFilter ?? null) as maplibregl.FilterSpecification | null);
      }
      if (map.getLayer(OHM_SCHICHT)) map.removeLayer(OHM_SCHICHT);
      if (map.getSource(OHM_QUELLE)) map.removeSource(OHM_QUELLE);
      const satellit = map.getSource("jon-satellit") as (maplibregl.RasterTileSource & { setTiles?: (t: string[]) => void }) | undefined;
      if (satellit?.setTiles && this.ursprungKacheln) satellit.setTiles(this.ursprungKacheln);
      map.getCanvas().style.filter = this.ursprungCanvas;
    } catch {
      return;
    }
  }
}
