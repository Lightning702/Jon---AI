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
}

export async function getUserSettings(): Promise<UserSettings> {
  const res = await fetch(`${BASE}/settings`);
  if (!res.ok) return { custom_prompt: "", prompt_mode: "append", tool_mode: "ask" };
  return res.json();
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
