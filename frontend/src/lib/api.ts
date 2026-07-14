const BASE =
  window.location.protocol.startsWith("http") &&
  window.location.port === "8756"
    ? `${window.location.origin}/api`
    : "http://127.0.0.1:8756/api";

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
  auto_failover: boolean;
  provider: string;
  model: string;
  theme: string;
  pet_accent: string;
  pet_face: string;
  pet_cheeks: boolean;
  pet_scale: number;
  pet_eyes: string;
  dream_auto: boolean;
  dream_idle_minutes: number;
  vision_model: string;
  briefing_city: string;
  clipboard_history: boolean;
  webcam_enabled: boolean;
  mail_imap_host: string;
  mail_imap_user: string;
  mail_imap_password: string;
  mail_smtp_host: string;
  mail_smtp_port: number;
  calendar_ics_url: string;
  telegram_bot_token: string;
  telegram_chat_id: string;
  telegram_provider: string;
  telegram_model: string;
  pet_provider: string;
  pet_model: string;
  relay_enabled: boolean;
  relay_broker: string;
  relay_port: number;
  ha_url: string;
  ha_token: string;
  natural_voice: boolean;
  spotify_client_id: string;
  spotify_client_secret: string;
}

export async function getUserSettings(): Promise<UserSettings> {
  const res = await fetch(`${BASE}/settings`);
  if (!res.ok)
    return {
      custom_prompt: "",
      prompt_mode: "append",
      tool_mode: "ask",
      personality: true,
      auto_failover: true,
      provider: "",
      model: "",
      theme: "dark",
      pet_accent: "#d4af37",
      pet_face: "#0a0a0e",
      pet_cheeks: false,
      pet_scale: 1.0,
      pet_eyes: "round",
      dream_auto: true,
      dream_idle_minutes: 5,
      vision_model: "",
      briefing_city: "",
      clipboard_history: true,
      webcam_enabled: false,
      mail_imap_host: "",
      mail_imap_user: "",
      mail_imap_password: "",
      mail_smtp_host: "",
      mail_smtp_port: 587,
      calendar_ics_url: "",
      telegram_bot_token: "",
      telegram_chat_id: "",
      telegram_provider: "",
      telegram_model: "openai/gpt-oss-20b",
      pet_provider: "",
      pet_model: "openai/gpt-oss-20b",
      relay_enabled: false,
      relay_broker: "broker.hivemq.com",
      relay_port: 1883,
      ha_url: "",
      ha_token: "",
      natural_voice: true,
      spotify_client_id: "",
      spotify_client_secret: "",
    };
  return res.json();
}

export async function getWeekly(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/weekly`);
  if (!res.ok) throw new Error("weekly failed");
  return res.json();
}

export async function getHealthCheck(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/system/health-check`);
  if (!res.ok) throw new Error("health-check failed");
  return res.json();
}

export interface HumanizeScore {
  score: number;
  label: string;
  burstiness: number;
  phrases: string[];
}

export interface HumanizeResult {
  text: string;
  before: HumanizeScore;
  after: HumanizeScore;
  words: number;
}

export async function humanizeText(
  text: string,
  style: string,
  strength: number,
  provider: string,
  model: string
): Promise<HumanizeResult> {
  const res = await fetch(`${BASE}/humanize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, style, strength, provider, model }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? "Umschreiben fehlgeschlagen");
  }
  return res.json();
}

export async function scoreText(text: string): Promise<HumanizeScore> {
  const res = await fetch(`${BASE}/humanize/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("score failed");
  return res.json();
}

export interface DownloadInfo {
  title: string;
  matched: string;
  thumbnail: string;
  duration: number;
  uploader: string;
  extractor: string;
  max_height: number;
  audio_only: boolean;
  music: boolean;
  url: string;
}

export async function analyzeDownload(url: string): Promise<DownloadInfo> {
  const res = await fetch(`${BASE}/downloader/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Analyse fehlgeschlagen.");
  return data;
}

export async function startDownload(
  url: string,
  format: string,
  quality: string,
  title: string
): Promise<string> {
  const res = await fetch(`${BASE}/downloader/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, format, quality, title }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Start fehlgeschlagen.");
  return data.job;
}

export function downloadProgressUrl(job: string): string {
  return `${BASE}/downloader/progress/${job}`;
}

export function downloadFileUrl(job: string): string {
  return `${BASE}/downloader/file/${job}`;
}

export interface Watcher {
  id: string;
  path: string;
  task: string;
  active: boolean;
  last_result: string | null;
  last_run_at: string | null;
}

export async function getWatchers(): Promise<Watcher[]> {
  const res = await fetch(`${BASE}/watchers`);
  if (!res.ok) return [];
  return res.json();
}

export async function getWatcherReports(): Promise<Watcher[]> {
  const res = await fetch(`${BASE}/watchers/reports`);
  if (!res.ok) return [];
  return res.json();
}

export async function speakServer(
  text: string,
  options: { voice?: string; rate?: string; volume?: string; pitch?: string } = {}
): Promise<Blob | null> {
  try {
    const res = await fetch(`${BASE}/system/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, ...options }),
    });
    if (!res.ok) return null;
    return await res.blob();
  } catch {
    return null;
  }
}

export async function observeScreen(
  provider?: string,
  model?: string
): Promise<{ observation: string; error?: string }> {
  const res = await fetch(`${BASE}/screen/observe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, model }),
  });
  if (!res.ok) return { observation: "" };
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

export async function makeDir(path: string): Promise<boolean> {
  const res = await fetch(`${BASE}/system/files/mkdir`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  return res.ok;
}

export async function readFileBase64(
  path: string
): Promise<{ data: string; mime: string }> {
  const res = await fetch(`${BASE}/system/files/read-base64`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
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

export async function getBriefing(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/briefing`);
  if (!res.ok) throw new Error("briefing failed");
  return res.json();
}

export interface ClipboardEntry {
  id: string;
  text: string;
  created_at: string;
}

export async function getClipboardHistory(
  query = ""
): Promise<ClipboardEntry[]> {
  const res = await fetch(
    `${BASE}/clipboard${query ? `?query=${encodeURIComponent(query)}` : ""}`
  );
  if (!res.ok) return [];
  return res.json();
}

export async function restoreClipboardEntry(id: string): Promise<boolean> {
  const res = await fetch(`${BASE}/clipboard/${id}/restore`, { method: "POST" });
  if (!res.ok) return false;
  const data = await res.json();
  return data.restored === true;
}

export async function deleteClipboardEntry(id: string): Promise<void> {
  await fetch(`${BASE}/clipboard/${id}`, { method: "DELETE" });
}

export async function clearClipboardHistory(): Promise<void> {
  await fetch(`${BASE}/clipboard`, { method: "DELETE" });
}

export interface AutomationTask {
  id: string;
  task: string;
  time: string;
  repeat: string;
  active: boolean;
  last_run_at: string | null;
  last_result: string | null;
}

export async function getTasks(): Promise<AutomationTask[]> {
  const res = await fetch(`${BASE}/tasks`);
  if (!res.ok) return [];
  return res.json();
}

export async function deleteTask(id: string): Promise<void> {
  await fetch(`${BASE}/tasks/${id}`, { method: "DELETE" });
}

export async function getTaskReports(): Promise<AutomationTask[]> {
  const res = await fetch(`${BASE}/tasks/reports`);
  if (!res.ok) return [];
  return res.json();
}

export interface Capsule {
  id: string;
  text?: string;
  preview?: string;
  deliver_date: string;
  created_at: string;
  mood?: string;
  delivered: boolean;
}

export async function getCapsules(): Promise<Capsule[]> {
  const res = await fetch(`${BASE}/capsules`);
  if (!res.ok) return [];
  return res.json();
}

export async function getDueCapsules(): Promise<Capsule[]> {
  const res = await fetch(`${BASE}/capsules/due`);
  if (!res.ok) return [];
  return res.json();
}

export interface KnowledgeDoc {
  id: string;
  title: string;
  source: string;
  kind: string;
  chunks: number;
  chars: number;
  created_at: string;
}

export async function getKnowledgeDocs(): Promise<KnowledgeDoc[]> {
  const res = await fetch(`${BASE}/knowledge`);
  if (!res.ok) return [];
  return res.json();
}

export interface ExtractedAttachment {
  kind: string;
  name: string;
  content: string;
  pages?: number;
}

export async function extractAttachment(
  name: string,
  mime: string,
  dataBase64: string
): Promise<ExtractedAttachment> {
  const res = await fetch(`${BASE}/attachments/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, mime, data: dataBase64 }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) detail = String(data.detail);
    } catch {
      /* leer */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function observeWebcam(
  question = ""
): Promise<{ beschreibung?: string; error?: string }> {
  const res = await fetch(`${BASE}/webcam/observe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) return { error: `HTTP ${res.status}` };
  return res.json();
}

export interface P2PIdentity {
  id: string;
  name: string;
  avatar: string;
  enabled: boolean;
  code: string;
  public_key: string;
}

export interface P2PPeer {
  id: string;
  name: string;
  avatar: string;
  ip: string;
  online: boolean;
  typing: boolean;
  encrypted: boolean;
  waiting: boolean;
  last_seen: string;
  unread: number;
}

export interface P2PRequest {
  id: string;
  name: string;
  avatar: string;
  ip: string;
  location: string;
  created_at: string;
}

export interface P2PDiscovered {
  id: string;
  name: string;
  avatar: string;
}

export interface P2PGroup {
  id: string;
  name: string;
  members: string[];
  member_names: string[];
  unread: number;
}

export interface P2PNotification {
  id: string;
  peer_id: string;
  sender_name: string;
  avatar: string;
  text: string;
  media_kind: "image" | "video" | "file" | null;
}

export interface P2PMessage {
  id: string;
  peer_id: string;
  group_id: string | null;
  direction: "in" | "out";
  sender_name: string;
  text: string;
  media_kind: "image" | "video" | "audio" | "file" | null;
  media_name: string | null;
  media_mime: string | null;
  transcript: string | null;
  reply_to: string | null;
  reply_preview: string | null;
  reactions: Record<string, string[]>;
  deleted: boolean;
  delivered: boolean;
  read: boolean;
  has_media: boolean;
  created_at: string;
  chat_name?: string;
  chat_id?: string;
}

export interface P2PGroupInvite {
  id: string;
  name: string;
  from_name: string;
  members: string[];
}

export const mediaUrl = (messageId: string) => `${BASE}/p2p/media/${messageId}`;

export async function getIdentity(): Promise<P2PIdentity> {
  const res = await fetch(`${BASE}/p2p/me`);
  if (!res.ok) throw new Error("identity failed");
  return res.json();
}

export async function saveIdentity(
  name: string,
  avatar: string
): Promise<P2PIdentity> {
  const res = await fetch(`${BASE}/p2p/me`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, avatar }),
  });
  if (!res.ok) throw new Error("Name konnte nicht gespeichert werden");
  return res.json();
}

export interface P2PInfo {
  ip: string;
  unread: number;
  requests: number;
  relay: { enabled: boolean; connected: boolean; broker: string };
}

export async function getP2PInfo(): Promise<P2PInfo> {
  const res = await fetch(`${BASE}/p2p/info`);
  if (!res.ok)
    return {
      ip: "",
      unread: 0,
      requests: 0,
      relay: { enabled: false, connected: false, broker: "" },
    };
  return res.json();
}

export async function getRequests(): Promise<P2PRequest[]> {
  const res = await fetch(`${BASE}/p2p/requests`);
  if (!res.ok) return [];
  return res.json();
}

export async function getDiscoveredPeers(): Promise<P2PDiscovered[]> {
  const res = await fetch(`${BASE}/p2p/discovered`);
  if (!res.ok) return [];
  return res.json();
}

export async function answerRequest(
  peerId: string,
  action: "accept" | "reject" | "block"
): Promise<void> {
  const res = await fetch(`${BASE}/p2p/requests/${peerId}/${action}`, {
    method: "POST",
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(
      detail.detail ?? "Anfrage konnte nicht beantwortet werden"
    );
  }
}

export async function getGroups(): Promise<P2PGroup[]> {
  const res = await fetch(`${BASE}/p2p/groups`);
  if (!res.ok) return [];
  return res.json();
}

export async function createGroup(
  name: string,
  members: string[]
): Promise<void> {
  const res = await fetch(`${BASE}/p2p/groups`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, members }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? `HTTP ${res.status}`);
  }
}

export async function deleteGroup(groupId: string): Promise<void> {
  await fetch(`${BASE}/p2p/groups/${groupId}`, { method: "DELETE" });
}

export async function getGroupInvites(): Promise<P2PGroupInvite[]> {
  const res = await fetch(`${BASE}/p2p/groups/invites`);
  if (!res.ok) return [];
  return res.json();
}

export async function answerGroupInvite(
  groupId: string,
  action: "accept" | "reject"
): Promise<void> {
  const res = await fetch(`${BASE}/p2p/groups/${groupId}/${action}`, {
    method: "POST",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? `HTTP ${res.status}`);
  }
}

export async function leaveGroup(groupId: string): Promise<void> {
  await fetch(`${BASE}/p2p/groups/${groupId}/leave`, { method: "POST" });
}

export async function reactToMessage(
  messageId: string,
  emoji: string
): Promise<void> {
  await fetch(`${BASE}/p2p/messages/${messageId}/react`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ emoji }),
  });
}

export async function deleteMessage(
  messageId: string,
  forAll = false
): Promise<void> {
  await fetch(`${BASE}/p2p/messages/${messageId}?for_all=${forAll}`, {
    method: "DELETE",
  });
}

export async function clearChat(chatId: string): Promise<void> {
  await fetch(`${BASE}/p2p/chats/${chatId}`, { method: "DELETE" });
}

export async function searchChats(query: string): Promise<P2PMessage[]> {
  const res = await fetch(`${BASE}/p2p/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) return [];
  return res.json();
}

export async function transcribeMessage(messageId: string): Promise<string> {
  const res = await fetch(`${BASE}/p2p/messages/${messageId}/transcribe`, {
    method: "POST",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
  return String(data.transcript ?? "");
}

export async function checkUpdate(): Promise<{
  current: string;
  latest: string;
  update: boolean;
  url: string;
}> {
  const res = await fetch(`${BASE}/update`);
  if (!res.ok) throw new Error("update check failed");
  return res.json();
}

export function backupUrl(): string {
  return `${BASE}/backup/export`;
}

export async function importBackup(file: File): Promise<string> {
  const res = await fetch(`${BASE}/backup/import`, {
    method: "POST",
    body: await file.arrayBuffer(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
  return `${data.restored} Einträge wiederhergestellt. ${data.hinweis ?? ""}`;
}

export async function getPeers(): Promise<P2PPeer[]> {
  const res = await fetch(`${BASE}/p2p/peers`);
  if (!res.ok) return [];
  return res.json();
}

export async function addPeer(
  value: string,
  mode: "name" | "code" = "name"
): Promise<void> {
  const res = await fetch(`${BASE}/p2p/peers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mode === "code" ? { code: value } : { name: value }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? `HTTP ${res.status}`);
  }
}

export async function deletePeer(peerId: string): Promise<void> {
  await fetch(`${BASE}/p2p/peers/${peerId}`, { method: "DELETE" });
}

export async function getP2PMessages(peerId: string): Promise<P2PMessage[]> {
  const res = await fetch(`${BASE}/p2p/messages/${peerId}`);
  if (!res.ok) return [];
  return res.json();
}

export async function sendP2PMessage(
  peerId: string,
  text: string,
  media?: { name: string; mime: string; data: string },
  groupId = "",
  replyTo = ""
): Promise<void> {
  const res = await fetch(`${BASE}/p2p/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      peer_id: peerId,
      text,
      media: media ?? null,
      group_id: groupId,
      reply_to: replyTo,
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? `HTTP ${res.status}`);
  }
}

export async function getChatNotifications(): Promise<P2PNotification[]> {
  const res = await fetch(`${BASE}/p2p/notifications`);
  if (!res.ok) return [];
  return res.json();
}

export interface P2PTyping {
  peer_id: string;
  group_id: string;
}

export async function getTypingPeers(): Promise<P2PTyping[]> {
  try {
    const res = await fetch(`${BASE}/p2p/typing`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.typing) ? data.typing : [];
  } catch {
    return [];
  }
}

export async function sendTyping(
  peerId: string,
  groupId = ""
): Promise<void> {
  try {
    await fetch(`${BASE}/p2p/typing`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ peer_id: peerId, group_id: groupId }),
    });
  } catch {
    /* egal */
  }
}

export async function getAutostart(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/system/autostart`);
    if (!res.ok) return false;
    const data = await res.json();
    return data.enabled === true;
  } catch {
    return false;
  }
}

export async function setAutostart(enabled: boolean): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/system/autostart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    return res.ok;
  } catch {
    return false;
  }
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
