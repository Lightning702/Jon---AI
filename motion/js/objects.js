window.JON = window.JON || {};

JON.OBJ = (function () {
  const CFG = JON.CFG, U = JON.U;
  const c3 = (hex) => new THREE.Color(hex);

  const VS = `
    varying vec2 vUv;
    void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }
`;

  function plane(w, h, mat) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h, 1, 1), mat);
    m.frustumCulled = false;
    return m;
  }

  class Backdrop {
    constructor() {
      this.u = {
        uTime: { value: 0 }, uOpacity: { value: 1 },
        uCore: { value: 0.10 }, uColor: { value: c3(CFG.C.gold) }
      };
      this.obj = plane(26, 46, new THREE.ShaderMaterial({
        uniforms: this.u, vertexShader: VS, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending,
        fragmentShader: `
          uniform float uTime, uOpacity, uCore; uniform vec3 uColor; varying vec2 vUv;
          float n(vec2 p){
            vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
            float a = fract(sin(dot(i,vec2(41.3,289.1)))*43758.5);
            float b = fract(sin(dot(i+vec2(1,0),vec2(41.3,289.1)))*43758.5);
            float c = fract(sin(dot(i+vec2(0,1),vec2(41.3,289.1)))*43758.5);
            float d = fract(sin(dot(i+vec2(1,1),vec2(41.3,289.1)))*43758.5);
            return mix(mix(a,b,f.x), mix(c,d,f.x), f.y);
          }
          void main(){
            vec2 p = vUv - 0.5;
            float r = length(p * vec2(1.7, 1.0));
            float halo = exp(-r * 3.6) * uCore;
            float clouds = (n(p * 5.0 + uTime * 0.03) * 0.6 + n(p * 11.0 - uTime * 0.02) * 0.4);
            halo += clouds * exp(-r * 3.4) * 0.035;
            gl_FragColor = vec4(uColor * halo, 1.0) * uOpacity;
          }`
      }));
      this.obj.position.z = -9;
    }
  }

  class Particles {
    constructor(count) {
      count = count || 6000;
      const r = U.rng(7331);
      const pos = new Float32Array(count * 3);
      const seed = new Float32Array(count);
      const size = new Float32Array(count);
      const tint = new Float32Array(count);

      for (let i = 0; i < count; i++) {

        const th = r() * U.TAU, ph = Math.acos(2 * r() - 1);
        const rad = 1.2 + Math.pow(r(), 0.65) * 8.5;
        pos[i * 3] = Math.sin(ph) * Math.cos(th) * rad * 0.85;
        pos[i * 3 + 1] = Math.cos(ph) * rad * 1.25;
        pos[i * 3 + 2] = Math.sin(ph) * Math.sin(th) * rad * 0.7;
        seed[i] = r() * 100;
        size[i] = 0.6 + Math.pow(r(), 2.4) * 3.6;
        tint[i] = r();
      }

      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
      g.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
      g.setAttribute('aTint', new THREE.BufferAttribute(tint, 1));

      this.u = {
        uTime: { value: 0 }, uOpacity: { value: 0 }, uSpread: { value: 1 },
        uSwirl: { value: 0 }, uPull: { value: 0 }, uDrift: { value: 1 },
        uSize: { value: 1 }, uA: { value: c3(CFG.C.goldHi) }, uB: { value: c3(CFG.C.goldPale) },
        uPixel: { value: CFG.HEIGHT }
      };

      this.obj = new THREE.Points(g, new THREE.ShaderMaterial({
        uniforms: this.u, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        vertexShader: `
          attribute float aSeed, aSize, aTint;
          uniform float uTime, uSpread, uSwirl, uPull, uDrift, uSize, uPixel;
          varying float vA, vT;
          void main(){
            vec3 p = position * uSpread;

            float s = aSeed;
            p.x += sin(uTime * 0.35 + s) * 0.42 * uDrift;
            p.y += cos(uTime * 0.28 + s * 1.7) * 0.5 * uDrift + uTime * 0.06 * uDrift;
            p.z += sin(uTime * 0.24 + s * 2.3) * 0.35 * uDrift;

            float a = uSwirl * (0.35 + 0.5 / (0.7 + length(p.xy)));
            float ca = cos(a), sa = sin(a);
            p.xy = mat2(ca, -sa, sa, ca) * p.xy;

            p = mix(p, normalize(p + 1e-4) * 0.55, uPull);

            vec4 mv = modelViewMatrix * vec4(p, 1.0);
            gl_Position = projectionMatrix * mv;

            gl_PointSize = aSize * uSize * (uPixel * 0.019) / max(-mv.z, 0.001);
            vA = smoothstep(46.0, 6.0, -mv.z);
            vT = aTint;
          }`,
        fragmentShader: `
          uniform float uOpacity; uniform vec3 uA, uB;
          varying float vA, vT;
          void main(){
            vec2 d = gl_PointCoord - 0.5;
            float r = length(d);
            if (r > 0.5) discard;

            float core = exp(-r * r * 26.0);
            float halo = exp(-r * 5.5) * 0.45;
            vec3 col = mix(uA, uB, vT) * (core + halo);
            gl_FragColor = vec4(col, (core + halo) * vA * uOpacity);
          }`
      }));
    }
  }

  class LogoMark {
    constructor() {
      this.u = {
        uRing: { value: 0 }, uEyes: { value: 0 }, uSmile: { value: 0 },
        uDisc: { value: 0 }, uOpacity: { value: 1 }, uGlow: { value: 1 },
        uPulse: { value: 0 }, uTime: { value: 0 },
        uGold: { value: c3(CFG.C.gold) }, uHi: { value: c3(CFG.C.goldHi) }, uPale: { value: c3(CFG.C.goldPale) }
      };
      this.obj = plane(2.6, 2.6, new THREE.ShaderMaterial({
        uniforms: this.u, vertexShader: VS, transparent: true, depthWrite: false,

        blending: THREE.CustomBlending,
        blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
        blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor,
        fragmentShader: `
          uniform float uRing, uEyes, uSmile, uDisc, uOpacity, uGlow, uPulse, uTime;
          uniform vec3 uGold, uHi, uPale;
          varying vec2 vUv;
          const float TAU = 6.28318530718;

          float sdArc(vec2 p, vec2 sc, float ra, float rb){
            p.x = abs(p.x);
            return ((sc.y * p.x > sc.x * p.y) ? length(p - sc * ra) : abs(length(p) - ra)) - rb;
          }

          const float R_RING = 0.800, W_RING = 0.078, R_DISC = 0.726;
          const vec2  P_EYE  = vec2(0.255, 0.111);
          const float R_EYE  = 0.119, R_HL = 0.036;
          const vec2  O_HL   = vec2(0.025, 0.058);
          const float Y_MOUTH = -0.024, R_MOUTH = 0.296, W_MOUTH = 0.038, A_MOUTH = 1.04;

          void main(){
            vec2 p = (vUv - 0.5) * 2.6;
            float r = length(p);
            vec3 col = vec3(0.0);
            float alpha = 0.0;

            float disc = smoothstep(0.006, -0.006, r - R_DISC) * uDisc;
            vec3 discCol = mix(vec3(0.009, 0.008, 0.011), vec3(0.052, 0.044, 0.028),
                               smoothstep(0.75, -0.75, p.y));
            col += discCol * disc;
            alpha = disc;
            float inside = mix(1.0, 0.14, disc);

            float ringD = abs(r - R_RING) - W_RING;
            float ang = atan(p.x, p.y) / TAU;
            float t = fract(ang + 1.0);
            float open = 1.0 - smoothstep(uRing, uRing + 0.012, t);
            open = max(open, step(1.0, uRing));

            float ringA = smoothstep(0.010, 0.0, ringD) * open;
            float ringG = exp(-max(ringD, 0.0) * 13.0) * open * uGlow * inside;

            vec3 ringCol = mix(uGold, uPale, smoothstep(-0.8, 0.8, p.y) * 0.50 + 0.06);
            col += ringCol * ringA * 1.30 + uHi * ringG * 0.50;
            alpha = clamp(alpha + ringA + ringG * 0.45, 0.0, 1.0);

            float head = exp(-pow(ringD / 0.055, 2.0)) * exp(-pow((t - uRing) / 0.010, 2.0));
            head *= (1.0 - step(1.0, uRing));
            col += vec3(1.0, 0.95, 0.84) * head * 4.5;
            alpha = clamp(alpha + head, 0.0, 1.0);

            float on = step(0.001, uEyes);
            float grow = min(uEyes * 1.12, 1.0);
            float eye = min(length(p - P_EYE), length(p - vec2(-P_EYE.x, P_EYE.y))) - R_EYE * grow;
            float eyeA = smoothstep(0.009, 0.0, eye) * on;
            col += mix(uGold, uHi, 0.45) * eyeA * 1.60;
            col += uHi * exp(-max(eye, 0.0) * 26.0) * 0.30 * uGlow * grow * on;
            alpha = clamp(alpha + eyeA, 0.0, 1.0);

            float hl = min(length(p - P_EYE - O_HL), length(p - vec2(-P_EYE.x, P_EYE.y) - O_HL)) - R_HL * grow;
            float hlA = smoothstep(0.007, 0.0, hl) * on;
            col += vec3(1.0, 0.99, 0.96) * hlA * 1.30;
            alpha = clamp(alpha + hlA, 0.0, 1.0);

            vec2 q = vec2(p.x, -(p.y - Y_MOUTH));
            float mouth = sdArc(q, vec2(sin(A_MOUTH), cos(A_MOUTH)), R_MOUTH, W_MOUTH);
            float lim = mix(-0.36, 0.36, clamp(uSmile, 0.0, 1.0));
            float draw = (1.0 - smoothstep(lim, lim + 0.04, p.x)) * step(0.001, uSmile);
            float mA = smoothstep(0.009, 0.0, mouth) * draw;
            col += mix(uGold, uPale, 0.40) * mA * 1.55;
            col += uHi * exp(-max(mouth, 0.0) * 22.0) * draw * 0.35 * uGlow;
            alpha = clamp(alpha + mA, 0.0, 1.0);

            float aura = exp(-pow(max(r - R_RING, 0.0) / (0.20 + 0.12 * sin(uTime * 1.6)), 2.0));
            col += uHi * aura * uPulse * 0.60;
            alpha = clamp(alpha + aura * uPulse * 0.30, 0.0, 1.0);

            gl_FragColor = vec4(col * uOpacity, alpha * uOpacity);
          }`
      }));
    }

    headPoint(ringT) {
      const a = ringT * U.TAU;
      return new THREE.Vector3(Math.sin(a) * 0.80, Math.cos(a) * 0.80, 0)
        .multiplyScalar(this.obj.scale.x).add(this.obj.position);
    }
  }

  class Beam {
    constructor() {
      this.u = { uOpacity: { value: 0 }, uColor: { value: c3(CFG.C.goldPale) }, uTime: { value: 0 } };
      this.obj = plane(1, 1, new THREE.ShaderMaterial({
        uniforms: this.u, vertexShader: VS, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending,
        fragmentShader: `
          uniform float uOpacity, uTime; uniform vec3 uColor; varying vec2 vUv;
          void main(){

            float across = exp(-pow((vUv.y - 0.5) / (0.055 + 0.16 * (1.0 - vUv.x)), 2.0));
            float along = smoothstep(0.0, 0.25, vUv.x) * pow(vUv.x, 1.6);
            float flick = 0.88 + 0.12 * sin(uTime * 41.0);
            gl_FragColor = vec4(uColor * across * along * 2.2 * flick, across * along * uOpacity);
          }`
      }));
      this.obj.geometry.translate(0.5, 0, 0);
    }

    aim(from, to) {
      const d = to.clone().sub(from);
      this.obj.position.copy(from);
      this.obj.rotation.z = Math.atan2(d.y, d.x);
      this.obj.scale.set(d.length(), 1, 1);
    }
  }

  class TextPlane {
    constructor(runs, opts) {
      opts = opts || {};
      const t = U.textTexture(runs, opts);

      const h = opts.em ? opts.em * t.unit : (opts.height || 0.42);
      this.u = {
        map: { value: t.texture }, uOpacity: { value: 0 }, uReveal: { value: 1 },
        uBlur: { value: 0 }, uTint: { value: c3(opts.tint || 0xffffff) }, uLead: { value: 0 }
      };
      this.obj = plane(h * t.aspect, h, new THREE.ShaderMaterial({
        uniforms: this.u, vertexShader: VS, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending,
        fragmentShader: `
          uniform sampler2D map; uniform float uOpacity, uReveal, uBlur, uLead; uniform vec3 uTint;
          varying vec2 vUv;
          void main(){
            vec4 c;
            if (uBlur > 0.0005){

              float b = uBlur * 0.06;
              c  = texture2D(map, vUv + vec2(-b, 0.0)) + texture2D(map, vUv + vec2(b, 0.0));
              c += texture2D(map, vUv + vec2(0.0, -b * 0.5)) + texture2D(map, vUv + vec2(0.0, b * 0.5));
              c += texture2D(map, vUv + vec2(-b * 2.0, 0.0)) + texture2D(map, vUv + vec2(b * 2.0, 0.0));
              c /= 6.0;
            } else c = texture2D(map, vUv);

            float edge = uReveal * 1.24 - 0.12;
            float m = 1.0 - smoothstep(edge, edge + 0.14, vUv.x);
            float lead = exp(-pow((vUv.x - edge) / 0.035, 2.0)) * uLead;

            vec3 col = c.rgb * uTint + vec3(1.0, 0.9, 0.7) * lead * c.a * 2.0;
            gl_FragColor = vec4(col, 1.0) * (c.a * m + lead * c.a) * uOpacity;
          }`
      }));
      this.aspect = t.aspect;
      this.height = h;
    }
  }

  class Card {
    constructor(icon, label, o) {
      o = o || {};
      const t = U.cardTexture(icon, label, o);
      const h = o.height || 0.86;
      this.u = {
        map: { value: t.texture }, uOpacity: { value: 0 }, uTime: { value: 0 },
        uShimmer: { value: 0 }, uGlow: { value: 0 }
      };
      this.obj = plane(h * t.aspect, h, new THREE.ShaderMaterial({
        uniforms: this.u, vertexShader: VS, transparent: true, depthWrite: false,
        blending: THREE.NormalBlending,
        fragmentShader: `
          uniform sampler2D map; uniform float uOpacity, uTime, uShimmer, uGlow;
          varying vec2 vUv;
          void main(){
            vec4 c = texture2D(map, vUv);

            float s = exp(-pow((vUv.x + vUv.y * 0.6 - fract(uTime * 0.22 + uShimmer) * 1.9) / 0.12, 2.0));
            c.rgb += vec3(1.0, 0.92, 0.72) * s * 0.35 * c.a;
            c.rgb *= 1.0 + uGlow;
            gl_FragColor = vec4(c.rgb, c.a * uOpacity);
          }`
      }));
    }
  }

  class LinkLine {
    constructor(width) {
      this.u = {
        uOpacity: { value: 0 }, uProgress: { value: 1 }, uTime: { value: 0 },
        uSpeed: { value: 0.5 }, uOffset: { value: Math.random() }, uColor: { value: c3(CFG.C.goldHi) }
      };
      this.obj = plane(1, width || 0.05, new THREE.ShaderMaterial({
        uniforms: this.u, vertexShader: VS, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending,
        fragmentShader: `
          uniform float uOpacity, uProgress, uTime, uSpeed, uOffset; uniform vec3 uColor;
          varying vec2 vUv;
          void main(){
            float core = exp(-pow((vUv.y - 0.5) / 0.14, 2.0));
            float drawn = 1.0 - smoothstep(uProgress, uProgress + 0.06, vUv.x);
            float head = exp(-pow((vUv.x - fract(uTime * uSpeed + uOffset) * uProgress) / 0.035, 2.0));
            float fade = smoothstep(0.0, 0.08, vUv.x) * smoothstep(1.0, 0.92, vUv.x);
            float a = (core * 0.55 + core * head * 1.8) * drawn * fade;
            gl_FragColor = vec4(uColor * (1.0 + head * 2.4), a * uOpacity);
          }`
      }));
      this.obj.geometry.translate(0.5, 0, 0);
    }
    connect(from, to) {
      const d = to.clone().sub(from);
      this.obj.position.copy(from);
      this.obj.rotation.z = Math.atan2(d.y, d.x);
      this.obj.scale.x = d.length();
    }
  }

  class CodeRain {
    constructor(count) {
      count = count || 900;
      const atlas = U.glyphAtlas();
      const r = U.rng(20125);

      const base = new THREE.PlaneGeometry(0.13, 0.17);
      const g = new THREE.InstancedBufferGeometry();
      g.setIndex(base.index);
      g.setAttribute('position', base.attributes.position);
      g.setAttribute('uv', base.attributes.uv);
      g.instanceCount = count;

      const iPos = new Float32Array(count * 3), iG = new Float32Array(count),
        iS = new Float32Array(count), iA = new Float32Array(count);
      for (let i = 0; i < count; i++) {
        const a = r() * U.TAU, rad = 0.6 + Math.pow(r(), 0.6) * 4.2;
        iPos[i * 3] = Math.cos(a) * rad * 1.0;
        iPos[i * 3 + 1] = (r() - 0.5) * 12.0;
        iPos[i * 3 + 2] = Math.sin(a) * rad * 0.8 - r() * 34;
        iG[i] = Math.floor(r() * 128);
        iS[i] = 0.6 + r() * 1.1;
        iA[i] = 0.25 + r() * 0.75;
      }
      g.setAttribute('iPos', new THREE.InstancedBufferAttribute(iPos, 3));
      g.setAttribute('iGlyph', new THREE.InstancedBufferAttribute(iG, 1));
      g.setAttribute('iSpeed', new THREE.InstancedBufferAttribute(iS, 1));
      g.setAttribute('iAlpha', new THREE.InstancedBufferAttribute(iA, 1));

      this.u = {
        map: { value: atlas.texture }, uTime: { value: 0 }, uOpacity: { value: 0 },
        uSpeed: { value: 6.0 }, uStretch: { value: 0 }, uRange: { value: 40.0 },
        uCols: { value: atlas.cols }, uRows: { value: atlas.rows },
        uA: { value: c3(CFG.C.goldHi) }, uB: { value: c3(CFG.C.goldPale) }
      };

      this.obj = new THREE.Mesh(g, new THREE.ShaderMaterial({
        uniforms: this.u, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        vertexShader: `
          attribute vec3 iPos; attribute float iGlyph, iSpeed, iAlpha;
          uniform float uTime, uSpeed, uStretch, uRange, uCols, uRows;
          varying vec2 vUv; varying float vA;
          void main(){
            vec3 p = position;
            p.y *= 1.0 + uStretch * iSpeed * 5.0;
            vec3 o = iPos;
            o.z = mod(o.z + uTime * uSpeed * iSpeed, uRange) - uRange * 0.82;
            vec4 mv = modelViewMatrix * vec4(o + p, 1.0);
            gl_Position = projectionMatrix * mv;

            float gi = iGlyph;
            vec2 cell = vec2(mod(gi, uCols), floor(gi / uCols));
            vUv = (uv + cell) / vec2(uCols, uRows);

            vA = iAlpha * smoothstep(0.0, 6.0, -mv.z) * smoothstep(34.0, 12.0, -mv.z);
          }`,
        fragmentShader: `
          uniform sampler2D map; uniform float uOpacity; uniform vec3 uA, uB;
          varying vec2 vUv; varying float vA;
          void main(){
            float m = texture2D(map, vUv).r;
            vec3 col = mix(uA, uB, vA);
            gl_FragColor = vec4(col * (0.7 + vA), m * vA * uOpacity);
          }`
      }));
      this.obj.frustumCulled = false;
    }
  }

  class HoloWindow {
    constructor(kind, height) {
      const t = U.windowTexture(kind);
      const h = height || 1.05;
      this.u = { map: { value: t.texture }, uOpacity: { value: 0 }, uReveal: { value: 1 }, uTime: { value: 0 } };
      this.obj = plane(h * t.aspect, h, new THREE.ShaderMaterial({
        uniforms: this.u, vertexShader: VS, transparent: true, depthWrite: false,
        blending: THREE.NormalBlending,
        fragmentShader: `
          uniform sampler2D map; uniform float uOpacity, uReveal, uTime; varying vec2 vUv;
          void main(){
            vec4 c = texture2D(map, vUv);

            float e = uReveal * 1.15 - 0.08;
            float m = 1.0 - smoothstep(e, e + 0.10, vUv.y);
            float scan = exp(-pow((vUv.y - e) / 0.02, 2.0)) * (1.0 - step(1.0, uReveal));

            float lines = 0.94 + 0.06 * sin((vUv.y * 240.0) - uTime * 3.0);
            vec3 col = c.rgb * lines + vec3(1.0, 0.88, 0.62) * scan;
            gl_FragColor = vec4(col, (c.a * m + scan * 0.8) * uOpacity);
          }`
      }));
    }
  }

  class Ring {
    constructor(radius, thickness) {
      this.u = {
        uOpacity: { value: 0 }, uTime: { value: 0 }, uDash: { value: 26.0 },
        uSpeed: { value: 0.4 }, uColor: { value: c3(CFG.C.goldHi) }, uSolid: { value: 0.25 }
      };
      const geo = new THREE.TorusGeometry(radius, thickness || 0.012, 8, 220);
      this.obj = new THREE.Mesh(geo, new THREE.ShaderMaterial({
        uniforms: this.u, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        vertexShader: `
          varying vec2 vUv; varying vec3 vN, vV;
          void main(){
            vUv = uv;
            vN = normalize(normalMatrix * normal);
            vec4 mv = modelViewMatrix * vec4(position, 1.0);
            vV = normalize(-mv.xyz);
            gl_Position = projectionMatrix * mv;
          }`,
        fragmentShader: `
          uniform float uOpacity, uTime, uDash, uSpeed, uSolid; uniform vec3 uColor;
          varying vec2 vUv; varying vec3 vN, vV;
          void main(){
            float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 1.6);
            float d = sin((vUv.x * uDash - uTime * uSpeed) * 6.2831853) * 0.5 + 0.5;
            float a = (uSolid + d * 0.9) * (0.35 + f * 1.3);
            gl_FragColor = vec4(uColor * (0.8 + d * 1.6), a * uOpacity);
          }`
      }));
    }
  }

  class Rays {
    constructor(n) {
      this.obj = new THREE.Group();
      this.u = { uOpacity: { value: 0 }, uTime: { value: 0 }, uColor: { value: c3(CFG.C.goldHi) } };
      const mat = new THREE.ShaderMaterial({
        uniforms: this.u, vertexShader: VS, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending,
        fragmentShader: `
          uniform float uOpacity, uTime; uniform vec3 uColor; varying vec2 vUv;
          void main(){

            float across = exp(-pow((vUv.y - 0.5) / (0.10 + 0.62 * vUv.x), 2.0));
            float along = pow(1.0 - vUv.x, 2.2) * smoothstep(0.0, 0.18, vUv.x);
            float breathe = 0.6 + 0.4 * sin(uTime * 0.55 + vUv.y * 2.0);
            gl_FragColor = vec4(uColor * across * along * breathe * 0.5, across * along * uOpacity * 0.6);
          }`
      });
      n = n || 5;
      for (let i = 0; i < n; i++) {
        const m = plane(1, 1, mat);
        m.geometry.translate(0.5, 0, 0);
        m.scale.set(7.5 + (i % 3) * 3.2, 2.2 + (i % 4) * 1.1, 1);
        m.rotation.z = (i / n) * U.TAU + 0.55;
        this.obj.add(m);
      }
    }
  }

  return { Backdrop, Particles, LogoMark, Beam, TextPlane, Card, LinkLine, CodeRain, HoloWindow, Ring, Rays, plane, VS };
})();
