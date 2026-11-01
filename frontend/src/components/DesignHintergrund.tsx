import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { Design, hintergrundUrl, useDesign } from "../lib/design";
import { hexFarbe, zeichnerBauen } from "../lib/liveHintergrund";

const BILDRATE = 1000 / 30;

function LiveLeinwand({ design }: { design: Design }) {
  const leinwand = useRef<HTMLCanvasElement>(null);
  const tempo = useRef(design.tempo);
  tempo.current = design.tempo;

  useEffect(() => {
    const element = leinwand.current;
    const ctx = element?.getContext("2d");
    if (!element || !ctx) return;
    const farben = { akzent: hexFarbe(design.akzent), leuchten: hexFarbe(design.leuchten), basis: hexFarbe(design.hintergrund) };
    const maus = { x: -1, y: -1 };
    const ruhig = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let zeichner = zeichnerBauen(design.live, farben, window.innerWidth, window.innerHeight, maus);
    let zeit = 0;
    let letzte = 0;
    let rahmen = 0;

    const groesseAnpassen = () => {
      zeichner = zeichnerBauen(design.live, farben, window.innerWidth, window.innerHeight, maus);
      element.width = Math.max(1, Math.round(window.innerWidth * zeichner.aufloesung));
      element.height = Math.max(1, Math.round(window.innerHeight * zeichner.aufloesung));
      zeichner.zeichnen(ctx, element.width, element.height, zeit);
    };

    const schleife = (jetzt: number) => {
      rahmen = window.requestAnimationFrame(schleife);
      if (letzte && jetzt - letzte < BILDRATE - 2) return;
      const dt = letzte ? Math.min(0.1, (jetzt - letzte) / 1000) : 0;
      letzte = jetzt;
      zeit += dt * (tempo.current / 100);
      zeichner.zeichnen(ctx, element.width, element.height, zeit);
    };

    const bewegen = (ereignis: PointerEvent) => {
      maus.x = ereignis.clientX;
      maus.y = ereignis.clientY;
    };
    const weg = () => {
      maus.x = -1;
      maus.y = -1;
    };

    groesseAnpassen();
    window.addEventListener("resize", groesseAnpassen);
    window.addEventListener("pointermove", bewegen, { passive: true });
    document.addEventListener("pointerleave", weg);
    if (!ruhig) rahmen = window.requestAnimationFrame(schleife);
    return () => {
      window.cancelAnimationFrame(rahmen);
      window.removeEventListener("resize", groesseAnpassen);
      window.removeEventListener("pointermove", bewegen);
      document.removeEventListener("pointerleave", weg);
    };
  }, [design.live, design.akzent, design.leuchten, design.hintergrund]);

  return <canvas ref={leinwand} />;
}

const VERSUCHE = 6;

function flaeche(anpassung: Design["anpassung"], quelleB: number, quelleH: number, zielB: number, zielH: number) {
  if (anpassung === "fill") return { x: 0, y: 0, b: zielB, h: zielH };
  const faktor = anpassung === "cover" ? Math.max(zielB / quelleB, zielH / quelleH) : Math.min(zielB / quelleB, zielH / quelleH);
  const b = quelleB * faktor;
  const h = quelleH * faktor;
  return { x: (zielB - b) / 2, y: (zielH - h) / 2, b, h };
}

function VideoHintergrund({ url, design }: { url: string; design: Design }) {
  const video = useRef<HTMLVideoElement>(null);
  const leinwand = useRef<HTMLCanvasElement>(null);
  const [versuch, setVersuch] = useState(0);
  const einstellungen = useRef(design);
  einstellungen.current = design;
  const weich = design.bildUnschaerfe > 0 || design.bildHelligkeit > 100;

  useEffect(() => {
    if (video.current) video.current.playbackRate = design.tempo / 100;
  }, [design.tempo, versuch]);

  useEffect(() => {
    const element = video.current;
    if (!element) return;
    let aus = false;
    let stillstand = 0;
    let letzteZeit = -1;
    const spielen = () => {
      if (aus || document.hidden || !element.paused) return;
      void element.play().catch(() => undefined);
    };
    const nachPause = () => window.setTimeout(spielen, 250);
    const ende = () => {
      element.currentTime = 0;
      spielen();
    };
    const sichtbarkeit = () => {
      if (document.hidden) element.pause();
      else spielen();
    };
    const waechter = window.setInterval(() => {
      if (aus || document.hidden) return;
      if (element.paused) {
        spielen();
        return;
      }
      if (element.currentTime === letzteZeit) {
        stillstand += 1;
        if (stillstand >= 2) {
          stillstand = 0;
          const stelle = element.currentTime;
          element.load();
          element.currentTime = stelle;
          spielen();
        }
      } else {
        stillstand = 0;
      }
      letzteZeit = element.currentTime;
    }, 4000);
    element.addEventListener("pause", nachPause);
    element.addEventListener("ended", ende);
    document.addEventListener("visibilitychange", sichtbarkeit);
    spielen();
    return () => {
      aus = true;
      window.clearInterval(waechter);
      element.removeEventListener("pause", nachPause);
      element.removeEventListener("ended", ende);
      document.removeEventListener("visibilitychange", sichtbarkeit);
    };
  }, [url, versuch]);

  useEffect(() => {
    const element = video.current;
    const ziel = leinwand.current;
    const ctx = ziel?.getContext("2d", { alpha: false });
    if (!weich || !element || !ziel || !ctx) return;
    let aus = false;
    let letzte = 0;
    let griff = 0;

    const malen = () => {
      const d = einstellungen.current;
      const radius = d.bildUnschaerfe;
      const skala = radius > 0 ? Math.max(0.08, Math.min(0.5, 4 / radius)) : Math.min(1, window.devicePixelRatio || 1);
      const breite = Math.max(2, Math.round(window.innerWidth * skala));
      const hoehe = Math.max(2, Math.round(window.innerHeight * skala));
      if (ziel.width !== breite || ziel.height !== hoehe) {
        ziel.width = breite;
        ziel.height = hoehe;
      }
      if (element.readyState < 2 || !element.videoWidth) return;
      const klein = radius * skala;
      const rand = klein * 2;
      const teil = flaeche(d.anpassung, element.videoWidth, element.videoHeight, breite + rand * 2, hoehe + rand * 2);
      ctx.filter = "none";
      ctx.fillStyle = d.hintergrund;
      ctx.fillRect(0, 0, breite, hoehe);
      ctx.filter = [d.bildHelligkeit !== 100 ? `brightness(${d.bildHelligkeit / 100})` : "", klein > 0.2 ? `blur(${klein.toFixed(2)}px)` : ""].filter(Boolean).join(" ") || "none";
      ctx.drawImage(element, teil.x - rand, teil.y - rand, teil.b, teil.h);
    };

    const schritt = (jetzt: number) => {
      if (aus) return;
      griff = window.requestAnimationFrame(schritt);
      if (jetzt - letzte < BILDRATE - 2 || element.paused) return;
      letzte = jetzt;
      malen();
    };
    const neuMalen = () => malen();
    window.addEventListener("resize", neuMalen);
    element.addEventListener("loadeddata", neuMalen);
    element.addEventListener("seeked", neuMalen);
    malen();
    griff = window.requestAnimationFrame(schritt);
    return () => {
      aus = true;
      window.cancelAnimationFrame(griff);
      window.removeEventListener("resize", neuMalen);
      element.removeEventListener("loadeddata", neuMalen);
      element.removeEventListener("seeked", neuMalen);
    };
  }, [weich, url, versuch]);

  useEffect(() => setVersuch(0), [url]);

  if (versuch >= VERSUCHE) return null;
  const abdunkeln = !weich && design.bildHelligkeit < 100 ? 1 - design.bildHelligkeit / 100 : 0;

  return (
    <>
      <video
        key={`${url}#${versuch}`}
        ref={video}
        src={url}
        className={weich ? "jd-quelle" : undefined}
        style={{ objectFit: design.anpassung }}
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        disablePictureInPicture
        disableRemotePlayback
        onLoadedMetadata={(e) => {
          e.currentTarget.playbackRate = einstellungen.current.tempo / 100;
        }}
        onError={() => {
          const naechster = versuch + 1;
          window.setTimeout(() => setVersuch(naechster), naechster >= VERSUCHE ? 0 : 1500 * naechster);
        }}
      />
      {weich && <canvas ref={leinwand} />}
      {abdunkeln > 0 && <div className="jd-dunkel" style={{ opacity: abdunkeln }} />}
    </>
  );
}

export default function DesignHintergrund() {
  const d = useDesign();
  const [kaputt, setKaputt] = useState("");
  const datei = d.hintergrundArt === "bild" || d.hintergrundArt === "video";
  const url = datei ? hintergrundUrl(d.quelle) : "";

  if (d.hintergrundArt === "farbe") return null;
  if (datei && (!url || kaputt === url)) return null;

  const video = d.hintergrundArt === "video";
  const unschaerfe = video ? 0 : d.bildUnschaerfe + (d.hintergrundArt === "live" && d.live === "nebel" ? 6 : 0);
  const helligkeit = video ? 100 : d.bildHelligkeit;
  const medien: CSSProperties = {
    filter: [helligkeit !== 100 ? `brightness(${helligkeit / 100})` : "", unschaerfe ? `blur(${unschaerfe}px)` : ""].filter(Boolean).join(" ") || undefined,
    transform: unschaerfe ? `scale(${1 + unschaerfe / 150})` : undefined,
  };

  return (
    <div className={`jd-hintergrund ${video ? "jd-video" : ""}`} aria-hidden="true">
      <div className="jd-medien" style={medien}>
        {d.hintergrundArt === "bild" && (
          <img key={url} src={url} alt="" draggable={false} style={{ objectFit: d.anpassung }} onError={() => setKaputt(url)} />
        )}
        {video && <VideoHintergrund url={url} design={d} />}
        {d.hintergrundArt === "live" && <LiveLeinwand design={d} />}
      </div>
      {d.abdunkeln > 0 && <div className="jd-abdunkeln" style={{ opacity: d.abdunkeln / 100 }} />}
    </div>
  );
}
