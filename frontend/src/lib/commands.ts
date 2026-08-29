export interface SlashCommand {
  cmd: string;
  aliases: string[];
  icon: string;
  title: string;
  arg?: string;
  gruppe: string;
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    cmd: "/maps",
    aliases: ["/karte", "/navigation"],
    icon: "🗺️",
    title: "Jon Maps öffnen — mit Frage dahinter nutzt Jon direkt die Karte",
    arg: "Frage zur Karte",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/bild",
    aliases: ["/foto", "/video", "/studio"],
    icon: "🎨",
    title: "Video / Foto — Bilder und Videos erstellen",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/lerne",
    aliases: ["/deep", "/deeplearning", "/research", "/forschung"],
    icon: "🧠",
    title: "Deep Learning — Jon recherchiert ein Thema in die Tiefe",
    arg: "Thema",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/suche",
    aliases: ["/search", "/find"],
    icon: "🔎",
    title: "Alles durchsuchen (Strg+K)",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/kalender",
    aliases: ["/calendar"],
    icon: "📅",
    title: "Deine nächsten 7 Tage",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/notizen",
    aliases: ["/notes"],
    icon: "📌",
    title: "Haftnotizen",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/lernen",
    aliases: ["/quiz"],
    icon: "🎴",
    title: "Lern-Karteikarten",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/tagebuch",
    aliases: ["/journal"],
    icon: "📔",
    title: "Sprach-Tagebuch",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/telefon",
    aliases: ["/anruf", "/anrufe", "/phone"],
    icon: "📞",
    title: "Telefonanrufe",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/tresor",
    aliases: ["/vault", "/passwort"],
    icon: "🔒",
    title: "Passwort-Tresor",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/human",
    aliases: ["/humanize"],
    icon: "✍️",
    title: "Humanisierer — Text natürlicher schreiben",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/meeting",
    aliases: ["/mitschrift"],
    icon: "📝",
    title: "Mitschrift starten oder beenden",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/briefing",
    aliases: [],
    icon: "☀️",
    title: "Dein Tages-Briefing",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/team",
    aliases: [],
    icon: "🧑‍🤝‍🧑",
    title: "KI-Team berät über deine Frage",
    arg: "Frage oder Thema",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/simulate",
    aliases: ["/simuliere"],
    icon: "🔮",
    title: "Was wäre wenn — Jon spielt es durch",
    arg: "Was wäre wenn …",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/dream",
    aliases: ["/traum"],
    icon: "🌙",
    title: "Aufgabe für den Hintergrund notieren",
    arg: "Aufgabe",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/dreams",
    aliases: ["/traeume"],
    icon: "🌙",
    title: "Dream-Aufgaben jetzt abarbeiten",
    gruppe: "Arbeiten",
  },
  {
    cmd: "/erklaer",
    aliases: ["/erklaere", "/screen"],
    icon: "🔍",
    title: "Bildschirm erklären (Strg+Alt+E)",
    gruppe: "PC",
  },
  {
    cmd: "/check",
    aliases: ["/pc"],
    icon: "🩺",
    title: "PC-Check — Jon schaut sich dein System an",
    gruppe: "PC",
  },
  {
    cmd: "/aufraeumen",
    aliases: ["/cleanup"],
    icon: "🧹",
    title: "Ordner aufräumen",
    gruppe: "PC",
  },
  {
    cmd: "/download",
    aliases: ["/dl"],
    icon: "⬇️",
    title: "Downloader für Videos und Musik",
    gruppe: "PC",
  },
  {
    cmd: "/privat",
    aliases: ["/private", "/inkognito"],
    icon: "🕶️",
    title: "Privater Browser",
    gruppe: "PC",
  },
  {
    cmd: "/clipboard",
    aliases: ["/zwischenablage"],
    icon: "📋",
    title: "Clipboard-Historie",
    gruppe: "PC",
  },
  {
    cmd: "/kochen",
    aliases: ["/rezept"],
    icon: "🍳",
    title: "Kochassistent",
    gruppe: "PC",
  },
  {
    cmd: "/webcam",
    aliases: ["/kamera"],
    icon: "📷",
    title: "Jon schaut durch die Webcam",
    arg: "Frage",
    gruppe: "PC",
  },
  {
    cmd: "/tasks",
    aliases: ["/automationen"],
    icon: "🤖",
    title: "Deine Automationen",
    gruppe: "PC",
  },
  {
    cmd: "/fokus",
    aliases: ["/focus", "/stats"],
    icon: "📊",
    title: "App-Zeiten der letzten 7 Tage",
    gruppe: "PC",
  },
  {
    cmd: "/woche",
    aliases: ["/weekly", "/week"],
    icon: "🗓️",
    title: "Wochenrückblick",
    gruppe: "PC",
  },
  {
    cmd: "/log",
    aliases: [],
    icon: "📜",
    title: "Aktionsprotokoll",
    arg: "Quelle oder Tag",
    gruppe: "PC",
  },
  {
    cmd: "/papierkorb",
    aliases: ["/trash"],
    icon: "🗑️",
    title: "Papierkorb ansehen",
    gruppe: "PC",
  },
  {
    cmd: "/restore",
    aliases: ["/wiederherstellen"],
    icon: "↩️",
    title: "Datei aus dem Papierkorb zurückholen",
    arg: "Nummer",
    gruppe: "PC",
  },
  {
    cmd: "/undo",
    aliases: [],
    icon: "↩️",
    title: "Letzte Dateiaktion rückgängig machen",
    gruppe: "PC",
  },
  {
    cmd: "/snapshot",
    aliases: [],
    icon: "⏳",
    title: "Snapshot anlegen",
    arg: "Name",
    gruppe: "PC",
  },
  {
    cmd: "/snapshots",
    aliases: ["/zeitreise"],
    icon: "⏳",
    title: "Alle Snapshots zeigen",
    gruppe: "PC",
  },
  {
    cmd: "/spiele",
    aliases: ["/games"],
    icon: "🕹️",
    title: "Alle Spiele",
    gruppe: "Spiel & Spass",
  },
  {
    cmd: "/spiel",
    aliases: ["/blockwelt", "/game"],
    icon: "🧱",
    title: "BLOCKWELT starten",
    gruppe: "Spiel & Spass",
  },
  {
    cmd: "/echo",
    aliases: [],
    icon: "🌀",
    title: "ECHO starten",
    gruppe: "Spiel & Spass",
  },
  {
    cmd: "/harmonie",
    aliases: [],
    icon: "🎵",
    title: "HARMONIE starten",
    gruppe: "Spiel & Spass",
  },
  {
    cmd: "/aetheria",
    aliases: [],
    icon: "✨",
    title: "AETHERIA starten",
    gruppe: "Spiel & Spass",
  },
  {
    cmd: "/show",
    aliases: ["/abendshow"],
    icon: "🎙️",
    title: "Abend-Show",
    gruppe: "Spiel & Spass",
  },
  {
    cmd: "/konten",
    aliases: ["/accounts", "/login"],
    icon: "👤",
    title: "Konten & Anmeldungen",
    gruppe: "Jon",
  },
  {
    cmd: "/usage",
    aliases: ["/nutzung"],
    icon: "📈",
    title: "Verbrauch und Kosten",
    gruppe: "Jon",
  },
  {
    cmd: "/skills",
    aliases: [],
    icon: "📚",
    title: "Jons Skills",
    gruppe: "Jon",
  },
  {
    cmd: "/export",
    aliases: [],
    icon: "💾",
    title: "Diese Unterhaltung als Datei sichern",
    gruppe: "Jon",
  },
  {
    cmd: "/update",
    aliases: [],
    icon: "🔄",
    title: "Jon aktualisieren",
    gruppe: "Jon",
  },
];

export function matchCommands(input: string): SlashCommand[] {
  const query = input.trim().toLowerCase();
  if (!query.startsWith("/")) return [];
  if (query === "/") return SLASH_COMMANDS;
  const starts = SLASH_COMMANDS.filter(
    (c) =>
      c.cmd.startsWith(query) || c.aliases.some((a) => a.startsWith(query))
  );
  if (starts.length) return starts;
  const word = query.slice(1);
  return SLASH_COMMANDS.filter(
    (c) =>
      c.cmd.includes(word) ||
      c.aliases.some((a) => a.includes(word)) ||
      c.title.toLowerCase().includes(word)
  );
}
