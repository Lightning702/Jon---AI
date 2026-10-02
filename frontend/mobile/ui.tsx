import React, {useEffect, useId, useRef, useState} from "react";
import {createPortal} from "react-dom";
import {AnimatePresence, animate, motion, PanInfo} from "framer-motion";
import {ArrowLeft, Check, ChevronDown, ChevronRight, Copy, Download, Image as ImageIcon, LoaderCircle, TriangleAlert, X} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {binary, call, enc, haptic, saveFile} from "./bridge";

export const spring = {type: "spring", stiffness: 420, damping: 38, mass: .9} as const;
export const softSpring = {type: "spring", stiffness: 300, damping: 32} as const;
export const errorText = (error: unknown) => error instanceof Error ? error.message : "Das hat nicht funktioniert.";

export function overlayHost() {return document.getElementById("overlay-host") || document.body;}

export const dictation = {target: "chat"};

export function useDictation(target: string, voice: any, onText: (text: string) => void) {
  const seq = useRef(voice?.seq || 0);
  useEffect(() => {
    if (voice?.mode === "dictate" && voice.transcript && voice.seq && voice.seq !== seq.current) {
      seq.current = voice.seq;
      if (dictation.target === target) onText(voice.transcript);
    }
  }, [voice]);
  return () => {dictation.target = target; haptic("tap"); return call("voice", {mode: "dictate"});};
}

const backHandlers: {fn: () => void}[] = [];
export function useBackHandler(active: boolean, fn: () => void) {
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    if (!active) return;
    const handler = {fn: () => ref.current()};
    backHandlers.push(handler);
    return () => {const index = backHandlers.indexOf(handler); if (index >= 0) backHandlers.splice(index, 1);};
  }, [active]);
}
export function handleBack() {
  const handler = backHandlers[backHandlers.length - 1];
  if (!handler) return false;
  handler.fn();
  return true;
}

export function MenuLines() {
  return <svg className="menu-lines" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M4 8.5h16"/><path d="M4 15.5h10"/></svg>;
}

export function WaveIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round"><path d="M4 10v4"/><path d="M8.5 6.5v11"/><path d="M13 9v6"/><path d="M17.5 5v14"/><path d="M21 10.5v3"/></svg>;
}

export function DashedChat() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" strokeDasharray="3.2 3.4"/></svg>;
}

export function JonMark({glow = true}: {glow?: boolean}) {
  const id = useId().replace(/:/g, "");
  return <svg viewBox="0 0 108 108" fill="none">
    <defs>
      <linearGradient id={`r${id}`} x1="22" y1="26" x2="88" y2="86" gradientUnits="userSpaceOnUse"><stop stopColor="#5EE7FF"/><stop offset=".5" stopColor="#3B6CFF"/><stop offset="1" stopColor="#A35CFF"/></linearGradient>
      {glow && <filter id={`g${id}`} x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3.2"/></filter>}
    </defs>
    {glow && <circle cx="54" cy="54" r="30" stroke={`url(#r${id})`} strokeWidth="7" opacity=".55" filter={`url(#g${id})`}/>}
    <circle cx="54" cy="54" r="30" stroke={`url(#r${id})`} strokeWidth="3.4" opacity=".5"/>
    <path d="M78.2 71.6A30 30 0 0 1 24.4 49.6" stroke={`url(#r${id})`} strokeWidth="5.4" strokeLinecap="round"/>
    <g stroke="currentColor" strokeWidth="4.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M43 44.5V57.5A5.5 5.5 0 0 1 32 57.5"/>
      <circle cx="54.5" cy="57" r="6"/>
      <path d="M66 51V63M66 57A5.5 5.5 0 0 1 77 57V63"/>
    </g>
  </svg>;
}

export function Orb({size = 170, level = 0, phase = "idle", onClick}: {size?: number; level?: number; phase?: string; onClick?: () => void}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const live = useRef({level, phase});
  live.current = {level, phase};
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    canvas.width = Math.round(size * dpr);
    canvas.height = Math.round(size * dpr);
    let frame = 0, running = true, visible = true, smooth = 0, energy = .1, spin = 0, last = performance.now();
    const c = size / 2;
    const draw = (now: number) => {
      frame = 0;
      const dt = Math.min(.05, (now - last) / 1000);
      last = now;
      const t = now / 1000;
      const {level: lv, phase: ph} = live.current;
      smooth += (lv - smooth) * .3;
      const target = ph === "thinking" ? .55 : ph === "speaking" ? .35 + smooth * .9 : ph === "listening" ? .18 + smooth * 1.3 : ph === "error" || ph === "offline" ? .05 : .14;
      energy += (target - energy) * .08;
      spin += dt * (ph === "thinking" ? 1.9 : .45 + energy);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, size, size);
      const R = size * .29 * (1 + energy * .09 + Math.sin(t * 1.7) * .012);
      let g = ctx.createRadialGradient(c, c, R * .55, c, c, size * .5);
      g.addColorStop(0, `rgba(59,120,255,${.34 + energy * .35})`);
      g.addColorStop(.5, `rgba(96,70,255,${.12 + energy * .16})`);
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, size, size);
      g = ctx.createRadialGradient(c - R * .38, c - R * .42, R * .08, c, c, R);
      g.addColorStop(0, "#2552c8");
      g.addColorStop(.5, "#0b1d58");
      g.addColorStop(1, "#030714");
      ctx.beginPath();
      ctx.arc(c, c, R, 0, Math.PI * 2);
      ctx.fillStyle = g;
      ctx.fill();
      ctx.save();
      ctx.beginPath();
      ctx.arc(c, c, R * .985, 0, Math.PI * 2);
      ctx.clip();
      ctx.globalCompositeOperation = "lighter";
      for (let k = 0; k < 4; k++) {
        const amp = R * (.08 + energy * .34) * (1 - k * .16);
        const freq = 1.6 + k * .55;
        const speed = (ph === "speaking" ? 3.4 : 1.4) + k * .6;
        const lg = ctx.createLinearGradient(c - R, c, c + R, c);
        lg.addColorStop(0, "rgba(56,211,255,0)");
        lg.addColorStop(.3, k % 2 ? "rgba(155,92,255,.9)" : "rgba(56,211,255,.95)");
        lg.addColorStop(.7, "rgba(59,108,246,.9)");
        lg.addColorStop(1, "rgba(155,92,255,0)");
        ctx.strokeStyle = lg;
        ctx.lineWidth = 1.4 + energy * 1.6 - k * .15;
        ctx.globalAlpha = .75 - k * .13;
        ctx.beginPath();
        for (let x = -R; x <= R; x += 2) {
          const n = x / R;
          const env = Math.cos(n * Math.PI / 2);
          const y = c + R * .12 + Math.sin(n * Math.PI * freq + t * speed + k * 1.3) * amp * env + (k - 1.5) * R * .05;
          if (x === -R) ctx.moveTo(c + x, y); else ctx.lineTo(c + x, y);
        }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      g = ctx.createRadialGradient(c, c + R * .95, R * .1, c, c + R * .7, R * .9);
      g.addColorStop(0, `rgba(80,200,255,${.35 + energy * .3})`);
      g.addColorStop(1, "rgba(80,200,255,0)");
      ctx.fillStyle = g;
      ctx.fillRect(c - R, c - R, R * 2, R * 2);
      ctx.restore();
      const conic = ctx.createConicGradient(spin, c, c);
      conic.addColorStop(0, "rgba(94,231,255,1)");
      conic.addColorStop(.25, "rgba(59,108,255,.9)");
      conic.addColorStop(.5, "rgba(163,92,255,.85)");
      conic.addColorStop(.72, "rgba(59,108,255,.15)");
      conic.addColorStop(1, "rgba(94,231,255,1)");
      ctx.strokeStyle = conic;
      ctx.shadowColor = "rgba(70,150,255,.9)";
      ctx.shadowBlur = 16 + energy * 26;
      ctx.lineWidth = 2.2 + energy * 2.6;
      ctx.beginPath();
      ctx.arc(c, c, R, 0, Math.PI * 2);
      ctx.stroke();
      ctx.lineWidth = 1;
      ctx.shadowBlur = 8;
      for (let k = 0; k < 2; k++) {
        ctx.globalAlpha = .28 + energy * .3;
        ctx.beginPath();
        ctx.ellipse(c, c, R * (1.24 + k * .1), R * (.36 + k * .08), (k ? -.5 : .42) + Math.sin(t * .3 + k) * .08, spin * (k ? -.6 : .4), spin * (k ? -.6 : .4) + Math.PI * 1.35);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      ctx.shadowBlur = 0;
      if (running && visible) frame = requestAnimationFrame(draw);
    };
    const start = () => {if (!frame && running && visible && !document.hidden) {last = performance.now(); frame = requestAnimationFrame(draw);}};
    const stop = () => {if (frame) cancelAnimationFrame(frame); frame = 0;};
    const observer = new IntersectionObserver(entries => {visible = entries.some(e => e.isIntersecting); if (visible) start(); else stop();});
    observer.observe(canvas);
    const onVisibility = () => {if (document.hidden) stop(); else start();};
    document.addEventListener("visibilitychange", onVisibility);
    start();
    return () => {running = false; stop(); observer.disconnect(); document.removeEventListener("visibilitychange", onVisibility);};
  }, [size]);
  return <canvas ref={ref} onClick={onClick} style={{width: size, height: size, display: "block"}}/>;
}

export function Circle({children, label, onClick, className = ""}: {children: React.ReactNode; label: string; onClick: () => void; className?: string}) {
  return <button aria-label={label} className={`circle ${className}`} onClick={() => {haptic("tick"); onClick();}}>{children}</button>;
}

export function PageHeader({title, subtitle, onBack, right, onTitle}: {title: string; subtitle?: React.ReactNode; onBack: () => void; right?: React.ReactNode; onTitle?: () => void}) {
  return <header className="page-header">
    <Circle label="Zurück" onClick={onBack}><ArrowLeft/></Circle>
    <div className="title">{onTitle ? <button onClick={onTitle} style={{color: "var(--fg)", fontSize: 19, gap: 6}}><strong>{title}</strong><ChevronDown size={18}/></button> : <strong>{title}</strong>}{subtitle}</div>
    <div className="slot">{right}</div>
  </header>;
}

export function Sheet({open, title, onClose, children, footer}: {open: boolean; title: React.ReactNode; onClose: () => void; children: React.ReactNode; footer?: React.ReactNode}) {
  const body = useRef<HTMLDivElement>(null);
  useBackHandler(open, onClose);
  function end(_: unknown, info: PanInfo) {if (info.offset.y > 110 || info.velocity.y > 600) onClose();}
  return createPortal(<AnimatePresence>{open && <motion.div key="scrim" className="scrim" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} transition={{duration: .2}} onClick={onClose}>
    <motion.section className="sheet" role="dialog" initial={{y: "100%"}} animate={{y: 0}} exit={{y: "100%"}} transition={spring} drag="y" dragConstraints={{top: 0, bottom: 0}} dragElastic={{top: .04, bottom: .9}} dragListener={true} onDragEnd={end} onClick={e => e.stopPropagation()} onPointerDownCapture={e => {const el = body.current; if (el && el.contains(e.target as Node) && el.scrollTop > 0) e.stopPropagation();}}>
      <div className="sheet-handle"/>
      <header><h2>{title}</h2><Circle label="Schließen" onClick={onClose}><X/></Circle></header>
      <div className="sheet-body" ref={body}>{children}</div>
      {footer}
    </motion.section>
  </motion.div>}</AnimatePresence>, overlayHost());
}

export function Popover({open, onClose, children, className = ""}: {open: boolean; onClose: () => void; children: React.ReactNode; className?: string}) {
  useBackHandler(open, onClose);
  return createPortal(<AnimatePresence>{open && <motion.div key="pop" className="popover-layer" onClick={onClose} initial={{opacity: 1}} exit={{opacity: 1}}>
    <motion.div className={`popover ${className}`} onClick={e => e.stopPropagation()} initial={{opacity: 0, scale: .82, y: -8}} animate={{opacity: 1, scale: 1, y: 0}} exit={{opacity: 0, scale: .9, y: -6}} transition={{type: "spring", stiffness: 520, damping: 34}}>{children}</motion.div>
  </motion.div>}</AnimatePresence>, overlayHost());
}

export function Modal({open, onClose, children, className = ""}: {open: boolean; onClose: () => void; children: React.ReactNode; className?: string}) {
  useBackHandler(open, onClose);
  return createPortal(<AnimatePresence>{open && <motion.div key="modal" className="modal-layer" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} onClick={onClose}>
    <motion.div className={`modal ${className}`} onClick={e => e.stopPropagation()} initial={{y: 60, opacity: 0, scale: .96}} animate={{y: 0, opacity: 1, scale: 1}} exit={{y: 40, opacity: 0}} transition={spring}>{children}</motion.div>
  </motion.div>}</AnimatePresence>, overlayHost());
}

export class Fehlergrenze extends React.Component<{children: React.ReactNode; zurueck?: () => void}, {fehler: string}> {
  state = {fehler: ""};
  static getDerivedStateFromError(e: unknown) {return {fehler: e instanceof Error ? e.message : "Unbekannter Fehler"};}
  render() {
    if (!this.state.fehler) return this.props.children;
    return <div className="empty fehlergrenze"><div className="box"><TriangleAlert/></div><h2>Hier ist etwas schiefgelaufen</h2><p>{this.state.fehler}</p>
      <button className="btn soft" onClick={() => this.props.zurueck ? this.props.zurueck() : location.reload()}>{this.props.zurueck ? "Zurück" : "Neu laden"}</button>
    </div>;
  }
}

export function Zaehler({wert, format = (n: number) => Math.round(n).toLocaleString("de-DE")}: {wert: number; format?: (n: number) => string}) {
  const [anzeige, setAnzeige] = useState(0);
  const vorher = useRef(0);
  useEffect(() => {
    const ziel = Number.isFinite(wert) ? wert : 0;
    const steuerung = animate(vorher.current, ziel, {duration: .9, ease: [.2, .8, .2, 1], onUpdate: setAnzeige});
    vorher.current = ziel;
    return () => steuerung.stop();
  }, [wert]);
  return <>{format(anzeige)}</>;
}

export function Busy({text = "Wird geladen …"}: {text?: string}) {return <div className="busy"><LoaderCircle className="spin"/>{text}</div>;}
export function Empty({icon, title, text}: {icon: React.ReactNode; title: string; text?: string}) {return <div className="empty"><div className="box">{icon}</div><h2>{title}</h2>{text && <p>{text}</p>}</div>;}
export function Field({label, value, onChange, type = "text", multiline = false, placeholder, autoFocus}: {label: string; value: string; onChange: (v: string) => void; type?: string; multiline?: boolean; placeholder?: string; autoFocus?: boolean}) {
  return <label className="field"><span>{label}</span>{multiline ? <textarea value={value} placeholder={placeholder} autoFocus={autoFocus} onChange={e => onChange(e.target.value)} rows={4}/> : <input type={type} value={value} placeholder={placeholder} autoFocus={autoFocus} autoComplete="off" onChange={e => onChange(e.target.value)}/>}</label>;
}
export function Switch({on, onChange}: {on: boolean; onChange: (v: boolean) => void}) {
  return <button role="switch" aria-checked={on} className={`switch ${on ? "on" : ""}`} onClick={e => {e.stopPropagation(); haptic("tick"); onChange(!on);}}><i/></button>;
}
export function Row({icon, label, detail, onClick, tone = "", value, right, chevron = true}: {icon?: React.ReactNode; label: React.ReactNode; detail?: React.ReactNode; onClick?: () => void; tone?: string; value?: React.ReactNode; right?: React.ReactNode; chevron?: boolean}) {
  return <button className={`row-btn ${tone}`} onClick={() => {haptic("tick"); onClick?.();}}>{icon}<span>{label}{detail !== undefined && detail !== "" && <small>{detail}</small>}</span>{value !== undefined && <span className="value">{value}</span>}{right}{!right && chevron && onClick && <ChevronRight className="chev"/>}</button>;
}

export function useLoad<T>(load: () => Promise<T>, dependencies: unknown[] = []) {
  const [data, setData] = useState<T | null>(null), [error, setError] = useState(""), [busy, setBusy] = useState(true);
  const loader = useRef(load);
  loader.current = load;
  async function refresh() {setBusy(true); setError(""); try {setData(await loader.current());} catch (e) {setError(errorText(e));} finally {setBusy(false);}}
  useEffect(() => {
    let live = true;
    setBusy(true);
    setError("");
    loader.current().then(v => {if (live) setData(v);}).catch(e => {if (live) setError(errorText(e));}).finally(() => {if (live) setBusy(false);});
    return () => {live = false;};
  }, dependencies);
  return {data, error, busy, refresh, setData};
}

const pictures = new Map<string, string>();
export function imageUrl(path: string) {return path.startsWith("/api/") ? path : `/api/mobile/preview?path=${enc(path)}`;}
export function showImage(src: string, name = "Jon-Bild.jpg") {window.dispatchEvent(new CustomEvent("jon-bild", {detail: {src, name}}));}

export function Lightbox() {
  const [bild, setBild] = useState<{src: string; name: string} | null>(null);
  const [zoom, setZoom] = useState(1), [pos, setPos] = useState({x: 0, y: 0});
  const zeiger = useRef(new Map<number, {x: number; y: number}>());
  const start = useRef({abstand: 0, zoom: 1, x: 0, y: 0, px: 0, py: 0, zeit: 0});
  useEffect(() => {
    const h = (e: Event) => {setBild((e as CustomEvent).detail); setZoom(1); setPos({x: 0, y: 0});};
    window.addEventListener("jon-bild", h);
    return () => window.removeEventListener("jon-bild", h);
  }, []);
  const schliessen = () => setBild(null);
  useBackHandler(!!bild, schliessen);
  const abstand = () => {const p = [...zeiger.current.values()]; return p.length < 2 ? 0 : Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);};
  return createPortal(<AnimatePresence>{bild && <motion.div key="lb" className="lightbox" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} style={{touchAction: "none"}}
    onPointerDown={e => {
      zeiger.current.set(e.pointerId, {x: e.clientX, y: e.clientY});
      const jetzt = Date.now();
      if (zeiger.current.size === 1 && jetzt - start.current.zeit < 280) {haptic("tick"); if (zoom > 1) {setZoom(1); setPos({x: 0, y: 0});} else setZoom(2.6);}
      start.current = {abstand: abstand(), zoom, x: pos.x, y: pos.y, px: e.clientX, py: e.clientY, zeit: jetzt};
    }}
    onPointerMove={e => {
      if (!zeiger.current.has(e.pointerId)) return;
      zeiger.current.set(e.pointerId, {x: e.clientX, y: e.clientY});
      if (zeiger.current.size >= 2 && start.current.abstand) setZoom(Math.min(5, Math.max(1, start.current.zoom * abstand() / start.current.abstand)));
      else setPos({x: start.current.x + e.clientX - start.current.px, y: start.current.y + e.clientY - start.current.py});
    }}
    onPointerUp={e => {
      zeiger.current.delete(e.pointerId);
      if (zeiger.current.size === 0 && zoom <= 1.02) {if (Math.abs(pos.y) > 140) schliessen(); else setPos({x: 0, y: 0});}
      if (zeiger.current.size === 1) {const p = [...zeiger.current.values()][0]; start.current = {...start.current, x: pos.x, y: pos.y, px: p.x, py: p.y, zoom, abstand: 0};}
    }}
    onPointerCancel={e => zeiger.current.delete(e.pointerId)}>
    <motion.img src={bild.src} alt="" initial={{scale: .85}} animate={{scale: zoom, x: pos.x, y: pos.y, opacity: zoom <= 1.02 ? 1 - Math.min(.5, Math.abs(pos.y) / 500) : 1}} transition={zeiger.current.size ? {duration: 0} : spring} draggable={false}/>
    <div className="lightbox-bar">
      <button aria-label="Schließen" onClick={schliessen}><X/></button>
      <span/>
      <button aria-label="Speichern" onClick={() => {const [kopf, daten] = bild.src.split(","); call("save", {name: bild.name, mime: /data:(.*?);/.exec(kopf)?.[1] || "image/jpeg", data: daten}).then(() => haptic("success")).catch(() => {});}}><Download/></button>
    </div>
  </motion.div>}</AnimatePresence>, overlayHost());
}

export function PiImage({path, alt = "", onClick, zoom = false}: {path: string; alt?: string; onClick?: () => void; zoom?: boolean}) {
  const [source, setSource] = useState(pictures.get(path) || ""), [failed, setFailed] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (pictures.has(path)) {setSource(pictures.get(path)!); return;}
    let live = true;
    const observer = new IntersectionObserver(entries => {
      if (!entries.some(e => e.isIntersecting)) return;
      observer.disconnect();
      binary(imageUrl(path)).then(result => {
        if (!String(result.mime).startsWith("image/")) throw new Error("Kein Bild");
        const value = `data:${result.mime};base64,${result.data}`;
        if (pictures.size > 80) pictures.delete(pictures.keys().next().value!);
        pictures.set(path, value);
        if (live) setSource(value);
      }).catch(() => {if (live) setFailed(true);});
    }, {rootMargin: "300px"});
    if (ref.current) observer.observe(ref.current);
    return () => {live = false; observer.disconnect();};
  }, [path]);
  return <div ref={ref} className="pi-image" onClick={onClick || (zoom && source ? () => {haptic("tap"); showImage(source, `${(alt || "Jon-Bild").slice(0, 40).replace(/[^\w äöüÄÖÜß-]/g, "")}.jpg`);} : undefined)}>{source ? <img src={source} alt={alt}/> : failed ? <ImageIcon/> : <LoaderCircle className="spin"/>}</div>;
}

export async function saveStudio(name: string) {
  const data = await binary(`/api/studio/file/${enc(name)}`);
  return call("save", {...data, name});
}

function CodeBlock({children, lang, notify}: {children: React.ReactNode; lang: string; notify: (s: string) => void}) {
  const ref = useRef<HTMLElement>(null);
  const [done, setDone] = useState(false);
  return <pre><div className="code-head"><span>{lang || "Code"}</span><button onClick={() => call("copy", {text: ref.current?.innerText || ""}).then(() => {setDone(true); haptic("success"); setTimeout(() => setDone(false), 1500);}).catch(e => notify(errorText(e)))}>{done ? <Check/> : <Copy/>}{done ? "Kopiert" : "Kopieren"}</button></div><code ref={ref}>{children}</code></pre>;
}

export function Markdown({text, notify}: {text: string; notify: (s: string) => void}) {
  return <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{
    a: ({href, children}) => <button className="text-link" onClick={() => {
      if (href?.startsWith("/home/") || href?.startsWith("/api/dateien/inhalt")) {
        const path = href.startsWith("/api/") ? new URL(href, "https://jon.local").searchParams.get("pfad") || "" : href;
        notify("Download beginnt");
        saveFile(path).then(() => notify("In Downloads/Jon gespeichert.")).catch(e => notify(errorText(e)));
      } else call("copy", {text: href || ""}).then(() => notify("Link kopiert.")).catch(e => notify(errorText(e)));
    }}>{children}</button>,
    img: ({src, alt}) => src?.startsWith("/api/") || src?.startsWith("/home/") ? <PiImage path={src} alt={alt}/> : <span>{alt || "Bild"}</span>,
    pre: ({children}) => {
      const child = React.Children.toArray(children)[0] as React.ReactElement<{className?: string; children?: React.ReactNode}> | undefined;
      const lang = /language-(\w+)/.exec(child?.props?.className || "")?.[1] || "";
      return <CodeBlock lang={lang} notify={notify}>{child?.props?.children ?? children}</CodeBlock>;
    }
  }}>{text}</ReactMarkdown></div>;
}
