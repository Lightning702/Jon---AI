import { BASE } from "./api";

export type MapsTheme = "dark" | "light";
export type TravelMode = "fuss" | "auto" | "fahrrad" | "oepnv";
export type MapsAction = "suche" | "umgebung" | "route" | "erkunden";

export interface MapsPlace {
  id: string;
  name: string;
  label: string;
  lat: number;
  lon: number;
  kind: string;
  category: string;
  address: Record<string, string>;
  bbox: number[] | null;
  distance_m: number | null;
  source: string;
  extra: Record<string, unknown>;
}

export interface MapsRouteStep {
  text: string;
  distance_m: number;
  duration_s: number;
  modifier: string;
  road: string;
  mode: string;
  lat: number | null;
  lon: number | null;
}

export interface MapsRoute {
  id: string;
  mode: TravelMode;
  distance_m: number;
  duration_s: number;
  geometry: [number, number][];
  steps: MapsRouteStep[];
  summary: string;
  source: string;
  legs: Record<string, unknown>[];
  extra: Record<string, unknown>;
}

export interface StreetImage {
  id: string;
  lat: number;
  lon: number;
  bearing: number;
  url: string;
  thumb: string;
  spherical: boolean;
  captured_at: string;
  sequence: string;
  index: number;
  source: string;
}

export interface StreetResult {
  modus: "fotos" | "render";
  anbieter: string;
  bilder: StreetImage[];
  hinweis: string;
}

export interface MapsHome {
  lat: number;
  lon: number;
  name: string;
  quelle: string;
}

export interface FriendLocation {
  id: string;
  name: string;
  avatar: string;
  lat: number;
  lon: number;
  genauigkeit_m: number | null;
  alter_s: number;
  frisch: boolean;
  online: boolean;
}

export interface FriendSharing {
  aktiv: boolean;
  alle: boolean;
  peers: string[];
}

export interface FriendContact {
  id: string;
  name: string;
  avatar: string;
}

export interface FriendsResult {
  freunde: FriendLocation[];
  teilen: FriendSharing;
  zuletzt_gesendet: number;
  kontakte: FriendContact[];
}

export interface MapsConfig {
  anbieter: Record<string, unknown>;
  themes: MapsTheme[];
  start: { lat: number; lon: number; zoom: number };
  standort?: MapsHome;
  modi: { id: TravelMode; label: string }[];
  kategorien: { id: string; label: string; icon: string }[];
  ebenen: Record<string, boolean>;
  faehigkeiten: Record<string, boolean>;
  attribution: string;
}

export interface TripLeg {
  von: string;
  nach: string;
  distanz_m: number;
  dauer_s: number;
  zusammenfassung: string;
}

export interface MapsCardData {
  aktion: MapsAction;
  anfrage?: string;
  kategorie?: string;
  filter?: string;
  ziel_optionen?: MapsPlace[];
  treffer?: MapsPlace[];
  start?: MapsPlace;
  ziel?: MapsPlace;
  ort?: MapsPlace;
  zwischenstopps?: MapsPlace[];
  stationen?: MapsPlace[];
  abschnitte?: TripLeg[];
  routen?: MapsRoute[];
  modus?: TravelMode;
  modus_label?: string;
  street?: StreetResult;
  mittelpunkt?: { lat: number; lon: number };
  karte: {
    center: { lat: number; lon: number } | null;
    zoom?: number;
    marker?: MapsPlace[];
    route?: [number, number][];
    modus?: string;
  };
  text: string;
}

export interface NewsArticle {
  titel: string;
  url: string;
  quelle: string;
  domain: string;
  bild: string;
  zeit: string;
  bereich: "lokal" | "national" | string;
}

export interface PlaceWeather {
  ort: string;
  temperatur: number | null;
  gefuehlt: number | null;
  luftfeuchte: number | null;
  niederschlag: number | null;
  regen_prozent: number | null;
  max: number | null;
  min: number | null;
  wind_kmh: number | null;
  code: number | null;
  zustand: string;
  tag: boolean;
  stand: string;
}

export interface PlaceInfo {
  ort: string;
  land: string;
  bereich: string;
  news: NewsArticle[];
  news_fehler: string;
  wetter: PlaceWeather | null;
  wetter_fehler: string;
}

export interface InfoTarget {
  key: string;
  name: string;
  land: string;
  code: string;
  scope: "stadt" | "land";
  lat: number;
  lon: number;
}

const CITY_TYPES = new Set([
  "city",
  "town",
  "village",
  "hamlet",
  "municipality",
  "borough",
  "suburb",
  "city_district",
  "quarter",
  "neighbourhood",
]);

const COUNTRY_TYPES = new Set(["country", "state", "region", "province"]);

export function infoTargetOf(place: MapsPlace): InfoTarget | null {
  const address = (place.address ?? {}) as Record<string, string>;
  const osmType = String(place.extra?.osm_type ?? "");
  const land = address.country ?? "";
  const code = address.country_code ?? "";
  const city =
    address.city ??
    address.town ??
    address.village ??
    address.municipality ??
    address.hamlet ??
    "";
  if (COUNTRY_TYPES.has(osmType)) {
    const name = osmType === "country" ? place.name || land : place.name;
    return {
      key: `land:${(code || name).toLowerCase()}:${name}`,
      name: name || land,
      land: land || name,
      code,
      scope: "land",
      lat: place.lat,
      lon: place.lon,
    };
  }
  if (CITY_TYPES.has(osmType) || (place.kind === "ort" && city)) {
    const name = place.name || city;
    return {
      key: `stadt:${code}:${name.toLowerCase()}`,
      name,
      land,
      code,
      scope: "stadt",
      lat: place.lat,
      lon: place.lon,
    };
  }
  if (!city && !land) return null;
  return {
    key: `stadt:${code}:${(city || land).toLowerCase()}`,
    name: city || land,
    land,
    code,
    scope: city ? "stadt" : "land",
    lat: place.lat,
    lon: place.lon,
  };
}

export function isRegion(place: MapsPlace): boolean {
  const osmType = String(place.extra?.osm_type ?? "");
  return CITY_TYPES.has(osmType) || COUNTRY_TYPES.has(osmType);
}

export function formatNewsAge(iso: string): string {
  if (!iso) return "";
  const stamp = Date.parse(iso);
  if (Number.isNaN(stamp)) return "";
  const minutes = Math.round((Date.now() - stamp) / 60000);
  if (minutes < 2) return "gerade eben";
  if (minutes < 60) return `vor ${minutes} Min.`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `vor ${hours} Std.`;
  const days = Math.round(hours / 24);
  return days === 1 ? "gestern" : `vor ${days} Tagen`;
}

export const WEATHER_ICONS: { codes: number[]; day: string; night: string }[] = [
  { codes: [0], day: "☀️", night: "🌙" },
  { codes: [1, 2], day: "🌤️", night: "🌤️" },
  { codes: [3], day: "☁️", night: "☁️" },
  { codes: [45, 48], day: "🌫️", night: "🌫️" },
  { codes: [51, 53, 55, 56, 57], day: "🌦️", night: "🌦️" },
  { codes: [61, 63, 65, 66, 67, 80, 81, 82], day: "🌧️", night: "🌧️" },
  { codes: [71, 73, 75, 77, 85, 86], day: "🌨️", night: "🌨️" },
  { codes: [95, 96, 99], day: "⛈️", night: "⛈️" },
];

export function weatherIcon(code: number | null, day = true): string {
  if (code == null) return "🌡️";
  const entry = WEATHER_ICONS.find((item) => item.codes.includes(code));
  if (!entry) return "🌡️";
  return day ? entry.day : entry.night;
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export function getMapsConfig(): Promise<MapsConfig> {
  return json<MapsConfig>(`${BASE}/maps/config`);
}

export function getMapsStyleUrl(theme: MapsTheme): string {
  return `${BASE}/maps/styles/${theme}`;
}

export async function searchPlaces(
  query: string,
  near?: { lat: number; lon: number },
  limit = 8
): Promise<MapsPlace[]> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  if (near) {
    params.set("lat", String(near.lat));
    params.set("lon", String(near.lon));
  }
  const data = await json<{ treffer: MapsPlace[] }>(
    `${BASE}/maps/search?${params.toString()}`
  );
  return data.treffer ?? [];
}

export async function nearbyPlaces(
  category: string,
  lat: number,
  lon: number,
  radius = 1500,
  limit = 24
): Promise<MapsPlace[]> {
  const params = new URLSearchParams({
    category,
    lat: String(lat),
    lon: String(lon),
    radius: String(radius),
    limit: String(limit),
  });
  const data = await json<{ treffer: MapsPlace[] }>(
    `${BASE}/maps/nearby?${params.toString()}`
  );
  return data.treffer ?? [];
}

export function getFriends(): Promise<FriendsResult> {
  return json<FriendsResult>(`${BASE}/maps/friends`);
}

export function setFriendSharing(
  patch: Partial<FriendSharing>
): Promise<FriendSharing> {
  return json<FriendSharing>(`${BASE}/maps/friends/sharing`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}

export function shareLocationNow(): Promise<{
  gesendet: number;
  empfaenger?: number;
  grund?: string;
}> {
  return json(`${BASE}/maps/friends/ping`, { method: "POST" });
}

export function forgetFriendLocations(): Promise<{ geloescht: number }> {
  return json(`${BASE}/maps/friends`, { method: "DELETE" });
}

export function formatAge(seconds: number): string {
  if (seconds < 90) return "gerade eben";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `vor ${minutes} Min.`;
  const hours = Math.floor(minutes / 60);
  return `vor ${hours} Std. ${minutes % 60} Min.`;
}

export function getHome(): Promise<MapsHome> {
  return json<MapsHome>(`${BASE}/maps/home`);
}

export function setHome(
  lat: number,
  lon: number,
  source: "geraet" | "karte" | "ip" = "geraet"
): Promise<MapsHome> {
  return json<MapsHome>(`${BASE}/maps/home`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lat, lon, source }),
  });
}

export function locateViaJon(): Promise<MapsHome & { genauigkeit_m?: number }> {
  return json<MapsHome & { genauigkeit_m?: number }>(`${BASE}/maps/locate`, {
    method: "POST",
  });
}

export function locateDevice(timeout = 9000): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Dieses Gerät kennt keine Ortung."));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout,
      maximumAge: 120000,
    });
  });
}

export function reversePlace(lat: number, lon: number): Promise<MapsPlace> {
  return json<MapsPlace>(`${BASE}/maps/reverse?lat=${lat}&lon=${lon}`);
}

export async function planRoute(
  points: { lat: number; lon: number }[],
  mode: TravelMode,
  alternatives = true
): Promise<MapsRoute[]> {
  const data = await json<{ routen: MapsRoute[] }>(`${BASE}/maps/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ points, mode, alternatives }),
  });
  return data.routen ?? [];
}

export function streetImages(
  lat: number,
  lon: number,
  radius = 160,
  limit = 24
): Promise<StreetResult> {
  return json<StreetResult>(
    `${BASE}/maps/street?lat=${lat}&lon=${lon}&radius=${radius}&limit=${limit}`
  );
}

export async function streetSequence(id: string): Promise<StreetImage[]> {
  const data = await json<{ bilder: StreetImage[] }>(
    `${BASE}/maps/street/sequence/${encodeURIComponent(id)}`
  );
  return data.bilder ?? [];
}

export function placeInfo(
  target: InfoTarget,
  signal?: AbortSignal,
  limit = 5
): Promise<PlaceInfo> {
  const params = new URLSearchParams({
    lat: String(target.lat),
    lon: String(target.lon),
    name: target.name,
    country: target.land,
    country_code: target.code,
    scope: target.scope,
    limit: String(limit),
  });
  return json<PlaceInfo>(`${BASE}/maps/info?${params.toString()}`, { signal });
}

export function mapsAction(
  action: MapsAction,
  args: Record<string, unknown>
): Promise<MapsCardData> {
  return json<MapsCardData>(`${BASE}/maps/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, args }),
  });
}

const NUMBER_ONLY = /^\d+\s*[a-zA-Z]?$/;

function unique(parts: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const part of parts) {
    const value = part.trim();
    if (!value) continue;
    const key = value.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(value);
  }
  return result;
}

export function placeFullLabel(place: MapsPlace): string {
  const address = (place.address ?? {}) as Record<string, string>;
  const road =
    address.road ??
    address.street ??
    address.pedestrian ??
    address.footway ??
    address.residential ??
    "";
  const number = address.house_number ?? address.housenumber ?? "";
  const town =
    address.city ??
    address.town ??
    address.village ??
    address.municipality ??
    address.hamlet ??
    "";
  const district = address.suburb ?? address.city_district ?? address.borough ?? "";
  const name = (place.name ?? "").trim();
  const parts: string[] = [];
  if (name && !NUMBER_ONLY.test(name)) parts.push(name);
  if (road) parts.push([road, number].filter(Boolean).join(" "));
  else if (number) parts.push(`${town || district} Hausnummer ${number}`.trim());
  parts.push([address.postcode ?? "", town].filter(Boolean).join(" "));
  if (district && district !== town) parts.push(district);
  parts.push(address.state ?? "");
  parts.push(address.country ?? "");
  const full = unique(parts).join(", ");
  return full || place.label || name || "dieser Ort";
}

export function placeTitle(place: MapsPlace): string {
  const name = (place.name ?? "").trim();
  if (name && !NUMBER_ONLY.test(name)) return name;
  const address = (place.address ?? {}) as Record<string, string>;
  const road = address.road ?? address.street ?? address.pedestrian ?? "";
  const town = address.city ?? address.town ?? address.village ?? address.suburb ?? "";
  if (road) return [road, name].filter(Boolean).join(" ");
  if (town && name) return `${town} Hausnummer ${name}`;
  return name || place.label || "Ort";
}

export function placeAskText(place: MapsPlace): string {
  const label = placeFullLabel(place);
  const point = `${place.lat.toFixed(5)}, ${place.lon.toFixed(5)}`;
  return `/maps Was kann ich rund um ${label} unternehmen? Genau dieser Punkt: ${point}`;
}

export function formatDistance(meters: number): string {
  if (meters < 950) return `${Math.round(meters / 10) * 10} m`;
  if (meters < 100000)
    return `${(meters / 1000).toFixed(1).replace(".", ",")} km`;
  return `${Math.round(meters / 1000)} km`;
}

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 1) return "unter 1 Min.";
  if (minutes < 60) return `${minutes} Min.`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} Std.` : `${hours} Std. ${rest} Min.`;
}

export const MODE_ICONS: Record<TravelMode, string> = {
  fuss: "🚶",
  auto: "🚗",
  fahrrad: "🚲",
  oepnv: "🚌",
};

export const MODE_LABELS: Record<TravelMode, string> = {
  fuss: "Zu Fuß",
  auto: "Auto",
  fahrrad: "Fahrrad",
  oepnv: "Bus & Bahn",
};
