declare global {
  interface Window {
    jon?: {
      minimize: () => void;
      maximize: () => void;
      close: () => void;
      platform: string;
    };
  }
}

export default function TitleBar() {
  const api = window.jon;
  return (
    <div className="drag flex items-center justify-between h-10 px-4 select-none">
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
