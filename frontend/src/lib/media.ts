import {BASE} from "./api";
import {harnessRequest} from "./harness";
import {withToken} from "./token";

export type MediaJob = {id: string; kind: string; title: string; status: string; progress: number; message?: string; error?: string; preview?: string; preview_truncated?: boolean; summary?: string; files?: string[]; url?: string; automatic?: boolean};
export async function uploadMedia(file: File): Promise<{id: string; name: string}> {
  if (file.size > 200 * 1024 * 1024) throw new Error("Audiodateien dürfen höchstens 200 MB groß sein.");
  const response = await fetch(BASE + "/media/uploads?name=" + encodeURIComponent(file.name), {method: "POST", body: file, signal: AbortSignal.timeout(180000)});
  if (!response.ok) {const data = await response.json().catch(() => ({})); throw new Error(data.detail || "Audio konnte nicht hochgeladen werden.");}
  return response.json();
}
export const mediaFile = (job: string, file: string) => withToken(BASE + "/media/jobs/" + encodeURIComponent(job) + "/files/" + encodeURIComponent(file));
export const mediaRequest = <T,>(path: string, body?: unknown) => harnessRequest<T>("/media" + path, body);
