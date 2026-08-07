window.JON = window.JON || {};

JON.buildTimeline = function (world) {
  const CFG = JON.CFG, T = CFG.T, S = world.state;
  const tl = gsap.timeline({ paused: true, defaults: { ease: 'power2.out', immediateRender: false } });

  const to = (target, vars, at) => tl.fromTo(target,
    vars.from, Object.assign({ immediateRender: false }, vars.to), at);

  function flash(at, peak, up, down) {
    tl.fromTo(S, { flash: 0 }, { flash: peak, duration: up || .05, ease: 'none', immediateRender: false }, at);
    tl.fromTo(S, { flash: peak }, { flash: 0, duration: down || .35, ease: 'power2.out', immediateRender: false }, at + (up || .05));
  }

  function smear(at, peak, dur) {
    tl.fromTo(S, { feedback: 0 }, { feedback: peak, duration: .10, ease: 'none', immediateRender: false }, at);
    tl.fromTo(S, { feedback: peak }, { feedback: 0, duration: dur || .55, ease: 'power2.out', immediateRender: false }, at + .10);
  }

  function textIn(t, at, o) {
    o = o || {};
    const d = o.dur || .85, y = t.obj.position.y;
    tl.fromTo(t.u.uOpacity, { value: 0 }, { value: 1, duration: d * .45, ease: 'power2.out', immediateRender: false }, at);
    tl.fromTo(t.u.uReveal, { value: 0 }, { value: 1, duration: d, ease: 'power3.inOut', immediateRender: false }, at);
    tl.fromTo(t.u.uLead, { value: 1.2 }, { value: 0, duration: d * 1.1, ease: 'power2.out', immediateRender: false }, at);
    tl.fromTo(t.u.uBlur, { value: o.blur === undefined ? .8 : o.blur }, { value: 0, duration: d * .8, ease: 'power3.out', immediateRender: false }, at);
    tl.fromTo(t.obj.position, { y: y - (o.rise === undefined ? .08 : o.rise) }, { y: y, duration: d * 1.3, ease: 'power3.out', immediateRender: false }, at);
    tl.fromTo(t.obj.scale, { x: .93, y: .93 }, { x: 1, y: 1, duration: d * 1.4, ease: 'power3.out', immediateRender: false }, at);
  }

  function textOut(t, at, o) {
    o = o || {};
    const d = o.dur || .40, y = t.obj.position.y;
    tl.fromTo(t.u.uOpacity, { value: 1 }, { value: 0, duration: d, ease: 'power2.in', immediateRender: false }, at);
    tl.fromTo(t.u.uBlur, { value: 0 }, { value: 1.4, duration: d, ease: 'power2.in', immediateRender: false }, at);
    tl.fromTo(t.obj.position, { y: y }, { y: y + (o.rise === undefined ? .12 : o.rise), duration: d, ease: 'power2.in', immediateRender: false }, at);
  }

  to(S, { from: { fade: 0 }, to: { fade: 1, duration: .9, ease: 'power2.inOut' } }, 0);
  to(S, { from: { camZ: 9.9 }, to: { camZ: 8.0, duration: 3.6, ease: 'power2.out' } }, 0);
  to(S, { from: { camRoll: .035 }, to: { camRoll: 0, duration: 3.6, ease: 'power2.out' } }, 0);
  to(world.backdrop.u.uOpacity, { from: { value: 0 }, to: { value: 1, duration: 2.0 } }, .3);

  to(world.particles.u.uOpacity, { from: { value: 0 }, to: { value: 1, duration: 1.6, ease: 'power1.out' } }, .15);
  to(world.particles.u.uSpread, { from: { value: 2.6 }, to: { value: 1.0, duration: 3.4, ease: 'power2.out' } }, 0);
  to(world.particles.u.uSwirl, { from: { value: .9 }, to: { value: .12, duration: 3.4, ease: 'power2.out' } }, 0);
  to(world.particles.u.uSize, { from: { value: 1.5 }, to: { value: 1.0, duration: 2.6 } }, .2);

  to(world.beam.u.uOpacity, { from: { value: 0 }, to: { value: 1, duration: .30 } }, .45);
  to(world.logo.u.uRing, { from: { value: 0 }, to: { value: 1, duration: 1.42, ease: 'power1.inOut' } }, .58);
  to(world.logo.u.uGlow, { from: { value: 1.6 }, to: { value: 1.0, duration: 2.0 } }, .6);

  to(world.beam.u.uOpacity, { from: { value: 1 }, to: { value: 0, duration: .26, ease: 'power2.in' } }, 1.90);
  flash(2.00, .18, .05, .45);
  to(world.logo.u.uDisc, { from: { value: 0 }, to: { value: 1, duration: .38, ease: 'power2.out' } }, 1.96);
  to(world.logo.u.uEyes, { from: { value: 0 }, to: { value: 1, duration: .48, ease: 'back.out(2.4)' } }, 2.12);
  to(world.logo.u.uSmile, { from: { value: 0 }, to: { value: 1, duration: .52, ease: 'power2.out' } }, 2.32);
  to(world.rays.u.uOpacity, { from: { value: 0 }, to: { value: .55, duration: 1.2 } }, 2.10);

  to(world.particles.u.uPull, { from: { value: 0 }, to: { value: .18, duration: .5, ease: 'power2.out' } }, 1.96);
  to(world.particles.u.uPull, { from: { value: .18 }, to: { value: 0, duration: 1.4, ease: 'power2.out' } }, 2.46);

  textIn(world.txtMeet, 2.42, { dur: .90 });

  const s2 = T.s2;

  smear(s2 - .12, .34, .6);
  flash(s2 - .06, .12);
  to(S, { from: { skillsOn: 0 }, to: { skillsOn: 1, duration: .01 } }, s2 - .25);
  textOut(world.txtMeet, s2 - .30, { dur: .35, rise: .16 });

  to(S, { from: { camZ: 8.0 }, to: { camZ: 7.35, duration: 3.2, ease: 'power1.inOut' } }, s2);
  to(world.logo.obj.scale, { from: { x: .72, y: .72, z: 1 }, to: { x: .80, y: .80, duration: 1.4, ease: 'power2.out' } }, s2);
  to(world.logo.obj.position, { from: { z: 0 }, to: { z: .45, duration: 3.2, ease: 'power1.inOut' } }, s2);
  to(S, { from: { skillDrift: -.30 }, to: { skillDrift: .62, duration: 3.4, ease: 'none' } }, s2);

  world.skills.forEach((c, i) => {
    const at = s2 + .18 + i * .13;
    to(c.appear, { from: { v: 0 }, to: { v: 1, duration: .55, ease: 'power2.out' } }, at);
    to(c.obj.scale, { from: { x: .55, y: .55 }, to: { x: 1, y: 1, duration: .95, ease: 'back.out(1.5)' } }, at);
    const lk = world.skillLinks[i];
    to(lk.appear, { from: { v: 0 }, to: { v: .95, duration: .5 } }, at + .18);
    to(lk.u.uProgress, { from: { value: 0 }, to: { value: 1, duration: .75, ease: 'power2.out' } }, at + .18);
  });

  textIn(world.txtPersonal, s2 + 1.05, { dur: 1.0 });

  world.skills.forEach((c, i) => {
    const at = T.s3 - .55 + i * .035;
    to(c.appear, { from: { v: 1 }, to: { v: 0, duration: .40, ease: 'power2.in' } }, at);
    to(c.obj.scale, { from: { x: 1, y: 1 }, to: { x: 1.25, y: 1.25, duration: .45, ease: 'power2.in' } }, at);
    to(world.skillLinks[i].appear, { from: { v: .95 }, to: { v: 0, duration: .35 } }, at);
  });
  textOut(world.txtPersonal, T.s3 - .45);
  to(S, { from: { skillsOn: 1 }, to: { skillsOn: 0, duration: .01 } }, T.s3 + .1);

  const s3 = T.s3;

  to(S, { from: { streamOn: 0 }, to: { streamOn: 1, duration: .01 } }, s3 - .3);
  smear(s3 - .18, .45, .8);
  flash(s3 - .05, .22, .05, .5);
  to(S, { from: { ca: 1 }, to: { ca: 1.9, duration: .18, ease: 'power2.out' } }, s3 - .18);
  to(S, { from: { ca: 1.9 }, to: { ca: 1, duration: 1.1, ease: 'power2.out' } }, s3);

  to(S, { from: { camZ: 7.35 }, to: { camZ: 6.75, duration: .55, ease: 'power3.out' } }, s3 - .15);
  to(S, { from: { camZ: 6.75 }, to: { camZ: 7.6, duration: 3.8, ease: 'power1.inOut' } }, s3 + .4);
  to(S, { from: { camRoll: -.03 }, to: { camRoll: .03, duration: 4.0, ease: 'sine.inOut' } }, s3);

  to(world.logo.u.uOpacity, { from: { value: 1 }, to: { value: .18, duration: .5 } }, s3 - .1);
  to(world.logo.obj.position, { from: { z: .45 }, to: { z: -2.6, duration: 1.2, ease: 'power2.out' } }, s3 - .1);
  to(world.rays.u.uOpacity, { from: { value: .55 }, to: { value: .12, duration: .6 } }, s3 - .1);
  to(world.particles.u.uOpacity, { from: { value: 1 }, to: { value: .45, duration: .6 } }, s3 - .1);

  to(world.rain.u.uOpacity, { from: { value: 0 }, to: { value: 1, duration: .45 } }, s3 - .1);
  to(world.rain.u.uSpeed, { from: { value: 15 }, to: { value: 5.5, duration: 1.6, ease: 'power2.out' } }, s3 - .1);
  to(world.rain.u.uStretch, { from: { value: .55 }, to: { value: .06, duration: 1.4, ease: 'power2.out' } }, s3 - .1);

  world.windows.forEach((o, i) => {
    const at = s3 + .35 + i * .85;
    to(o.w.u.uOpacity, { from: { value: 0 }, to: { value: 1, duration: .30 } }, at);
    to(o.w.u.uReveal, { from: { value: 0 }, to: { value: 1, duration: .60, ease: 'power3.out' } }, at);
    to(o.w.obj.scale, { from: { x: .88, y: .88 }, to: { x: 1, y: 1, duration: .9, ease: 'power3.out' } }, at);
    to(o.w.u.uOpacity, { from: { value: 1 }, to: { value: 0, duration: .35, ease: 'power2.in' } }, T.s4 - .5 + i * .06);
    to(o.w.obj.scale, { from: { x: 1, y: 1 }, to: { x: 1.12, y: 1.12, duration: .4, ease: 'power2.in' } }, T.s4 - .5 + i * .06);
  });

  world.txtWords.forEach((t, i) => {
    const at = s3 + .55 + i * 1.05;
    to(t.u.uOpacity, { from: { value: 0 }, to: { value: 1, duration: .16 } }, at);
    to(t.u.uReveal, { from: { value: 0 }, to: { value: 1, duration: .42, ease: 'power3.out' } }, at);
    to(t.u.uBlur, { from: { value: 1.6 }, to: { value: 0, duration: .40, ease: 'power3.out' } }, at);
    to(t.u.uLead, { from: { value: 1.5 }, to: { value: 0, duration: .5 } }, at);
    to(t.obj.scale, { from: { x: .84, y: .84 }, to: { x: 1.05, y: 1.05, duration: 1.5, ease: 'power1.out' } }, at);

    to(t.u.uOpacity, { from: { value: 1 }, to: { value: 0, duration: .28, ease: 'power2.in' } }, at + .78);
    to(t.u.uBlur, { from: { value: 0 }, to: { value: 2.0, duration: .3, ease: 'power2.in' } }, at + .78);
    to(t.obj.scale, { from: { x: 1.02, y: 1.02 }, to: { x: 1.22, y: 1.22, duration: .3, ease: 'power2.in' } }, at + .78);
    flash(at, .10, .04, .28);
  });

  to(world.rain.u.uOpacity, { from: { value: 1 }, to: { value: 0, duration: .5, ease: 'power2.in' } }, T.s4 - .45);
  to(S, { from: { streamOn: 1 }, to: { streamOn: 0, duration: .01 } }, T.s4 + .1);

  const s4 = T.s4;

  to(S, { from: { orbitOn: 0 }, to: { orbitOn: 1, duration: .01 } }, s4 - .35);
  smear(s4 - .2, .40, .7);
  flash(s4 - .05, .20, .05, .55);

  to(world.logo.u.uOpacity, { from: { value: .18 }, to: { value: 1, duration: .55 } }, s4 - .3);
  to(world.logo.obj.position, { from: { z: -2.6 }, to: { z: 0, duration: 1.1, ease: 'power3.out' } }, s4 - .3);
  to(world.logo.obj.scale, { from: { x: .80, y: .80 }, to: { x: .70, y: .70, duration: 1.1, ease: 'power3.out' } }, s4 - .3);
  to(world.rays.u.uOpacity, { from: { value: .12 }, to: { value: .50, duration: 1.2 } }, s4);
  to(world.particles.u.uOpacity, { from: { value: .45 }, to: { value: .85, duration: 1.0 } }, s4 - .2);

  to(S, { from: { camZ: 7.6 }, to: { camZ: 8.5, duration: 2.0, ease: 'power2.out' } }, s4 - .2);
  to(S, { from: { camZ: 8.5 }, to: { camZ: 8.1, duration: 3.0, ease: 'power1.inOut' } }, s4 + 2.0);

  world.rings.forEach((r, i) => {
    to(r.u.uOpacity, { from: { value: 0 }, to: { value: [.85, .6, .45][i], duration: .9 } }, s4 - .1 + i * .18);
  });

  to(S, { from: { orbitRadiusX: .25, orbitRadiusY: .30 }, to: { orbitRadiusX: 1.02, orbitRadiusY: 1.95, duration: 1.9, ease: 'power2.out' } }, s4);
  to(S, { from: { orbitAngle: -.55 }, to: { orbitAngle: 3.05, duration: 5.0, ease: 'none' } }, s4);
  world.nodes.forEach((c, i) => {
    to(c.u.uOpacity, { from: { value: 0 }, to: { value: 1, duration: .55, ease: 'power2.out' } }, s4 + .05 + i * .11);
  });

  const s5 = T.s5;

  to(S, { from: { orbitRadiusX: 1.02, orbitRadiusY: 1.95 }, to: { orbitRadiusX: 3.4, orbitRadiusY: 4.2, duration: 1.6, ease: 'power2.in' } }, s5 - .85);
  world.nodes.forEach((c, i) => {
    to(c.u.uOpacity, { from: { value: 1 }, to: { value: 0, duration: .55, ease: 'power2.in' } }, s5 - .85 + i * .05);
  });
  world.rings.forEach((r, i) => {
    to(r.u.uOpacity, { from: { value: [.85, .6, .45][i] }, to: { value: 0, duration: .7, ease: 'power2.in' } }, s5 - .8 + i * .08);
  });
  to(S, { from: { orbitOn: 1 }, to: { orbitOn: 0, duration: .01 } }, s5 + .3);

  smear(s5 - .1, .38, .9);
  flash(s5, .26, .06, .8);

  to(world.logo.obj.scale, { from: { x: .70, y: .70 }, to: { x: .78, y: .78, duration: 2.2, ease: 'power2.out' } }, s5 - .3);
  to(world.logo.u.uPulse, { from: { value: 0 }, to: { value: .55, duration: 1.6 } }, s5);
  to(world.logo.u.uGlow, { from: { value: 1.0 }, to: { value: 1.5, duration: 1.6 } }, s5);
  to(world.rays.u.uOpacity, { from: { value: .50 }, to: { value: .78, duration: 1.4 } }, s5);

  to(world.particles.u.uSpread, { from: { value: 1.0 }, to: { value: 1.35, duration: 4.0, ease: 'power1.out' } }, s5 - .2);
  to(world.particles.u.uOpacity, { from: { value: .85 }, to: { value: .55, duration: 2.5 } }, s5 + .4);
  to(world.particles.u.uSwirl, { from: { value: .12 }, to: { value: .55, duration: 4.0, ease: 'power1.out' } }, s5 - .2);

  to(S, { from: { camZ: 8.1 }, to: { camZ: 7.55, duration: 4.4, ease: 'power1.inOut' } }, s5);
  to(S, { from: { vignette: 1 }, to: { vignette: 1.25, duration: 3.0 } }, s5);

  textIn(world.txtOne, s5 + .55, { dur: 1.0 });
  textIn(world.txtUnlimited, s5 + 2.35, { dur: 1.1 });
  to(world.txtUrl.u.uReveal, { from: { value: 0 }, to: { value: 1, duration: 1.1, ease: 'power2.out' } }, s5 + 3.15);
  to(world.txtUrl.u.uOpacity, { from: { value: 0 }, to: { value: .95, duration: 1.0 } }, s5 + 3.2);

  to(S, { from: { fade: 1 }, to: { fade: 0, duration: .55, ease: 'power2.in' } }, T.end - .55);
  to(S, { from: { bloom: 1 }, to: { bloom: 1.12, duration: .5, ease: 'power2.in' } }, T.end - .6);

  tl.duration(CFG.DURATION);
  return tl;
};

JON.resetWorld = function (world) {
  const s = world.state;
  Object.assign(s, {
    camX: 0, camY: 0, camZ: 9.9, camRoll: .035, fov: 35, camTargetY: 0,
    bloom: 1, feedback: 0, grain: 1, vignette: 1, ca: 1, exposure: 1,
    fade: 0, flash: 0, threshold: .62,
    skillsOn: 0, streamOn: 0, orbitOn: 0,
    orbitAngle: -.55, orbitRadiusX: .25, orbitRadiusY: .30, skillDrift: -.30
  });

  const L = world.logo.u;
  L.uRing.value = 0; L.uEyes.value = 0; L.uSmile.value = 0; L.uDisc.value = 0;
  L.uOpacity.value = 1; L.uGlow.value = 1.6; L.uPulse.value = 0;
  world.logo.obj.scale.setScalar(.72);
  world.logo.obj.position.z = 0;

  world.beam.u.uOpacity.value = 0;
  world.rays.u.uOpacity.value = 0;
  world.backdrop.u.uOpacity.value = 0;

  const P = world.particles.u;
  P.uOpacity.value = 0; P.uSpread.value = 2.6; P.uSwirl.value = .9; P.uPull.value = 0; P.uSize.value = 1.5;

  world.rain.u.uOpacity.value = 0; world.rain.u.uSpeed.value = 15; world.rain.u.uStretch.value = .55;
  world.windows.forEach(o => { o.w.u.uOpacity.value = 0; o.w.u.uReveal.value = 0; o.w.obj.scale.setScalar(1); });
  world.skills.forEach(c => { c.u.uOpacity.value = 0; c.appear.v = 0; c.obj.scale.setScalar(1); });
  world.skillLinks.forEach(l => { l.u.uOpacity.value = 0; l.appear.v = 0; l.u.uProgress.value = 0; });
  world.nodes.forEach(c => { c.u.uOpacity.value = 0; });
  world.rings.forEach(r => { r.u.uOpacity.value = 0; });

  [world.txtMeet, world.txtPersonal, world.txtOne, world.txtUnlimited, world.txtUrl]
    .concat(world.txtWords).forEach(t => {
      t.u.uOpacity.value = 0; t.u.uReveal.value = 0; t.u.uBlur.value = 0; t.u.uLead.value = 0;
      t.obj.scale.set(1, 1, 1);
    });
};
