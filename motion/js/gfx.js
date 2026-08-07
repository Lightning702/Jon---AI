window.JON = window.JON || {};

JON.GFX = (function () {
  const CFG = JON.CFG;

  const QUAD_VS = `
    varying vec2 vUv;
    void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;

  function pass(fragment, uniforms) {
    return new THREE.ShaderMaterial({
      uniforms: uniforms,
      vertexShader: QUAD_VS,
      fragmentShader: fragment,
      depthTest: false, depthWrite: false, transparent: false
    });
  }

  const FS_BRIGHT = `
    uniform sampler2D tDiffuse; uniform float uThreshold, uKnee;
    varying vec2 vUv;
    void main(){
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      float l = max(c.r, max(c.g, c.b));
      float s = clamp((l - uThreshold + uKnee) / (2.0 * uKnee), 0.0, 1.0);
      float w = max(l - uThreshold, s * s * uKnee) / max(l, 1e-4);
      gl_FragColor = vec4(c * w, 1.0);
    }
`;

  const FS_BLUR = `
    uniform sampler2D tDiffuse; uniform vec2 uDir; uniform float uRadius;
    varying vec2 vUv;
    void main(){
      vec2 d = uDir * uRadius;
      vec3 s = texture2D(tDiffuse, vUv).rgb * 0.1964825;
      s += (texture2D(tDiffuse, vUv + d * 1.411764).rgb + texture2D(tDiffuse, vUv - d * 1.411764).rgb) * 0.2969069;
      s += (texture2D(tDiffuse, vUv + d * 3.294117).rgb + texture2D(tDiffuse, vUv - d * 3.294117).rgb) * 0.0944703;
      s += (texture2D(tDiffuse, vUv + d * 5.176470).rgb + texture2D(tDiffuse, vUv - d * 5.176470).rgb) * 0.0103813;
      gl_FragColor = vec4(s, 1.0);
    }
`;

  const FS_COPY = `
    uniform sampler2D tDiffuse; varying vec2 vUv;
    void main(){ gl_FragColor = texture2D(tDiffuse, vUv); }
`;

  const FS_COMPOSITE = `
    uniform sampler2D tScene, tBloomWide, tBloomTight, tPrev;
    uniform float uBloom, uFeedback, uGrain, uVignette, uCA, uExposure, uFade, uTime, uFlash;
    varying vec2 vUv;

    vec3 aces(vec3 x){
      return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
    }

    float hash(vec2 p){
      vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
      q += dot(q, q.yzx + 33.33);
      return fract((q.x + q.y) * q.z);
    }

    void main(){
      vec2 uv = vUv;
      vec2 off = (uv - 0.5);
      float r2 = dot(off, off);

      float ca = uCA * (0.0016 + r2 * 0.010);
      vec3 col;
      col.r = texture2D(tScene, uv - off * ca).r;
      col.g = texture2D(tScene, uv).g;
      col.b = texture2D(tScene, uv + off * ca).b;

      vec3 bloom = texture2D(tBloomWide, uv).rgb * vec3(1.0, 0.80, 0.52) * 0.50
                 + texture2D(tBloomTight, uv).rgb * vec3(1.0, 0.88, 0.64) * 0.74;
      col += bloom * uBloom;

      col += vec3(1.0, 0.87, 0.58) * uFlash * exp(-r2 * 3.4);

      col *= uExposure * uFade;
      col = aces(col);

      col *= mix(1.0, smoothstep(0.95, 0.10, r2 * 1.25), uVignette);

      float g = hash(gl_FragCoord.xy + fract(uTime) * vec2(311.0, 197.0)) - 0.5;
      col += g * uGrain * (0.030 + 0.040 * (1.0 - length(col))) * uFade;

      vec3 prev = texture2D(tPrev, uv).rgb;
      col = mix(col, prev, uFeedback * 0.55);

      gl_FragColor = vec4(col, 1.0);
    }
`;

  class Pipeline {
    constructor(canvas) {
      this.renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance',
        preserveDrawingBuffer: true
      });
      this.renderer.setPixelRatio(1);
      this.renderer.setClearColor(0x000000, 1);
      this.renderer.autoClear = true;

      this.quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      this.quadScene = new THREE.Scene();
      this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), pass(FS_COPY, { tDiffuse: { value: null } }));
      this.quad.frustumCulled = false;
      this.quadScene.add(this.quad);

      this.mBright = pass(FS_BRIGHT, { tDiffuse: { value: null }, uThreshold: { value: 0.78 }, uKnee: { value: 0.38 } });
      this.mBlur = pass(FS_BLUR, { tDiffuse: { value: null }, uDir: { value: new THREE.Vector2(1, 0) }, uRadius: { value: 1 } });
      this.mCopy = pass(FS_COPY, { tDiffuse: { value: null } });
      this.mComp = pass(FS_COMPOSITE, {
        tScene: { value: null }, tBloomWide: { value: null }, tBloomTight: { value: null }, tPrev: { value: null },
        uBloom: { value: 1 }, uFeedback: { value: 0 }, uGrain: { value: 1 }, uVignette: { value: 1 },
        uCA: { value: 1 }, uExposure: { value: 1 }, uFade: { value: 1 }, uTime: { value: 0 }, uFlash: { value: 0 }
      });

      this.targets = [];
      this.setSize(CFG.WIDTH, CFG.HEIGHT);
    }

    _rt(w, h, depth) {
      const rt = new THREE.WebGLRenderTarget(Math.max(2, Math.round(w)), Math.max(2, Math.round(h)), {
        minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter,
        format: THREE.RGBAFormat, type: THREE.HalfFloatType,
        depthBuffer: !!depth, stencilBuffer: false
      });
      this.targets.push(rt);
      return rt;
    }

    setSize(w, h) {
      this.targets.forEach(t => t.dispose());
      this.targets = [];
      this.w = w; this.h = h;
      this.renderer.setSize(w, h, false);

      this.rtScene = this._rt(w, h, true);
      this.rtHalfA = this._rt(w / 2, h / 2);
      this.rtHalfB = this._rt(w / 2, h / 2);
      this.rtQuartA = this._rt(w / 4, h / 4);
      this.rtQuartB = this._rt(w / 4, h / 4);
      this.rtOutA = this._rt(w, h);
      this.rtOutB = this._rt(w, h);
      this.prev = this.rtOutB;
      this.out = this.rtOutA;
    }

    _run(material, target) {
      this.quad.material = material;
      this.renderer.setRenderTarget(target || null);
      this.renderer.render(this.quadScene, this.quadCam);
    }

    _blur(src, tmp, dst, radius) {
      this.mBlur.uniforms.tDiffuse.value = src.texture;
      this.mBlur.uniforms.uDir.value.set(1 / tmp.width, 0);
      this.mBlur.uniforms.uRadius.value = radius;
      this._run(this.mBlur, tmp);

      this.mBlur.uniforms.tDiffuse.value = tmp.texture;
      this.mBlur.uniforms.uDir.value.set(0, 1 / dst.height);
      this._run(this.mBlur, dst);
    }

    render(scene, camera, p) {
      const R = this.renderer;

      R.setRenderTarget(this.rtScene);
      R.clear();
      R.render(scene, camera);

      this.mBright.uniforms.tDiffuse.value = this.rtScene.texture;
      this.mBright.uniforms.uThreshold.value = p.threshold !== undefined ? p.threshold : 0.78;
      this._run(this.mBright, this.rtHalfA);

      this._blur(this.rtHalfA, this.rtHalfB, this.rtHalfA, 1.1);

      this.mCopy.uniforms.tDiffuse.value = this.rtHalfA.texture;
      this._run(this.mCopy, this.rtQuartA);
      this._blur(this.rtQuartA, this.rtQuartB, this.rtQuartA, 2.0);
      this._blur(this.rtQuartA, this.rtQuartB, this.rtQuartA, 3.4);

      const u = this.mComp.uniforms;
      u.tScene.value = this.rtScene.texture;
      u.tBloomTight.value = this.rtHalfA.texture;
      u.tBloomWide.value = this.rtQuartA.texture;
      u.tPrev.value = this.prev.texture;
      u.uBloom.value = p.bloom;
      u.uFeedback.value = p.feedback;
      u.uGrain.value = p.grain;
      u.uVignette.value = p.vignette;
      u.uCA.value = p.ca;
      u.uExposure.value = p.exposure;
      u.uFade.value = p.fade;
      u.uFlash.value = p.flash;
      u.uTime.value = p.time;
      this._run(this.mComp, this.out);

      this.mCopy.uniforms.tDiffuse.value = this.out.texture;
      this._run(this.mCopy, null);

      const t = this.prev; this.prev = this.out; this.out = t;
    }
  }

  return { Pipeline, pass, QUAD_VS };
})();
