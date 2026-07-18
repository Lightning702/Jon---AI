export const de = {
  // Common
  cancel: "Abbrechen",
  save: "Speichern",
  delete: "Löschen",
  close: "Schließen",
  edit: "Bearbeiten",
  new_entry: "+ Eintrag",
  today: "Heute",
  manual: "Manuell",
  
  // Update
  update_available: "Version {version} ist da",
  update_old: "Du nutzt eine ältere Version von Jon.",
  update_start: "Auto-Update",
  update_progress: "⚙️ Starte Update...\n",
  
  // Calendar
  cal_title: "📅 Jons Kalender",
  cal_month: "Monat",
  cal_week: "Woche",
  cal_no_entries: "Keine Einträge. Doppelklick auf einen Tag oder „+ Eintrag“ — oder sag Jon einfach: „Trag Freitag 15 Uhr Zahnarzt ein.“",
  cal_edit_entry: "Eintrag bearbeiten",
  cal_new_entry: "Neuer Eintrag",
  cal_title_ph: "Titel",
  cal_type_termin: "Termin",
  cal_type_task: "Task",
  cal_type_reminder: "Erinnerung",
  cal_duration_ph: "Dauer (Min)",
  cal_note_ph: "Notiz (optional)",
  cal_done: "Erledigt",
  
  // Trash
  trash_title: "🗑️ Lade Papierkorb …",
  trash_empty: "Der Papierkorb ist leer. Gelöschte, überschriebene und verschobene Dateien landen hier und bleiben 30 Tage erhalten.",
  trash_info: "**🗑️ Papierkorb** (wird nach 30 Tagen geleert):\n\n{items}\n\nWiederherstellen: `/restore <Nummer>` — oder `/undo` für die letzte Aktion.",
  
  // Pairing
  pair_request: "„{name}“ möchte sich mit Jon koppeln",
  pair_code_hint: "Gib diesen Code auf dem Gerät ein:",
  pair_deny: "Ablehnen",
  
  // Log
  log_load: "📜 Lade Aktionsprotokoll …",
  log_empty: "Noch keine Aktionen protokolliert.",
  
  // Settings
  settings_language: "Sprache",
  settings_lang_de: "Deutsch",
  settings_lang_en: "English",
  
  // Chat
  chat_placeholder: "Frag Jon...",
};

export type Translations = typeof de;
