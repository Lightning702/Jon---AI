type Packet = {id?: string; event?: string; data?: any; result?: any; error?: string; chunk?: any};
declare global {interface Window {JonNative?: {post: (data: string) => void}; jonReceive: (packet: Packet) => void}}

const waiting = new Map<string, {resolve: (v: any) => void; reject: (e: Error) => void; chunk?: (v: any) => void; timer: ReturnType<typeof setTimeout>}>();
const events = new Map<string, Set<(v: any) => void>>();
const latest = new Map<string, any>();
let serial = 0;

window.jonReceive = packet => {
  if (packet.event) {
    latest.set(packet.event, packet.data);
    events.get(packet.event)?.forEach(callback => callback(packet.data));
    return;
  }
  const item = waiting.get(packet.id || "");
  if (!item) return;
  if (packet.chunk) {item.chunk?.(packet.chunk); return;}
  clearTimeout(item.timer);
  waiting.delete(packet.id!);
  if (packet.error) item.reject(new Error(packet.error)); else item.resolve(packet.result);
};

export function listen(event: string, callback: (v: any) => void, replay = false) {
  if (!events.has(event)) events.set(event, new Set());
  events.get(event)!.add(callback);
  if (replay && latest.has(event)) callback(latest.get(event));
  return () => {events.get(event)?.delete(callback);};
}

export function native<T = any>(op: string, data: Record<string, unknown> = {}, chunk?: (v: any) => void, timeout = 260_000) {
  const id = `r${Date.now()}_${++serial}`;
  const promise = new Promise<T>((resolve, reject) => {
    if (!window.JonNative) {reject(new Error("Diese Funktion braucht die Jon-App auf dem Gerät.")); return;}
    const timer = setTimeout(() => {
      waiting.delete(id);
      reject(new Error("Der Pi antwortet nicht. Verbindung prüfen."));
      window.JonNative?.post(JSON.stringify({op: "cancel", id: `c${++serial}`, target: id}));
    }, timeout);
    waiting.set(id, {resolve, reject, chunk, timer});
    window.JonNative.post(JSON.stringify({id, op, ...data}));
  });
  return {promise, cancel: () => window.JonNative?.post(JSON.stringify({op: "cancel", id: `c${++serial}`, target: id}))};
}

export const call = <T = any>(op: string, data: Record<string, unknown> = {}, timeout?: number) => native<T>(op, data, undefined, timeout).promise;

export async function api<T = any>(path: string, method = "GET", body?: unknown): Promise<T> {
  const result = await native("api", {path, method, body}).promise;
  return JSON.parse(result.text || "{}");
}

export async function binary(path: string): Promise<{data: string; mime: string}> {
  return native("api", {path, binary: true}).promise;
}

export async function saveFile(path: string) {
  const transfer = (await native("save-start").promise).transfer;
  let offset = 0, size = 1;
  let file: any;
  try {
    do {
      file = await api(`/api/mobile/file?path=${encodeURIComponent(path)}&offset=${offset}`);
      if (file.offset <= offset && file.size !== 0) throw new Error("Dateiübertragung unterbrochen.");
      offset = file.offset;
      size = file.size;
      await native("save-chunk", {transfer, data: file.data}).promise;
    } while (offset < size);
    return await native("save-end", {transfer, name: file.name, mime: file.mime}).promise;
  } catch (e) {
    native("save-abort", {transfer}).promise.catch(() => {});
    throw e;
  }
}

export function haptic(kind: "tap" | "tick" | "success" | "error" = "tap") {
  if (window.JonNative) window.JonNative.post(JSON.stringify({id: `h${++serial}`, op: "haptic", kind}));
}

export const enc = encodeURIComponent;
export const toBase64 = (text: string) => btoa(unescape(encodeURIComponent(text)));
