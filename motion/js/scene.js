window.JON = window.JON || {};

JON.World = (function () {
  const CFG = JON.CFG, U = JON.U, O = JON.OBJ;

  const LOGO_Y = 0.55;

  class World {
    constructor() {
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0x000000);

      this.camera = new THREE.PerspectiveCamera(CFG.CAM.fov, CFG.ASPECT, CFG.CAM.near, CFG.CAM.far);
      this.camera.position.set(0, 0, CFG.CAM.z);

      this.state = {

        camX: 0, camY: 0, camZ: 8, camRoll: 0, fov: 35, camTargetY: 0,

        bloom: 1, feedback: 0, grain: 1, vignette: 1, ca: 1, exposure: 1,
        fade: 1, flash: 0, threshold: 0.62,

        skillsOn: 0, streamOn: 0, orbitOn: 0,

        orbitAngle: 0, orbitRadiusX: 1.20, orbitRadiusY: 1.52, skillDrift: 0
      };

      this._build();
    }

    _build() {
      const S = this.scene;

      this.backdrop = new O.Backdrop(); S.add(this.backdrop.obj);
      this.particles = new O.Particles(6000); S.add(this.particles.obj);

      this.rays = new O.Rays(9);
      this.rays.obj.position.set(0, LOGO_Y, -1.2);
      S.add(this.rays.obj);

      this.logo = new O.LogoMark();
      this.logo.obj.position.set(0, LOGO_Y, 0);
      this.logo.obj.scale.setScalar(0.72);
      S.add(this.logo.obj);

      this.beam = new O.Beam();
      this.beam.obj.position.z = 0.02;
      S.add(this.beam.obj);
      this.beamSrc = new THREE.Vector3(-2.6, 3.4, 0.02);

      this.skills = [];
      this.skillLinks = [];
      this.gSkills = new THREE.Group(); S.add(this.gSkills);

      const n = CFG.SKILLS.length;
      const LANE = 0.78, ZS = [0.30, -0.40, 0.52, -0.25, 0.42, -0.50, 0.18];
      CFG.SKILLS.forEach((s, i) => {
        const card = new O.Card(s.icon, s.label, { height: 0.72 });
        card.home = new THREE.Vector3(
          (i % 2 ? 1 : -1) * LANE,
          -0.75 + i * 0.55,
          ZS[i % ZS.length]
        );
        card.phase = i * 0.9;
        card.u.uShimmer.value = i * 0.17;

        card.appear = { v: 0 };
        this.gSkills.add(card.obj);
        this.skills.push(card);

        const link = new O.LinkLine(0.10);
        link.u.uSpeed.value = 0.35 + (i % 4) * 0.12;
        link.u.uOffset.value = i / n;
        link.appear = { v: 0 };
        this.gSkills.add(link.obj);
        this.skillLinks.push(link);
      });

      this.gStream = new THREE.Group(); S.add(this.gStream);
      this.rain = new O.CodeRain(1100);
      this.gStream.add(this.rain.obj);

      this.windows = [
        { w: new O.HoloWindow('chat', 1.00), pos: [-0.26, 1.10, -0.30], rot: 0.24 },
        { w: new O.HoloWindow('code', 0.92), pos: [0.34, 0.02, 0.30], rot: -0.20 },
        { w: new O.HoloWindow('web', 0.82), pos: [-0.34, -1.10, 0.00], rot: 0.28 }
      ];
      this.windows.forEach(o => {
        o.w.obj.position.set(o.pos[0], o.pos[1], o.pos[2]);
        o.w.obj.rotation.y = o.rot;
        this.gStream.add(o.w.obj);
      });

      this.gOrbit = new THREE.Group();
      this.gOrbit.position.set(0, LOGO_Y, 0);
      S.add(this.gOrbit);

      this.rings = [
        new O.Ring(1.05, 0.010), new O.Ring(1.38, 0.008), new O.Ring(1.72, 0.012)
      ];
      this.rings.forEach((r, i) => {
        r.u.uDash.value = [22, 34, 14][i];
        r.u.uSpeed.value = [0.35, -0.22, 0.16][i];
        r.obj.rotation.set(1.15 + i * 0.12, i * 0.4, 0);
        this.gOrbit.add(r.obj);
      });

      this.nodes = [];
      this.nodeLinks = [];
      CFG.ORBIT.forEach((s, i) => {
        const card = new O.Card(s.icon, s.label, { height: 0.86 });
        card.u.uShimmer.value = i * 0.23;
        this.gOrbit.add(card.obj);
        this.nodes.push(card);

        const link = new O.LinkLine(0.085);
        link.u.uSpeed.value = 0.28 + i * 0.06;
        link.u.uOffset.value = i / CFG.ORBIT.length;
        this.gOrbit.add(link.obj);
        this.nodeLinks.push(link);
      });

      const mk = (runs, o) => { const t = new O.TextPlane(runs, o); S.add(t.obj); return t; };

      this.txtMeet = mk([
        { text: 'Meet ', weight: 200, color: 0xffffff },
        { text: 'Jon', weight: 800, grad: true }
      ], { size: 120, tracking: 0.01, em: 0.46, glow: true });
      this.txtMeet.obj.position.set(0, -0.62, 0.2);

      this.txtPersonal = mk(CFG.TXT.s2, { size: 92, weight: 300, tracking: 0.12, em: 0.21, glow: true });
      this.txtPersonal.obj.position.set(0, -1.34, 0.2);

      this.txtWords = CFG.TXT.s3.map((w, i) => {
        const t = mk([{ text: w, weight: 800, grad: i === 1 }], { size: 150, tracking: 0.0, em: 0.44, glow: true });
        t.obj.position.set(0, 0.52, 0.9);
        return t;
      });

      this.txtOne = mk([{ text: 'One ', weight: 200, color: 0xffffff }, { text: 'AI.', weight: 800, grad: true }],
        { size: 130, tracking: 0.01, em: 0.50, glow: true });
      this.txtOne.obj.position.set(0, -0.55, 0.2);

      this.txtUnlimited = mk(CFG.TXT.s5b, { size: 96, weight: 200, tracking: 0.05, em: 0.18, glow: true });
      this.txtUnlimited.obj.position.set(0, -1.02, 0.2);

      this.txtUrl = mk(CFG.TXT.url, { size: 64, weight: 500, tracking: 0.26, em: 0.135, tint: 0xd9c489 });
      this.txtUrl.obj.position.set(0, -1.42, 0.2);

      [this.txtMeet, this.txtPersonal, this.txtOne, this.txtUnlimited, this.txtUrl]
        .concat(this.txtWords).forEach(t => { t.u.uOpacity.value = 0; t.u.uReveal.value = 0; });
    }

    update(t) {
      const s = this.state, cam = this.camera;

      cam.position.set(s.camX, s.camY, s.camZ);
      cam.rotation.z = s.camRoll;
      if (cam.fov !== s.fov) { cam.fov = s.fov; cam.updateProjectionMatrix(); }

      cam.position.x += Math.sin(t * 0.43) * 0.018 + Math.sin(t * 1.31) * 0.005;
      cam.position.y += Math.cos(t * 0.37) * 0.022 + s.camTargetY;

      this.backdrop.u.uTime.value = t;
      this.particles.u.uTime.value = t;

      const L = this.logo;
      L.u.uTime.value = t;

      if (L.u.uRing.value < 1 && this.beam.u.uOpacity.value > 0.001) {
        const head = L.headPoint(L.u.uRing.value);
        this.beamSrc.set(-2.6 + Math.sin(t * 0.6) * 0.25, 3.4 + Math.cos(t * 0.5) * 0.2, 0.02);
        this.beam.aim(this.beamSrc, head);
      }
      this.beam.u.uTime.value = t;
      this.rays.u.uTime.value = t;
      this.rays.obj.rotation.z = t * 0.045;

      const logoPos = L.obj.position;
      const rim = 0.80 * L.obj.scale.x * 1.06;
      this.skills.forEach((c, i) => {
        c.u.uTime.value = t;
        const ph = c.phase;
        c.obj.position.set(
          c.home.x + Math.sin(t * 0.42 + ph) * 0.06,
          c.home.y + Math.cos(t * 0.35 + ph) * 0.08 + s.skillDrift,
          c.home.z + Math.sin(t * 0.30 + ph) * 0.12
        );

        c.obj.rotation.y = (cam.position.x - c.obj.position.x) * 0.12;
        c.obj.rotation.x = (c.obj.position.y - cam.position.y) * 0.05;

        const edge = 1 - U.smoothstep(1.50, 2.15, c.obj.position.y);
        c.u.uOpacity.value = s.skillsOn * c.appear.v * edge;

        const link = this.skillLinks[i];
        link.u.uTime.value = t;
        const d = c.obj.position.clone().sub(logoPos);
        link.connect(logoPos.clone().add(d.clone().normalize().multiplyScalar(rim)), c.obj.position);
        link.u.uOpacity.value = s.skillsOn * link.appear.v * edge;
      });

      this.rain.u.uTime.value = t;
      this.windows.forEach((o, i) => {
        o.w.u.uTime.value = t;
        o.w.obj.position.y = o.pos[1] + Math.sin(t * 0.5 + i * 2.1) * 0.045;
        o.w.obj.rotation.y = o.rot + Math.sin(t * 0.35 + i) * 0.05;
      });

      const N = this.nodes.length;
      this.nodes.forEach((c, i) => {
        c.u.uTime.value = t;
        const a = s.orbitAngle + (i / N) * U.TAU;
        const x = Math.sin(a) * s.orbitRadiusX;
        const y = Math.cos(a) * s.orbitRadiusY * 0.72 + Math.sin(t * 0.5 + i) * 0.04;
        const z = Math.cos(a) * 0.9 - 0.1;
        c.obj.position.set(x, y, z);

        const depth = (z + 1.0) / 2.0;
        c.obj.scale.setScalar(0.72 + depth * 0.42);
        c.u.uGlow.value = depth * 0.35;
        c.obj.rotation.y = -x * 0.28;

        const link = this.nodeLinks[i];
        link.u.uTime.value = t;

        const dir = c.obj.position.clone().normalize().multiplyScalar(rim);
        link.connect(dir, c.obj.position);
        link.u.uOpacity.value = this.nodeOpacity(i) * (0.35 + depth * 0.65);
      });
      this.rings.forEach((r, i) => {
        r.u.uTime.value = t;
        r.obj.rotation.z = t * (0.12 + i * 0.05) * (i % 2 ? -1 : 1);
        r.obj.rotation.x = 1.15 + i * 0.12 + Math.sin(t * 0.3 + i) * 0.08;
      });

      this.gSkills.visible = s.skillsOn > 0.001;
      this.gStream.visible = s.streamOn > 0.001;
      this.gOrbit.visible = s.orbitOn > 0.001;
    }

    nodeOpacity(i) { return this.nodes[i].u.uOpacity.value; }

    look(t) {
      const s = this.state;
      return {
        bloom: s.bloom, feedback: s.feedback, grain: s.grain, vignette: s.vignette,
        ca: s.ca, exposure: s.exposure, fade: s.fade, flash: s.flash,
        threshold: s.threshold, time: t
      };
    }
  }

  return World;
})();
