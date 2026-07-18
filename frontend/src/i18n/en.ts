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
  cal_all_day: "all day",
  cal_source_jon: "Jon",
  cal_source_automation: "Automation",
  cal_source_reminder: "Reminder",
  cal_source_ics: "Google/Outlook",

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
  search_history: "Search history …",
  drop_file: "Drop file here …",
  new_chat: "New chat",
  no_conversations: "No conversations yet",
  empty_title: "How can I help?",
  empty_hint: "Ask me something, give me a task, or say „Jon“.",
  header_mini_jon: "Mini Jon",
  header_calendar: "Calendar",
  header_tools: "Tools",
  live_screen_on: "Live screen on — Jon is watching",
  live_screen_off: "Live screen off",
  voice_on: "Listening on — say „Jon“",
  voice_off: "Listening off",
  tools_work: "Work",
  tools_pc: "PC & Media",
  tools_fun: "Fun & more",
};
