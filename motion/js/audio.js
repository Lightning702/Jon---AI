window.JON = window.JON || {};

JON.Audio = (function () {
  const CFG = JON.CFG, T = CFG.T;

  const N = {
    F1: 43.65, Ab1: 51.91, Db1: 34.65, Eb1: 38.89,
    F2: 87.31, Ab2: 103.83, C3: 130.81, Db2: 69.30, Eb2: 77.78,
    F3: 174.61, Ab3: 207.65, C4: 261.63, Db3: 138.59, Eb3: 155.56,
    F4: 349.23, Ab4: 415.30, Bb4: 466.16, C5: 523.25, Eb5: 622.25, Db4: 277.18
  };

  const CHORDS = [
    { t: 0.0, notes: [N.F2, N.C3, N.Ab3, N.F3] },
    { t: T.s2, notes: [N.Db2, N.Ab2, N.F3, N.Db4] },
    { t: T.s3, notes: [N.Ab2, N.Eb3, N.C4, N.Ab3] },
    { t: T.s4, notes: [N.Eb2, N.Bb4 / 2, N.Eb3, N.C4] },
    { t: T.s5, notes: [N.F2, N.C3, N.F3, N.Ab3] }
  ];

  function noise(ctx, dur) {
    const len = Math.ceil(ctx.sampleRate * dur);
    const b = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = b.getChannelData(0);
    let last = 0;
    for (let i = 0; i < len; i++) { last = (last + (Math.random() * 2 - 1) * 0.4) * 0.94; d[i] = last; }
    return b;
  }

  function impulse(ctx, dur, decay) {
    const len = Math.ceil(ctx.sampleRate * dur);
    const b = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = b.getChannelData(ch);
      for (let i = 0; i < len; i++) {
        const t = i / len;
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - t, decay) * (1 - t * 0.35);
      }
    }
    return b;
  }

  function env(param, t, a, peak, d, sus, r, dur) {
    param.setValueAtTime(0.0001, t);
    param.exponentialRampToValueAtTime(Math.max(peak, 0.0002), t + a);
    param.exponentialRampToValueAtTime(Math.max(sus, 0.0002), t + a + d);
    param.setValueAtTime(Math.max(sus, 0.0002), t + Math.max(dur - r, a + d));
    param.exponentialRampToValueAtTime(0.0001, t + dur);
  }

  function impact(ctx, bus, t, o) {
    o = o || {};
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(o.gain || 0.9, t + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0001, t + (o.dur || 1.5));
    g.connect(bus.dry); g.connect(bus.wet);

    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(o.f || 120, t);
    osc.frequency.exponentialRampToValueAtTime((o.f || 120) * 0.28, t + (o.dur || 1.5) * 0.55);
    osc.connect(g); osc.start(t); osc.stop(t + (o.dur || 1.5) + 0.05);

    const s = ctx.createBufferSource(); s.buffer = noise(ctx, 0.35);
    const f = ctx.createBiquadFilter(); f.type = 'bandpass';
    f.frequency.setValueAtTime(2400, t); f.frequency.exponentialRampToValueAtTime(320, t + 0.3);
    f.Q.value = 0.9;
    const ng = ctx.createGain();
    ng.gain.setValueAtTime((o.gain || 0.9) * 0.5, t);
    ng.gain.exponentialRampToValueAtTime(0.0001, t + 0.32);
    s.connect(f); f.connect(ng); ng.connect(bus.dry); ng.connect(bus.wet);
    s.start(t); s.stop(t + 0.36);
  }

  function whoosh(ctx, bus, t, dur, o) {
    o = o || {};
    const s = ctx.createBufferSource(); s.buffer = noise(ctx, dur + 0.1);
    const f = ctx.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = o.q || 1.6;
    f.frequency.setValueAtTime(o.f0 || 260, t);
    f.frequency.exponentialRampToValueAtTime(o.f1 || 5200, t + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(o.gain || 0.32, t + dur * (o.peak || 0.72));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    const p = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    if (p) { p.pan.setValueAtTime(o.pan === undefined ? -0.6 : o.pan, t); p.pan.linearRampToValueAtTime(-(o.pan === undefined ? -0.6 : o.pan), t + dur); }
    s.connect(f); f.connect(g);
    if (p) { g.connect(p); p.connect(bus.dry); p.connect(bus.wet); } else { g.connect(bus.dry); g.connect(bus.wet); }
    s.start(t); s.stop(t + dur + 0.1);
  }

  function blip(ctx, bus, t, f, o) {
    o = o || {};
    const osc = ctx.createOscillator();
    osc.type = o.type || 'triangle';
    osc.frequency.setValueAtTime(f, t);
    if (o.slide) osc.frequency.exponentialRampToValueAtTime(f * o.slide, t + (o.dur || 0.13));
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(o.gain || 0.14, t + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, t + (o.dur || 0.13));
    osc.connect(g); g.connect(bus.dry); g.connect(bus.wet);
    osc.start(t); osc.stop(t + (o.dur || 0.13) + 0.02);
  }

  function pluck(ctx, bus, t, f, o) {
    o = o || {};
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(o.gain || 0.10, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t + (o.dur || 0.9));
    const f1 = ctx.createBiquadFilter(); f1.type = 'lowpass';
    f1.frequency.setValueAtTime(5200, t);
    f1.frequency.exponentialRampToValueAtTime(900, t + (o.dur || 0.9));
    [1, 2.004].forEach((mul, i) => {
      const osc = ctx.createOscillator();
      osc.type = i ? 'sine' : 'triangle';
      osc.frequency.value = f * mul;
      const og = ctx.createGain(); og.gain.value = i ? 0.35 : 1;
      osc.connect(og); og.connect(f1);
      osc.start(t); osc.stop(t + (o.dur || 0.9) + 0.05);
    });
    f1.connect(g); g.connect(bus.dry); g.connect(bus.wet);
  }

  function padChord(ctx, bus, t, dur, notes, gain) {
    const g = ctx.createGain(); g.gain.value = 0;
    env(g.gain, t, 1.1, gain, 1.4, gain * 0.72, 1.6, dur);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 0.8;
    lp.frequency.setValueAtTime(320, t);
    lp.frequency.linearRampToValueAtTime(1900, t + dur * 0.7);
    lp.frequency.linearRampToValueAtTime(700, t + dur);
    notes.forEach((f, i) => {
      [-6, 6].forEach(cents => {
        const osc = ctx.createOscillator();
        osc.type = i === 0 ? 'sine' : 'sawtooth';
        osc.frequency.value = f * Math.pow(2, cents / 1200);
        const og = ctx.createGain(); og.gain.value = (i === 0 ? 0.55 : 0.16) / notes.length;
        osc.connect(og); og.connect(lp);
        osc.start(t); osc.stop(t + dur + 0.1);
      });
    });
    lp.connect(g); g.connect(bus.dry); g.connect(bus.wet);
  }

  function riser(ctx, bus, t, dur, gain) {
    const s = ctx.createBufferSource(); s.buffer = noise(ctx, dur + 0.1);
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass';
    hp.frequency.setValueAtTime(300, t);
    hp.frequency.exponentialRampToValueAtTime(6000, t + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(gain || 0.20, t + dur * 0.92);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.06);
    s.connect(hp); hp.connect(g); g.connect(bus.dry); g.connect(bus.wet);
    s.start(t); s.stop(t + dur + 0.1);

    const osc = ctx.createOscillator(); osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(N.F2, t);
    osc.frequency.exponentialRampToValueAtTime(N.F4 * 1.5, t + dur);
    const og = ctx.createGain();
    og.gain.setValueAtTime(0.0001, t);
    og.gain.exponentialRampToValueAtTime((gain || 0.20) * 0.5, t + dur * 0.95);
    og.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.05);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 3000;
    osc.connect(lp); lp.connect(og); og.connect(bus.dry); og.connect(bus.wet);
    osc.start(t); osc.stop(t + dur + 0.1);
  }

  function drone(ctx, bus, t, dur) {
    const osc = ctx.createOscillator(); osc.type = 'sine'; osc.frequency.value = N.F1;
    const osc2 = ctx.createOscillator(); osc2.type = 'sine'; osc2.frequency.value = N.F1 * 1.5;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.42, t + 2.2);
    g.gain.setValueAtTime(0.42, t + dur - 2.0);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    const g2 = ctx.createGain(); g2.gain.value = 0.10;
    osc.connect(g); osc2.connect(g2); g2.connect(g);
    g.connect(bus.dry);
    osc.start(t); osc.stop(t + dur + 0.1);
    osc2.start(t); osc2.stop(t + dur + 0.1);
  }

  function score(ctx, bus, t0, skip) {
    skip = skip || 0;
    const at = (x) => t0 + x;
    const ok = (x, len) => (x + (len || 0)) > skip;

    if (ok(0, CFG.DURATION)) drone(ctx, bus, at(Math.max(0, skip - 0.2)), CFG.DURATION - Math.max(0, skip - 0.2) + 1.0);

    CHORDS.forEach((c, i) => {
      const end = (i + 1 < CHORDS.length ? CHORDS[i + 1].t : CFG.DURATION + 1.2);
      const len = end - c.t + 1.2;
      if (ok(c.t, len)) padChord(ctx, bus, at(Math.max(c.t, skip)), len - Math.max(0, skip - c.t), c.notes, i === 4 ? 0.30 : 0.20);
    });

    for (let i = 0; i < 9; i++) {
      const t = 0.35 + i * 0.22 + (i % 3) * 0.05;
      if (ok(t)) blip(ctx, bus, at(t), [N.C5, N.Eb5, N.Ab4, N.F4][i % 4] * 2, { gain: 0.045, dur: 0.5, type: 'sine' });
    }
    if (ok(0.45, 1.6)) whoosh(ctx, bus, at(0.45), 1.55, { f0: 400, f1: 3600, gain: 0.16, pan: -0.7 });
    if (ok(1.86, 0.4)) whoosh(ctx, bus, at(1.86), 0.36, { f0: 5200, f1: 700, gain: 0.22, pan: 0.6 });
    if (ok(1.98, 1.6)) impact(ctx, bus, at(1.98), { f: 96, gain: 0.62, dur: 1.7 });
    if (ok(2.14)) blip(ctx, bus, at(2.14), N.C5 * 2, { gain: 0.10, dur: 0.18 });
    if (ok(2.22)) blip(ctx, bus, at(2.22), N.Eb5 * 2, { gain: 0.10, dur: 0.18 });
    if (ok(2.42, 1.0)) { [N.F4, N.Ab4, N.C5].forEach((f, i) => ok(2.42 + i * 0.1) && pluck(ctx, bus, at(2.42 + i * 0.1), f, { gain: 0.075 })); }

    if (ok(T.s2 - 0.7, 0.7)) riser(ctx, bus, at(T.s2 - 0.7), 0.68, 0.16);
    if (ok(T.s2 - 0.3, 0.4)) whoosh(ctx, bus, at(T.s2 - 0.30), 0.42, { f0: 300, f1: 4800, gain: 0.26, pan: 0.7 });
    if (ok(T.s2, 1.8)) impact(ctx, bus, at(T.s2), { f: 108, gain: 0.75, dur: 1.9 });
    CFG.SKILLS.forEach((s, i) => {
      const t = T.s2 + 0.20 + i * 0.13;
      if (ok(t)) blip(ctx, bus, at(t), [N.F4, N.Ab4, N.C5, N.Eb5][i % 4] * (i > 3 ? 2 : 1),
        { gain: 0.085, dur: 0.16, slide: 1.35 });
    });
    if (ok(T.s2 + 1.05, 1.2)) [N.Ab4, N.C5, N.F4 * 2].forEach((f, i) => pluck(ctx, bus, at(T.s2 + 1.05 + i * 0.14), f, { gain: 0.07 }));

    if (ok(T.s3 - 1.0, 1.0)) riser(ctx, bus, at(T.s3 - 1.0), 0.98, 0.26);
    if (ok(T.s3 - 0.35, 0.45)) whoosh(ctx, bus, at(T.s3 - 0.35), 0.45, { f0: 240, f1: 6400, gain: 0.34, pan: -0.8 });
    if (ok(T.s3, 2.2)) impact(ctx, bus, at(T.s3), { f: 132, gain: 0.95, dur: 2.2 });
    if (ok(T.s3, 3.6)) whoosh(ctx, bus, at(T.s3 + 0.05), 3.4, { f0: 1800, f1: 700, gain: 0.09, q: 0.7, peak: 0.2, pan: 0.4 });

    CFG.TXT.s3.forEach((w, i) => {
      const t = T.s3 + 0.55 + i * 1.05;
      if (ok(t - 0.22, 0.25)) whoosh(ctx, bus, at(t - 0.22), 0.24, { f0: 5000, f1: 900, gain: 0.20, pan: i % 2 ? 0.7 : -0.7 });
      if (ok(t, 1.2)) impact(ctx, bus, at(t), { f: 150 + i * 18, gain: 0.55, dur: 1.1 });
      if (ok(t + 0.02)) blip(ctx, bus, at(t + 0.02), [N.F4, N.Ab4, N.C5][i] * 2, { gain: 0.11, dur: 0.22, type: 'square' });
    });

    for (let i = 0; i < 16; i++) {
      const t = T.s3 + 0.6 + i * 0.2;
      if (t < T.s4 - 0.2 && ok(t)) pluck(ctx, bus, at(t), [N.F4, N.Ab4, N.C5, N.Eb5, N.C5, N.Ab4][i % 6], { gain: 0.05, dur: 0.55 });
    }

    if (ok(T.s4 - 0.8, 0.8)) riser(ctx, bus, at(T.s4 - 0.8), 0.78, 0.20);
    if (ok(T.s4 - 0.28, 0.35)) whoosh(ctx, bus, at(T.s4 - 0.28), 0.36, { f0: 400, f1: 5200, gain: 0.28, pan: 0.7 });
    if (ok(T.s4, 2.4)) impact(ctx, bus, at(T.s4), { f: 118, gain: 0.85, dur: 2.4 });
    CFG.ORBIT.forEach((s, i) => {
      const t = T.s4 + 0.10 + i * 0.11;
      if (ok(t)) blip(ctx, bus, at(t), [N.C5, N.Eb5, N.F4 * 2, N.Ab4 * 2][i % 4], { gain: 0.07, dur: 0.2, slide: 1.5 });
    });
    for (let i = 0; i < 20; i++) {
      const t = T.s4 + 0.5 + i * 0.24;
      if (t < T.s5 - 0.4 && ok(t)) pluck(ctx, bus, at(t), [N.Eb3 * 2, N.C4 * 2, N.Ab3 * 2, N.Eb5][i % 4], { gain: 0.042, dur: 1.1 });
    }

    if (ok(T.s5 - 1.3, 1.3)) riser(ctx, bus, at(T.s5 - 1.3), 1.28, 0.34);
    if (ok(T.s5 - 0.3, 0.35)) whoosh(ctx, bus, at(T.s5 - 0.30), 0.34, { f0: 6000, f1: 500, gain: 0.30, pan: -0.6 });
    if (ok(T.s5, 3.4)) impact(ctx, bus, at(T.s5), { f: 84, gain: 1.0, dur: 3.4 });
    if (ok(T.s5 + 0.55, 1.4)) [N.F4, N.C5, N.Ab4].forEach((f, i) => pluck(ctx, bus, at(T.s5 + 0.55 + i * 0.13), f, { gain: 0.085, dur: 1.4 }));
    if (ok(T.s5 + 2.35, 1.6)) [N.Ab4, N.C5, N.F4 * 2].forEach((f, i) => pluck(ctx, bus, at(T.s5 + 2.35 + i * 0.15), f, { gain: 0.075, dur: 1.6 }));
    if (ok(T.s5 + 3.2, 0.4)) blip(ctx, bus, at(T.s5 + 3.2), N.C5 * 2, { gain: 0.07, dur: 0.4, type: 'sine' });
    if (ok(CFG.DURATION - 0.6, 1.8)) impact(ctx, bus, at(CFG.DURATION - 0.55), { f: 70, gain: 0.55, dur: 1.9 });

    bus.master.gain.setValueAtTime(0.78, at(CFG.DURATION - 0.55));
    bus.master.gain.linearRampToValueAtTime(0.0001, at(CFG.DURATION));
  }

  function softClipCurve(threshold) {
    const n = 8192, c = new Float32Array(n), t = threshold;
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * 2 - 1, a = Math.abs(x);
      c[i] = a <= t ? x : Math.sign(x) * (t + (1 - t) * Math.tanh((a - t) / (1 - t)));
    }
    return c;
  }

  function makeBus(ctx, destination) {
    const master = ctx.createGain(); master.gain.value = 0.78;
    const limiter = ctx.createWaveShaper();
    limiter.curve = softClipCurve(0.72);
    limiter.oversample = '4x';

    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -14; comp.knee.value = 26; comp.ratio.value = 3.4;
    comp.attack.value = 0.004; comp.release.value = 0.22;

    const conv = ctx.createConvolver();
    conv.buffer = impulse(ctx, 3.2, 2.6);
    const wet = ctx.createGain(); wet.gain.value = 0.26;
    const dry = ctx.createGain(); dry.gain.value = 1.0;

    const air = ctx.createBiquadFilter(); air.type = 'highshelf';
    air.frequency.value = 7200; air.gain.value = -3.5;

    dry.connect(comp);
    wet.connect(conv); conv.connect(comp);
    comp.connect(air); air.connect(master);
    master.connect(limiter); limiter.connect(destination);
    return { dry, wet, master };
  }

  class Engine {
    constructor() { this.ctx = null; this.muted = false; this.streamDest = null; }

    ensure() {
      if (!this.ctx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return null;
        this.ctx = new AC({ latencyHint: 'interactive' });
        this.out = this.ctx.createGain();
        this.out.gain.value = this.muted ? 0 : 1;
        this.out.connect(this.ctx.destination);
        this.streamDest = this.ctx.createMediaStreamDestination();
        this.out.connect(this.streamDest);
      }
      if (this.ctx.state === 'suspended') this.ctx.resume();
      return this.ctx;
    }

    play(from) {
      this.stop();
      const ctx = this.ensure(); if (!ctx) return;
      this.bus = makeBus(ctx, this.out);
      this.nodes = this.bus;
      score(ctx, this.bus, ctx.currentTime + 0.06 - from, from);
      this.playing = true;
    }

    stop() {
      if (this.bus) {
        try {
          this.bus.master.gain.cancelScheduledValues(this.ctx.currentTime);
          this.bus.master.gain.setTargetAtTime(0, this.ctx.currentTime, 0.03);
          const b = this.bus;
          setTimeout(() => { try { b.master.disconnect(); } catch (e) { } }, 300);
        } catch (e) { }
        this.bus = null;
      }
      this.playing = false;
    }

    setMuted(m) {
      this.muted = m;
      if (this.out) this.out.gain.setTargetAtTime(m ? 0 : 1, this.ctx.currentTime, 0.02);
    }

    async renderBuffer(sampleRate) {
      sampleRate = sampleRate || 48000;
      const len = Math.ceil(CFG.DURATION * sampleRate);
      const OC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
      const octx = new OC(2, len, sampleRate);
      const out = octx.createGain(); out.connect(octx.destination);
      const bus = makeBus(octx, out);
      score(octx, bus, 0, 0);
      return octx.startRendering();
    }

    async renderWav(sampleRate) {
      return encodeWav(await this.renderBuffer(sampleRate));
    }
  }

  function encodeWav(buf) {
    const ch = buf.numberOfChannels, len = buf.length;
    const bytes = 44 + len * ch * 2;
    const dv = new DataView(new ArrayBuffer(bytes));
    let p = 0;
    const str = s => { for (let i = 0; i < s.length; i++) dv.setUint8(p++, s.charCodeAt(i)); };
    const u32 = v => { dv.setUint32(p, v, true); p += 4; };
    const u16 = v => { dv.setUint16(p, v, true); p += 2; };

    str('RIFF'); u32(bytes - 8); str('WAVE');
    str('fmt '); u32(16); u16(1); u16(ch); u32(buf.sampleRate);
    u32(buf.sampleRate * ch * 2); u16(ch * 2); u16(16);
    str('data'); u32(len * ch * 2);

    const data = [];
    for (let c = 0; c < ch; c++) data.push(buf.getChannelData(c));
    for (let i = 0; i < len; i++) {
      for (let c = 0; c < ch; c++) {
        let s = Math.max(-1, Math.min(1, data[c][i]));
        dv.setInt16(p, s < 0 ? s * 0x8000 : s * 0x7FFF, true); p += 2;
      }
    }
    return new Blob([dv.buffer], { type: 'audio/wav' });
  }

  return Engine;
})();
