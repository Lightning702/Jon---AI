import type { Design } from "./design";

const GROESSE = 256;
const STANDARD_AKZENT = "#d4af37";

function teile(hex: string): number[] {
  const zahl = parseInt(hex.slice(1), 16);
  return [(zahl >> 16) & 255, (zahl >> 8) & 255, zahl & 255];
}

function mix(hex: string, ziel: string, anteil: number): string {
  const a = teile(hex);
  const b = teile(ziel);
  return "#" + a.map((w, i) => Math.round(w + (b[i] - w) * anteil).toString(16).padStart(2, "0")).join("");
}

export function herzPfad(ctx: CanvasRenderingContext2D, x: number, y: number, s: number): void {
  ctx.beginPath();
  ctx.moveTo(x, y - s * 0.2);
  ctx.bezierCurveTo(x - s * 0.15, y - s * 0.45, x - s * 0.5, y - s * 0.4, x - s * 0.5, y - s * 0.1);
  ctx.bezierCurveTo(x - s * 0.5, y + s * 0.15, x - s * 0.2, y + s * 0.3, x, y + s * 0.5);
  ctx.bezierCurveTo(x + s * 0.2, y + s * 0.3, x + s * 0.5, y + s * 0.15, x + s * 0.5, y - s * 0.1);
  ctx.bezierCurveTo(x + s * 0.5, y - s * 0.4, x + s * 0.15, y - s * 0.45, x, y - s * 0.2);
  ctx.closePath();
}

export function iconZeichnen(d: Design): string {
  if (!d.herzen && d.akzent.toLowerCase() === STANDARD_AKZENT) return "";
  const leinwand = document.createElement("canvas");
  leinwand.width = GROESSE;
  leinwand.height = GROESSE;
  const ctx = leinwand.getContext("2d");
  if (!ctx) return "";
  const s = GROESSE;
  const m = s / 2;
  const akzent = d.akzent;
  const hell = mix(akzent, "#ffffff", 0.45);
  const dunkel = mix(akzent, "#000000", 0.38);

  const ring = ctx.createLinearGradient(0, 0, s, s);
  ring.addColorStop(0, hell);
  ring.addColorStop(0.45, akzent);
  ring.addColorStop(1, dunkel);
  ctx.beginPath();
  ctx.arc(m, m, s * 0.47, 0, Math.PI * 2);
  ctx.fillStyle = ring;
  ctx.fill();
  ctx.lineWidth = s * 0.012;
  ctx.strokeStyle = dunkel;
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(m, m, s * 0.437, Math.PI * 1.02, Math.PI * 1.72);
  ctx.lineWidth = s * 0.05;
  ctx.strokeStyle = "rgba(255,255,255,0.32)";
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(m, m, s * 0.405, 0, Math.PI * 2);
  ctx.fillStyle = d.herzen ? "#1c0612" : "#0b0b0f";
  ctx.fill();

  if (d.herzen) {
    for (const x of [0.33, 0.67]) {
      const wange = ctx.createRadialGradient(s * x, s * 0.62, 0, s * x, s * 0.62, s * 0.08);
      wange.addColorStop(0, "rgba(255,120,170,0.55)");
      wange.addColorStop(1, "rgba(255,120,170,0)");
      ctx.fillStyle = wange;
      ctx.fillRect(s * (x - 0.1), s * 0.52, s * 0.2, s * 0.2);
    }
    for (const x of [0.357, 0.643]) {
      herzPfad(ctx, s * x, s * 0.43, s * 0.2);
      const fuellung = ctx.createLinearGradient(s * (x - 0.1), s * 0.33, s * (x + 0.1), s * 0.53);
      fuellung.addColorStop(0, "#ff7aa8");
      fuellung.addColorStop(1, "#e0164f");
      ctx.fillStyle = fuellung;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(s * (x - 0.04), s * 0.4, s * 0.022, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(255,255,255,0.9)";
      ctx.fill();
    }
  } else {
    for (const x of [0.357, 0.643]) {
      ctx.beginPath();
      ctx.arc(s * x, s * 0.44, s * 0.075, 0, Math.PI * 2);
      ctx.fillStyle = akzent;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(s * (x + 0.02), s * 0.42, s * 0.024, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.fill();
    }
  }

  ctx.beginPath();
  ctx.arc(m, s * 0.498, s * 0.186, 0.75, Math.PI - 0.75);
  ctx.lineWidth = s * 0.043;
  ctx.lineCap = "butt";
  ctx.strokeStyle = d.herzen ? "#ff6fa5" : akzent;
  ctx.stroke();

  return leinwand.toDataURL("image/png");
}
