import { useRef, useState } from "react";

interface Props {
  disabled: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
  streaming: boolean;
}

export default function Composer({ disabled, onSend, onStop, streaming }: Props) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const value = text.trim();
    if (!value || disabled) return;
    onSend(value);
    setText("");
    if (ref.current) ref.current.style.height = "auto";
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="p-4">
      <div className="glass rounded-2xl flex items-end gap-2 p-2">
        <textarea
          ref={ref}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = Math.min(e.target.scrollHeight, 180) + "px";
          }}
          onKeyDown={onKey}
          rows={1}
          placeholder="Schreibe Jon eine Nachricht ..."
          className="flex-1 bg-transparent resize-none outline-none px-3 py-2 text-white/90 placeholder-white/30 max-h-44"
        />
        {streaming ? (
          <button
            onClick={onStop}
            className="px-4 py-2 rounded-xl bg-red-500/80 hover:bg-red-500 text-white font-medium transition"
          >
            Stop
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={disabled || !text.trim()}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold shadow-gold disabled:opacity-40 hover:brightness-110 transition"
          >
            Senden
          </button>
        )}
      </div>
    </div>
  );
}
