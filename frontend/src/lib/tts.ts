import { speakServer } from "./api";

let cachedVoice: SpeechSynthesisVoice | null = null;
let naturalVoice = true;
let audio: HTMLAudioElement | null = null;
let context: AudioContext | null = null;
const wired = new WeakSet<HTMLAudioElement>();

const MALE_PATTERN = /stefan|klaus|conrad|bernd|jonas|paul|markus|male|mann/i;
const BOOST = 2.2;

export function setNaturalVoice(enabled: boolean): void {
  naturalVoice = enabled;
}

async function amplify(player: HTMLAudioElement): Promise<void> {
  if (wired.has(player)) return;
  try {
    context = context ?? new AudioContext();
    await context.resume();
    if (context.state !== "running") return;
    const source = context.createMediaElementSource(player);
    const compressor = context.createDynamicsCompressor();
    compressor.threshold.value = -18;
    compressor.knee.value = 12;
    compressor.ratio.value = 4;
    compressor.attack.value = 0.003;
    compressor.release.value = 0.2;
    const gain = context.createGain();
    gain.gain.value = BOOST;
    source.connect(compressor);
    compressor.connect(gain);
    gain.connect(context.destination);
    wired.add(player);
  } catch {
    player.volume = 1;
  }
}

function pickVoice(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis?.getVoices() ?? [];
  if (!voices.length) return null;
  const german = voices.filter((v) => v.lang.toLowerCase().startsWith("de"));
  const male = german.find((v) => MALE_PATTERN.test(v.name));
  return male ?? german[0] ?? voices[0];
}

export function initTts(): void {
  if (!window.speechSynthesis) return;
  cachedVoice = pickVoice();
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoice = pickVoice();
  };
}

function cleanForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " Codeblock. ")
    .replace(/\[(.*?)\]\(.*?\)/g, "$1")
    .replace(/https?:\/\/\S+/g, " Link ")
    .replace(/[*_#`>|]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export async function speak(text: string): Promise<void> {
  if (naturalVoice) {
    const clean = cleanForSpeech(text).slice(0, 1200);
    if (!clean) return;
    const blob = await speakServer(clean);
    if (blob) {
      stopSpeaking();
      const url = URL.createObjectURL(blob);
      const player = new Audio(url);
      player.volume = 1;
      await amplify(player);
      audio = player;
      await new Promise<void>((resolve) => {
        const finish = () => {
          URL.revokeObjectURL(url);
          if (audio === player) audio = null;
          resolve();
        };
        player.onended = finish;
        player.onerror = finish;
        void player.play().catch(finish);
      });
      return;
    }
  }
  return speakBrowser(text);
}

function speakBrowser(text: string): Promise<void> {
  return new Promise((resolve) => {
    const synth = window.speechSynthesis;
    if (!synth) {
      resolve();
      return;
    }
    synth.cancel();
    const clean = cleanForSpeech(text).slice(0, 600);
    if (!clean) {
      resolve();
      return;
    }
    if (!cachedVoice) cachedVoice = pickVoice();
    const utterance = new SpeechSynthesisUtterance(clean);
    if (cachedVoice) utterance.voice = cachedVoice;
    const male = cachedVoice ? MALE_PATTERN.test(cachedVoice.name) : false;
    utterance.lang = "de-DE";
    utterance.rate = 1.05;
    utterance.pitch = male ? 1 : 0.7;
    utterance.volume = 1;
    let settled = false;
    const finish = () => {
      if (!settled) {
        settled = true;
        resolve();
      }
    };
    utterance.onend = finish;
    utterance.onerror = finish;
    window.setTimeout(finish, 45000);
    synth.speak(utterance);
  });
}

export function stopSpeaking(): void {
  window.speechSynthesis?.cancel();
  if (audio) {
    audio.pause();
    audio = null;
  }
}
