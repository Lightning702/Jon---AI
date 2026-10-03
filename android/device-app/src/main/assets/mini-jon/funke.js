(function () {
  var FARBEN = {
    idle: ["#fff6dc", "#7fd3ff", "#6b5cff"],
    listening: ["#f2fffb", "#5ff0c8", "#2f8cff"],
    thinking: ["#fff6dc", "#a98bff", "#5b3dff"],
    working: ["#fff4d1", "#ffc56b", "#ff6b9a"],
    speaking: ["#f5fbff", "#8fd8ff", "#4f7dff"],
    happy: ["#fffbe6", "#ffe07a", "#ff9f43"],
    sleeping: ["#e9ecff", "#7a86c9", "#3a3f7a"],
    error: ["#fff0ee", "#ff8f87", "#c2413a"]
  };
  var AGENTEN = ["#7fe0a4", "#79d0ff", "#c7a6ff", "#ffad74", "#f59ccd", "#ffd36a"];

  function mischen(a, b, t) {
    var x = parseInt(a.slice(1), 16), y = parseInt(b.slice(1), 16);
    var r = Math.round(((x >> 16) & 255) + ((((y >> 16) & 255) - ((x >> 16) & 255)) * t));
    var g = Math.round(((x >> 8) & 255) + ((((y >> 8) & 255) - ((x >> 8) & 255)) * t));
    var bl = Math.round((x & 255) + (((y & 255) - (x & 255)) * t));
    return "rgb(" + r + "," + g + "," + bl + ")";
  }

  function create(canvas, optionen) {
    if (!canvas || !canvas.getContext) return null;
    var ctx = canvas.getContext("2d");
    if (!ctx) return null;
    optionen = optionen || {};
    var ruhig = false;
    try { ruhig = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}
    var zustand = "idle", vorher = "idle", wechsel = 0, laeuft = false, frame = 0, zuletzt = 0, start = performance.now();
    var pegel = 0, glatt = 0, blinzeln = 0, naechstesBlinzeln = 2.2, blick = {x: 0, y: 0}, blickZiel = {x: 0, y: 0}, blickWechsel = 0;
    var funken = [], glut = [], agenten = 0, freude = 0, breite = 0, hoehe = 0;
    for (var i = 0; i < 10; i++) funken.push({w: Math.random() * Math.PI * 2, r: 0.62 + Math.random() * 0.3, s: 0.4 + Math.random() * 0.6, g: 0.6 + Math.random() * 0.8, k: Math.random() * 0.5 - 0.25});

    function messen() {
      var dpr = Math.min(window.devicePixelRatio || 1, 2.5);
      var b = canvas.clientWidth || canvas.width || 200, h = canvas.clientHeight || canvas.height || 200;
      if (b !== breite || h !== hoehe || canvas.width !== Math.round(b * dpr)) {
        breite = b; hoehe = h;
        canvas.width = Math.round(b * dpr); canvas.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function farben(t) {
      var neu = FARBEN[zustand] || FARBEN.idle, alt = FARBEN[vorher] || FARBEN.idle;
      var k = Math.min(1, (t - wechsel) / 0.6);
      return [mischen(alt[0], neu[0], k), mischen(alt[1], neu[1], k), mischen(alt[2], neu[2], k)];
    }

    function flamme(cx, cy, r, t, f) {
      var flackern = Math.sin(t * 7.3) * 0.06 + Math.sin(t * 11.1) * 0.04;
      var spitze = r * (1.55 + flackern + (zustand === "working" ? 0.25 : 0) + freude * 0.3);
      var neigung = Math.sin(t * 1.7) * r * 0.18;
      ctx.beginPath();
      ctx.moveTo(cx - r, cy);
      ctx.bezierCurveTo(cx - r, cy - r * 0.9, cx - r * 0.35 + neigung * 0.4, cy - spitze * 0.75, cx + neigung, cy - spitze);
      ctx.bezierCurveTo(cx + r * 0.35 + neigung * 0.4, cy - spitze * 0.75, cx + r, cy - r * 0.9, cx + r, cy);
      ctx.arc(cx, cy, r, 0, Math.PI, false);
      ctx.closePath();
      var verlauf = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.35, r * 0.1, cx, cy - r * 0.2, spitze * 1.1);
      verlauf.addColorStop(0, f[0]);
      verlauf.addColorStop(0.45, f[1]);
      verlauf.addColorStop(1, f[2]);
      ctx.fillStyle = verlauf;
      ctx.shadowColor = f[1];
      ctx.shadowBlur = r * (0.9 + glatt * 0.8 + (zustand === "working" ? 0.4 : 0));
      ctx.fill();
      ctx.shadowBlur = 0;
      var glanz = ctx.createRadialGradient(cx - r * 0.38, cy - r * 0.42, 0, cx - r * 0.38, cy - r * 0.42, r * 0.6);
      glanz.addColorStop(0, "rgba(255,255,255,0.75)");
      glanz.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = glanz;
      ctx.beginPath();
      ctx.arc(cx - r * 0.38, cy - r * 0.42, r * 0.6, 0, Math.PI * 2);
      ctx.fill();
    }

    function gesicht(cx, cy, r, t) {
      var augenAbstand = r * 0.36, augenY = cy - r * 0.08 + blick.y * r * 0.06;
      var offen = 1 - blinzeln;
      var schlaf = zustand === "sleeping";
      ctx.fillStyle = "rgba(20,18,40,0.92)";
      ctx.strokeStyle = "rgba(20,18,40,0.92)";
      ctx.lineCap = "round";
      for (var s = -1; s <= 1; s += 2) {
        var ax = cx + s * augenAbstand + blick.x * r * 0.1;
        if (schlaf || zustand === "happy") {
          ctx.lineWidth = r * 0.09;
          ctx.beginPath();
          if (schlaf) ctx.arc(ax, augenY - r * 0.02, r * 0.11, 0.15 * Math.PI, 0.85 * Math.PI);
          else ctx.arc(ax, augenY + r * 0.06, r * 0.12, 1.15 * Math.PI, 1.85 * Math.PI);
          ctx.stroke();
          continue;
        }
        var ah = r * (zustand === "listening" ? 0.3 : 0.26) * Math.max(0.08, offen), ab = r * 0.17;
        ctx.beginPath();
        ctx.ellipse(ax, augenY, ab / 2, ah / 2, 0, 0, Math.PI * 2);
        ctx.fill();
        if (offen > 0.4) {
          ctx.fillStyle = "rgba(255,255,255,0.9)";
          ctx.beginPath();
          ctx.arc(ax + ab * 0.18 + blick.x * r * 0.03, augenY - ah * 0.2, r * 0.035, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = "rgba(20,18,40,0.92)";
        }
      }
      ctx.lineWidth = r * 0.075;
      ctx.beginPath();
      var my = cy + r * 0.3, mb = r * 0.2;
      if (zustand === "speaking") {
        var oeffnung = r * (0.05 + glatt * 0.16 + Math.abs(Math.sin(t * 12)) * 0.05);
        ctx.ellipse(cx, my, mb * 0.55, oeffnung, 0, 0, Math.PI * 2);
        ctx.fill();
        return;
      }
      if (zustand === "thinking") {
        ctx.moveTo(cx - mb * 0.6, my + r * 0.02);
        ctx.quadraticCurveTo(cx, my - r * 0.04, cx + mb * 0.7, my - r * 0.05);
      } else if (zustand === "error") {
        ctx.arc(cx, my + r * 0.16, mb * 0.8, 1.2 * Math.PI, 1.8 * Math.PI);
      } else if (schlaf) {
        ctx.arc(cx, my, mb * 0.3, 0, Math.PI * 2);
      } else {
        var laecheln = zustand === "happy" ? 0.95 : zustand === "working" ? 0.55 : 0.7;
        ctx.arc(cx, my - mb * 0.6, mb * laecheln, 0.2 * Math.PI, 0.8 * Math.PI);
      }
      ctx.stroke();
    }

    function zeichnen(jetzt) {
      frame = 0;
      var t = (jetzt - start) / 1000;
      var dt = Math.min(0.05, (jetzt - (zuletzt || jetzt)) / 1000);
      zuletzt = jetzt;
      messen();
      ctx.clearRect(0, 0, breite, hoehe);
      glatt += (pegel - glatt) * 0.25;
      freude = Math.max(0, freude - dt * 0.8);
      if (!ruhig) {
        naechstesBlinzeln -= dt;
        if (naechstesBlinzeln <= 0) { blinzeln = 1; naechstesBlinzeln = 2.5 + Math.random() * 3.5; }
        blinzeln = Math.max(0, blinzeln - dt * 7);
        blickWechsel -= dt;
        if (blickWechsel <= 0) { blickZiel = {x: Math.random() * 2 - 1, y: Math.random() * 1.4 - 0.7}; blickWechsel = 1.4 + Math.random() * 2.4; }
        if (zustand === "thinking") blickZiel = {x: 0.7, y: -0.8};
        if (zustand === "listening" || zustand === "speaking") blickZiel = {x: 0, y: 0};
        blick.x += (blickZiel.x - blick.x) * Math.min(1, dt * 5);
        blick.y += (blickZiel.y - blick.y) * Math.min(1, dt * 5);
      }
      var f = farben(t);
      var basis = Math.min(breite, hoehe);
      var r = basis * 0.22 * (1 + glatt * 0.12 + freude * 0.08);
      var schweben = ruhig ? 0 : Math.sin(t * (zustand === "sleeping" ? 0.9 : 1.8)) * basis * 0.025 - freude * basis * 0.06;
      var cx = breite / 2, cy = hoehe * 0.6 + schweben;
      var tempo = zustand === "working" ? 2.4 : zustand === "thinking" ? 1.7 : zustand === "sleeping" ? 0.15 : 0.6;
      var aura = ctx.createRadialGradient(cx, cy - r * 0.3, r * 0.4, cx, cy - r * 0.3, basis * 0.5);
      aura.addColorStop(0, f[1].replace("rgb", "rgba").replace(")", ",0.28)"));
      aura.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = aura;
      ctx.fillRect(0, 0, breite, hoehe);
      if (zustand === "listening" && !ruhig) {
        for (var w = 0; w < 3; w++) {
          var phase = (t * 0.9 + w / 3) % 1;
          ctx.strokeStyle = f[1].replace("rgb", "rgba").replace(")", "," + (0.45 * (1 - phase) * (0.4 + glatt)) + ")");
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(cx, cy - r * 0.2, r * (1.2 + phase * 1.4), 0, Math.PI * 2);
          ctx.stroke();
        }
      }
      var anzahl = zustand === "working" ? 10 : zustand === "thinking" ? 7 : zustand === "sleeping" ? 2 : 4;
      for (var n = 0; n < anzahl; n++) {
        var p = funken[n];
        if (!ruhig) p.w += dt * tempo * p.s;
        var orbitX = r * (zustand === "working" ? 1.9 : 1.6) * p.r * 1.15, orbitY = r * (zustand === "working" ? 0.9 : 0.75) * p.r;
        var px = cx + Math.cos(p.w) * orbitX, py = cy - r * 0.25 + Math.sin(p.w) * orbitY + Math.sin(p.w * 2 + p.k) * r * 0.12;
        var vorne = Math.sin(p.w) > 0;
        var farbe = zustand === "working" && n < Math.max(agenten, 0) + 4 ? AGENTEN[n % AGENTEN.length] : f[0];
        ctx.globalAlpha = vorne ? 0.95 : 0.45;
        ctx.fillStyle = farbe;
        ctx.shadowColor = farbe;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(px, py, Math.max(1.2, basis * 0.012 * p.g * (vorne ? 1.2 : 0.8)), 0, Math.PI * 2);
        ctx.fill();
        if (zustand === "working" || zustand === "thinking") {
          ctx.globalAlpha *= 0.35;
          ctx.beginPath();
          ctx.arc(cx + Math.cos(p.w - 0.18) * orbitX, cy - r * 0.25 + Math.sin(p.w - 0.18) * orbitY, basis * 0.008 * p.g, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
      ctx.shadowBlur = 0;
      if (!ruhig && zustand !== "sleeping" && Math.random() < (zustand === "working" ? 0.6 : 0.25) + freude) glut.push({x: cx + (Math.random() - 0.5) * r * 0.6, y: cy - r * 1.3, vx: (Math.random() - 0.5) * 18, vy: -(25 + Math.random() * 35) - freude * 60, l: 1, g: 1 + Math.random() * 2});
      for (var g = glut.length - 1; g >= 0; g--) {
        var e = glut[g];
        e.x += e.vx * dt; e.y += e.vy * dt; e.l -= dt * 0.9;
        if (e.l <= 0) { glut.splice(g, 1); continue; }
        ctx.globalAlpha = e.l * 0.85;
        ctx.fillStyle = f[0];
        ctx.beginPath();
        ctx.arc(e.x, e.y, e.g * e.l, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      if (glut.length > 80) glut.splice(0, glut.length - 80);
      flamme(cx, cy, r, ruhig ? 0 : t, f);
      gesicht(cx, cy, r, t);
      if (zustand === "sleeping" && !ruhig) {
        ctx.fillStyle = "rgba(200,210,255,0.7)";
        ctx.font = "600 " + Math.round(r * 0.45) + "px system-ui, sans-serif";
        for (var z = 0; z < 2; z++) {
          var zp = (t * 0.35 + z * 0.5) % 1;
          ctx.globalAlpha = 1 - zp;
          ctx.fillText("z", cx + r * (0.9 + zp * 0.6), cy - r * (1.2 + zp * 1.1));
        }
        ctx.globalAlpha = 1;
      }
      if (laeuft && !ruhig) frame = requestAnimationFrame(zeichnen);
    }

    var api = {
      start: function () { if (laeuft) return; laeuft = true; zuletzt = 0; frame = requestAnimationFrame(zeichnen); },
      stop: function () { laeuft = false; if (frame) cancelAnimationFrame(frame); frame = 0; },
      destroy: function () { api.stop(); funken = []; glut = []; },
      render: function () { zeichnen(performance.now()); },
      setState: function (wert) {
        var neu = FARBEN[wert] ? wert : "idle";
        if (neu === zustand) return;
        vorher = zustand; zustand = neu; wechsel = (performance.now() - start) / 1000;
        if (neu === "happy") freude = 1;
        if (!laeuft || ruhig) api.render();
      },
      setLevel: function (wert) { pegel = Math.max(0, Math.min(1, Number(wert) || 0)); },
      setAgents: function (wert) { agenten = Math.max(0, Math.min(6, Number(wert) || 0)); },
      jubeln: function () { freude = 1; if (!laeuft || ruhig) api.render(); },
      get state() { return zustand; }
    };
    if (optionen.state) api.setState(optionen.state);
    return api;
  }

  window.Funke = {create: create};
})();
