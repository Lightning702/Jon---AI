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

export default function DesignHintergrund() {
  const d = useDesign();
  const video = useRef<HTMLVideoElement>(null);
  const [kaputt, setKaputt] = useState("");
  const datei = d.hintergrundArt === "bild" || d.hintergrundArt === "video";
  const url = datei ? hintergrundUrl(d.quelle) : "";

  useEffect(() => {
    if (video.current) video.current.playbackRate = d.tempo / 100;
  }, [d.tempo, url]);

  if (d.hintergrundArt === "farbe") return null;
  if (datei && (!url || kaputt === url)) return null;

  const unschaerfe = d.bildUnschaerfe + (d.hintergrundArt === "live" && d.live === "nebel" ? 6 : 0);
  const medien: CSSProperties = {
    filter: [d.bildHelligkeit !== 100 ? `brightness(${d.bildHelligkeit / 100})` : "", unschaerfe ? `blur(${unschaerfe}px)` : ""].filter(Boolean).join(" ") || undefined,
    transform: unschaerfe ? `scale(${1 + unschaerfe / 150})` : undefined,
  };
  const passend: CSSProperties = { objectFit: d.anpassung };

  return (
    <div className="jd-hintergrund" aria-hidden="true">
      <div className="jd-medien" style={medien}>
        {d.hintergrundArt === "bild" && (
          <img key={url} src={url} alt="" draggable={false} style={passend} onError={() => setKaputt(url)} />
        )}
        {d.hintergrundArt === "video" && (
          <video
            key={url}
            ref={video}
            src={url}
            style={passend}
            autoPlay
            loop
            muted
            playsInline
            disablePictureInPicture
            onLoadedMetadata={(e) => {
              e.currentTarget.playbackRate = d.tempo / 100;
            }}
            onError={() => setKaputt(url)}
          />
        )}
        {d.hintergrundArt === "live" && <LiveLeinwand design={d} />}
      </div>
      {d.abdunkeln > 0 && <div className="jd-abdunkeln" style={{ opacity: d.abdunkeln / 100 }} />}
    </div>
  );
}
