export const TOOL_LABELS: Record<string, string> = {
  run_powershell: "PowerShell",
  run_cmd: "CMD",
  open_url: "URL öffnen",
  start_program: "Programm starten",
  kill_program: "Programm beenden",
  open_explorer: "Explorer",
  list_dir: "Ordner lesen",
  read_file: "Datei lesen",
  write_file: "Datei schreiben",
  move_path: "Verschieben",
  delete_path: "Löschen",
  open_in_vscode: "VS Code",
  get_screen_info: "Bildschirm-Info",
  mouse_move: "Maus bewegen",
  mouse_click: "Mausklick",
  mouse_scroll: "Scrollen",
  keyboard_type: "Tippen",
  keyboard_press: "Taste drücken",
  keyboard_hotkey: "Tastenkombination",
  list_windows: "Fenster auflisten",
  focus_window: "Fenster fokussieren",
  wait: "Warten",
  remember: "Merken",
  recall: "Erinnern",
  forget: "Vergessen",
  learn_document: "Dokument lernen",
  ask_knowledge: "Wissensbasis",
  list_documents: "Dokumente",
  forget_document: "Dokument vergessen",
  clipboard_history: "Clipboard-Verlauf",
  add_task: "Automation planen",
  list_tasks: "Automationen",
  delete_task: "Automation löschen",
  time_capsule: "Zeitkapsel",
  list_capsules: "Zeitkapseln",
  webcam_look: "Webcam",
  check_mail: "Mails prüfen",
  read_mail: "Mail lesen",
  send_mail: "Mail senden",
  get_calendar: "Kalender",
  media_control: "Medien",
  add_watcher: "Ordner überwachen",
  list_watchers: "Wächter",
  delete_watcher: "Wächter löschen",
  smarthome_devices: "Smart-Home-Geräte",
  smarthome_control: "Smart Home",
  scan_network: "Netzwerk scannen",
  wake_device: "Gerät wecken",
  list_printers: "Drucker",
  print_file: "Drucken",
  spotify_play: "Spotify abspielen",
  spotify_search: "Spotify-Suche",
  spotify_now_playing: "Läuft gerade",
  amazon_play: "Amazon Music",
  amazon_now_playing: "Läuft gerade",
};

export function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? name;
}

export function toolDetail(
  name: string,
  args?: Record<string, unknown>
): string {
  if (!args || Object.keys(args).length === 0) return "";
  if (typeof args.command === "string") return args.command;
  if (typeof args.url === "string") return args.url;
  if (typeof args.path === "string") return String(args.path);
  if (typeof args.text === "string") return String(args.text);
  if (typeof args.content === "string") return String(args.content);
  if (Array.isArray(args.keys)) return args.keys.join(" + ");
  if (typeof args.title === "string") return String(args.title);
  if (typeof args.query === "string") return String(args.query);
  if (name === "move_path")
    return `${args.source ?? ""} → ${args.destination ?? ""}`;
  try {
    return JSON.stringify(args, null, 2);
  } catch {
    return "";
  }
}
