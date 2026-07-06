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
