import { useRef } from "react";

declare global {
  interface Window {
    jon?: {
      minimize: () => void;
      maximize: () => void;
      close: () => void;
      moveBy?: (dx: number, dy: number) => void;
      platform: string;
    };
  }
}

export default function TitleBar() {
  const api = window.jon;
  const dragging = useRef(false);
  const last = useRef({ x: 0, y: 0 });

  const onMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    if ((e.target as HTMLElement).closest(".no-drag")) return;
    if (!api?.moveBy) return;
    dragging.current = true;
    last.current = { x: e.screenX, y: e.screenY };
    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const dx = ev.screenX - last.current.x;
      const dy = ev.screenY - last.current.y;
      last.current = { x: ev.screenX, y: ev.screenY };
      if (dx || dy) api.moveBy?.(dx, dy);
    };
    const onUp = () => {
      dragging.current = false;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const onDoubleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest(".no-drag")) return;
    api?.maximize();
  };

  return (
    <div
      onMouseDown={onMouseDown}
      onDoubleClick={onDoubleClick}
      className="flex items-center justify-between h-10 px-4 select-none"
    >
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-gold shadow-gold" />
        <span className="text-sm font-semibold tracking-wide gold-text">JON</span>
      </div>
      {api && (
        <div className="no-drag flex items-center gap-1">
          <button
            onClick={() => api.minimize()}
            className="w-8 h-8 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition"
          >
            &#8211;
          </button>
          <button
            onClick={() => api.maximize()}
            className="w-8 h-8 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition"
          >
            &#9633;
          </button>
          <button
            onClick={() => api.close()}
            className="w-8 h-8 rounded-lg hover:bg-red-500/70 text-white/60 hover:text-white transition"
          >
            &#10005;
          </button>
        </div>
      )}
    </div>
  );
}
