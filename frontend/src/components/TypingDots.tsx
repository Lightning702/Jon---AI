export default function TypingDots({ tone = "gold" }: { tone?: "gold" | "white" }) {
  const color = tone === "gold" ? "bg-gold/80" : "bg-white/60";
  return (
    <span className="inline-flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${color} animate-bounce`}
          style={{ animationDelay: `${i * 0.15}s`, animationDuration: "0.9s" }}
        />
      ))}
    </span>
  );
}
