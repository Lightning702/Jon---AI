import { useEffect, useRef, useState } from "react";
import SpaceBackdrop from "./SpaceBackdrop";

interface Props {
  lat: number;
  lon: number;
  zoom: number;
  bearing: number;
  fadeFrom?: number;
  fadeTo?: number;
}

const ECKEN = `#version 300 es
const vec2 ecken[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
void main() {
  gl_Position = vec4(ecken[gl_VertexID], 0.0, 1.0);
}`;

const KOPF = `#version 300 es
precision highp float;
out vec4 farbe;
const vec3 LOCH = vec3(0.4472, 0.2236, -0.8660);
const float ABSTAND = 46.0;
const float BEREICH = 0.4;
`;

const RAUSCHEN = `
float hash13(vec3 p) {
  p = fract(p * 0.1031);
  p += dot(p, p.zyx + 31.32);
  return fract((p.x + p.y) * p.z);
}

vec3 hash33(vec3 p) {
  p = fract(p * vec3(0.1031, 0.1030, 0.0973));
  p += dot(p, p.yxz + 33.33);
  return fract((p.xxy + p.yxx) * p.zyx);
}

float rauschen(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash13(i);
  float b = hash13(i + vec3(1.0, 0.0, 0.0));
  float c = hash13(i + vec3(0.0, 1.0, 0.0));
  float d = hash13(i + vec3(1.0, 1.0, 0.0));
  float e = hash13(i + vec3(0.0, 0.0, 1.0));
  float g = hash13(i + vec3(1.0, 0.0, 1.0));
  float h = hash13(i + vec3(0.0, 1.0, 1.0));
  float k = hash13(i + vec3(1.0, 1.0, 1.0));
  return mix(mix(mix(a, b, f.x), mix(c, d, f.x), f.y), mix(mix(e, g, f.x), mix(h, k, f.x), f.y), f.z);
}

float fbm(vec3 p) {
  float summe = 0.0;
  float staerke = 0.5;
  for (int i = 0; i < 5; i++) {
    summe += staerke * rauschen(p);
    p = p * 2.03 + vec3(1.7, 9.2, 3.1);
    staerke *= 0.5;
  }
  return summe;
}

float fbm3(vec3 p) {
  return 0.5 * rauschen(p) + 0.25 * rauschen(p * 2.03 + 1.7) + 0.125 * rauschen(p * 4.1 + 5.3);
}
`;

const STERNE = `
vec3 sternfarbe(float t) {
  vec3 rot = vec3(1.0, 0.66, 0.42);
  vec3 weiss = vec3(1.0, 0.96, 0.9);
  vec3 blau = vec3(0.66, 0.78, 1.0);
  return t < 0.5 ? mix(rot, weiss, t * 2.0) : mix(weiss, blau, (t - 0.5) * 2.0);
}

vec3 sterne(vec3 d, float pixel, float zeit) {
  vec3 summe = vec3(0.0);
  for (int stufe = 0; stufe < 3; stufe++) {
    float dichte = stufe == 0 ? 15.0 : stufe == 1 ? 29.0 : 54.0;
    vec3 zelle = floor(d * dichte);
    vec3 zufall = hash33(zelle);
    float anteil = stufe == 0 ? 0.62 : stufe == 1 ? 0.68 : 0.74;
    if (hash13(zelle + 17.0) < anteil) continue;
    vec3 mitte = normalize((zelle + 0.2 + 0.6 * zufall) / dichte);
    float abstand = length(mitte - d) / max(pixel, 1e-5);
    float hell = pow(zufall.x, 4.0) * (stufe == 0 ? 4.5 : stufe == 1 ? 1.6 : 0.7) + (stufe == 2 ? 0.05 : 0.12);
    float funkeln = 0.82 + 0.18 * sin(zeit * (0.7 + zufall.y * 2.6) + zufall.z * 40.0);
    float kern = exp(-abstand * abstand * 1.6);
    float schein = stufe == 0 ? exp(-abstand * 0.7) * 0.06 * hell : 0.0;
    summe += sternfarbe(zufall.y) * (kern * hell + schein) * funkeln;
  }
  return summe;
}
`;

const HIMMEL = `

vec3 milchstrasse(vec3 d) {
  vec3 achse = normalize(vec3(0.18, 0.93, 0.32));
  vec3 zentrum = normalize(cross(achse, vec3(0.3, -0.2, 1.0)));
  float breite = dot(d, achse);
  float nah = max(0.0, dot(d, zentrum));
  float band = exp(-breite * breite / (0.018 + 0.05 * nah * nah));
  float wolken = fbm(d * 5.5);
  float fein = fbm(d * 17.0 + 3.0);
  float staub = smoothstep(0.42, 0.72, fbm(d * 10.0 + 4.0)) * exp(-breite * breite / 0.0045);
  vec3 kalt = vec3(0.32, 0.42, 0.72);
  vec3 warm = vec3(1.0, 0.76, 0.5);
  vec3 licht = mix(kalt, warm, pow(nah, 2.5)) * band * (0.2 + 0.9 * wolken + 0.35 * fein) * (0.3 + 1.6 * pow(nah, 5.0));
  return licht * (1.0 - 0.88 * staub) * 0.55;
}

vec3 nebel(vec3 d) {
  float a = fbm(d * 2.3 + 11.0);
  float b = fbm(d * 3.6 - 5.0);
  return vec3(0.42, 0.16, 0.5) * smoothstep(0.56, 0.86, a) * 0.1 + vec3(0.08, 0.3, 0.42) * smoothstep(0.6, 0.9, b) * 0.08;
}

vec3 galaxie(vec3 d, vec3 ziel, vec3 oben, float groesse, float neigung, float lage, float arme, float windung, vec3 ton, float art) {
  vec3 g = normalize(ziel);
  if (dot(d, g) < cos(groesse * 3.2)) return vec3(0.0);
  vec3 e1 = normalize(cross(oben, g));
  vec3 e2 = cross(g, e1);
  vec2 uv = vec2(dot(d, e1), dot(d, e2)) / groesse;
  float c = cos(lage), s = sin(lage);
  uv = mat2(c, -s, s, c) * uv;
  uv.y /= max(0.06, cos(neigung));
  float r = length(uv);
  float w = atan(uv.y, uv.x);
  float rand = smoothstep(1.7, 0.7, r);
  float kern = exp(-r * r * 60.0) * 2.4 + exp(-r * 8.0) * 0.55;
  if (art > 0.5) {
    return vec3(1.0, 0.86, 0.68) * (exp(-r * 3.0) * 0.8 + kern * 0.6) * rand * 0.75;
  }
  float scheibe = exp(-r * 2.4);
  float spirale = pow(0.5 + 0.5 * cos(arme * w - windung * log(r + 0.035)), 2.2);
  float flocken = fbm(vec3(uv * 6.5, art * 13.0 + groesse * 40.0));
  float staub = smoothstep(0.5, 0.8, fbm(vec3(uv * 10.0 + 3.0, groesse * 70.0))) * smoothstep(0.04, 0.3, r);
  vec3 arm = mix(vec3(0.55, 0.68, 1.0), ton, 0.35) * (spirale * 0.9 + 0.12) * scheibe * (0.45 + flocken);
  float knoten = step(0.982, hash13(floor(vec3(uv * 36.0, groesse * 91.0)))) * spirale * scheibe * 2.6;
  float band = neigung > 1.3 ? smoothstep(0.08, 0.0, abs(uv.y * cos(neigung)) * 4.0) * smoothstep(0.05, 0.4, r) : 0.0;
  vec3 licht = arm * (1.0 - 0.7 * staub) + vec3(1.0, 0.86, 0.6) * kern + vec3(1.0, 0.45, 0.62) * knoten;
  return licht * rand * (1.0 - 0.85 * band) * 0.9;
}

vec3 galaxien(vec3 d) {
  vec3 summe = vec3(0.0);
  summe += galaxie(d, vec3(-0.55, 0.28, -0.79), vec3(0.2, 1.0, 0.1), 0.11, 1.3, 0.62, 2.0, 5.2, vec3(1.0, 0.85, 0.7), 0.0);
  summe += galaxie(d, vec3(0.08, -0.32, -0.94), vec3(0.0, 1.0, 0.0), 0.05, 0.25, 1.9, 2.0, 6.0, vec3(0.7, 0.8, 1.0), 0.0);
  summe += galaxie(d, vec3(0.83, -0.12, -0.55), vec3(0.1, 1.0, 0.0), 0.03, 1.45, -0.3, 3.0, 4.0, vec3(1.0, 0.9, 0.75), 0.0);
  summe += galaxie(d, vec3(-0.2, 0.62, -0.76), vec3(0.0, 1.0, 0.3), 0.016, 0.9, 2.5, 2.0, 5.0, vec3(0.8, 0.85, 1.0), 0.0);
  summe += galaxie(d, vec3(0.32, 0.55, -0.77), vec3(0.0, 1.0, 0.0), 0.012, 0.6, 0.4, 0.0, 0.0, vec3(1.0), 1.0);
  summe += galaxie(d, vec3(-0.85, -0.3, -0.43), vec3(0.0, 1.0, 0.0), 0.022, 0.55, 1.1, 4.0, 4.6, vec3(0.75, 0.82, 1.0), 0.0);
  summe += galaxie(d, vec3(0.6, 0.1, 0.79), vec3(0.0, 1.0, 0.0), 0.05, 1.1, 0.3, 2.0, 5.0, vec3(1.0, 0.85, 0.75), 0.0);
  return summe * 1.5;
}
`;

const BACKEN = `${KOPF}
uniform vec2 uGroesse;
uniform float uKodiert;
${RAUSCHEN}
${HIMMEL}
void main() {
  vec2 uv = gl_FragCoord.xy / uGroesse;
  float laenge = (uv.x - 0.5) * 6.2831853;
  float breite = (uv.y - 0.5) * 3.1415927;
  vec3 d = vec3(cos(breite) * cos(laenge), sin(breite), cos(breite) * sin(laenge));
  vec3 c = milchstrasse(d) + nebel(d) + galaxien(d);
  farbe = uKodiert > 0.5 ? vec4(sqrt(clamp(c / 8.0, 0.0, 1.0)), 1.0) : vec4(c, 1.0);
}`;

const KOSMOS = `${KOPF}
uniform vec2 uAufloesung;
uniform float uZeit;
uniform vec3 uBlick;
uniform float uSicht;
uniform float uKodiert;
uniform sampler2D uHimmel;
uniform float uPixel;
${RAUSCHEN}
${STERNE}

vec3 himmel(vec3 d) {
  vec2 uv = vec2(atan(d.z, d.x) / 6.2831853 + 0.5, asin(clamp(d.y, -1.0, 1.0)) / 3.1415927 + 0.5);
  vec3 c = texture(uHimmel, uv).rgb;
  return (uKodiert > 0.5 ? c * c * 8.0 : c) + sterne(d, uPixel, uZeit);
}

mat3 drehung(vec3 b) {
  float cy = cos(b.x), sy = sin(b.x);
  float cp = cos(b.y), sp = sin(b.y);
  mat3 gier = mat3(cy, 0.0, -sy, 0.0, 1.0, 0.0, sy, 0.0, cy);
  mat3 nick = mat3(1.0, 0.0, 0.0, 0.0, cp, sp, 0.0, -sp, cp);
  return gier * nick;
}

vec3 gluehen(float t) {
  t = max(t, 0.0);
  return vec3(1.0, 0.42, 0.1) * t + vec3(0.0, 0.26, 0.24) * t * t + vec3(0.0, 0.03, 0.22) * t * t * t;
}

vec4 scheibe(vec3 q, float r, vec3 strahl, vec3 n, vec3 a1, vec3 a2) {
  float innen = 3.0;
  float temperatur = pow(innen / r, 0.75) * pow(max(0.0, 1.0 - sqrt(innen / r)), 0.25) * 2.4;
  vec3 tangente = normalize(cross(n, q));
  float beta = sqrt(0.5 / r);
  float gamma = 1.0 / sqrt(1.0 - beta * beta);
  float doppler = 1.0 / (gamma * (1.0 - beta * dot(tangente, -strahl)));
  float g = doppler * sqrt(max(0.0, 1.0 - 1.0 / r));
  float winkel = atan(dot(q, a2), dot(q, a1)) - uZeit * 1.6 * pow(r, -1.5);
  float streifen = fbm3(vec3(cos(winkel) * r * 1.4, sin(winkel) * r * 1.4, r * 2.4)) * 1.15;
  float ringe = 0.62 + 0.38 * sin(r * 6.5 + streifen * 7.0);
  float dichte = smoothstep(3.0, 3.7, r) * smoothstep(14.0, 8.5, r) * (0.3 + 0.95 * streifen * ringe);
  vec3 licht = gluehen(temperatur * g) * pow(g, 3.5) * 1.9;
  return vec4(licht, clamp(dichte, 0.0, 1.0));
}

vec3 loch(vec3 d) {
  vec3 oben0 = normalize(cross(cross(LOCH, vec3(0.08, 1.0, 0.0)), LOCH));
  vec3 n = normalize(oben0 * cos(0.16) - LOCH * sin(0.16));
  vec3 a1 = normalize(cross(n, vec3(0.0, 0.0, 1.0)));
  vec3 a2 = cross(n, a1);
  vec3 p = -LOCH * ABSTAND;
  vec3 v = d;
  float b = dot(p, v);
  float c = dot(p, p) - 400.0;
  float wurzel = b * b - c;
  if (wurzel > 0.0) {
    float t = -b - sqrt(wurzel);
    if (t > 0.0) p += v * t;
  }
  vec3 drall = cross(p, v);
  float h2 = dot(drall, drall);
  vec3 licht = vec3(0.0);
  float deckung = 0.0;
  for (int i = 0; i < 110; i++) {
    float r2 = dot(p, p);
    float r = sqrt(r2);
    if (r < 1.0) return licht;
    float schritt = clamp(0.1 * (r - 0.85), 0.02, 1.2);
    vec3 neuV = v - 1.5 * h2 * p / (r2 * r2 * r) * schritt;
    vec3 neuP = p + neuV * schritt;
    float s0 = dot(p, n);
    float s1 = dot(neuP, n);
    if (s0 * s1 < 0.0) {
      vec3 q = mix(p, neuP, s0 / (s0 - s1));
      float rq = length(q);
      if (rq > 3.0 && rq < 14.0) {
        vec4 e = scheibe(q, rq, normalize(neuV), n, a1, a2);
        licht += (1.0 - deckung) * e.rgb * e.a;
        deckung += (1.0 - deckung) * e.a;
        if (deckung > 0.98) return licht;
      }
    }
    p = neuP;
    v = neuV;
    if (r > 21.0 && dot(p, v) > 0.0) break;
  }
  return licht + (1.0 - deckung) * himmel(normalize(v));
}

vec3 schwachLinsen(vec3 d) {
  float w = clamp(dot(d, LOCH), -1.0, 1.0);
  float stoss = ABSTAND * sqrt(max(0.0, 1.0 - w * w));
  float ablenkung = 2.0 / max(stoss, 1.0);
  vec3 weg = normalize(d - LOCH * w);
  return normalize(d * cos(ablenkung) - weg * sin(ablenkung));
}

void main() {
  vec2 uv = (gl_FragCoord.xy - 0.5 * uAufloesung) / uAufloesung.y;
  vec3 d = normalize(vec3(uv * 2.0 * tan(uSicht * 0.5), -1.0));
  d = drehung(uBlick) * d;
  float w = dot(d, LOCH);
  vec3 c = w > cos(BEREICH) ? loch(d) : w > 0.0 ? himmel(schwachLinsen(d)) : himmel(d);
  c = vec3(1.0) - exp(-c * 1.15);
  c = pow(c, vec3(0.95));
  float rand = 1.0 - 0.28 * dot(uv, uv);
  farbe = vec4(c * rand + vec3(0.004, 0.004, 0.012), 1.0);
}`;

function bauen(gl: WebGL2RenderingContext, fragment: string): WebGLProgram | null {
  const teil = (art: number, quelle: string) => {
    const shader = gl.createShader(art);
    if (!shader) return null;
    gl.shaderSource(shader, quelle);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.warn(gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  };
  const ecken = teil(gl.VERTEX_SHADER, ECKEN);
  const flaeche = teil(gl.FRAGMENT_SHADER, fragment);
  if (!ecken || !flaeche) return null;
  const programm = gl.createProgram();
  if (!programm) return null;
  gl.attachShader(programm, ecken);
  gl.attachShader(programm, flaeche);
  gl.linkProgram(programm);
  gl.deleteShader(ecken);
  gl.deleteShader(flaeche);
  if (!gl.getProgramParameter(programm, gl.LINK_STATUS)) {
    console.warn(gl.getProgramInfoLog(programm));
    return null;
  }
  return programm;
}

export default function KosmosHimmel(props: Props) {
  const { lat, lon, zoom, bearing, fadeFrom = 4.2, fadeTo = 6.4 } = props;
  const holder = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const viewRef = useRef({ lat, lon, zoom, bearing });
  viewRef.current = { lat, lon, zoom, bearing };
  const fadeRef = useRef({ from: fadeFrom, to: fadeTo });
  fadeRef.current = { from: fadeFrom, to: fadeTo };
  const [ohneGl, setOhneGl] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const box = holder.current;
    if (!canvas || !box) return;
    const gl = canvas.getContext("webgl2", { antialias: false, alpha: false, depth: false, stencil: false, powerPreference: "low-power" });
    if (!gl) {
      setOhneGl(true);
      return;
    }
    const backen = bauen(gl, BACKEN);
    const kosmos = bauen(gl, KOSMOS);
    if (!backen || !kosmos) {
      setOhneGl(true);
      return;
    }
    const huelle = gl.createVertexArray();
    gl.bindVertexArray(huelle);

    const gleitend = !!gl.getExtension("EXT_color_buffer_float");
    const texturBreite = Math.min(2048, gl.getParameter(gl.MAX_TEXTURE_SIZE) as number);
    const texturHoehe = texturBreite / 2;
    const textur = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, textur);
    gl.texImage2D(gl.TEXTURE_2D, 0, gleitend ? gl.RGBA16F : gl.RGBA8, texturBreite, texturHoehe, 0, gl.RGBA, gleitend ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    const rahmen = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, rahmen);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, textur, 0);
    const kodiert = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE && gleitend ? 0 : 1;
    if (kodiert && gleitend) {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, texturBreite, texturHoehe, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    const backOrt = {
      groesse: gl.getUniformLocation(backen, "uGroesse"),
      kodiert: gl.getUniformLocation(backen, "uKodiert"),
    };
    const ort = {
      aufloesung: gl.getUniformLocation(kosmos, "uAufloesung"),
      zeit: gl.getUniformLocation(kosmos, "uZeit"),
      blick: gl.getUniformLocation(kosmos, "uBlick"),
      sicht: gl.getUniformLocation(kosmos, "uSicht"),
      kodiert: gl.getUniformLocation(kosmos, "uKodiert"),
      himmel: gl.getUniformLocation(kosmos, "uHimmel"),
      pixel: gl.getUniformLocation(kosmos, "uPixel"),
    };

    const streifen = 24;
    let gebacken = 0;
    let qualitaet = 0.7;
    let vorher = 0;
    let breite = 0;
    let hoehe = 0;
    let bild = 0;
    let zuletzt = 0;
    let messung: number[] = [];
    let sichtbar = false;
    const anfang = performance.now();

    const groesse = () => {
      const rect = box.getBoundingClientRect();
      const dichte = Math.min(1.25, window.devicePixelRatio || 1) * qualitaet;
      breite = Math.max(160, Math.round(rect.width * dichte));
      hoehe = Math.max(120, Math.round(rect.height * dichte));
      canvas.width = breite;
      canvas.height = hoehe;
    };

    const backschritt = () => {
      const hoeheStreifen = Math.ceil(texturHoehe / streifen);
      gl.bindFramebuffer(gl.FRAMEBUFFER, rahmen);
      gl.viewport(0, 0, texturBreite, texturHoehe);
      gl.enable(gl.SCISSOR_TEST);
      gl.scissor(0, gebacken * hoeheStreifen, texturBreite, hoeheStreifen);
      gl.useProgram(backen);
      gl.uniform2f(backOrt.groesse, texturBreite, texturHoehe);
      gl.uniform1f(backOrt.kodiert, kodiert);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.disable(gl.SCISSOR_TEST);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gebacken += 1;
    };

    const zeichnen = (jetzt: number) => {
      bild = requestAnimationFrame(zeichnen);
      const view = viewRef.current;
      const fade = fadeRef.current;
      const staerke = Math.max(0, Math.min(1, (fade.to - view.zoom) / Math.max(0.1, fade.to - fade.from)));
      if (gebacken < streifen) {
        backschritt();
        return;
      }
      if (staerke <= 0.001) {
        if (sichtbar) {
          sichtbar = false;
          canvas.style.opacity = "0";
        }
        return;
      }
      const takt = jetzt - vorher;
      vorher = jetzt;
      if (takt > 0 && takt < 250 && sichtbar) messung.push(takt);
      if (messung.length >= 45) {
        messung.sort((a, b) => a - b);
        const mittel = messung[Math.floor(messung.length / 2)];
        messung = [];
        const alt = qualitaet;
        if (mittel > 48 && qualitaet > 0.45) qualitaet = Math.max(0.45, qualitaet - 0.08);
        else if (mittel < 36 && qualitaet < 0.85) qualitaet = Math.min(0.85, qualitaet + 0.05);
        if (alt !== qualitaet) groesse();
      }
      if (jetzt - zuletzt < 30) return;
      zuletzt = jetzt;
      sichtbar = true;
      canvas.style.opacity = staerke.toFixed(3);
      const gier = (-(view.lon * 0.22) - view.bearing * 0.55) * (Math.PI / 180);
      const nick = Math.max(-70, Math.min(70, view.lat)) * 0.32 * (Math.PI / 180);
      gl.viewport(0, 0, breite, hoehe);
      gl.useProgram(kosmos);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, textur);
      gl.uniform1i(ort.himmel, 0);
      gl.uniform1f(ort.kodiert, kodiert);
      gl.uniform2f(ort.aufloesung, breite, hoehe);
      gl.uniform1f(ort.zeit, (jetzt - anfang) / 1000);
      gl.uniform3f(ort.blick, gier, nick, 0);
      gl.uniform1f(ort.sicht, (68 * Math.PI) / 180);
      gl.uniform1f(ort.pixel, (2 * Math.tan((34 * Math.PI) / 180)) / hoehe);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    const verloren = (e: Event) => {
      e.preventDefault();
      setOhneGl(true);
    };
    canvas.addEventListener("webglcontextlost", verloren);
    canvas.style.opacity = "0";
    groesse();
    bild = requestAnimationFrame(zeichnen);
    const beobachter = new ResizeObserver(() => groesse());
    beobachter.observe(box);
    return () => {
      cancelAnimationFrame(bild);
      beobachter.disconnect();
      canvas.removeEventListener("webglcontextlost", verloren);
      gl.deleteProgram(backen);
      gl.deleteProgram(kosmos);
      gl.deleteTexture(textur);
      gl.deleteFramebuffer(rahmen);
      gl.deleteVertexArray(huelle);
    };
  }, []);

  if (ohneGl) return <SpaceBackdrop {...props} />;
  return (
    <div ref={holder} className="jm-space">
      <canvas ref={canvasRef} className="jm-space-canvas" />
    </div>
  );
}
