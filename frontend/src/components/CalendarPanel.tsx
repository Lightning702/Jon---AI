import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  CalendarEvent,
  addCalendarEntry,
  deleteCalendarEntry,
  getCalendar,
  updateCalendarEntry,
} from "../lib/api";
import { useT } from "../hooks/useT";

const WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const MONTHS = [
  "Januar",
  "Februar",
  "März",
  "April",
  "Mai",
  "Juni",
  "Juli",
  "August",
  "September",
  "Oktober",
  "November",
  "Dezember",
];

const SOURCE_STYLE: Record<string, string> = {
  jon: "border-gold/50 bg-gold/15 text-gold",
  automation: "border-violet-400/40 bg-violet-400/10 text-violet-200",
  erinnerung: "border-amber-400/40 bg-amber-400/10 text-amber-200",
  ics: "border-sky-400/40 bg-sky-400/10 text-sky-200",
};

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function mondayOf(d: Date): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() - ((copy.getDay() + 6) % 7));
  return copy;
}

interface FormState {
  id: string;
  title: string;
  date: string;
  time: string;
  duration: string;
  note: string;
  kind: string;
  done: boolean;
}

const EMPTY_FORM: FormState = {
  id: "",
  title: "",
  date: "",
  time: "",
  duration: "",
  note: "",
  kind: "termin",
  done: false,
};

export default function CalendarPanel({ onClose }: { onClose: () => void }) {
  const { t, lang } = useT();
  const SOURCE_LABEL: Record<string, string> = {
    jon: t("cal_source_jon"),
    automation: t("cal_source_automation"),
    erinnerung: t("cal_source_reminder"),
    ics: t("cal_source_ics"),
  };
  const [view, setView] = useState<"monat" | "woche">("monat");
  const [cursor, setCursor] = useState(() => new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selectedDay, setSelectedDay] = useState(() => iso(new Date()));
  const [form, setForm] = useState<FormState | null>(null);
  const [hint, setHint] = useState("");
  const today = iso(new Date());

  const range = useMemo(() => {
    if (view === "woche") {
      return { start: iso(mondayOf(cursor)), days: 7 };
    }
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    return { start: iso(mondayOf(first)), days: 42 };
  }, [view, cursor]);

  const load = useCallback(async () => {
    setEvents(await getCalendar(range.start, range.days));
  }, [range]);

  useEffect(() => {
    void load();
  }, [load]);

  const byDay = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {};
    for (const e of events) (map[e.datum] ??= []).push(e);
    return map;
  }, [events]);

  const days = useMemo(() => {
    const list: Date[] = [];
    const start = new Date(range.start);
    for (let i = 0; i < range.days; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      list.push(d);
    }
    return list;
  }, [range]);

  const shift = (dir: number) => {
    const next = new Date(cursor);
    if (view === "monat") next.setMonth(next.getMonth() + dir);
    else next.setDate(next.getDate() + dir * 7);
    setCursor(next);
  };

  const openNew = (day: string) => {
    setForm({ ...EMPTY_FORM, date: day });
    setHint("");
  };

  const openEdit = (e: CalendarEvent) => {
    if (e.quelle !== "jon") return;
    setForm({
      id: e.id,
      title: e.titel,
      date: e.datum,
      time: e.zeit,
      duration: e.dauer_minuten ? String(e.dauer_minuten) : "",
      note: e.notiz ?? "",
      kind: e.typ,
      done: e.erledigt,
    });
    setHint("");
  };

  const save = async () => {
    if (!form || !form.title.trim()) return;
    const payload = {
      title: form.title.trim(),
      date: form.date,
      time: form.time.trim(),
      duration_minutes: parseInt(form.duration, 10) || 0,
      note: form.note.trim(),
      kind: form.kind,
    };
    const result = form.id
      ? await updateCalendarEntry(form.id, { ...payload, done: form.done })
      : await addCalendarEntry(payload);
    if (result.detail) {
      setHint(String(result.detail));
      return;
    }
    if (result.konflikte?.length) {
      const k = result.konflikte as { titel: string; zeit: string }[];
      setHint(
        `⚠️ Überschneidet sich mit: ${k.map((x) => `${x.titel} (${x.zeit})`).join(", ")}`
      );
    } else {
      setHint("");
    }
    setForm(null);
    await load();
  };

  const remove = async () => {
    if (!form?.id) return;
    await deleteCalendarEntry(form.id);
    setForm(null);
    await load();
  };

  const toggleDone = async (e: CalendarEvent) => {
    if (e.quelle !== "jon") return;
    await updateCalendarEntry(e.id, { done: !e.erledigt });
    await load();
  };

  const dayList = byDay[selectedDay] ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.97, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        className="glass rounded-2xl border border-white/15 w-[96%] max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
      >
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-[15px] font-semibold gold-text">
              {t("cal_title")}
            </span>
            <div className="flex items-center gap-1 text-[12px]">
              <button
                onClick={() => shift(-1)}
                className="w-6 h-6 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:bg-white/10"
              >
                ‹
              </button>
              <span className="min-w-[130px] text-center text-white/80">
                {view === "monat"
                  ? `${MONTHS[cursor.getMonth()]} ${cursor.getFullYear()}`
                  : `${t("cal_week")} — ${new Date(range.start).toLocaleDateString(lang === "en" ? "en-US" : "de-DE")}`}
              </span>
              <button
                onClick={() => shift(1)}
                className="w-6 h-6 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:bg-white/10"
              >
                ›
              </button>
              <button
                onClick={() => {
                  setCursor(new Date());
                  setSelectedDay(today);
                }}
                className="ml-1 px-2 h-6 rounded-lg border border-gold/30 bg-gold/10 text-gold/90 text-[11px]"
              >
                {t("today")}
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-white/10 overflow-hidden text-[11px]">
              {(["monat", "woche"] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`px-2.5 py-1 ${
                    view === v
                      ? "bg-gold/15 text-gold"
                      : "bg-white/5 text-white/50 hover:bg-white/10"
                  }`}
                >
                  {v === "monat" ? t("cal_month") : t("cal_week")}
                </button>
              ))}
            </div>
            <button
              onClick={() => openNew(selectedDay)}
              className="px-2.5 h-7 rounded-lg border border-gold/40 bg-gold/15 text-gold text-[12px]"
            >
              + Eintrag
            </button>
            <button
              onClick={onClose}
              className="text-white/40 hover:text-white/80 text-xl leading-none pl-1"
            >
              ×
            </button>
          </div>
        </div>

        <div className="flex-1 min-h-0 flex">
          <div className="flex-1 min-w-0 overflow-y-auto p-4">
            <div className="grid grid-cols-7 gap-1 mb-1">
              {WEEKDAYS.map((w) => (
                <div
                  key={w}
                  className="text-center text-[10px] uppercase tracking-wider text-white/35"
                >
                  {w}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {days.map((d) => {
                const key = iso(d);
                const inMonth =
                  view === "woche" || d.getMonth() === cursor.getMonth();
                const list = byDay[key] ?? [];
                const isToday = key === today;
                const isSelected = key === selectedDay;
                return (
                  <button
                    key={key}
                    onClick={() => setSelectedDay(key)}
                    onDoubleClick={() => openNew(key)}
                    className={`text-left rounded-xl border p-1.5 transition-colors ${
                      view === "woche" ? "min-h-[180px]" : "min-h-[74px]"
                    } ${
                      isToday
                        ? "border-gold/60 bg-gold/10"
                        : isSelected
                          ? "border-white/30 bg-white/10"
                          : "border-white/8 bg-white/[0.03] hover:bg-white/[0.07]"
                    } ${inMonth ? "" : "opacity-35"}`}
                  >
                    <div
                      className={`text-[11px] mb-1 ${
                        isToday ? "text-gold font-bold" : "text-white/55"
                      }`}
                    >
                      {d.getDate()}
                    </div>
                    <div className="space-y-0.5">
                      {list.slice(0, view === "woche" ? 8 : 3).map((e) => (
                        <div
                          key={e.id}
                          className={`truncate rounded-md border px-1 py-0.5 text-[9.5px] leading-tight ${
                            SOURCE_STYLE[e.quelle] ?? SOURCE_STYLE.jon
                          } ${e.erledigt ? "line-through opacity-50" : ""}`}
                        >
                          {e.zeit && <span className="opacity-75">{e.zeit} </span>}
                          {e.titel}
                        </div>
                      ))}
                      {list.length > (view === "woche" ? 8 : 3) && (
                        <div className="text-[9px] text-white/40 px-1">
                          +{list.length - (view === "woche" ? 8 : 3)} weitere
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
            <div className="flex gap-3 mt-3 flex-wrap">
              {Object.entries(SOURCE_LABEL).map(([k, label]) => (
                <div key={k} className="flex items-center gap-1.5 text-[10px] text-white/45">
                  <span
                    className={`w-2.5 h-2.5 rounded-full border ${SOURCE_STYLE[k]}`}
                  />
                  {label}
                </div>
              ))}
            </div>
          </div>

          <div className="w-72 shrink-0 border-l border-white/10 flex flex-col min-h-0">
            <div className="px-4 py-3 border-b border-white/10 shrink-0">
              <div className="text-[12px] text-white/80 font-medium">
                {new Date(selectedDay).toLocaleDateString("de-DE", {
                  weekday: "long",
                  day: "2-digit",
                  month: "long",
                })}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5">
              {dayList.length === 0 && (
                <div className="text-[11.5px] text-white/35 px-1">
                  Keine Einträge. Doppelklick auf einen Tag oder „+ Eintrag“ —
                  oder sag Jon einfach: „Trag Freitag 15 Uhr Zahnarzt ein.“
                </div>
              )}
              {dayList.map((e) => (
                <div
                  key={e.id}
                  className={`rounded-xl border px-2.5 py-2 ${
                    SOURCE_STYLE[e.quelle] ?? SOURCE_STYLE.jon
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {e.typ === "task" && e.quelle === "jon" && (
                      <button
                        onClick={() => void toggleDone(e)}
                        className="mt-0.5 w-3.5 h-3.5 shrink-0 rounded border border-current flex items-center justify-center text-[9px]"
                      >
                        {e.erledigt ? "✓" : ""}
                      </button>
                    )}
                    <div className="min-w-0 flex-1">
                      <div
                        className={`text-[12px] leading-snug ${
                          e.erledigt ? "line-through opacity-50" : ""
                        }`}
                      >
                        {e.titel}
                      </div>
                      <div className="text-[10px] opacity-70">
                        {e.zeit || t("cal_all_day")}
                        {e.dauer_minuten ? ` · ${e.dauer_minuten} Min` : ""}
                        {" · "}
                        {SOURCE_LABEL[e.quelle]}
                      </div>
                      {e.notiz && (
                        <div className="text-[10px] opacity-60 mt-0.5">{e.notiz}</div>
                      )}
                    </div>
                    {e.quelle === "jon" && (
                      <button
                        onClick={() => openEdit(e)}
                        className="text-[11px] opacity-60 hover:opacity-100"
                      >
                        ✎
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {hint && (
              <div className="px-4 py-2 text-[10.5px] text-amber-200/90 border-t border-white/10">
                {hint}
              </div>
            )}
          </div>
        </div>

        {form && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/60">
            <div className="glass rounded-2xl border border-white/20 w-[92%] max-w-sm p-4 space-y-2.5">
              <div className="text-[13px] font-semibold gold-text">
                {form.id ? t("cal_edit_entry") : t("cal_new_entry")}
              </div>
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder={t("cal_title_ph")}
                autoFocus
                className="w-full bg-white/5 border border-white/15 rounded-lg px-2.5 py-1.5 text-[12.5px] text-white outline-none focus:border-gold/50"
              />
              <div className="flex gap-2">
                <input
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                  className="flex-1 bg-white/5 border border-white/15 rounded-lg px-2 py-1.5 text-[12px] text-white outline-none focus:border-gold/50 [color-scheme:dark]"
                />
                <input
                  type="time"
                  value={form.time}
                  onChange={(e) => setForm({ ...form, time: e.target.value })}
                  className="w-24 bg-white/5 border border-white/15 rounded-lg px-2 py-1.5 text-[12px] text-white outline-none focus:border-gold/50 [color-scheme:dark]"
                />
              </div>
              <div className="flex gap-2">
                <select
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}
                  className="flex-1 bg-white/5 border border-white/15 rounded-lg px-2 py-1.5 text-[12px] text-white outline-none [&>option]:bg-zinc-900"
                >
                  <option value="termin">{t("cal_type_termin")}</option>
                  <option value="task">{t("cal_type_task")}</option>
                  <option value="erinnerung">{t("cal_type_reminder")}</option>
                </select>
                <input
                  value={form.duration}
                  onChange={(e) =>
                    setForm({ ...form, duration: e.target.value.replace(/\D/g, "") })
                  }
                  placeholder={t("cal_duration_ph")}
                  className="w-28 bg-white/5 border border-white/15 rounded-lg px-2 py-1.5 text-[12px] text-white outline-none focus:border-gold/50"
                />
              </div>
              <textarea
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
                placeholder={t("cal_note_ph")}
                rows={2}
                className="w-full bg-white/5 border border-white/15 rounded-lg px-2.5 py-1.5 text-[12px] text-white outline-none focus:border-gold/50 resize-none"
              />
              {form.id && form.kind === "task" && (
                <label className="flex items-center gap-2 text-[12px] text-white/70">
                  <input
                    type="checkbox"
                    checked={form.done}
                    onChange={(e) => setForm({ ...form, done: e.target.checked })}
                    className="accent-gold"
                  />
                  Erledigt
                </label>
              )}
              <div className="flex items-center justify-between pt-1">
                {form.id ? (
                  <button
                    onClick={() => void remove()}
                    className="text-[12px] text-red-300/80 hover:text-red-300"
                  >
                    Löschen
                  </button>
                ) : (
                  <span />
                )}
                <div className="flex gap-2">
                  <button
                    onClick={() => setForm(null)}
                    className="px-3 py-1.5 rounded-lg border border-white/15 bg-white/5 text-white/70 text-[12px]"
                  >
                    Abbrechen
                  </button>
                  <button
                    onClick={() => void save()}
                    className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12px]"
                  >
                    Speichern
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
