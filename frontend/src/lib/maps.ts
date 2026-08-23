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

export interface MapsCardData {
  aktion: MapsAction;
  anfrage?: string;
  kategorie?: string;
  treffer?: MapsPlace[];
  start?: MapsPlace;
  ziel?: MapsPlace;
  ort?: MapsPlace;
  zwischenstopps?: MapsPlace[];
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
