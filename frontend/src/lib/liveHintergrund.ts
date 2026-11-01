import type { LiveArt } from "./design";
import { herzPfad } from "./designIcon";

export type Farbe = [number, number, number];

export interface LiveFarben {
  akzent: Farbe;
  leuchten: Farbe;
  basis: Farbe;
}

export interface Zeichner {
  aufloesung: number;
  zeichnen: (ctx: CanvasRenderingContext2D, b: number, h: number, t: number) => void;
}

export function hexFarbe(hex: string): Farbe {
  const zahl = parseInt(hex.slice(1), 16);
  return [(zahl >> 16) & 255, (zahl >> 8) & 255, zahl & 255];
}

function rgba(f: Farbe, a: number): string {
  return `rgba(${f[0]},${f[1]},${f[2]},${a})`;
}

function mix(a: Farbe, b: Farbe, anteil: number): Farbe {
  return [a[0] + (b[0] - a[0]) * anteil, a[1] + (b[1] - a[1]) * anteil, a[2] + (b[2] - a[2]) * anteil];
}

function drehen(f: Farbe, grad: number): Farbe {
  const [r, g, b] = f.map((w) => w / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return f;
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let ton = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  ton = (((ton * 60 + grad) % 360) + 360) % 360 / 360;
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const kanal = (x: number) => {
    const k = x < 0 ? x + 1 : x > 1 ? x - 1 : x;
    if (k < 1 / 6) return p + (q - p) * 6 * k;
    if (k < 1 / 2) return q;
    if (k < 2 / 3) return p + (q - p) * (2 / 3 - k) * 6;
    return p;
  };
  return [kanal(ton + 1 / 3) * 255, kanal(ton) * 255, kanal(ton - 1 / 3) * 255];
}

function zufall(start: number): () => number {
  let wert = start >>> 0;
  return () => {
    wert = (wert * 1664525 + 1013904223) >>> 0;
    return wert / 4294967296;
  };
}

function aurora(f: LiveFarben): Zeichner {
  const flecken = Array.from({ length: 6 }, (_, i) => ({
    fx: 0.06 + i * 0.028,
    fy: 0.05 + i * 0.022,
    phase: i * 1.7,
    groesse: 0.38 + (i % 3) * 0.12,
    farbe: i % 3 === 0 ? f.akzent : i % 3 === 1 ? drehen(f.akzent, 45) : drehen(f.akzent, -55),
  }));
  return {
    aufloesung: 0.3,
    zeichnen(ctx, b, h, t) {
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = rgba(f.basis, 1);
      ctx.fillRect(0, 0, b, h);
      ctx.globalCompositeOperation = "lighter";
      const gross = Math.max(b, h);
      for (const fleck of flecken) {
        const x = b * (0.5 + 0.42 * Math.sin(t * fleck.fx + fleck.phase));
        const y = h * (0.5 + 0.4 * Math.cos(t * fleck.fy + fleck.phase * 1.3));
        const r = gross * fleck.groesse * (0.9 + 0.1 * Math.sin(t * 0.3 + fleck.phase));
        const verlauf = ctx.createRadialGradient(x, y, 0, x, y, r);
        verlauf.addColorStop(0, rgba(fleck.farbe, 0.42));
        verlauf.addColorStop(0.5, rgba(fleck.farbe, 0.14));
        verlauf.addColorStop(1, rgba(fleck.farbe, 0));
        ctx.fillStyle = verlauf;
        ctx.fillRect(0, 0, b, h);
      }
      ctx.globalCompositeOperation = "source-over";
    },
  };
}

function nebel(f: LiveFarben): Zeichner {
  let bild: ImageData | null = null;
  const zweit = drehen(f.akzent, 60);
  const oben = mix(f.leuchten, f.akzent, 0.7);
  return {
    aufloesung: 0.1,
    zeichnen(ctx, b, h, t) {
      if (!bild || bild.width !== b || bild.height !== h) bild = ctx.createImageData(b, h);
      const daten = bild.data;
      const s = t * 0.35;
      let i = 0;
      for (let y = 0; y < h; y++) {
        const v = (y / h) * 4;
        for (let x = 0; x < b; x++) {
          const u = (x / b) * 6;
          const welle =
            Math.sin(u + s) +
            Math.sin(v * 1.3 - s * 0.8) +
            Math.sin((u + v) * 0.7 + s * 0.6) +
            Math.sin(Math.hypot(u - 3 + Math.sin(s * 0.4) * 2, v - 2 + Math.cos(s * 0.3)) * 1.6 - s);
          const n = (welle + 4) / 8;
          const farbe = n < 0.45 ? mix(f.basis, f.leuchten, n / 0.45) : n < 0.75 ? mix(f.leuchten, f.akzent, ((n - 0.45) / 0.3) * 0.7) : mix(oben, zweit, ((n - 0.75) / 0.25) * 0.6);
          daten[i] = farbe[0];
          daten[i + 1] = farbe[1];
          daten[i + 2] = farbe[2];
          daten[i + 3] = 255;
          i += 4;
        }
      }
      ctx.putImageData(bild, 0, 0);
    },
  };
}

function sterne(f: LiveFarben, b: number, h: number, dichte: number): Zeichner {
  const r = zufall(7);
  const anzahl = Math.min(700, Math.round((b * h) / (dichte * dichte * 2600)));
  const liste = Array.from({ length: anzahl }, () => ({
    x: r(),
    y: r(),
    groesse: (0.3 + r() * r() * 1.5) * dichte,
    tiefe: 0.2 + r() * 0.8,
    funkeln: 0.5 + r() * 2.5,
    phase: r() * Math.PI * 2,
    farbe: r() < 0.14 ? mix(f.akzent, [255, 255, 255], 0.3) : ([235, 240, 255] as Farbe),
  }));
  let schnuppe = { start: -10, x: 0, y: 0, winkel: 0 };
  return {
    aufloesung: dichte,
    zeichnen(ctx, b, h, t) {
      const verlauf = ctx.createLinearGradient(0, 0, b, h);
      verlauf.addColorStop(0, rgba(f.basis, 1));
      verlauf.addColorStop(0.55, rgba(mix(f.basis, f.leuchten, 0.9), 1));
      verlauf.addColorStop(1, rgba(f.basis, 1));
      ctx.fillStyle = verlauf;
      ctx.fillRect(0, 0, b, h);
      for (const stern of liste) {
        const x = (((stern.x - t * 0.004 * stern.tiefe) % 1) + 1) % 1;
        const hell = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * stern.funkeln + stern.phase));
        ctx.fillStyle = rgba(stern.farbe, hell * stern.tiefe);
        ctx.beginPath();
        ctx.arc(x * b, stern.y * h, stern.groesse, 0, Math.PI * 2);
        ctx.fill();
      }
      if (t - schnuppe.start > 7) {
        schnuppe = { start: t + 1 + Math.random() * 5, x: 0.2 + Math.random() * 0.7, y: Math.random() * 0.4, winkel: 0.35 + Math.random() * 0.4 };
      }
      const alter = t - schnuppe.start;
      if (alter > 0 && alter < 1.1) {
        const weg = alter * 0.5 * Math.max(b, h);
        const kx = schnuppe.x * b - Math.cos(schnuppe.winkel) * weg;
        const ky = schnuppe.y * h + Math.sin(schnuppe.winkel) * weg;
        const laenge = 140 * dichte;
        const ex = kx + Math.cos(schnuppe.winkel) * laenge;
        const ey = ky - Math.sin(schnuppe.winkel) * laenge;
        const spur = ctx.createLinearGradient(kx, ky, ex, ey);
        const sichtbar = Math.sin((alter / 1.1) * Math.PI);
        spur.addColorStop(0, rgba([255, 255, 255], 0.9 * sichtbar));
        spur.addColorStop(1, rgba(f.akzent, 0));
        ctx.strokeStyle = spur;
        ctx.lineWidth = 1.6 * dichte;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(kx, ky);
        ctx.lineTo(ex, ey);
        ctx.stroke();
      }
    },
  };
}

function wellen(f: LiveFarben, dichte: number): Zeichner {
  const lagen = Array.from({ length: 5 }, (_, i) => ({
    hoehe: 0.5 + i * 0.09,
    weite: 0.0035 + i * 0.0009,
    tempo: 0.35 + i * 0.12,
    phase: i * 1.9,
    alpha: 0.08 + i * 0.05,
    farbe: i % 2 ? drehen(f.akzent, 18) : f.akzent,
  }));
  return {
    aufloesung: dichte,
    zeichnen(ctx, b, h, t) {
      const himmel = ctx.createLinearGradient(0, 0, 0, h);
      himmel.addColorStop(0, rgba(f.basis, 1));
      himmel.addColorStop(1, rgba(f.leuchten, 1));
      ctx.fillStyle = himmel;
      ctx.fillRect(0, 0, b, h);
      const schritt = Math.max(4, 6 * dichte);
      for (const lage of lagen) {
        const y0 = h * lage.hoehe;
        const hub = h * 0.035 * (1 + lage.hoehe);
        const k = lage.weite / dichte;
        ctx.beginPath();
        ctx.moveTo(0, h);
        for (let x = 0; x <= b + schritt; x += schritt) {
          const y = y0 + hub * Math.sin(x * k + t * lage.tempo + lage.phase) + hub * 0.45 * Math.sin(x * k * 2.3 - t * lage.tempo * 1.4 + lage.phase);
          ctx.lineTo(x, y);
        }
        ctx.lineTo(b, h);
        ctx.closePath();
        const fuellung = ctx.createLinearGradient(0, y0 - hub, 0, h);
        fuellung.addColorStop(0, rgba(lage.farbe, lage.alpha * 1.6));
        fuellung.addColorStop(1, rgba(lage.farbe, lage.alpha * 0.3));
        ctx.fillStyle = fuellung;
        ctx.fill();
      }
    },
  };
}

function partikel(f: LiveFarben, b: number, h: number, dichte: number, maus: { x: number; y: number }): Zeichner {
  const r = zufall(11);
  const anzahl = Math.max(30, Math.min(120, Math.round((b * h) / (dichte * dichte * 15000))));
  const liste = Array.from({ length: anzahl }, () => ({
    x: r() * b,
    y: r() * h,
    vx: (r() - 0.5) * 18 * dichte,
    vy: (r() - 0.5) * 18 * dichte,
  }));
  const reichweite = 140 * dichte;
  let vorher = 0;
  return {
    aufloesung: dichte,
    zeichnen(ctx, b, h, t) {
      const dt = Math.min(0.1, Math.max(0, t - vorher));
      vorher = t;
      const glanz = ctx.createRadialGradient(b * 0.3, h * 0.2, 0, b * 0.3, h * 0.2, Math.max(b, h));
      glanz.addColorStop(0, rgba(f.leuchten, 1));
      glanz.addColorStop(1, rgba(f.basis, 1));
      ctx.fillStyle = glanz;
      ctx.fillRect(0, 0, b, h);
      const mx = maus.x * dichte;
      const my = maus.y * dichte;
      for (const p of liste) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        if (p.x < 0 || p.x > b) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
        p.x = Math.min(b, Math.max(0, p.x));
        p.y = Math.min(h, Math.max(0, p.y));
      }
      ctx.lineWidth = dichte;
      for (let i = 0; i < liste.length; i++) {
        const a = liste[i];
        for (let j = i + 1; j < liste.length; j++) {
          const c = liste[j];
          const abstand = Math.hypot(a.x - c.x, a.y - c.y);
          if (abstand > reichweite) continue;
          ctx.strokeStyle = rgba(f.akzent, (1 - abstand / reichweite) * 0.4);
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(c.x, c.y);
          ctx.stroke();
        }
        const zurMaus = Math.hypot(a.x - mx, a.y - my);
        if (maus.x >= 0 && zurMaus < reichweite * 1.4) {
          ctx.strokeStyle = rgba(f.akzent, (1 - zurMaus / (reichweite * 1.4)) * 0.6);
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(mx, my);
          ctx.stroke();
        }
      }
      for (const p of liste) {
        ctx.fillStyle = rgba(f.akzent, 0.85);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.7 * dichte, 0, Math.PI * 2);
        ctx.fill();
      }
    },
  };
}

function roseMalen(groesse: number): HTMLCanvasElement {
  const bild = document.createElement("canvas");
  bild.width = groesse;
  bild.height = groesse;
  const ctx = bild.getContext("2d");
  if (ctx) {
    ctx.font = `${Math.round(groesse * 0.82)}px "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("\u{1F339}", groesse / 2, groesse / 2 + groesse * 0.04);
  }
  return bild;
}

function herzen(f: LiveFarben, b: number, h: number, dichte: number): Zeichner {
  const r = zufall(14);
  const toene: Farbe[] = [f.akzent, mix(f.akzent, [255, 255, 255], 0.35), [224, 22, 79], [255, 143, 184], [255, 194, 214]];
  const anzahl = Math.max(16, Math.min(46, Math.round((b * h) / (dichte * dichte * 26000))));
  const liste = Array.from({ length: anzahl }, () => ({
    x: r(),
    y: r() * 1.2,
    groesse: (9 + r() * r() * 34) * dichte,
    tempo: 0.025 + r() * 0.05,
    schwanken: 0.012 + r() * 0.03,
    phase: r() * Math.PI * 2,
    farbe: toene[Math.floor(r() * toene.length)],
    alpha: 0.35 + r() * 0.55,
  }));
  const blaetter = Array.from({ length: Math.round(anzahl * 0.45) }, () => ({
    x: r(),
    y: r() * 1.2 - 0.1,
    groesse: (4 + r() * 5) * dichte,
    tempo: 0.03 + r() * 0.04,
    drehen: 0.6 + r() * 1.6,
    phase: r() * Math.PI * 2,
    farbe: r() < 0.5 ? ([214, 22, 79] as Farbe) : ([255, 120, 160] as Farbe),
  }));
  const rosenBild = roseMalen(Math.round(64 * dichte));
  const rosen = Array.from({ length: 9 }, () => ({
    x: r(),
    y: r() * 1.2 - 0.1,
    groesse: (30 + r() * 30) * dichte,
    tempo: 0.012 + r() * 0.018,
    drehen: (r() - 0.5) * 0.6,
    phase: r() * Math.PI * 2,
  }));
  return {
    aufloesung: dichte,
    zeichnen(ctx, b, h, t) {
      const grund = ctx.createRadialGradient(b * 0.5, h * 1.05, 0, b * 0.5, h * 0.9, Math.max(b, h) * 1.05);
      grund.addColorStop(0, rgba(f.leuchten, 1));
      grund.addColorStop(1, rgba(f.basis, 1));
      ctx.fillStyle = grund;
      ctx.fillRect(0, 0, b, h);
      const puls = 0.5 + 0.5 * Math.sin(t * 2.2);
      const mitte = Math.min(b, h) * (0.42 + puls * 0.03);
      const schein = ctx.createRadialGradient(b * 0.5, h * 0.48, 0, b * 0.5, h * 0.48, mitte);
      schein.addColorStop(0, rgba(f.akzent, 0.1 + puls * 0.05));
      schein.addColorStop(1, rgba(f.akzent, 0));
      ctx.fillStyle = schein;
      ctx.fillRect(0, 0, b, h);
      herzPfad(ctx, b * 0.5, h * 0.48, mitte * 1.1);
      ctx.fillStyle = rgba(f.akzent, 0.035 + puls * 0.025);
      ctx.fill();
      for (const rose of rosen) {
        const y = (((rose.y + t * rose.tempo) % 1.3) + 1.3) % 1.3 - 0.15;
        const x = rose.x + Math.sin(t * 0.4 + rose.phase) * 0.02;
        ctx.save();
        ctx.translate(x * b, y * h);
        ctx.rotate(rose.drehen + Math.sin(t * 0.6 + rose.phase) * 0.25);
        ctx.globalAlpha = 0.85;
        ctx.drawImage(rosenBild, -rose.groesse / 2, -rose.groesse / 2, rose.groesse, rose.groesse);
        ctx.restore();
      }
      for (const blatt of blaetter) {
        const y = (((blatt.y + t * blatt.tempo) % 1.3) + 1.3) % 1.3 - 0.15;
        const x = blatt.x + Math.sin(t * 0.9 + blatt.phase) * 0.03;
        ctx.save();
        ctx.translate(x * b, y * h);
        ctx.rotate(t * blatt.drehen + blatt.phase);
        ctx.scale(1, 0.45 + 0.55 * Math.abs(Math.cos(t * blatt.drehen * 1.3 + blatt.phase)));
        ctx.beginPath();
        ctx.ellipse(0, 0, blatt.groesse * 0.6, blatt.groesse, 0, 0, Math.PI * 2);
        ctx.fillStyle = rgba(blatt.farbe, 0.7);
        ctx.fill();
        ctx.restore();
      }
      for (const herz of liste) {
        const y = 1.15 - ((((herz.y + t * herz.tempo) % 1.3) + 1.3) % 1.3);
        const x = herz.x + Math.sin(t * 0.8 + herz.phase) * herz.schwanken;
        const px = x * b;
        const py = y * h;
        const s = herz.groesse * (1 + 0.06 * Math.sin(t * 3 + herz.phase));
        if (s > 22 * dichte) {
          const glanz = ctx.createRadialGradient(px, py, 0, px, py, s * 1.3);
          glanz.addColorStop(0, rgba(herz.farbe, 0.18 * herz.alpha));
          glanz.addColorStop(1, rgba(herz.farbe, 0));
          ctx.fillStyle = glanz;
          ctx.fillRect(px - s * 1.3, py - s * 1.3, s * 2.6, s * 2.6);
        }
        ctx.save();
        ctx.translate(px, py);
        ctx.rotate(Math.sin(t * 0.7 + herz.phase) * 0.25);
        herzPfad(ctx, 0, 0, s);
        const fuellung = ctx.createLinearGradient(-s * 0.4, -s * 0.4, s * 0.4, s * 0.5);
        fuellung.addColorStop(0, rgba(mix(herz.farbe, [255, 255, 255], 0.35), herz.alpha));
        fuellung.addColorStop(1, rgba(herz.farbe, herz.alpha));
        ctx.fillStyle = fuellung;
        ctx.fill();
        ctx.restore();
      }
    },
  };
}

export function zeichnerBauen(art: LiveArt, farben: LiveFarben, breite: number, hoehe: number, maus: { x: number; y: number }): Zeichner {
  const dichte = Math.min(1.5, window.devicePixelRatio || 1);
  switch (art) {
    case "nebel":
      return nebel(farben);
    case "sterne":
      return sterne(farben, breite * dichte, hoehe * dichte, dichte);
    case "wellen":
      return wellen(farben, dichte);
    case "partikel":
      return partikel(farben, breite * dichte, hoehe * dichte, dichte, maus);
    case "herzen":
      return herzen(farben, breite * dichte, hoehe * dichte, dichte);
    default:
      return aurora(farben);
  }
}
