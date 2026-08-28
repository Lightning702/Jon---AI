import { useEffect, useRef } from "react";

interface Props {
  lat: number;
  lon: number;
  zoom: number;
  bearing: number;
  fadeFrom?: number;
  fadeTo?: number;
}

function seeded(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function makeCanvas(width: number, height: number): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(2, Math.round(width));
  canvas.height = Math.max(2, Math.round(height));
  return canvas;
}

function paintStars(
  width: number,
  height: number,
  count: number,
  maxRadius: number,
  seed: number
): HTMLCanvasElement {
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext("2d");
  if (!ctx) return canvas;
  const random = seeded(seed);
  const tints = [
    "255, 255, 255",
    "214, 228, 255",
    "255, 232, 205",
    "255, 208, 196",
    "205, 240, 255",
  ];
  for (let index = 0; index < count; index += 1) {
    const x = random() * width;
    const y = random() * height;
    const radius = 0.24 + random() * maxRadius;
    const alpha = 0.2 + random() * 0.75;
    const tint = tints[Math.floor(random() * tints.length)];
    ctx.fillStyle = `rgba(${tint}, ${alpha.toFixed(3)})`;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    if (radius > maxRadius * 0.82) {
      const halo = ctx.createRadialGradient(x, y, 0, x, y, radius * 7);
      halo.addColorStop(0, `rgba(${tint}, ${(alpha * 0.5).toFixed(3)})`);
      halo.addColorStop(1, `rgba(${tint}, 0)`);
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(x, y, radius * 7, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  return canvas;
}

function paintGalaxy(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  tilt: number,
  spin: number,
  hue: string,
  seed: number
): void {
  const random = seeded(seed);
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(tilt);
  ctx.scale(1, 0.42);
  const core = ctx.createRadialGradient(0, 0, 0, 0, 0, size);
  core.addColorStop(0, "rgba(255, 249, 232, 0.95)");
  core.addColorStop(0.16, `rgba(${hue}, 0.55)`);
  core.addColorStop(0.55, `rgba(${hue}, 0.16)`);
  core.addColorStop(1, `rgba(${hue}, 0)`);
  ctx.fillStyle = core;
  ctx.beginPath();
  ctx.arc(0, 0, size, 0, Math.PI * 2);
  ctx.fill();
  for (let arm = 0; arm < 2; arm += 1) {
    for (let index = 0; index < 620; index += 1) {
      const progress = index / 620;
      const angle =
        arm * Math.PI + progress * spin + (random() - 0.5) * 0.42;
      const radius = size * (0.12 + progress * 0.95);
      const drift = (random() - 0.5) * size * 0.16;
      const px = Math.cos(angle) * radius + drift;
      const py = Math.sin(angle) * radius + drift;
      const alpha = (1 - progress) * 0.55 * (0.3 + random() * 0.7);
      ctx.fillStyle =
        random() > 0.72
          ? `rgba(255, 255, 255, ${alpha.toFixed(3)})`
          : `rgba(${hue}, ${alpha.toFixed(3)})`;
      ctx.beginPath();
      ctx.arc(px, py, 0.35 + random() * 1.05, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.restore();
}

function paintFeatures(width: number, height: number): HTMLCanvasElement {
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext("2d");
  if (!ctx) return canvas;
  const random = seeded(9137);

  const base = ctx.createLinearGradient(0, 0, width * 0.4, height);
  base.addColorStop(0, "#04040a");
  base.addColorStop(0.5, "#05050c");
  base.addColorStop(1, "#020207");
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, width, height);

  ctx.globalCompositeOperation = "screen";
  const clouds: [number, number, number, string][] = [
    [0.18, 0.24, 0.46, "78, 62, 168"],
    [0.72, 0.68, 0.52, "22, 96, 140"],
    [0.44, 0.86, 0.4, "150, 48, 120"],
    [0.9, 0.18, 0.34, "38, 120, 176"],
    [0.08, 0.78, 0.3, "120, 54, 150"],
  ];
  clouds.forEach(([fx, fy, fr, tint]) => {
    const cx = width * fx;
    const cy = height * fy;
    const radius = Math.max(width, height) * fr;
    const cloud = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    cloud.addColorStop(0, `rgba(${tint}, 0.3)`);
    cloud.addColorStop(0.45, `rgba(${tint}, 0.12)`);
    cloud.addColorStop(1, `rgba(${tint}, 0)`);
    ctx.fillStyle = cloud;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.save();
  ctx.translate(width * 0.5, height * 0.52);
  ctx.rotate(-0.38);
  const band = ctx.createLinearGradient(0, -height * 0.22, 0, height * 0.22);
  band.addColorStop(0, "rgba(120, 140, 220, 0)");
  band.addColorStop(0.42, "rgba(150, 165, 235, 0.14)");
  band.addColorStop(0.5, "rgba(226, 226, 255, 0.2)");
  band.addColorStop(0.58, "rgba(150, 165, 235, 0.14)");
  band.addColorStop(1, "rgba(120, 140, 220, 0)");
  ctx.fillStyle = band;
  ctx.fillRect(-width, -height * 0.22, width * 2, height * 0.44);
  for (let index = 0; index < 2600; index += 1) {
    const x = (random() - 0.5) * width * 2;
    const spread = (random() + random() + random() - 1.5) / 1.5;
    const y = spread * height * 0.18;
    const alpha = 0.2 + random() * 0.6;
    ctx.fillStyle = `rgba(240, 240, 255, ${alpha.toFixed(3)})`;
    ctx.beginPath();
    ctx.arc(x, y, 0.28 + random() * 0.6, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = "rgba(6, 5, 12, 0.55)";
  for (let index = 0; index < 60; index += 1) {
    const x = (random() - 0.5) * width * 1.8;
    const y = (random() - 0.5) * height * 0.2;
    ctx.beginPath();
    ctx.ellipse(
      x,
      y,
      width * (0.02 + random() * 0.06),
      height * (0.004 + random() * 0.016),
      random() * Math.PI,
      0,
      Math.PI * 2
    );
    ctx.fill();
  }
  ctx.restore();

  paintGalaxy(
    ctx,
    width * 0.19,
    height * 0.7,
    Math.min(width, height) * 0.11,
    -0.62,
    5.6,
    "126, 168, 255",
    4211
  );
  paintGalaxy(
    ctx,
    width * 0.83,
    height * 0.79,
    Math.min(width, height) * 0.062,
    0.9,
    -4.8,
    "255, 176, 140",
    7789
  );
  ctx.globalCompositeOperation = "source-over";
  return canvas;
}

function paintBlackHole(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  phase: number
): void {
  ctx.save();
  ctx.translate(x, y);

  const halo = ctx.createRadialGradient(0, 0, radius, 0, 0, radius * 6.4);
  halo.addColorStop(0, "rgba(255, 186, 96, 0.3)");
  halo.addColorStop(0.28, "rgba(226, 122, 60, 0.12)");
  halo.addColorStop(1, "rgba(120, 60, 30, 0)");
  ctx.fillStyle = halo;
  ctx.beginPath();
  ctx.arc(0, 0, radius * 6.4, 0, Math.PI * 2);
  ctx.fill();

  const disk = (squash: number, width: number, alpha: number) => {
    ctx.save();
    ctx.rotate(-0.36);
    ctx.scale(1, squash);
    const spin = ctx.createConicGradient(phase, 0, 0);
    spin.addColorStop(0, `rgba(255, 244, 214, ${alpha})`);
    spin.addColorStop(0.2, `rgba(255, 176, 82, ${alpha * 0.75})`);
    spin.addColorStop(0.45, `rgba(212, 96, 40, ${alpha * 0.42})`);
    spin.addColorStop(0.7, `rgba(255, 156, 70, ${alpha * 0.68})`);
    spin.addColorStop(1, `rgba(255, 244, 214, ${alpha})`);
    ctx.strokeStyle = spin;
    ctx.lineWidth = width;
    ctx.beginPath();
    ctx.arc(0, 0, radius * 2.05, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  };

  disk(0.19, radius * 1.5, 0.85);

  const rim = ctx.createRadialGradient(0, 0, radius * 0.72, 0, 0, radius * 1.24);
  rim.addColorStop(0, "rgba(0, 0, 0, 1)");
  rim.addColorStop(0.76, "rgba(0, 0, 0, 1)");
  rim.addColorStop(0.87, "rgba(255, 214, 150, 0.92)");
  rim.addColorStop(0.95, "rgba(255, 160, 70, 0.32)");
  rim.addColorStop(1, "rgba(255, 140, 60, 0)");
  ctx.fillStyle = rim;
  ctx.beginPath();
  ctx.arc(0, 0, radius * 1.24, 0, Math.PI * 2);
  ctx.fill();

  ctx.save();
  ctx.beginPath();
  ctx.rect(-radius * 8, 0, radius * 16, radius * 8);
  ctx.clip();
  disk(0.19, radius * 1.5, 0.95);
  ctx.restore();

  ctx.fillStyle = "#000000";
  ctx.beginPath();
  ctx.arc(0, 0, radius * 0.94, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

export default function SpaceBackdrop({
  lat,
  lon,
  zoom,
  bearing,
  fadeFrom = 4.2,
  fadeTo = 6.4,
}: Props) {
  const holder = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const viewRef = useRef({ lat, lon, zoom, bearing });
  viewRef.current = { lat, lon, zoom, bearing };
  const fadeRef = useRef({ from: fadeFrom, to: fadeTo });
  fadeRef.current = { from: fadeFrom, to: fadeTo };

  useEffect(() => {
    const canvas = canvasRef.current;
    const box = holder.current;
    if (!canvas || !box) return;
    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let ratio = 1;
    let far: HTMLCanvasElement | null = null;
    let near: HTMLCanvasElement | null = null;
    let features: HTMLCanvasElement | null = null;
    let heroes: { x: number; y: number; size: number; speed: number }[] = [];
    let frame = 0;
    let visible = true;

    const build = () => {
      const rect = box.getBoundingClientRect();
      ratio = Math.min(1.5, window.devicePixelRatio || 1);
      width = Math.max(240, Math.round(rect.width * ratio));
      height = Math.max(180, Math.round(rect.height * ratio));
      canvas.width = width;
      canvas.height = height;
      far = paintStars(width, height, Math.round((width * height) / 2600), 0.9, 1301);
      near = paintStars(width, height, Math.round((width * height) / 9000), 1.5, 8677);
      features = paintFeatures(Math.round(width * 1.35), Math.round(height * 1.35));
      const random = seeded(5501);
      heroes = Array.from({ length: 52 }, () => ({
        x: random() * width,
        y: random() * height,
        size: 1.1 + random() * 2.2,
        speed: 0.5 + random() * 2.1,
      }));
    };

    const tile = (
      layer: HTMLCanvasElement,
      offsetX: number,
      offsetY: number
    ) => {
      const x = ((offsetX % width) + width) % width;
      const y = ((offsetY % height) + height) % height;
      ctx.drawImage(layer, x - width, y - height);
      ctx.drawImage(layer, x, y - height);
      ctx.drawImage(layer, x - width, y);
      ctx.drawImage(layer, x, y);
    };

    const draw = (now: number) => {
      frame = requestAnimationFrame(draw);
      const view = viewRef.current;
      const fade = fadeRef.current;
      const strength = Math.max(
        0,
        Math.min(1, (fade.to - view.zoom) / Math.max(0.1, fade.to - fade.from))
      );
      if (strength <= 0.001) {
        if (visible) {
          visible = false;
          canvas.style.opacity = "0";
        }
        return;
      }
      if (!visible) {
        visible = true;
      }
      canvas.style.opacity = strength.toFixed(3);
      if (!far || !near || !features) return;

      const time = now / 1000;
      const shiftX = (view.lon / 360) * width + (view.bearing / 360) * width;
      const shiftY = (view.lat / 90) * height * 0.34;
      const turn = (view.bearing * Math.PI) / 180;

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "#030308";
      ctx.fillRect(0, 0, width, height);

      const fx = (width * 1.35 - width) / 2;
      const fy = (height * 1.35 - height) / 2;
      ctx.save();
      ctx.translate(width / 2, height / 2);
      ctx.rotate(-turn * 0.22);
      ctx.translate(-width / 2, -height / 2);
      ctx.drawImage(
        features,
        -fx - shiftX * 0.05 - Math.sin(time * 0.03) * 6,
        -fy + shiftY * 0.05
      );
      ctx.restore();

      ctx.globalCompositeOperation = "screen";
      tile(far, -shiftX * 0.14, shiftY * 0.14);
      tile(near, -shiftX * 0.32, shiftY * 0.32);

      heroes.forEach((star, index) => {
        const pulse =
          0.45 + 0.55 * Math.abs(Math.sin(time * star.speed * 0.55 + index));
        const size = star.size * (0.7 + pulse * 0.6) * ratio;
        const x = (((star.x - shiftX * 0.32) % width) + width) % width;
        const y = (((star.y + shiftY * 0.32) % height) + height) % height;
        const glow = ctx.createRadialGradient(x, y, 0, x, y, size * 5);
        glow.addColorStop(0, `rgba(255, 255, 255, ${(pulse * 0.9).toFixed(3)})`);
        glow.addColorStop(0.3, `rgba(190, 214, 255, ${(pulse * 0.32).toFixed(3)})`);
        glow.addColorStop(1, "rgba(140, 170, 255, 0)");
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, size * 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = `rgba(255, 255, 255, ${(pulse * 0.5).toFixed(3)})`;
        ctx.lineWidth = 0.7 * ratio;
        ctx.beginPath();
        ctx.moveTo(x - size * 3.4, y);
        ctx.lineTo(x + size * 3.4, y);
        ctx.moveTo(x, y - size * 3.4);
        ctx.lineTo(x, y + size * 3.4);
        ctx.stroke();
      });

      ctx.globalCompositeOperation = "source-over";
      ctx.save();
      ctx.translate(width / 2, height / 2);
      ctx.rotate(-turn * 0.22);
      ctx.translate(-width / 2, -height / 2);
      paintBlackHole(
        ctx,
        width * 0.78 - shiftX * 0.05,
        height * 0.26 + shiftY * 0.05,
        Math.min(width, height) * 0.048,
        time * 0.55
      );
      ctx.restore();
    };

    build();
    frame = requestAnimationFrame(draw);
    const observer = new ResizeObserver(() => build());
    observer.observe(box);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={holder} className="jm-space">
      <canvas ref={canvasRef} className="jm-space-canvas" />
    </div>
  );
}
