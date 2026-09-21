import { withToken } from "./token";

function backendBase(): string {
  const { protocol, hostname, port, origin } = window.location;
  if (!protocol.startsWith("http")) return "http://127.0.0.1:8756/api";
  if (port === "8756") return `${origin}/api`;
  const lokal =
    hostname === "localhost" || hostname === "127.0.0.1" || hostname === "";
  return lokal ? "http://127.0.0.1:8756/api" : `${origin}/api`;
}

export const BASE = backendBase();

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ProviderStatus {
  provider: string;
  configured: boolean;
  env_var: string;
  models: string[];
  label?: string;
  locked?: boolean;
  owner?: string;
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
  risiko?: string;
  approval_id?: string;
  card?: { kind: string; data: Record<string, unknown> };
  oeffne?: string;
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
  handy_ordner: string;
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
  mini_jon_bot_token: string;
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
  cowork_enabled: boolean;
  cowork_context: string;
  cowork_app: string;
  quickwrite_enabled: boolean;
  timeline_enabled: boolean;
  routine_enabled: boolean;
  telegram_morning: boolean;
  telegram_morning_time: string;
  pet_roam: boolean;
  pet_companion: string;
  wake_sensitivity: string;
  pet_wellness: boolean;
  pet_3d: boolean;
  autofile_enabled: boolean;
  app_usage_enabled: boolean;
  language: string;
  microphone_device?: string;
  microphone_name?: string;
  phone_enabled?: boolean;
  phone_sip_user?: string;
  phone_sip_port?: number;
  phone_advertise_host?: string;
  phone_caller_name?: string;
  phone_timezone?: string;
  phone_keep_transcript?: boolean;
  phone_max_seconds?: number;
  browser_agent?: boolean;
  browser_sichtbar?: boolean;
  browser_persistent?: boolean;
  browser_plan_modus?: string;
  browser_dry_run?: boolean;
  browser_max_schritte?: number;
  browser_suchmaschine?: string;
  browser_speicher?: string;
  web_browser?: string;
  initiative_enabled?: boolean;
  initiative_stunde?: number;
  wahrnehmung_enabled?: boolean;
  konsolidierung_auto?: boolean;
  kritiker_enabled?: boolean;
  kritiker_schwelle?: number;
  erwartung_enabled?: boolean;
  metakognition_enabled?: boolean;
  neugier_enabled?: boolean;
  neugier_auto?: boolean;
  neugier_pro_lauf?: number;
  fertigkeit_auto?: boolean;
  planer_enabled?: boolean;
  datenschutz_regel?: string;
  budget_tokens_tag?: number;
  budget_euro_monat?: number;
  semantik_modell?: string;
}

const STANDARD_SETTINGS: UserSettings = {
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
    handy_ordner: "",
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
    mini_jon_bot_token: "",
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
    cowork_enabled: false,
    cowork_context: "",
    cowork_app: "auto",
    quickwrite_enabled: true,
    timeline_enabled: false,
    routine_enabled: true,
    telegram_morning: false,
    telegram_morning_time: "07:30",
    pet_roam: false,
    pet_companion: "none",
    wake_sensitivity: "mittel",
    pet_wellness: true,
    pet_3d: false,
    autofile_enabled: false,
    app_usage_enabled: false,
    language: "de",
    phone_enabled: false,
    browser_agent: true,
    browser_sichtbar: true,
    browser_persistent: true,
    browser_plan_modus: "auto",
    browser_dry_run: false,
    browser_max_schritte: 25,
    browser_suchmaschine: "brave",
    browser_speicher: "festplatte",
    web_browser: "jon",
    initiative_enabled: false,
    initiative_stunde: 7,
    wahrnehmung_enabled: false,
    konsolidierung_auto: true,
    kritiker_enabled: false,
    kritiker_schwelle: 0.5,
    erwartung_enabled: true,
    metakognition_enabled: true,
    neugier_enabled: true,
    neugier_auto: false,
    neugier_pro_lauf: 3,
    fertigkeit_auto: false,
    planer_enabled: true,
    datenschutz_regel: "warnen",
    budget_tokens_tag: 0,
    budget_euro_monat: 0,
    semantik_modell: "",
  };

export async function getUserSettings(): Promise<UserSettings> {
  try {
    const res = await fetch(`${BASE}/settings`);
    if (!res.ok) return { ...STANDARD_SETTINGS };
    return await res.json();
  } catch {
    return { ...STANDARD_SETTINGS };
  }
}

export interface ShowLine {
  speaker: "jon" | "mini";
  text: string;
}

export async function buildShow(
  provider: string,
  model: string
): Promise<ShowLine[]> {
  const res = await fetch(`${BASE}/show`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, model }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Show fehlgeschlagen.");
  return data.lines;
}

export interface RoutineSuggestion {
  id: string;
  app: string;
  slot: string;
  days: number;
  time: string;
  text: string;
}

export async function getRoutineSuggestions(): Promise<RoutineSuggestion[]> {
  const res = await fetch(`${BASE}/routine/suggestions`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.suggestions ?? [];
}

export async function acceptRoutine(id: string): Promise<void> {
  await fetch(`${BASE}/routine/accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
}

export async function dismissRoutine(id: string): Promise<void> {
  await fetch(`${BASE}/routine/dismiss`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
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
  playlist: boolean;
  count: number;
  tracks: string[];
  cut: boolean;
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

export interface DownloadCookieState {
  file: boolean;
  count: number;
  updated: number;
  browser: string;
  browsers: string[];
}

export async function downloadCookieState(): Promise<DownloadCookieState> {
  const res = await fetch(`${BASE}/downloader/cookies`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Login-Status nicht ladbar.");
  return data;
}

export async function saveDownloadCookies(
  cookies: string,
  browser: string
): Promise<DownloadCookieState> {
  const res = await fetch(`${BASE}/downloader/cookies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cookies, browser }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Speichern fehlgeschlagen.");
  return data;
}

export async function clearDownloadCookies(): Promise<DownloadCookieState> {
  const res = await fetch(`${BASE}/downloader/cookies`, { method: "DELETE" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Entfernen fehlgeschlagen.");
  return data;
}

export function downloadProgressUrl(job: string): string {
  return withToken(`${BASE}/downloader/progress/${job}`);
}

export function downloadFileUrl(job: string): string {
  return withToken(`${BASE}/downloader/file/${job}`);
}

export function privatBrowserUrl(): string {
  return withToken(BASE.replace(/\/api$/, "") + "/privat");
}

export type SpielStatus =
  | "bereit"
  | "laeuft"
  | "baut"
  | "nicht_gebaut"
  | "fehler"
  | "fehlt"
  | "nicht_verfuegbar";

export interface Spiel {
  id: string;
  titel: string;
  genre: string;
  icon: string;
  kurz: string;
  beschreibung: string;
  steuerung: string;
  version: string;
  herausgeber: string;
  sammlung: string;
  typ: "nativ" | "web";
  pfad: string;
  status: SpielStatus;
  hinweis: string;
  vorschau: boolean;
  baubar: boolean;
  gebaut_am: string;
}

export interface SpielAktion {
  id: string;
  typ: "nativ" | "web";
  status: SpielStatus;
  pfad?: string;
  pid?: number;
  hinweis?: string;
}

async function spielAktion(id: string, aktion: string): Promise<SpielAktion> {
  const res = await fetch(`${BASE}/games/${encodeURIComponent(id)}/${aktion}`, { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Das Spiel konnte nicht gestartet werden.");
  return data;
}

export async function getSpiele(frisch = false): Promise<Spiel[]> {
  const res = await fetch(`${BASE}/games${frisch ? "?frisch=true" : ""}`);
  if (!res.ok) throw new Error("Die Spiele-Liste konnte nicht geladen werden.");
  return (await res.json()).spiele ?? [];
}

export async function startSpiel(id: string): Promise<SpielAktion> {
  return spielAktion(id, "start");
}

export async function stopSpiel(id: string): Promise<SpielAktion> {
  return spielAktion(id, "stop");
}

export async function buildSpiel(id: string): Promise<SpielAktion> {
  return spielAktion(id, "build");
}

export function spielVorschauUrl(id: string): string {
  return withToken(`${BASE}/games/${encodeURIComponent(id)}/vorschau`);
}

export function spielSeitenUrl(pfad: string): string {
  return BASE.replace(/\/api$/, "") + pfad;
}


export interface JournalEntry {
  id: string;
  date: string;
  time: string;
  title: string;
  tags: string[];
  mood: string;
  text: string;
}

export async function getJournal(): Promise<JournalEntry[]> {
  const res = await fetch(`${BASE}/journal`);
  if (!res.ok) return [];
  return (await res.json()).entries ?? [];
}

export async function addJournal(text: string): Promise<JournalEntry> {
  const res = await fetch(`${BASE}/journal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Speichern fehlgeschlagen.");
  return data;
}

export async function askJournal(query: string): Promise<string> {
  const res = await fetch(`${BASE}/journal/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Suche fehlgeschlagen.");
  return data.answer;
}

export async function deleteJournal(id: string): Promise<void> {
  await fetch(`${BASE}/journal/${id}`, { method: "DELETE" });
}

export interface CleanupPreview {
  plan: string;
  folder: string;
  count: number;
  summary: { ordner: string; dateien: number }[];
  sample: { name: string; target: string }[];
}

export async function cleanupPreview(
  folder: string,
  by: string
): Promise<CleanupPreview> {
  const res = await fetch(`${BASE}/cleanup/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder, by }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Vorschau fehlgeschlagen.");
  return data;
}

export async function cleanupApply(
  plan: string
): Promise<{ moved: number; failed: number }> {
  const res = await fetch(`${BASE}/cleanup/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Aufräumen fehlgeschlagen.");
  return data;
}

export interface RecipeIdea {
  name: string;
  dauer: string;
  schwierigkeit: string;
  beschreibung: string;
}

export async function recipeSuggest(ingredients: string): Promise<RecipeIdea[]> {
  const res = await fetch(`${BASE}/recipe/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ingredients }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Vorschlag fehlgeschlagen.");
  return data.vorschlaege ?? [];
}

export interface Recipe {
  name: string;
  portionen: number;
  zutaten: string[];
  schritte: string[];
}

export async function recipeMake(dish: string): Promise<Recipe> {
  const res = await fetch(`${BASE}/recipe/make`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dish }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Rezept fehlgeschlagen.");
  return data;
}

export interface Deck {
  id: string;
  titel: string;
  anzahl: number;
  faellig: number;
}

export async function getDecks(): Promise<Deck[]> {
  const res = await fetch(`${BASE}/flashcards`);
  if (!res.ok) return [];
  return (await res.json()).decks ?? [];
}

export async function generateDeck(
  topic: string
): Promise<{ id: string; titel: string; anzahl: number }> {
  const res = await fetch(`${BASE}/flashcards/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Erstellen fehlgeschlagen.");
  return data;
}

export interface NextCard {
  id?: string;
  frage?: string;
  stufe?: number;
  offen?: number;
  done?: boolean;
}

export async function nextCard(deck: string): Promise<NextCard> {
  const res = await fetch(`${BASE}/flashcards/${deck}/next`);
  if (!res.ok) throw new Error("Karte laden fehlgeschlagen.");
  return res.json();
}

export async function answerCard(
  deck: string,
  card: string,
  answer: string
): Promise<{ richtig: boolean; loesung: string; feedback: string }> {
  const res = await fetch(`${BASE}/flashcards/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deck, card, answer }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Antwort fehlgeschlagen.");
  return data;
}

export async function deleteDeck(deck: string): Promise<void> {
  await fetch(`${BASE}/flashcards/${deck}`, { method: "DELETE" });
}

export async function explainScreen(): Promise<string> {
  const res = await fetch(`${BASE}/screen/explain`, { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Erklärung fehlgeschlagen.");
  return data.explanation;
}

export async function startPomodoro(goal: string): Promise<void> {
  await fetch(`${BASE}/pomodoro/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ work: 25, brk: 5, rounds: 4, goal }),
  });
}

export interface Note {
  id: string;
  text: string;
  color: string;
  pinned: boolean;
  done: boolean;
}

export async function getNotes(): Promise<Note[]> {
  const res = await fetch(`${BASE}/notes`);
  if (!res.ok) return [];
  return (await res.json()).notes ?? [];
}

export async function addNote(text: string, color: string): Promise<Note> {
  const res = await fetch(`${BASE}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, color }),
  });
  return res.json();
}

export async function updateNote(id: string, patch: Partial<Note>): Promise<void> {
  await fetch(`${BASE}/notes`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, ...patch }),
  });
}

export async function deleteNote(id: string): Promise<void> {
  await fetch(`${BASE}/notes/${id}`, { method: "DELETE" });
}

export interface VaultEntry {
  id: string;
  title: string;
  username: string;
}

export async function vaultStatus(): Promise<{ exists: boolean; unlocked: boolean }> {
  const res = await fetch(`${BASE}/vault/status`);
  return res.json();
}

export async function vaultCreate(password: string): Promise<void> {
  const res = await fetch(`${BASE}/vault/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Fehlgeschlagen.");
}

export async function vaultUnlock(password: string): Promise<void> {
  const res = await fetch(`${BASE}/vault/unlock`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Falsches Passwort.");
}

export async function vaultLock(): Promise<void> {
  await fetch(`${BASE}/vault/lock`, { method: "POST" });
}

export async function vaultEntries(): Promise<{ locked: boolean; entries: VaultEntry[] }> {
  const res = await fetch(`${BASE}/vault/entries`);
  return res.json();
}

export async function vaultReveal(id: string): Promise<{ secret: string; username: string }> {
  const res = await fetch(`${BASE}/vault/reveal/${id}`);
  if (!res.ok) throw new Error((await res.json()).detail ?? "Gesperrt.");
  return res.json();
}

export async function vaultAdd(
  title: string,
  username: string,
  secret: string
): Promise<VaultEntry> {
  const res = await fetch(`${BASE}/vault/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, username, secret }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Fehlgeschlagen.");
  return res.json();
}

export async function vaultDelete(id: string): Promise<void> {
  await fetch(`${BASE}/vault/${id}`, { method: "DELETE" });
}

export async function vaultGenerate(length: number, symbols: boolean): Promise<string> {
  const res = await fetch(`${BASE}/vault/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ length, symbols }),
  });
  return (await res.json()).password;
}

export interface SearchGroup {
  kind: string;
  label: string;
  items: { id?: string; title?: string; snippet: string; path?: string }[];
}

export async function universalSearch(query: string): Promise<SearchGroup[]> {
  const res = await fetch(`${BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) return [];
  return (await res.json()).groups ?? [];
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

export interface BrowserPlanSchritt {
  id: number;
  beschreibung: string;
  art: string;
  risiko: string;
  bestaetigung_noetig: boolean;
}

export interface BrowserPlanDaten {
  ziel: string;
  schritte: BrowserPlanSchritt[];
  aktueller_schritt: number;
  risiko: string;
  bestaetigung_noetig: boolean;
  kritische_schritte: number[];
  status: string;
  grund?: string;
}

export interface BrowserTaskDaten {
  ok: boolean;
  auftrag: string;
  dry_run?: boolean;
  schritte?: number;
  bericht?: string;
  url?: string;
  titel?: string;
  abbruch?: string;
  hinweis?: string;
  plan?: BrowserPlanDaten;
  protokoll?: string[];
  bestaetigung?: {
    token?: string;
    zusammenfassung?: string;
    risiko?: string;
    art?: string;
  };
}

export interface BrowserZustand {
  aktiv: boolean;
  url: string;
  titel: string;
  letzte_aktion?: string;
  tab: string;
  tabs: { tab: string; titel: string; url: string; aktiv: boolean }[];
  laden: string;
  plan_schritt: number;
  plan_schritte: number;
  plan_ziel: string;
  status: string;
  fehler: string;
  aktualisiert: string;
}

export interface BrowserStatus {
  zustand: BrowserZustand;
  bestaetigung: {
    token: string;
    zusammenfassung: string;
    bestaetigt: boolean;
    abgelehnt: boolean;
    verbraucht: boolean;
    abgelaufen: boolean;
  } | null;
  protokoll: { zeit: string; aktion: string; detail: string }[];
}

export async function getBrowserStatus(): Promise<BrowserStatus | null> {
  try {
    const res = await fetch(`${BASE}/browser/status`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function confirmBrowserAction(
  token: string,
  approved: boolean
): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/browser/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, approved }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function stopBrowser(): Promise<void> {
  try {
    await fetch(`${BASE}/browser/stop`, { method: "POST" });
  } catch {
    return;
  }
}

export interface DenkZiel {
  id: string;
  titel: string;
  beschreibung: string;
  zustand: string;
  naechster_schritt: string;
  frist: string;
  tage_bis_frist: number | null;
  wichtigkeit: number;
  fortschritt: number;
}

export interface DenkVorschlag {
  id: string;
  titel: string;
  warum: string;
  wann: string;
  selbst_machbar: boolean;
  werkzeug: string;
  risiko: string;
  zustand: string;
}

export interface DenkZustand {
  zeit: string;
  browser?: { offen: string[]; sitzungen: Record<string, { url: string; titel: string }> };
  bildschirm?: { vorne?: string; fenster?: number; leerlauf_s?: number };
  auftraege?: { offen: number; titel: string[] };
  ziele?: { offen: number; faellig: string[] };
  netz?: { online: boolean };
  budget?: { tokens: number; euro: number; anfragen: number };
}

export interface DenkVerlauf {
  zeitraum: { beschreibung: string; von: string; bis: string };
  anzahl: number;
  nach_art: Record<string, number>;
  haeufigste_werkzeuge: [string, number][];
  fehler: string[];
  hoehepunkte: { zeit: string; art: string; titel: string; detail: string }[];
}

export interface DenkSelbstbild {
  werkzeuge: number;
  skills: string[];
  grenzen: string[];
  bilanz: {
    aktionen: number;
    schwaechste: { werkzeug: string; laeufe: number; erfolgsquote: number }[];
    staerkste: { werkzeug: string; laeufe: number; erfolgsquote: number }[];
  };
}

export async function getZiele(): Promise<{ offen: DenkZiel[]; faellig: DenkZiel[] }> {
  try {
    const res = await fetch(`${BASE}/denken/ziele`);
    if (!res.ok) return { offen: [], faellig: [] };
    return await res.json();
  } catch {
    return { offen: [], faellig: [] };
  }
}

export async function addZiel(
  titel: string,
  frist = "",
  naechster_schritt = ""
): Promise<DenkZiel | null> {
  try {
    const res = await fetch(`${BASE}/denken/ziele`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ titel, frist, naechster_schritt }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function updateZiel(
  id: string,
  werte: { zustand?: string; naechster_schritt?: string; fortschritt?: number }
): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/denken/ziele/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(werte),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function deleteZiel(id: string): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/denken/ziele/${id}`, { method: "DELETE" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function getDenkZustand(): Promise<DenkZustand | null> {
  try {
    const res = await fetch(`${BASE}/denken/zustand`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function getDenkVerlauf(zeitraum = "heute"): Promise<DenkVerlauf | null> {
  try {
    const res = await fetch(
      `${BASE}/denken/verlauf?zeitraum=${encodeURIComponent(zeitraum)}`
    );
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function getVorschlaege(): Promise<DenkVorschlag[]> {
  try {
    const res = await fetch(`${BASE}/denken/initiative`);
    if (!res.ok) return [];
    const daten = await res.json();
    return daten.vorschlaege ?? [];
  } catch {
    return [];
  }
}

export async function initiativeLauf(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/denken/initiative/lauf`, { method: "POST" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function vorschlagEntscheiden(
  id: string,
  angenommen: boolean,
  ausfuehren = false
): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/denken/initiative/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ angenommen, ausfuehren }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function getSelbstbild(): Promise<DenkSelbstbild | null> {
  try {
    const res = await fetch(`${BASE}/denken/selbstbild`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export interface DenkKalibrierung {
  anzahl: number;
  brier: number | null;
  treffer: number | null;
  ueberraschung: number;
  schwaechste: { werkzeug: string; ueberraschung: number; anzahl: number }[];
  text: string;
}

export interface DenkUeberraschung {
  id: string;
  zeit: string;
  werkzeug: string;
  bereich: string;
  erwartet: string;
  zutrauen: number;
  gelungen: boolean;
  ueberraschung: number;
  notiz: string;
}

export interface DenkFrage {
  id: string;
  text: string;
  thema: string;
  quelle: string;
  dringlichkeit: number;
  zustand: string;
  antwort: string;
  versuche: number;
  erstellt: string;
}

export interface DenkFertigkeit {
  id: string;
  name: string;
  beschreibung: string;
  ausloeser: string;
  schritte: { werkzeug: string; args: Record<string, unknown>; notiz?: string }[];
  versuche: number;
  erfolge: number;
  erfolgsquote: number | null;
  aktiv: boolean;
  quelle: string;
  benutzt: string;
}

export interface DenkPlanSchritt {
  id: string;
  titel: string;
  werkzeug: string;
  zustand: string;
  ergebnis: string;
  haengt_von: string[];
}

export interface DenkPlan {
  id: string;
  auftrag: string;
  zustand: string;
  schritte: DenkPlanSchritt[];
  erledigt: number;
  anzahl: number;
  fortschritt: number;
  ergebnis: string;
  umplanungen: number;
  erstellt: string;
}

export async function getErwartung(
  tage = 14
): Promise<{ kalibrierung: DenkKalibrierung; ueberraschungen: DenkUeberraschung[] } | null> {
  try {
    const res = await fetch(`${BASE}/denken/erwartung?tage=${tage}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function getFragen(): Promise<{
  offen: DenkFrage[];
  beantwortet: DenkFrage[];
} | null> {
  try {
    const res = await fetch(`${BASE}/denken/fragen`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function addFrage(text: string): Promise<DenkFrage | null> {
  try {
    const res = await fetch(`${BASE}/denken/fragen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function frageKlaeren(id: string): Promise<DenkFrage | null> {
  try {
    const res = await fetch(`${BASE}/denken/fragen/${id}`, { method: "POST" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function frageVerwerfen(id: string): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/denken/fragen/${id}`, { method: "DELETE" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fragenLauf(anzahl = 3): Promise<{ beantwortet: number } | null> {
  try {
    const res = await fetch(`${BASE}/denken/fragen/lauf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ anzahl }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function getFertigkeiten(): Promise<{
  anzahl: number;
  aktiv: number;
  fertigkeiten: DenkFertigkeit[];
} | null> {
  try {
    const res = await fetch(`${BASE}/denken/fertigkeiten`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function getFertigkeitVorschlaege(): Promise<
  { name: string; anzahl: number; beschreibung: string; schritte: unknown[] }[]
> {
  try {
    const res = await fetch(`${BASE}/denken/fertigkeiten/vorschlaege`);
    if (!res.ok) return [];
    return (await res.json()).vorschlaege ?? [];
  } catch {
    return [];
  }
}

export async function addFertigkeit(
  name: string,
  schritte: unknown[],
  beschreibung = "",
  ausloeser = ""
): Promise<DenkFertigkeit | null> {
  try {
    const res = await fetch(`${BASE}/denken/fertigkeiten`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, schritte, beschreibung, ausloeser, quelle: "nutzer" }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function deleteFertigkeit(name: string): Promise<boolean> {
  try {
    const res = await fetch(
      `${BASE}/denken/fertigkeiten/${encodeURIComponent(name)}`,
      { method: "DELETE" }
    );
    return res.ok;
  } catch {
    return false;
  }
}

export async function getPlaene(): Promise<DenkPlan[]> {
  try {
    const res = await fetch(`${BASE}/denken/plaene`);
    if (!res.ok) return [];
    return (await res.json()).plaene ?? [];
  } catch {
    return [];
  }
}

export async function addPlan(auftrag: string): Promise<DenkPlan | null> {
  try {
    const res = await fetch(`${BASE}/denken/plaene`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auftrag }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function planLauf(
  id: string,
  bestaetigt = false
): Promise<(DenkPlan & { ereignisse?: { art: string; text?: string }[] }) | null> {
  try {
    const res = await fetch(`${BASE}/denken/plaene/${id}/lauf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bestaetigt }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function planAbbrechen(id: string): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/denken/plaene/${id}`, { method: "DELETE" });
    return res.ok;
  } catch {
    return false;
  }
}

export interface JonDatei {
  type: "file";
  name: string;
  path: string;
  mimeType: string;
  kind: string;
  size: number;
  sizeText: string;
  folder: string;
  project: string;
  title: string;
  exists: boolean;
  actions: string[];
}

export interface JonDateiraum {
  wurzel: string;
  ordner: { name: string; pfad: string; dateien: number }[];
  bekannt: Record<string, string>;
  freigegeben: string[];
}

export function dateiInhaltUrl(pfad: string): string {
  return withToken(`${BASE}/dateien/inhalt?pfad=${encodeURIComponent(pfad)}`);
}

export async function dateiOeffnen(
  pfad: string,
  ordner = false
): Promise<{ ok?: boolean; error?: string } | null> {
  try {
    const res = await fetch(`${BASE}/dateien/oeffnen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pfad, ordner }),
    });
    const daten = await res.json().catch(() => null);
    if (!res.ok) {
      return { error: daten?.detail ?? "Das ließ sich nicht öffnen." };
    }
    return daten;
  } catch {
    return { error: "Jon antwortet gerade nicht." };
  }
}

export async function getDateiraum(): Promise<JonDateiraum | null> {
  try {
    const res = await fetch(`${BASE}/dateien/raum`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function sucheDateien(frage: string): Promise<JonDatei[]> {
  try {
    const res = await fetch(
      `${BASE}/dateien/suche?frage=${encodeURIComponent(frage)}`
    );
    if (!res.ok) return [];
    return (await res.json()).dateien ?? [];
  } catch {
    return [];
  }
}

export async function getUmgebung(neu = false): Promise<{
  plattform: string;
  python: string;
  dateimanager: string;
  werkzeuge: { befehl: string; titel: string; da: boolean; version?: string; wozu: string }[];
  pakete: { modul: string; paket: string; da: boolean; wozu: string; installieren: string }[];
  llm: { bereit: boolean; anbieter: string[]; ollama: boolean; hinweis: string };
  telegram: { bereit: boolean; hinweis: string };
  fehlt: string[];
  fehlende_pakete: string[];
} | null> {
  try {
    const res = await fetch(`${BASE}/dateien/umgebung?neu=${neu ? "true" : "false"}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
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
  pfad?: string;
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
    } catch {}
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

export const mediaUrl = (messageId: string) =>
  withToken(`${BASE}/p2p/media/${messageId}`);

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
  mode: "exe" | "git" | "manual";
  installer_url: string;
  installer_size: number;
  can_install: boolean;
  notes?: string;
}> {
  const res = await fetch(`${BASE}/update`);
  if (!res.ok) throw new Error("update check failed");
  return res.json();
}

export function backupUrl(): string {
  return withToken(`${BASE}/backup/export`);
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
  } catch {}
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
    active_file?: string | null;
    force_tool?: string;
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

export interface TrashEntry {
  id: string;
  action: string;
  original: string;
  name?: string;
  destination?: string;
  deleted_at?: string;
}

export async function getTrash(): Promise<TrashEntry[]> {
  const res = await fetch(`${BASE}/trash`);
  if (!res.ok) throw new Error("trash failed");
  return res.json();
}

export async function restoreTrash(
  id: string
): Promise<{ restored?: string; error?: string }> {
  const res = await fetch(`${BASE}/trash/restore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
  return res.json();
}

export async function undoTrash(): Promise<{
  restored?: string;
  error?: string;
}> {
  const res = await fetch(`${BASE}/trash/undo`, { method: "POST" });
  return res.json();
}

export interface ActionLogEntry {
  id: number;
  source: string;
  tool: string;
  args: string;
  result: string;
  ok: boolean;
  created_at: string;
}

export async function getActions(
  source = "",
  day = "",
  limit = 30
): Promise<ActionLogEntry[]> {
  const params = new URLSearchParams();
  if (source) params.set("source", source);
  if (day) params.set("day", day);
  params.set("limit", String(limit));
  const res = await fetch(`${BASE}/actions?${params.toString()}`);
  if (!res.ok) throw new Error("actions failed");
  return res.json();
}

export interface WakeStatus {
  available: boolean;
  listening: boolean;
  counter: number;
  error?: string;
}

export async function wakeStart(): Promise<WakeStatus> {
  const res = await fetch(`${BASE}/voice/wake/start`, { method: "POST" });
  if (!res.ok) throw new Error("wake start failed");
  return res.json();
}

export async function wakePoll(): Promise<WakeStatus> {
  const res = await fetch(`${BASE}/voice/wake`);
  if (!res.ok) throw new Error("wake poll failed");
  return res.json();
}

export async function wakeStop(): Promise<void> {
  await fetch(`${BASE}/voice/wake/stop`, { method: "POST" });
}

export interface CalendarEvent {
  id: string;
  quelle: "jon" | "automation" | "erinnerung" | "ics";
  titel: string;
  datum: string;
  zeit: string;
  dauer_minuten?: number;
  notiz?: string;
  ort?: string;
  typ: "termin" | "task" | "erinnerung";
  erledigt: boolean;
}

export async function getCalendar(
  start = "",
  days = 7
): Promise<CalendarEvent[]> {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  params.set("days", String(days));
  const res = await fetch(`${BASE}/calendar?${params.toString()}`);
  if (!res.ok) return [];
  return res.json();
}

export interface CalendarEntryIn {
  title: string;
  date: string;
  time?: string;
  duration_minutes?: number;
  note?: string;
  kind?: string;
}

export async function addCalendarEntry(
  entry: CalendarEntryIn
): Promise<{ id?: string; konflikte?: unknown[]; detail?: string }> {
  const res = await fetch(`${BASE}/calendar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  return res.json();
}

export async function updateCalendarEntry(
  id: string,
  fields: Partial<CalendarEntryIn> & { done?: boolean }
): Promise<{ konflikte?: unknown[]; detail?: string }> {
  const res = await fetch(`${BASE}/calendar/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  return res.json();
}

export async function deleteCalendarEntry(id: string): Promise<void> {
  await fetch(`${BASE}/calendar/${id}`, { method: "DELETE" });
}

export async function getCalendarDue(): Promise<
  { title: string; time: string }[]
> {
  const res = await fetch(`${BASE}/calendar/due`);
  if (!res.ok) return [];
  return res.json();
}

export interface AppUsageReport {
  zeitraum_tage: number;
  gesamt_minuten: number;
  apps: { app: string; minuten: number }[];
  pro_tag: Record<string, number>;
}

export async function getAppUsage(days = 7): Promise<AppUsageReport> {
  const res = await fetch(`${BASE}/usage/apps?days=${days}`);
  if (!res.ok) throw new Error("usage failed");
  return res.json();
}

export interface MeetingStatus {
  running: boolean;
  mikrofon?: string;
  sekunden?: number;
  segmente?: number;
}

export async function meetingStatus(): Promise<MeetingStatus> {
  const res = await fetch(`${BASE}/meeting/status`);
  if (!res.ok) return { running: false };
  return res.json();
}

export async function meetingStart(): Promise<{
  running?: boolean;
  mikrofon?: string;
  error?: string;
}> {
  const res = await fetch(`${BASE}/meeting/start`, { method: "POST" });
  return res.json();
}

export async function meetingStop(): Promise<{
  zusammenfassung?: string;
  todos?: string[];
  transkript?: string;
  error?: string;
}> {
  const res = await fetch(`${BASE}/meeting/stop`, { method: "POST" });
  return res.json();
}

export interface OllamaConfig {
  enabled: boolean;
  scheme: string;
  host: string;
  port: number;
  url: string;
  api_base: string;
  model: string;
  temperature: number;
  top_p: number;
  top_k: number;
  max_tokens: number;
  context_length: number;
  keep_alive: string;
  seed: number;
  system_prompt: string;
  stream: boolean;
  timeout: number;
  auto_reconnect: boolean;
  auto_load_models: boolean;
  last_success: string;
}

export type OllamaState = "online" | "offline" | "connecting" | "disabled";

export interface OllamaStatus {
  state: OllamaState;
  url: string;
  host: string;
  port: number;
  model: string;
  models: string[];
  model_count: number;
  version: string;
  response_ms: number;
  last_success: string;
  error: string;
  checked_at: string;
  ok?: boolean;
}

export async function getOllamaConfig(): Promise<OllamaConfig> {
  const res = await fetch(`${BASE}/ollama/config`);
  if (!res.ok) throw new Error("Ollama-Einstellungen nicht erreichbar.");
  return res.json();
}

export async function saveOllamaConfig(
  values: Partial<OllamaConfig>
): Promise<OllamaConfig> {
  const res = await fetch(`${BASE}/ollama/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Speichern fehlgeschlagen.");
  return data;
}

export async function resetOllamaConfig(): Promise<OllamaConfig> {
  const res = await fetch(`${BASE}/ollama/reset`, { method: "POST" });
  if (!res.ok) throw new Error("Zuruecksetzen fehlgeschlagen.");
  return res.json();
}

export async function getOllamaStatus(force = false): Promise<OllamaStatus> {
  const res = await fetch(`${BASE}/ollama/status?force=${force ? "true" : "false"}`);
  if (!res.ok) throw new Error("Status nicht abrufbar.");
  return res.json();
}

export async function testOllama(
  values: Partial<OllamaConfig> = {}
): Promise<OllamaStatus> {
  const res = await fetch(`${BASE}/ollama/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Verbindungstest fehlgeschlagen.");
  return data;
}

export async function getOllamaModels(
  refresh = false
): Promise<{ models: string[]; count: number; model: string }> {
  const res = await fetch(
    `${BASE}/ollama/models?refresh=${refresh ? "true" : "false"}`
  );
  if (!res.ok) return { models: [], count: 0, model: "" };
  return res.json();
}

export interface OllamaHost {
  label: string;
  host: string;
  kind: string;
  hint: string;
}

export async function getOllamaHosts(): Promise<OllamaHost[]> {
  const res = await fetch(`${BASE}/ollama/hosts`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.hosts ?? [];
}

export type ShareVisibility = "private" | "invited" | "public";

export interface OllamaInvite {
  code: string;
  label: string;
  created_at: string;
  used_by: string;
  link?: string;
}

export interface OllamaShare {
  enabled: boolean;
  name: string;
  description: string;
  visibility: ShareVisibility;
  code: string;
  created_at: string;
  host: string;
  port: number;
  link: string;
  owner: string;
  user_count: number;
  open_invites: OllamaInvite[];
  shared_model: string;
}

export interface OllamaShareUser {
  id: string;
  user: string;
  user_id: string;
  address: string;
  created_at: string;
  model: string;
  requests: number;
  sessions: number;
  state: string;
  last_activity: string;
  invite: string;
}

export interface OllamaRemote {
  code: string;
  host: string;
  port: number;
  base: string;
  grant_id: string;
  name: string;
  description: string;
  owner: string;
  added_at: string;
  last_ok: string;
  models: string[];
  model: string;
  error: string;
}

export async function getOllamaShare(): Promise<{
  share: OllamaShare;
  users: OllamaShareUser[];
}> {
  const res = await fetch(`${BASE}/ollama/share`);
  if (!res.ok) throw new Error("Freigabe nicht abrufbar.");
  return res.json();
}

export async function saveOllamaShare(
  values: Partial<OllamaShare>
): Promise<OllamaShare> {
  const res = await fetch(`${BASE}/ollama/share`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Speichern fehlgeschlagen.");
  return data;
}

export async function newOllamaShareCode(): Promise<OllamaShare> {
  const res = await fetch(`${BASE}/ollama/share/code`, { method: "POST" });
  if (!res.ok) throw new Error("Neuer Code fehlgeschlagen.");
  return res.json();
}

export async function createOllamaInvite(label: string): Promise<OllamaInvite> {
  const res = await fetch(`${BASE}/ollama/share/invites`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label }),
  });
  if (!res.ok) throw new Error("Einladung fehlgeschlagen.");
  return res.json();
}

export async function deleteOllamaInvite(code: string): Promise<void> {
  await fetch(`${BASE}/ollama/share/invites/${code}`, { method: "DELETE" });
}

export async function getOllamaShareUsers(): Promise<OllamaShareUser[]> {
  const res = await fetch(`${BASE}/ollama/share/users`);
  if (!res.ok) return [];
  return res.json();
}

export async function removeOllamaShareUser(id: string): Promise<void> {
  await fetch(`${BASE}/ollama/share/users/${id}`, { method: "DELETE" });
}

export async function revokeOllamaShare(): Promise<number> {
  const res = await fetch(`${BASE}/ollama/share/revoke`, { method: "POST" });
  if (!res.ok) return 0;
  const data = await res.json();
  return data.revoked ?? 0;
}

export async function getOllamaRemotes(): Promise<OllamaRemote[]> {
  const res = await fetch(`${BASE}/ollama/remote`);
  if (!res.ok) return [];
  return res.json();
}

export async function connectOllamaRemote(code: string): Promise<OllamaRemote> {
  const res = await fetch(`${BASE}/ollama/remote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Verbinden fehlgeschlagen.");
  return data;
}

export async function refreshOllamaRemote(code: string): Promise<OllamaRemote> {
  const res = await fetch(`${BASE}/ollama/remote/${code}/refresh`, {
    method: "POST",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Aktualisieren fehlgeschlagen.");
  return data;
}

export async function forgetOllamaRemote(code: string): Promise<void> {
  await fetch(`${BASE}/ollama/remote/${code}`, { method: "DELETE" });
}

export interface PhoneDevice {
  registered: boolean;
  contact: string;
  user_agent: string;
  source: string;
  expires_in: number;
  transport?: string;
}

export interface PhoneAttempt {
  at: number;
  source: string;
  transport: string;
  detail: string;
}

export interface PhoneStatus {
  enabled: boolean;
  running: boolean;
  status: string;
  error: string;
  sip_user: string;
  sip_port: number;
  realm: string;
  server: string;
  timezone: string;
  device: PhoneDevice;
  recognizer: { ready: boolean; error: string };
  ffmpeg: { ready: boolean; error: string };
  attempts: PhoneAttempt[];
  active_call: { id: string; status: string; reason: string; duration: number } | null;
  scheduled: number;
}

export interface PhoneCall {
  id: string;
  scheduled_at: string;
  timezone: string;
  reason: string;
  message: string;
  status: string;
  recurrence: string;
  duration: number;
  created_at: string;
}

export interface PhoneAddress {
  ip: string;
  label: string;
  kind: string;
  usable: boolean;
  selected: boolean;
}

export interface PhoneSetup {
  server: string;
  port: number;
  username: string;
  password: string;
  realm: string;
  transport: string;
  app: string;
  app_url: string;
  addresses: PhoneAddress[];
}

export interface PhoneCheck {
  name: string;
  ok: boolean;
  detail: string;
  fix?: string;
  fix_hint?: string;
}

export interface PhoneLogEntry {
  id: string;
  status: string;
  reason: string;
  message: string;
  started_at: string;
  duration: number;
  transcript: { who: string; text: string; at: string }[];
}

async function phoneJson(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}/phone${path}`, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? "Telefonfunktion nicht erreichbar.");
  return data;
}

export async function getPhoneStatus(): Promise<PhoneStatus> {
  return phoneJson("/status");
}

export async function getPhoneDiagnostics(): Promise<{
  ready: boolean;
  checks: PhoneCheck[];
  addresses: PhoneAddress[];
}> {
  return phoneJson("/diagnostics");
}

export async function setPhoneAddress(ip: string): Promise<PhoneSetup> {
  return phoneJson("/address", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ip }),
  });
}

export async function getPhoneSetup(): Promise<PhoneSetup> {
  return phoneJson("/setup");
}

export async function newPhoneCredentials(username?: string): Promise<PhoneSetup> {
  return phoneJson("/credentials/new", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: username ?? "" }),
  });
}

export async function restartPhone(): Promise<PhoneStatus> {
  return phoneJson("/start", { method: "POST" });
}

export async function getPhoneCalls(includeDone = false): Promise<PhoneCall[]> {
  const data = await phoneJson(`/calls?include_done=${includeDone}`);
  return data.calls ?? [];
}

export async function schedulePhoneCall(values: {
  when: string;
  message?: string;
  reason?: string;
  recurrence?: string;
  duration?: number;
}): Promise<PhoneCall> {
  return phoneJson("/calls", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
}

export async function updatePhoneCall(
  id: string,
  values: { when?: string; message?: string; reason?: string; recurrence?: string }
): Promise<PhoneCall> {
  return phoneJson(`/calls/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
}

export async function deletePhoneCall(id: string): Promise<void> {
  await phoneJson(`/calls/${id}`, { method: "DELETE" });
}

export async function testPhoneCall(): Promise<PhoneLogEntry> {
  return phoneJson("/test", { method: "POST" });
}

export async function hangupPhoneCall(): Promise<void> {
  await phoneJson("/hangup", { method: "POST" });
}

export async function getPhoneHistory(limit = 25): Promise<PhoneLogEntry[]> {
  const data = await phoneJson(`/history?limit=${limit}`);
  return data.calls ?? [];
}

export async function clearPhoneHistory(): Promise<void> {
  await phoneJson("/history", { method: "DELETE" });
}

export interface StudioProvider {
  id: string;
  label: string;
  auth: "api_key" | "lokal" | "frei";
  docs: string;
  hinweis: string;
  bild_modelle: string[];
  video_modelle: string[];
  video: boolean;
  bearbeiten: boolean;
  geerbt: boolean;
  basis: string;
  verbunden: boolean;
  modell_bild: string;
  modell_video: string;
}

export interface StudioWork {
  id: string;
  datei: string;
  art: "bild" | "video";
  prompt: string;
  anbieter: string;
  anbieter_label: string;
  modell: string;
  mime: string;
  groesse_bytes: number;
  dauer_s: number;
  erstellt: number;
}

export interface StudioConfig {
  anbieter: string;
  bereit: boolean;
  groesse: string;
  groessen: string[];
  liste: StudioProvider[];
  galerie: StudioWork[];
}

export function studioFileUrl(work: StudioWork): string {
  return withToken(`${BASE}/studio/file/${encodeURIComponent(work.datei)}`);
}

async function studioJson(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}/studio${path}`, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
  return data;
}

export function getStudioConfig(): Promise<StudioConfig> {
  return studioJson("/config");
}

export function connectStudio(body: {
  provider: string;
  api_key?: string;
  base_url?: string;
  model?: string;
  video_model?: string;
  size?: string;
}): Promise<StudioConfig> {
  return studioJson("/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function disconnectStudio(provider: string): Promise<StudioConfig> {
  return studioJson(`/connect/${encodeURIComponent(provider)}`, {
    method: "DELETE",
  });
}

export function generateStudioWork(body: {
  prompt: string;
  kind: "bild" | "video";
  provider?: string;
  model?: string;
  size?: string;
  negative?: string;
  image?: string;
}): Promise<StudioWork> {
  return studioJson("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getStudioGallery(): Promise<StudioWork[]> {
  const data = await studioJson("/gallery");
  return data.galerie ?? [];
}

export function saveStudioWork(
  id: string,
  folder = ""
): Promise<{ gespeichert: string; name: string }> {
  const suffix = folder ? `?folder=${encodeURIComponent(folder)}` : "";
  return studioJson(`/save/${encodeURIComponent(id)}${suffix}`, { method: "POST" });
}

export async function deleteStudioWork(id: string): Promise<void> {
  await studioJson(`/gallery/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export interface DienstStatus {
  dienst: string;
  ok?: number;
  fehler?: number;
  zuletzt_ok?: string;
  zuletzt_fehler?: string;
  meldung?: string;
}

export interface Diagnose {
  version: string;
  laufzeit: number;
  port: number;
  lan: boolean;
  adresse: string;
  datenverzeichnis: string;
  protokolldatei: string;
  dienste: DienstStatus[];
  fehlerhaft: string[];
  abgewiesen: number;
  meldungen: string[];
}

export interface Kopplung {
  token: string;
  lan: boolean;
  adresse: string;
  port: number;
  url: string;
  oberflaeche: boolean;
  env_datei: string;
}

export async function getDiagnose(): Promise<Diagnose> {
  const res = await fetch(`${BASE}/system/diagnostics`);
  if (!res.ok) throw new Error("Diagnose nicht verfuegbar");
  return res.json();
}

export function protokollUrl(): string {
  return withToken(`${BASE}/system/log`);
}

export async function getKopplung(): Promise<Kopplung> {
  const res = await fetch(`${BASE}/system/pairing`);
  if (!res.ok) throw new Error("Kopplung nicht verfuegbar");
  return res.json();
}

export interface HandyPc {
  id: string;
  name: string;
  version: string;
}

export interface HandyRelayStand {
  verbunden: boolean;
  thema: string;
  verbindet?: boolean;
  seit?: number;
}

export interface HandyKopplung {
  nutzlast: string;
  code: string;
  code_gruppiert: string;
  ablauf: number;
  pc: HandyPc;
  adresse: string;
  heimnetz: boolean;
  broker: { host: string; port: number };
  relay?: HandyRelayStand;
}

export interface HandyStand {
  status: string;
  code?: string;
  code_gruppiert?: string;
  geraet?: { name: string; plattform: string } | null;
  rest?: number;
  relay?: HandyRelayStand;
}

export interface HandyZustand {
  akku?: number;
  laedt?: boolean;
  netz?: string;
  android?: string;
  modell?: string;
  speicher_frei?: number;
}

export type HandyRechte = Record<string, boolean>;

export interface HandyGeraet {
  id: string;
  name: string;
  plattform: string;
  erstellt: number;
  gesehen: number;
  online?: boolean;
  rechte?: HandyRechte;
  stufen?: Record<string, string>;
  namen?: Record<string, string>;
  faehigkeiten?: string[];
  zustand?: HandyZustand;
  zustand_zeit?: number;
}

export async function handyKopplungStarten(): Promise<HandyKopplung> {
  const res = await fetch(`${BASE}/handy/pairing/start`, { method: "POST" });
  if (!res.ok) throw new Error("Kopplung konnte nicht gestartet werden");
  return res.json();
}

export async function handyKopplungStand(): Promise<HandyStand> {
  const res = await fetch(`${BASE}/handy/pairing/state`);
  if (!res.ok) throw new Error("Stand nicht verfuegbar");
  return res.json();
}

export async function handyKopplungAntworten(
  angenommen: boolean
): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/handy/pairing/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ angenommen }),
  });
  if (!res.ok) throw new Error("Antwort fehlgeschlagen");
  return res.json();
}

export async function handyKopplungAbbrechen(): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/handy/pairing/cancel`, { method: "POST" });
  if (!res.ok) throw new Error("Abbruch fehlgeschlagen");
  return res.json();
}

export async function handyGeraete(): Promise<{
  geraete: HandyGeraet[];
  pc: HandyPc;
}> {
  const res = await fetch(`${BASE}/handy/devices`);
  if (!res.ok) throw new Error("Geraete nicht verfuegbar");
  return res.json();
}

export async function handyGeraetLoeschen(
  id: string
): Promise<{ entfernt: boolean }> {
  const res = await fetch(`${BASE}/handy/devices/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Geraet konnte nicht entfernt werden");
  return res.json();
}

export interface Werkzeug {
  name: string;
  beschreibung: string;
  gruppe: string;
  ohne_rueckfrage: boolean;
  stufe?: string;
  recht?: string;
  frei?: boolean;
  connector?: string;
}

export interface WerkzeugGruppe {
  id: string;
  name: string;
  symbol: string;
  anzahl: number;
  werkzeuge: Werkzeug[];
}

export interface SkillKurz {
  name: string;
  title: string;
  chars?: number;
}

export async function werkzeuge(): Promise<{
  gruppen: WerkzeugGruppe[];
  anzahl: number;
  skills: SkillKurz[];
}> {
  const res = await fetch(`${BASE}/tools`);
  if (!res.ok) throw new Error("Werkzeuge nicht verfuegbar");
  return res.json();
}

export async function handyRechtSetzen(
  id: string,
  recht: string,
  wert: boolean
): Promise<{ rechte: HandyRechte }> {
  const res = await fetch(
    `${BASE}/handy/devices/${encodeURIComponent(id)}/rights`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recht, wert }),
    }
  );
  if (!res.ok) throw new Error("Berechtigung nicht gespeichert");
  return res.json();
}

export async function handyGeraetUmbenennen(
  id: string,
  name: string
): Promise<{ geraet: HandyGeraet }> {
  const res = await fetch(
    `${BASE}/handy/devices/${encodeURIComponent(id)}/name`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }
  );
  if (!res.ok) throw new Error("Name nicht gespeichert");
  return res.json();
}

export async function handyGeraetStand(
  id: string
): Promise<Record<string, unknown>> {
  const res = await fetch(
    `${BASE}/handy/devices/${encodeURIComponent(id)}/state`
  );
  if (!res.ok) throw new Error("Stand nicht verfuegbar");
  return res.json();
}

export async function handyDateiSenden(
  id: string,
  pfad: string
): Promise<Record<string, unknown>> {
  const res = await fetch(
    `${BASE}/handy/devices/${encodeURIComponent(id)}/file`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pfad }),
    }
  );
  if (!res.ok) {
    const grund = await res.json().catch(() => null);
    throw new Error(grund?.detail ?? "Datei konnte nicht gesendet werden");
  }
  return res.json();
}

export function handyQrUrl(text: string): string {
  return withToken(`${BASE}/handy/pairing/qr?text=${encodeURIComponent(text)}`);
}

export async function neuesToken(): Promise<Kopplung> {
  const res = await fetch(`${BASE}/system/pairing/reset`, { method: "POST" });
  if (!res.ok) throw new Error("Token konnte nicht erneuert werden");
  return res.json();
}

export interface JonProject {
  id: string;
  name: string;
  root: string;
  technik: string;
  notizen: string[];
  regeln: string[];
  geraet: string;
  erstellt: string;
  zuletzt: string;
}

export interface ProjectLanguage {
  name: string;
  dateien: number;
}

export interface ProjectGit {
  repo: boolean;
  branch?: string;
  geaendert?: number;
  dateien?: string[];
  letzter_commit?: string;
  remote?: string;
  hinweis?: string;
}

export interface ProjectAnalysis {
  root: string;
  name: string;
  dateien: number;
  ordner: number;
  textdateien: number;
  groesse_bytes: number;
  sprachen: ProjectLanguage[];
  projekttyp: string[];
  frameworks: string[];
  abhaengigkeiten: string[];
  skripte: Record<string, string>;
  schluesseldateien: string[];
  oberste_ebene: string[];
  git: ProjectGit;
  stand: string;
}

export interface ProjectSnapshot {
  root: string;
  dateien: Record<string, number[]>;
  stand: string;
}

export interface ProjectChanges {
  root: string;
  erstellt: string[];
  geloescht: string[];
  geaendert: string[];
  anzahl: { erstellt: number; geloescht: number; geaendert: number };
  snapshot: ProjectSnapshot;
}

export interface ProjectDiff {
  repo: boolean;
  stat?: string;
  diff?: string;
  gekuerzt?: boolean;
  fehler?: string;
  hinweis?: string;
}

export async function listProjects(): Promise<JonProject[]> {
  const res = await fetch(`${BASE}/projects`);
  if (!res.ok) return [];
  return res.json();
}

export async function addProject(
  root: string,
  name = "",
  note = ""
): Promise<JonProject> {
  const res = await fetch(`${BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root, name, note }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteProject(id: string): Promise<boolean> {
  const res = await fetch(`${BASE}/projects/${id}`, { method: "DELETE" });
  if (!res.ok) return false;
  return (await res.json()).geloescht ?? false;
}

export async function noteProject(id: string, note: string): Promise<JonProject> {
  const res = await fetch(`${BASE}/projects/${id}/note`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function analyzeProject(root: string): Promise<ProjectAnalysis> {
  const res = await fetch(
    `${BASE}/projects/analyze?root=${encodeURIComponent(root)}`
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function projectGit(
  root: string,
  mode: "status" | "diff" = "status"
): Promise<ProjectDiff & ProjectGit> {
  const res = await fetch(
    `${BASE}/projects/git?root=${encodeURIComponent(root)}&mode=${mode}`
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function projectSnapshot(root: string): Promise<ProjectSnapshot> {
  const res = await fetch(`${BASE}/projects/snapshot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function projectChanges(
  root: string,
  snapshot: ProjectSnapshot
): Promise<ProjectChanges> {
  const res = await fetch(`${BASE}/projects/changes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root, snapshot }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface InboxAction {
  typ: string;
  label: string;
  payload: Record<string, unknown>;
  freigabe: boolean;
}

export interface InboxAnalysis {
  typ: string;
  titel: string;
  zusammenfassung: string;
  wichtigkeit: string;
  datum: string;
  zeit: string;
  deadline: string;
  personen: string[];
  projekt: string;
  aktionen: InboxAction[];
  stand?: string;
}

export interface InboxItem {
  id: string;
  kategorie: string;
  titel: string;
  untertitel: string;
  text: string;
  zeit: string;
  wichtig: boolean;
  quelle: string;
  gesehen?: boolean;
  mail_id?: string;
  betreff?: string;
  von?: string;
  root?: string;
  analyse: InboxAnalysis | null;
}

export interface InboxFeed {
  kategorien: { id: string; label: string }[];
  zaehler: Record<string, number>;
  eintraege: InboxItem[];
  mail_fehler: string;
  stand: string;
}

export async function getInbox(limit = 12, days = 7): Promise<InboxFeed> {
  const res = await fetch(`${BASE}/inbox?limit=${limit}&days=${days}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function analyzeInboxItem(
  id: string,
  options: { text?: string; betreff?: string; von?: string; provider?: string; model?: string; force?: boolean } = {}
): Promise<InboxAnalysis> {
  const res = await fetch(`${BASE}/inbox/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, ...options }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Analyse fehlgeschlagen");
  }
  return res.json();
}

export async function runInboxAction(
  typ: string,
  payload: Record<string, unknown>
): Promise<{ aktion: string; ergebnis: Record<string, unknown> }> {
  const res = await fetch(`${BASE}/inbox/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ typ, payload, bestaetigt: true, quelle: "inbox" }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Aktion fehlgeschlagen");
  }
  return res.json();
}

export async function markInboxSeen(id: string): Promise<void> {
  await fetch(`${BASE}/inbox/seen`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
}


export type JonUhrArt = "timer" | "stoppuhr" | "wecker";

export interface JonUhr {
  id: string;
  art: JonUhrArt;
  titel: string;
  gestartet: number;
  gemessen: number;
  laeuft: boolean;
  verstrichen: number;
  quelle?: string;
  klingelt?: boolean;
  ton_pc?: boolean;
  dauer?: number;
  rest?: number;
  ziel?: number;
  klingelt_um?: string;
  fertig?: boolean;
}

export interface JonWecker {
  name: string;
  titel: string;
  klingelt: string;
}

export async function zeitStand(): Promise<{ uhren: JonUhr[] }> {
  const res = await fetch(`${BASE}/zeit`);
  if (!res.ok) throw new Error("Die Uhren ließen sich nicht laden.");
  return res.json();
}

export async function zeitNeu(): Promise<{ uhren: JonUhr[] }> {
  const res = await fetch(`${BASE}/zeit/neu`);
  if (!res.ok) return { uhren: [] };
  return res.json();
}

export async function zeitStarten(
  art: JonUhrArt,
  sekunden: number,
  titel = "",
  uhrzeit = ""
): Promise<JonUhr> {
  const res = await fetch(`${BASE}/zeit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ art, sekunden, titel, uhrzeit }),
  });
  if (!res.ok) throw new Error("Die Uhr ließ sich nicht starten.");
  return res.json();
}

export async function zeitPause(id: string): Promise<JonUhr> {
  const res = await fetch(`${BASE}/zeit/${id}/pause`, { method: "POST" });
  if (!res.ok) throw new Error("Pause ging nicht.");
  return res.json();
}

export async function zeitWeiter(id: string): Promise<JonUhr> {
  const res = await fetch(`${BASE}/zeit/${id}/weiter`, { method: "POST" });
  if (!res.ok) throw new Error("Weiterlaufen ging nicht.");
  return res.json();
}

export async function zeitAnpassen(id: string, sekunden: number): Promise<JonUhr> {
  const res = await fetch(`${BASE}/zeit/${id}/anpassen`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sekunden }),
  });
  if (!res.ok) throw new Error("Ändern ging nicht.");
  return res.json();
}

export async function zeitNeustart(id: string): Promise<JonUhr> {
  const res = await fetch(`${BASE}/zeit/${id}/neustart`, { method: "POST" });
  if (!res.ok) throw new Error("Neustart ging nicht.");
  return res.json();
}

export async function zeitRuhe(id: string): Promise<{ uhren: JonUhr[] }> {
  const res = await fetch(`${BASE}/zeit/${id}/ruhe`, { method: "POST" });
  if (!res.ok) throw new Error("Ton aus ging nicht.");
  return res.json();
}

export async function zeitStoppen(id: string): Promise<unknown> {
  const res = await fetch(`${BASE}/zeit/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Stoppen ging nicht.");
  return res.json();
}

export interface TerminalStand {
  installiert: boolean;
  befehl: string;
  ordner: string;
  im_pfad: boolean;
  gefunden: string;
  gebuendelt: boolean;
  system: string;
  neustart_noetig: boolean;
  hinweise?: string[];
}

export async function terminalStand(): Promise<TerminalStand> {
  const res = await fetch(`${BASE}/system/terminal`);
  if (!res.ok) throw new Error("Der Terminal-Status ließ sich nicht laden.");
  return res.json();
}

export async function terminalEinrichten(): Promise<TerminalStand> {
  const res = await fetch(`${BASE}/system/terminal`, { method: "POST" });
  if (!res.ok) throw new Error("Der Befehl ließ sich nicht einrichten.");
  return res.json();
}

export async function terminalEntfernen(): Promise<TerminalStand> {
  const res = await fetch(`${BASE}/system/terminal`, { method: "DELETE" });
  if (!res.ok) throw new Error("Der Befehl ließ sich nicht entfernen.");
  return res.json();
}

export interface MediaEintrag {
  id: string;
  name: string;
  art: "video" | "musik" | "datei";
  groesse: number;
  dauer: number;
  quelle: string;
  kanal: string;
  erstellt: number;
  bild: boolean;
  datei: string;
}

export async function mediathekListe(): Promise<{
  eintraege: MediaEintrag[];
  ordner: string;
  groesse: number;
}> {
  const res = await fetch(`${BASE}/mediathek`);
  if (!res.ok) throw new Error("Die Mediathek ließ sich nicht laden.");
  return res.json();
}

export function mediathekDateiUrl(id: string): string {
  return withToken(`${BASE}/mediathek/datei/${id}`);
}

export function mediathekBildUrl(id: string): string {
  return withToken(`${BASE}/mediathek/bild/${id}`);
}

export async function mediathekLoeschen(id: string): Promise<void> {
  const res = await fetch(`${BASE}/mediathek/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Löschen ging nicht.");
}

export interface VerbundGeraet {
  id: string;
  name: string;
  plattform: string;
  version: string;
  adressen: string[];
  erstellt: number;
  gesehen: number;
  weg: string;
  erreichbar?: boolean;
  grund?: string;
}

export async function verbundGeraete(): Promise<VerbundGeraet[]> {
  const res = await fetch(`${BASE}/verbund`);
  if (!res.ok) throw new Error("Die Geräteliste ließ sich nicht laden.");
  const daten = await res.json();
  return Array.isArray(daten.geraete) ? daten.geraete : [];
}

export async function verbundKoppeln(code: string): Promise<VerbundGeraet> {
  const res = await fetch(`${BASE}/verbund/koppeln`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  const daten = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(daten.detail || "Kopplung fehlgeschlagen.");
  return daten;
}

export async function verbundPruefen(id: string): Promise<VerbundGeraet> {
  const res = await fetch(`${BASE}/verbund/${id}/pruefen`);
  if (!res.ok) throw new Error("Das Gerät antwortet nicht.");
  return res.json();
}

export async function verbundEntfernen(id: string): Promise<void> {
  await fetch(`${BASE}/verbund/${id}`, { method: "DELETE" });
}

export async function verbundFragen(id: string, frage: string): Promise<string> {
  const res = await fetch(`${BASE}/verbund/${id}/fragen`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frage }),
  });
  const daten = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(daten.detail || "Keine Antwort.");
  return String(daten.antwort ?? "");
}

export function verbundBildUrl(id: string, stempel: number): string {
  return withToken(`${BASE}/verbund/${id}/bild?t=${stempel}`);
}

export interface LiveStand {
  laeuft: boolean;
  welcher: string;
  takt: number;
  zuschauer: number;
  telegram: string[];
  monitore: { id: string; name: string; breite: number; hoehe: number }[];
}

export async function liveStand(): Promise<LiveStand> {
  const res = await fetch(`${BASE}/live`);
  if (!res.ok) throw new Error("Der Stand ließ sich nicht laden.");
  return res.json();
}

export async function liveStarten(
  welcher = "alle",
  takt = 2
): Promise<LiveStand> {
  const res = await fetch(`${BASE}/live/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ welcher, takt }),
  });
  const daten = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(daten.detail || "Übertragung ging nicht.");
  return daten;
}

export async function liveStoppen(): Promise<LiveStand> {
  const res = await fetch(`${BASE}/live/stop`, { method: "POST" });
  return res.json();
}

export function liveSeiteUrl(welcher = "alle"): string {
  return withToken(
    BASE.replace(/\/api$/, "") + `/live?welcher=${encodeURIComponent(welcher)}`
  );
}

export interface TelegramStand {
  token_gesetzt: boolean;
  bot: string;
  bot_name: string;
  gruppen_erlaubt: boolean | null;
  liest_alles: boolean | null;
  webhook: string;
  webhook_fehler: string;
  offene_updates: number;
  letzte_abfrage: number;
  letzter_fehler: string;
  fehler_zeit: number;
  updates: number;
  webhook_entfernt: number;
  gruppen: {
    chat_id: string;
    titel: string;
    gesehen: number;
    erwaehnt: number;
    geantwortet: number;
    zuletzt: number;
  }[];
  hinweise: string[];
}

export async function getTelegramStand(): Promise<TelegramStand> {
  const res = await fetch(`${BASE}/system/telegram`);
  if (!res.ok) throw new Error("Telegram-Status nicht verfügbar");
  return res.json();
}
