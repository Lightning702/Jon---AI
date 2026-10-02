export {};
declare global {
  interface Window {
    Jon3D: { create(canvas: HTMLCanvasElement): { start(): void; stop(): void; destroy(): void; setActivity(value: string): void; setTaskState(value: string): void; setSleep(value: boolean): void; render(): void } | null };
  }
}
