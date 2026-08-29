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

export function installTokenFetch(): void {
  if (typeof window === "undefined" || !window.fetch) return;
  const original = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const target =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    if (!sameBackend(target)) return original(input, init);
    const value = resolveToken();
    if (!value) return original(input, init);
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    if (!headers.has(HEADER)) headers.set(HEADER, value);
    return original(input, { ...init, headers });
  };
}
