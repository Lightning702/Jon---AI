export type VoiceState = "idle" | "listening" | "recording" | "transcribing" | "armed";
export interface VoiceCallbacks {
    onState: (state: VoiceState) => void;
    onCommand: (text: string) => void;
}
export declare class VoiceListener {
    private callbacks;
    private stream;
    private context;
    private processor;
    private source;
    private preroll;
    private utterance;
    private inUtterance;
    private speechMs;
    private silenceMs;
    private utteranceMs;
    private armed;
    private armTimer;
    private running;
    private busy;
    constructor(callbacks: VoiceCallbacks);
    setBusy(busy: boolean): void;
    start(): Promise<void>;
    stop(): void;
    private disarm;
    private arm;
    private handleChunk;
    private finishUtterance;
    private handleTranscript;
}
