import { Translations } from "./de";

export const en: Translations = {
  // Common
  cancel: "Cancel",
  save: "Save",
  delete: "Delete",
  close: "Close",
  edit: "Edit",
  new_entry: "+ Entry",
  today: "Today",
  manual: "Manual",
  
  // Update
  update_available: "Version {version} is here",
  update_old: "You are using an older version of Jon.",
  update_start: "Auto-Update",
  update_progress: "⚙️ Starting update...\n",
  
  // Calendar
  cal_title: "📅 Jon's Calendar",
  cal_month: "Month",
  cal_week: "Week",
  cal_no_entries: "No entries. Double click a day or '+ Entry' — or just tell Jon: 'Add dentist appointment Friday 3pm.'",
  cal_edit_entry: "Edit Entry",
  cal_new_entry: "New Entry",
  cal_title_ph: "Title",
  cal_type_termin: "Appointment",
  cal_type_task: "Task",
  cal_type_reminder: "Reminder",
  cal_duration_ph: "Duration (min)",
  cal_note_ph: "Note (optional)",
  cal_done: "Done",
  
  // Trash
  trash_title: "🗑️ Loading Trash …",
  trash_empty: "Trash is empty. Deleted, overwritten, and moved files land here and are kept for 30 days.",
  trash_info: "**🗑️ Trash** (emptied after 30 days):\n\n{items}\n\nRestore: `/restore <Number>` — or `/undo` for the last action.",
  
  // Pairing
  pair_request: "'{name}' wants to pair with Jon",
  pair_code_hint: "Enter this code on the device:",
  pair_deny: "Deny",
  
  // Log
  log_load: "📜 Loading Action Log …",
  log_empty: "No actions logged yet.",
  
  // Settings
  settings_language: "Language",
  settings_lang_de: "Deutsch",
  settings_lang_en: "English",
  
  // Chat
  chat_placeholder: "Ask Jon...",
};
