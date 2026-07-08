const BASE = "http://127.0.0.1:8756/api";

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ProviderStatus {
  provider: string;
  configured: boolean;
  env_var: string;
  models: string[];
}

export interface ConversationSummary {
  id: string;
  title: string;
  provider: string;
  model: string;
  created_at: string;
  updated_at: string;
}

export interface Health {
  status: string;
  app: string;
  version: string;
  default_provider: string;
  default_model: string;
  available_providers: string[];
}

export interface StreamEvent {
  type: "meta" | "content" | "reasoning" | "tool" | "error" | "done";
  delta?: string;
  message?: string;
  provider?: string;
  model?: string;
  conversation_id?: string;
  name?: string;
  status?: "running" | "done";
  ok?: boolean;
  args?: Record<string, unknown>;
  summary?: string;
  approval_id?: string;
}

export type ToolMode = "ask" | "allow";

export interface StreamHandlers {
  onMeta?: (e: StreamEvent) => void;
  onContent?: (delta: string) => void;
  onReasoning?: (delta: string) => void;
  onTool?: (e: StreamEvent) => void;
  onError?: (message: string) => void;
  onDone?: (conversationId?: string) => void;
}

export async function transcribeAudio(wav: Blob): Promise<string> {
  const res = await fetch(`${BASE}/system/transcribe`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: wav,
  });
  if (!res.ok) return "";
  const data = await res.json();
  return typeof data.text === "string" ? data.text : "";
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error("health failed");
  return res.json();
}

export async function getProviders(): Promise<ProviderStatus[]> {
  const res = await fetch(`${BASE}/providers`);
  if (!res.ok) throw new Error("providers failed");
  return res.json();
}

export async function getConversations(): Promise<ConversationSummary[]> {
  const res = await fetch(`${BASE}/conversations`);
  if (!res.ok) return [];
  return res.json();
}

export async function getConversation(id: string) {
  const res = await fetch(`${BASE}/conversations/${id}`);
  if (!res.ok) throw new Error("conversation failed");
  return res.json();
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/conversations/${id}`, { method: "DELETE" });
}

export async function approveTool(
  id: string,
  approved: boolean
): Promise<void> {
  await fetch(`${BASE}/chat/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, approved }),
  });
}

export interface Account {
  provider: string;
  label: string;
  auth: string;
  docs: string;
  connected: boolean;
  source: "account" | "env" | "local" | null;
  default_model: string | null;
  account_name: string;
  avatar_url: string | null;
  plan: string;
  models: string[];
}

export interface UsageEntry {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  requests: number;
  total_latency: number;
  avg_latency: number;
  last_request: string | null;
  last_model: string | null;
}

export interface SkillSummary {
  name: string;
  title: string;
  chars: number;
}

export async function getAccounts(): Promise<Account[]> {
  const res = await fetch(`${BASE}/accounts`);
  if (!res.ok) return [];
  return res.json();
}

export async function connectAccount(
  provider: string,
  apiKey: string,
  defaultModel?: string
): Promise<void> {
  await fetch(`${BASE}/accounts/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider,
      api_key: apiKey,
      default_model: defaultModel,
    }),
  });
}

export async function setAccountModel(
  provider: string,
  model: string
): Promise<void> {
  await fetch(`${BASE}/accounts/${provider}/default-model`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
  });
}

export async function disconnectAccount(provider: string): Promise<void> {
  await fetch(`${BASE}/accounts/${provider}`, { method: "DELETE" });
}

export async function getUsage(): Promise<Record<string, UsageEntry>> {
  const res = await fetch(`${BASE}/usage`);
  if (!res.ok) return {};
  const data = await res.json();
  return data.usage ?? {};
}

export async function resetUsage(): Promise<void> {
  await fetch(`${BASE}/usage`, { method: "DELETE" });
}

export async function getSkills(): Promise<SkillSummary[]> {
  const res = await fetch(`${BASE}/skills`);
  if (!res.ok) return [];
  return res.json();
}

export async function getSkill(name: string): Promise<{ content: string }> {
  const res = await fetch(`${BASE}/skills/${name}`);
  if (!res.ok) throw new Error("skill failed");
  return res.json();
}

export async function saveSkill(name: string, content: string): Promise<void> {
  await fetch(`${BASE}/skills/${name}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

export async function deleteSkill(name: string): Promise<void> {
  await fetch(`${BASE}/skills/${name}`, { method: "DELETE" });
}

export interface UserSettings {
  custom_prompt: string;
  prompt_mode: string;
  tool_mode: string;
  personality: boolean;
  provider: string;
  model: string;
  theme: string;
  pet_accent: string;
  pet_face: string;
  pet_cheeks: boolean;
  pet_scale: number;
  pet_eyes: string;
}

export async function getUserSettings(): Promise<UserSettings> {
  const res = await fetch(`${BASE}/settings`);
  if (!res.ok)
    return {
      custom_prompt: "",
      prompt_mode: "append",
      tool_mode: "ask",
      personality: true,
      provider: "",
      model: "",
      theme: "dark",
      pet_accent: "#d4af37",
      pet_face: "#0a0a0e",
      pet_cheeks: true,
      pet_scale: 1.0,
      pet_eyes: "round",
    };
  return res.json();
}

export interface TeamVoice {
  key: string;
  name: string;
  role: string;
  emoji: string;
  text: string;
}

export async function runTeam(
  topic: string,
  provider?: string,
  model?: string
): Promise<{ voices: TeamVoice[]; recommendation: string }> {
  const res = await fetch(`${BASE}/team`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, provider, model }),
  });
  if (!res.ok) throw new Error("Team-Anfrage fehlgeschlagen");
  return res.json();
}

export async function runSimulation(
  scenario: string,
  provider?: string,
  model?: string
): Promise<{ result: string }> {
  const res = await fetch(`${BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, provider, model }),
  });
  if (!res.ok) throw new Error("Simulation fehlgeschlagen");
  return res.json();
}

export interface Snapshot {
  id: string;
  label: string;
  note: string;
  kind: string;
  workspace: string;
  created_at: string;
  files: number;
  archive: string | null;
}

export async function listSnapshots(): Promise<Snapshot[]> {
  const res = await fetch(`${BASE}/snapshots`);
  if (!res.ok) return [];
  return res.json();
}

export async function createSnapshot(
  label: string,
  workspace?: string,
  note = ""
): Promise<Snapshot> {
  const res = await fetch(`${BASE}/snapshots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label, workspace, note }),
  });
  return res.json();
}

export async function restoreSnapshot(id: string): Promise<{ restored: boolean }> {
  const res = await fetch(`${BASE}/snapshots/${id}/restore`, { method: "POST" });
  return res.json();
}

export interface DreamTask {
  id: string;
  task: string;
  status: string;
  result: string | null;
  created_at: string;
  done_at: string | null;
}

export async function listDreams(): Promise<DreamTask[]> {
  const res = await fetch(`${BASE}/dreams`);
  if (!res.ok) return [];
  return res.json();
}

export async function addDream(task: string): Promise<DreamTask> {
  const res = await fetch(`${BASE}/dreams`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task }),
  });
  return res.json();
}

export async function runDreams(): Promise<{ started: boolean; completed?: number }> {
  const res = await fetch(`${BASE}/dreams/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task: "" }),
  });
  return res.json();
}

export async function getDreamReports(): Promise<DreamTask[]> {
  const res = await fetch(`${BASE}/dreams/reports`);
  if (!res.ok) return [];
  return res.json();
}

export interface PersonaState {
  mood: string;
  mood_label: string;
  days_together: number;
  interactions: number;
  energy: number;
  warmth: number;
}

export async function getPersona(): Promise<PersonaState | null> {
  try {
    const res = await fetch(`${BASE}/persona`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function saveUserSettings(
  values: Partial<UserSettings>
): Promise<void> {
  await fetch(`${BASE}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
}

export interface Reminder {
  id: string;
  text: string;
  time: string;
  repeat: string;
  phone: string;
  active: boolean;
}

export async function getReminders(): Promise<Reminder[]> {
  const res = await fetch(`${BASE}/reminders`);
  if (!res.ok) return [];
  return res.json();
}

export async function addReminder(
  text: string,
  time: string,
  repeat: string
): Promise<void> {
  await fetch(`${BASE}/reminders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, time, repeat }),
  });
}

export async function getDueReminders(): Promise<Reminder[]> {
  const res = await fetch(`${BASE}/reminders/due`);
  if (!res.ok) return [];
  return res.json();
}

export async function deleteReminder(id: string): Promise<void> {
  await fetch(`${BASE}/reminders/${id}`, { method: "DELETE" });
}

export interface FileEntry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
}

export async function listDir(path: string): Promise<FileEntry[]> {
  const res = await fetch(`${BASE}/system/files/list`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) return [];
  return res.json();
}

export async function readWorkspaceFile(path: string): Promise<string> {
  const res = await fetch(`${BASE}/system/files/read`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.content ?? "";
}

export async function writeWorkspaceFile(
  path: string,
  content: string
): Promise<void> {
  await fetch(`${BASE}/system/files/write`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
}

export async function openInVscode(path: string): Promise<void> {
  await fetch(`${BASE}/system/vscode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
}

export async function pickFolderDialog(): Promise<string | null> {
  const res = await fetch(`${BASE}/system/pick-folder`, { method: "POST" });
  if (!res.ok) return null;
  const data = await res.json();
  return typeof data.path === "string" ? data.path : "";
}

export async function pathInfo(
  path: string
): Promise<{ exists: boolean; is_dir: boolean; parent: string }> {
  const res = await fetch(`${BASE}/system/path-info`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) return { exists: false, is_dir: false, parent: "" };
  return res.json();
}

export async function streamChat(
  body: {
    messages: ChatMessage[];
    provider?: string;
    model?: string;
    temperature?: number;
    conversation_id?: string | null;
    persist?: boolean;
    tool_mode?: ToolMode;
    mode?: "chat" | "coding";
    workspace?: string | null;
  },
  handlers: StreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok || !res.body) {
    handlers.onError?.(`HTTP ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const json = line.slice(5).trim();
      if (!json) continue;
      let evt: StreamEvent;
      try {
        evt = JSON.parse(json);
      } catch {
        continue;
      }
      if (evt.type === "meta") handlers.onMeta?.(evt);
      else if (evt.type === "content") handlers.onContent?.(evt.delta ?? "");
      else if (evt.type === "reasoning") handlers.onReasoning?.(evt.delta ?? "");
      else if (evt.type === "tool") handlers.onTool?.(evt);
      else if (evt.type === "error") handlers.onError?.(evt.message ?? "error");
      else if (evt.type === "done") handlers.onDone?.(evt.conversation_id);
    }
  }
}
