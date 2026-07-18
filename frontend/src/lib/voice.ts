import { transcribeAudio, wakePoll, wakeStart } from "./api";

export type VoiceState =
  | "idle"
  | "listening"
  | "recording"
  | "transcribing"
  | "armed";

export interface VoiceCallbacks {
  onState: (state: VoiceState) => void;
  onCommand: (text: string) => void;
  onBargeIn?: () => void;
}

const WAKE_WORDS = new Set(["jon", "john", "jonny", "johnny", "jonh"]);
const SPEECH_THRESHOLD = 0.015;
const SILENCE_END_MS = 1100;
const MIN_SPEECH_MS = 350;
const MAX_UTTERANCE_MS = 15000;
const PREROLL_CHUNKS = 5;
const ARM_TIMEOUT_MS = 12000;
const WAKE_POLL_MS = 400;

function downsampleTo16k(chunks: Float32Array[], inputRate: number): Int16Array {
  let total = 0;
  for (const c of chunks) total += c.length;
  const merged = new Float32Array(total);
  let offset = 0;
  for (const c of chunks) {
    merged.set(c, offset);
    offset += c.length;
  }
  const ratio = inputRate / 16000;
  const outLength = Math.floor(merged.length / ratio);
  const out = new Int16Array(outLength);
  for (let i = 0; i < outLength; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), merged.length);
    let sum = 0;
    for (let j = start; j < end; j++) sum += merged[j];
    const sample = sum / Math.max(end - start, 1);
    out[i] = Math.max(-1, Math.min(1, sample)) * 0x7fff;
  }
  return out;
}

function encodeWav(samples: Int16Array): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeStr = (pos: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(pos + i, str.charCodeAt(i));
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, 16000, true);
  view.setUint32(28, 32000, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    view.setInt16(44 + i * 2, samples[i], true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}

export class VoiceListener {
  private callbacks: VoiceCallbacks;
  private stream: MediaStream | null = null;
  private context: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private preroll: Float32Array[] = [];
  private utterance: Float32Array[] = [];
  private inUtterance = false;
  private speechMs = 0;
  private silenceMs = 0;
  private utteranceMs = 0;
  private armed = false;
  private armTimer: number | null = null;
  private running = false;
  private busy = false;
  private speaking = false;
  private speakingText = "";
  private mode: "backend" | "local" = "local";
  private pollTimer: number | null = null;
  private lastCounter = -1;
  private capturing = false;

  constructor(callbacks: VoiceCallbacks) {
    this.callbacks = callbacks;
  }

  setBusy(busy: boolean) {
    this.busy = busy;
  }

  setSpeaking(speaking: boolean, text = "") {
    this.speaking = speaking;
    this.speakingText = speaking ? text : "";
  }

  private isEcho(words: string[]): boolean {
    if (!this.speakingText) return false;
    const spoken = this.speakingText.toLowerCase();
    let hits = 0;
    for (const w of words) if (w.length > 3 && spoken.includes(w)) hits++;
    return hits >= Math.max(2, Math.ceil(words.length * 0.6));
  }

  isBackendWake(): boolean {
    return this.mode === "backend";
  }

  async start(): Promise<void> {
    if (this.running) return;
    this.running = true;
    try {
      const status = await wakeStart();
      if (status.listening) {
        this.mode = "backend";
        this.lastCounter = status.counter ?? 0;
        this.callbacks.onState("listening");
        this.pollTimer = window.setInterval(() => void this.pollWake(), WAKE_POLL_MS);
        return;
      }
    } catch {
      void 0;
    }
    this.mode = "local";
    await this.openMic();
    this.callbacks.onState("listening");
  }

  stop(): void {
    this.running = false;
    if (this.pollTimer !== null) {
      window.clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.closeMic();
    this.capturing = false;
    this.disarm();
    this.callbacks.onState("idle");
  }

  private async openMic(): Promise<void> {
    if (this.stream) return;
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    this.context = new AudioContext();
    await this.context.resume().catch(() => undefined);
    this.source = this.context.createMediaStreamSource(this.stream);
    this.processor = this.context.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (e) => this.handleChunk(e);
    this.source.connect(this.processor);
    this.processor.connect(this.context.destination);
  }

  private closeMic(): void {
    this.processor?.disconnect();
    this.source?.disconnect();
    this.stream?.getTracks().forEach((t) => t.stop());
    this.context?.close().catch(() => undefined);
    this.processor = null;
    this.source = null;
    this.stream = null;
    this.context = null;
    this.inUtterance = false;
    this.utterance = [];
    this.preroll = [];
  }

  private async pollWake(): Promise<void> {
    if (!this.running || this.capturing) return;
    try {
      const status = await wakePoll();
      if (!status.listening && this.running && !this.capturing) {
        void wakeStart().catch(() => undefined);
        return;
      }
      if (this.lastCounter < 0) {
        this.lastCounter = status.counter;
        return;
      }
      if (status.counter > this.lastCounter) {
        this.lastCounter = status.counter;
        if (this.busy && !this.speaking) return;
        if (this.speaking) this.callbacks.onBargeIn?.();
        void this.captureCommand();
      }
    } catch {
      void 0;
    }
  }

  private async captureCommand(): Promise<void> {
    if (this.capturing) return;
    this.capturing = true;
    this.armed = true;
    try {
      await this.openMic();
      this.callbacks.onState("armed");
      this.armTimer = window.setTimeout(() => {
        this.finishBackendCapture();
      }, ARM_TIMEOUT_MS);
    } catch {
      this.capturing = false;
      this.armed = false;
      this.callbacks.onState("listening");
    }
  }

  private finishBackendCapture(): void {
    if (this.mode !== "backend") return;
    this.disarm();
    this.closeMic();
    this.capturing = false;
    if (this.running) this.callbacks.onState("listening");
  }

  private disarm() {
    this.armed = false;
    if (this.armTimer !== null) {
      window.clearTimeout(this.armTimer);
      this.armTimer = null;
    }
  }

  private arm() {
    this.disarm();
    this.armed = true;
    this.callbacks.onState("armed");
    this.armTimer = window.setTimeout(() => {
      this.armed = false;
      if (this.mode === "backend") {
        this.finishBackendCapture();
        return;
      }
      if (this.running) this.callbacks.onState("listening");
    }, ARM_TIMEOUT_MS);
  }

  private handleChunk(e: AudioProcessingEvent) {
    if (!this.running || !this.context) return;
    const input = e.inputBuffer.getChannelData(0);
    const chunk = new Float32Array(input);
    const chunkMs = (chunk.length / this.context.sampleRate) * 1000;
    let sum = 0;
    for (let i = 0; i < chunk.length; i++) sum += chunk[i] * chunk[i];
    const rms = Math.sqrt(sum / chunk.length);
    const voiced = rms > SPEECH_THRESHOLD;

    if (!this.inUtterance) {
      this.preroll.push(chunk);
      if (this.preroll.length > PREROLL_CHUNKS) this.preroll.shift();
      if (voiced) {
        this.inUtterance = true;
        this.utterance = [...this.preroll];
        this.speechMs = chunkMs;
        this.silenceMs = 0;
        this.utteranceMs = chunkMs;
        this.callbacks.onState(this.armed ? "armed" : "recording");
      }
      return;
    }

    this.utterance.push(chunk);
    this.utteranceMs += chunkMs;
    if (voiced) {
      this.speechMs += chunkMs;
      this.silenceMs = 0;
    } else {
      this.silenceMs += chunkMs;
    }

    if (this.silenceMs >= SILENCE_END_MS || this.utteranceMs >= MAX_UTTERANCE_MS) {
      const chunks = this.utterance;
      const speechMs = this.speechMs;
      this.inUtterance = false;
      this.utterance = [];
      this.preroll = [];
      if (speechMs >= MIN_SPEECH_MS) {
        void this.finishUtterance(chunks, this.context.sampleRate);
      } else if (this.running) {
        this.callbacks.onState(this.armed ? "armed" : "listening");
      }
    }
  }

  private async finishUtterance(chunks: Float32Array[], sampleRate: number) {
    this.callbacks.onState("transcribing");
    let text = "";
    try {
      const wav = encodeWav(downsampleTo16k(chunks, sampleRate));
      text = await transcribeAudio(wav);
    } catch {
      text = "";
    }
    if (!this.running) return;
    this.handleTranscript(text.trim());
  }

  private handleTranscript(text: string) {
    if (!text) {
      if (this.mode === "backend" && this.armed) {
        this.callbacks.onState("armed");
        return;
      }
      this.callbacks.onState(this.armed ? "armed" : "listening");
      return;
    }
    const words = text
      .toLowerCase()
      .replace(/[^\p{L}\p{N} ]/gu, " ")
      .split(/\s+/)
      .filter(Boolean);

    if (this.busy && !this.speaking) {
      this.callbacks.onState("listening");
      return;
    }

    if (this.busy && this.speaking) {
      if (this.isEcho(words)) {
        this.callbacks.onState("listening");
        return;
      }
      const idx = words.findIndex((w) => WAKE_WORDS.has(w));
      if (!this.armed && idx < 0) {
        this.callbacks.onState("listening");
        return;
      }
      this.callbacks.onBargeIn?.();
      if (this.armed) {
        this.disarm();
        this.emitCommand(text);
        return;
      }
      const command = words.slice(idx + 1).join(" ").trim();
      if (command.length >= 3) this.emitCommand(command);
      else this.arm();
      return;
    }

    if (this.armed) {
      this.disarm();
      this.emitCommand(text);
      return;
    }

    const idx = words.findIndex((w) => WAKE_WORDS.has(w));
    if (idx < 0) {
      this.callbacks.onState("listening");
      return;
    }
    const command = words.slice(idx + 1).join(" ").trim();
    if (command.length >= 3) {
      this.emitCommand(command);
    } else {
      this.arm();
    }
  }

  private emitCommand(text: string) {
    if (this.mode === "backend") {
      this.disarm();
      this.closeMic();
      this.capturing = false;
    }
    this.callbacks.onCommand(text);
  }
}
