export type VoiceUiState = "idle" | "listening" | "recording" | "transcribing" | "armed" | "processing" | "speaking" | "done" | "error";
export default function VoiceIndicator({ state, detail, }: {
    state: VoiceUiState;
    detail?: string;
}): import("react").JSX.Element | null;
