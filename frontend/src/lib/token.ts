import { BASE } from "./api";

const HEADER = "X-Jon-Token";
const STORAGE_KEY = "jon.token";

function fromUrl(): string {
  try {
    const params = new URLSearchParams(window.location.search);
    const found = params.get("token");
    if (!found) return "";
    params.delete("token");
    const rest = params.toString();
    const clean =
      window.location.pathname + (rest ? `?${rest}` : "") + window.location.hash;
    window.history.replaceState(null, "", clean);
    return found;
  } catch {
    return "";
  }
}

function fromStorage(): string {
  try {
    return window.localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

function remember(value: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, value);
  } catch {
    return;
  }
}

let token = "";

export function resolveToken(): string {
  if (token) return token;
  const injected = typeof window !== "undefined" ? window.jon?.token : "";
  const urlToken = fromUrl();
  if (urlToken) remember(urlToken);
  token = injected || urlToken || fromStorage();
  return token;
}

export function setToken(value: string): void {
  token = value.trim();
  if (token) remember(token);
}

export function withToken(url: string): string {
  const value = resolveToken();
  if (!value) return url;
  return url + (url.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(value);
}

function backendOrigin(): string {
  try {
    return new URL(BASE, window.location.href).origin;
  } catch {
    return window.location.origin;
  }
}

function sameBackend(target: string): boolean {
  try {
    const parsed = new URL(target, window.location.href);
    if (!parsed.pathname.startsWith("/api/")) return false;
    return (
      parsed.origin === backendOrigin() || parsed.origin === window.location.origin
    );
  } catch {
    return false;
  }
}

let laufendeNachfrage: Promise<string> | null = null;

async function tokenNachfragen(): Promise<string> {
  const bruecke = typeof window !== "undefined" ? window.jon : undefined;
  if (!bruecke || typeof bruecke.getToken !== "function") return "";
  if (!laufendeNachfrage) {
    laufendeNachfrage = bruecke
      .getToken()
      .then((wert) => (typeof wert === "string" ? wert.trim() : ""))
      .catch(() => "")
      .finally(() => {
        laufendeNachfrage = null;
      });
  }
  return laufendeNachfrage;
}

function mitSchluessel(
  init: RequestInit | undefined,
  vorhandene: HeadersInit | undefined,
  value: string
): RequestInit {
  const headers = new Headers(init?.headers ?? vorhandene);
  headers.set(HEADER, value);
  return { ...init, headers };
}

export function installTokenFetch(): void {
  if (typeof window === "undefined" || !window.fetch) return;
  const original = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const target =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    if (!sameBackend(target)) return original(input, init);
    const vorhandene = input instanceof Request ? input.headers : undefined;
    const value = resolveToken();
    const antwort = value
      ? await original(input, mitSchluessel(init, vorhandene, value))
      : await original(input, init);
    if (antwort.status !== 401 || input instanceof Request) return antwort;
    const frisch = await tokenNachfragen();
    if (!frisch || frisch === value) return antwort;
    setToken(frisch);
    return original(input, mitSchluessel(init, vorhandene, frisch));
  };
  const bruecke = window.jon;
  if (bruecke && typeof bruecke.onToken === "function") {
    bruecke.onToken((value) => {
      if (typeof value === "string" && value.trim()) setToken(value);
    });
  }
}
