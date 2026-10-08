import type { LucideIcon } from "lucide-react";
import {
  Activity, AlarmClock, Archive, Ban, BarChart3, Bell, Bike, BookOpen, Bot, Box, Brain, BrickWall, Brush, Building2, Bus,
  Calendar, CalendarDays, Camera, Car, Cat, ChefHat, Circle, CircleCheck, CircleDot, CircleHelp, CircleStop, CircleX,
  Clapperboard, ClipboardList, Clock, Cloud, CloudDrizzle, CloudFog, CloudLightning, CloudRain, CloudSnow, CloudSun,
  Compass, Cpu, Dice5, Dog, Download, Droplet, Earth, Eye, FileText, Flag, Flame, Folder, FolderOpen, Footprints,
  Gamepad2, Gift, Glasses, Globe, Hand, Handshake, Headphones, Heart, Hourglass, House, Image, Inbox, Key, KeyRound,
  Laptop, Layers, Library, Lightbulb, Link, Lock, Mail, Map, MapPin, Megaphone, MessageCircle, Mic, Monitor, Moon,
  Mountain, MousePointer2, Music, Newspaper, NotebookPen, OctagonX, Package, Palette, Paperclip, PartyPopper, Pause,
  PenLine, PersonStanding, Phone, Pin, Plane, Plug, Presentation, Puzzle, RefreshCw, Repeat, Rocket, Route, Ruler,
  Satellite, SatelliteDish, Save, ScrollText, Search, Settings, SkipForward, Smartphone, Smile, Sparkles, Square,
  Star, StickyNote, Stethoscope, Sun, Sunrise, Target, Thermometer, ThumbsUp, Timer, Toolbox, TrafficCone, TrainFront,
  Trash2, TrendingUp, TriangleAlert, Upload, User, Users, Utensils, Video, Volume2, Wind, Wrench, Zap,
} from "lucide-react";

const KARTE: Record<string, LucideIcon> = {
  "🧠": Brain, "📍": MapPin, "🌙": Moon, "✅": CircleCheck, "🙂": Smile, "📅": Calendar, "🗓": CalendarDays, "🤖": Bot,
  "🗑": Trash2, "✈": Plane, "🔒": Lock, "🔐": KeyRound, "📊": BarChart3, "📈": TrendingUp, "👁": Eye, "👀": Eye,
  "🧭": Compass, "🗺": Map, "📁": Folder, "📂": FolderOpen, "🗂": Folder, "❌": CircleX, "✖": CircleX, "🎙": Mic,
  "📞": Phone, "☎": Phone, "🔍": Search, "🔎": Search, "💬": MessageCircle, "📄": FileText, "👥": Users, "🧑‍🤝‍🧑": Users,
  "🎬": Clapperboard, "🎥": Video, "🔔": Bell, "📝": NotebookPen, "⚠": TriangleAlert, "📜": ScrollText, "🎨": Palette,
  "📱": Smartphone, "📲": Smartphone, "📋": ClipboardList, "☀": Sun, "📷": Camera, "📸": Camera, "🔴": CircleDot,
  "🟢": CircleDot, "🟡": CircleDot, "🔵": CircleDot, "⚪": Circle, "✉": Mail, "📧": Mail, "📌": Pin, "📔": BookOpen,
  "📚": Library, "⏹": Square, "🛑": OctagonX, "⚙": Settings, "🎵": Music, "🎧": Headphones, "♪": Music, "📎": Paperclip,
  "🧰": Toolbox, "📥": Inbox, "📤": Upload, "✍": PenLine, "🎴": Layers, "🧹": Brush, "⬇": Download, "🕶": Glasses,
  "🍳": ChefHat, "🍴": Utensils, "🕹": Gamepad2, "🎮": Gamepad2, "👾": Gamepad2, "🎲": Dice5, "🚀": Rocket,
  "🌤": CloudSun, "⛅": CloudSun, "🌐": Globe, "🌍": Earth, "🌎": Earth, "💡": Lightbulb, "🖼": Image, "🔁": Repeat,
  "🔄": RefreshCw, "🤝": Handshake, "⚡": Zap, "🏁": Flag, "⏱": Timer, "⏳": Hourglass, "⌛": Hourglass,
  "🌡": Thermometer, "🎁": Gift, "💻": Laptop, "🖥": Monitor, "🔮": Sparkles, "✨": Sparkles, "✦": Sparkles,
  "👤": User, "⏰": AlarmClock, "🕑": Clock, "🕒": Clock, "🕓": Clock, "🖱": MousePointer2, "🎯": Target,
  "❓": CircleHelp, "🔌": Plug, "⏸": Pause, "💾": Save, "🎉": PartyPopper, "🚫": Ban, "👣": Footprints, "🐱": Cat,
  "🐶": Dog, "☁": Cloud, "🌫": CloudFog, "🌦": CloudDrizzle, "🌧": CloudRain, "🌨": CloudSnow, "⛈": CloudLightning,
  "🚲": Bike, "📏": Ruler, "📰": Newspaper, "📡": SatelliteDish, "🛰": Satellite, "🌅": Sunrise, "🏠": House,
  "📽": Presentation, "🧊": Box, "🗜": Archive, "📦": Package, "⏭": SkipForward, "❤": Heart, "👍": ThumbsUp,
  "🔥": Flame, "📣": Megaphone, "🔊": Volume2, "🗒": StickyNote, "🔑": Key, "🩺": Stethoscope, "🧱": BrickWall,
  "🌀": Activity, "🚶": PersonStanding, "🧍": PersonStanding, "🚗": Car, "🚌": Bus, "💧": Droplet, "🌬": Wind,
  "🏙": Building2, "⛰": Mountain, "🏔": Mountain, "🥾": Footprints, "🚦": TrafficCone, "🚇": TrainFront, "🔗": Link,
  "🛣": Route, "⏺": CircleStop, "🧩": Puzzle, "⭐": Star, "🌟": Star, "🙅": Hand, "🖐": Hand, "🔧": Wrench,
  "🛠": Wrench, "🧪": Cpu, "🔬": Search, "📖": BookOpen, "🗣": Megaphone, "🏆": Star,
};

const ZUSATZ = /[️‍]/g;

export function symbolFuer(zeichen: string | undefined | null): LucideIcon | null {
  if (!zeichen) return null;
  const roh = zeichen.trim();
  return KARTE[roh] ?? KARTE[roh.replace(ZUSATZ, "")] ?? KARTE[Array.from(roh.replace(ZUSATZ, ""))[0] ?? ""] ?? null;
}

const BILDZEICHEN = /\p{Extended_Pictographic}(?:️|⃣)?(?:‍\p{Extended_Pictographic}️?)*/gu;

export default function Symbol({
  zeichen,
  size = 15,
  className,
  strokeWidth = 1.9,
}: {
  zeichen: string | number | undefined | null;
  size?: number;
  className?: string;
  strokeWidth?: number;
}) {
  if (zeichen === undefined || zeichen === null || zeichen === "") return null;
  const text = String(zeichen);
  const gefunden = text.match(BILDZEICHEN) || [];
  const rest = text.replace(BILDZEICHEN, "").replace(/\s{2,}/g, " ").trim();
  const Icon = gefunden.length ? symbolFuer(gefunden[0]) : null;
  if (!Icon && !rest) return gefunden.length ? <span className={className}>{gefunden[0]}</span> : null;
  if (!Icon) return <span className={className}>{rest}</span>;
  const bild = <Icon size={size} className={rest ? undefined : className} strokeWidth={strokeWidth} aria-hidden="true" style={{ display: "inline-block", verticalAlign: "-0.15em", flexShrink: 0 }} />;
  if (!rest) return bild;
  return (
    <span className={className} style={{ display: "inline-flex", alignItems: "center", gap: "0.3em" }}>
      {bild}
      {rest}
    </span>
  );
}
