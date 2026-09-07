window.SZENEN = (function () {
  const { el, stil, setze, klemm, spanne, raus, ein, weich, zufall, tippe, stroeme } = window.B;

  function blinzeln(t, zeiten) {
    let w = 1;
    for (const z of zeiten) {
      const d = t - z;
      if (d >= 0 && d < 0.16) {
        const p = d / 0.16;
        w = Math.min(w, Math.abs(Math.cos(p * Math.PI)) < 0.02 ? 0 : 1 - Math.sin(p * Math.PI));
      }
    }
    return klemm(w, 0, 1);
  }

  function reden(t, an) {
    if (!an) return 0;
    return klemm(0.28 + 0.42 * Math.abs(Math.sin(t * 17.3)) + 0.3 * Math.abs(Math.sin(t * 9.1 + 1.2)), 0, 1);
  }

  function zeigeSchild(s, t, von, bis, wo) {
    const a = ein(t, von, 0.22);
    const b = 1 - ein(t, bis, 0.3);
    const p = Math.min(a, b);
    stil(s, { opacity: p, transform: "translateY(" + ((1 - a) * 10).toFixed(2) + "px)" });
    if (wo) stil(s, wo);
  }

  function fensterAuf(f, p) {
    stil(f, {
      opacity: p,
      transform: "translateY(" + ((1 - p) * 16).toFixed(2) + "px) scale(" + (0.988 + 0.012 * p).toFixed(4) + ")",
    });
  }

  function schreiber(text, laeuft, t) {
    const blink = Math.floor(t * 2) % 2 === 0;
    return text + (laeuft || blink ? '<span class="schreiber"></span>' : "");
  }

  function setzeText(n, s, laeuft, t) {
    n.innerHTML = "";
    n.appendChild(document.createTextNode(s));
    if (laeuft || Math.floor(t * 2) % 2 === 0) {
      const c = el("span", "schreiber");
      n.appendChild(c);
    }
  }

  function qrBild(seite) {
    const n = 25;
    let s = '<svg viewBox="0 0 25 25" width="' + seite + '" height="' + seite + '" shape-rendering="crispEdges">';
    s += '<rect width="25" height="25" fill="#f4f1e8"/>';
    const finder = (x, y) =>
      '<rect x="' + x + '" y="' + y + '" width="7" height="7" fill="#0b0b0f"/>' +
      '<rect x="' + (x + 1) + '" y="' + (y + 1) + '" width="5" height="5" fill="#f4f1e8"/>' +
      '<rect x="' + (x + 2) + '" y="' + (y + 2) + '" width="3" height="3" fill="#0b0b0f"/>';
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const imFinder =
          (x < 8 && y < 8) || (x > 16 && y < 8) || (x < 8 && y > 16);
        if (imFinder) continue;
        if (zufall(x * 31.7 + y * 17.3) > 0.52)
          s += '<rect x="' + x + '" y="' + y + '" width="1" height="1" fill="#0b0b0f"/>';
      }
    }
    s += finder(0, 0) + finder(18, 0) + finder(0, 18);
    return s + "</svg>";
  }

  function kachelBild(art) {
    const g = {
      echo:
        '<svg viewBox="0 0 120 78"><rect width="120" height="78" fill="#07070b"/>' +
        '<circle cx="60" cy="39" r="9" fill="none" stroke="#f5d67b" stroke-width="1.6"/>' +
        '<circle cx="60" cy="39" r="18" fill="none" stroke="rgba(212,175,55,.6)" stroke-width="1.2"/>' +
        '<circle cx="60" cy="39" r="27" fill="none" stroke="rgba(212,175,55,.32)" stroke-width="1"/>' +
        '<circle cx="60" cy="39" r="35" fill="none" stroke="rgba(212,175,55,.16)" stroke-width="1"/></svg>',
      aetheria:
        '<svg viewBox="0 0 120 78"><rect width="120" height="78" fill="#070a10"/>' +
        '<path d="M18 52 L44 52 L36 62 L26 62 Z" fill="#2c3b4e"/><rect x="22" y="46" width="18" height="6" fill="#3f5a45"/>' +
        '<path d="M62 34 L96 34 L88 45 L70 45 Z" fill="#2c3b4e"/><rect x="66" y="28" width="26" height="6" fill="#3f5a45"/>' +
        '<circle cx="94" cy="16" r="7" fill="rgba(245,214,123,.5)"/></svg>',
      starfall:
        '<svg viewBox="0 0 120 78"><rect width="120" height="78" fill="#04040a"/>' +
        '<ellipse cx="60" cy="39" rx="40" ry="9" fill="none" stroke="rgba(245,214,123,.75)" stroke-width="2.4"/>' +
        '<ellipse cx="60" cy="39" rx="26" ry="6" fill="none" stroke="rgba(212,175,55,.45)" stroke-width="1.6"/>' +
        '<circle cx="60" cy="39" r="10" fill="#000"/><circle cx="60" cy="39" r="11" fill="none" stroke="rgba(255,255,255,.25)" stroke-width="1"/></svg>',
      harmonie:
        '<svg viewBox="0 0 120 78"><rect width="120" height="78" fill="#050a0c"/>' +
        '<path d="M0 54 Q30 40 60 54 T120 54 V78 H0 Z" fill="#123038"/>' +
        '<path d="M0 62 Q30 50 60 62 T120 62 V78 H0 Z" fill="#0c2129"/>' +
        '<ellipse cx="46" cy="47" rx="15" ry="5" fill="#2f5b46"/><ellipse cx="82" cy="55" rx="11" ry="4" fill="#26493a"/></svg>',
      blockwelt:
        '<svg viewBox="0 0 120 78"><rect width="120" height="78" fill="#080a0e"/>' +
        '<path d="M60 22 L84 34 L60 46 L36 34 Z" fill="#4c7a3f"/><path d="M36 34 L60 46 L60 66 L36 54 Z" fill="#3a5c30"/><path d="M84 34 L60 46 L60 66 L84 54 Z" fill="#2e4a26"/>' +
        '<path d="M84 22 L96 28 L84 34 L72 28 Z" fill="#7a6242"/><path d="M72 28 L84 34 L84 44 L72 38 Z" fill="#5d4a33"/><path d="M96 28 L84 34 L84 44 L96 38 Z" fill="#4b3b28"/></svg>',
    };
    return g[art];
  }

  function malLeuchtturm(ctx, b, h, feinheit) {
    const q = klemm(feinheit, 0.05, 1);
    const bb = Math.max(8, Math.round(b * q));
    const hh = Math.max(6, Math.round(h * q));
    const o = malLeuchtturm.puffer || (malLeuchtturm.puffer = document.createElement("canvas"));
    o.width = bb;
    o.height = hh;
    const c = o.getContext("2d");
    c.setTransform(bb / b, 0, 0, hh / h, 0, 0);

    const hor = h * 0.665;
    const himmel = c.createLinearGradient(0, 0, 0, hor);
    himmel.addColorStop(0, "#04050a");
    himmel.addColorStop(0.55, "#0d131d");
    himmel.addColorStop(0.86, "#232e3c");
    himmel.addColorStop(1, "#33404f");
    c.fillStyle = himmel;
    c.fillRect(0, 0, b, hor + 2);

    const mond = c.createRadialGradient(b * 0.24, h * 0.3, 0, b * 0.24, h * 0.3, h * 0.42);
    mond.addColorStop(0, "rgba(150,168,190,0.2)");
    mond.addColorStop(1, "rgba(150,168,190,0)");
    c.fillStyle = mond;
    c.fillRect(0, 0, b, hor);

    for (let i = 0; i < 26; i++) {
      const x = zufall(i * 3.1) * b * 1.3 - b * 0.15;
      const y = zufall(i * 7.7 + 2) * hor * 0.86;
      const r = b * (0.09 + zufall(i * 5.3 + 9) * 0.19);
      const g = c.createRadialGradient(x, y - r * 0.2, 0, x, y, r);
      const hell = zufall(i * 2.9 + 5);
      g.addColorStop(0, "rgba(" + Math.round(34 + hell * 46) + "," + Math.round(40 + hell * 50) + "," + Math.round(52 + hell * 58) + ",0.5)");
      g.addColorStop(1, "rgba(20,24,32,0)");
      c.fillStyle = g;
      c.beginPath();
      c.ellipse(x, y, r, r * 0.42, 0, 0, 6.3);
      c.fill();
    }

    const turmX = b * 0.635;
    const turmFuss = hor + h * 0.028;
    const turmKopf = turmFuss - h * 0.45;
    const bR = b * 0.036;
    const oR = b * 0.023;

    c.save();
    c.globalCompositeOperation = "lighter";
    [[-2.42, 0.14], [0.42, 0.1]].forEach(function (paar) {
      const w = paar[0];
      const weite = paar[1];
      const g = c.createLinearGradient(turmX, turmKopf, turmX + Math.cos(w) * b, turmKopf + Math.sin(w) * b);
      g.addColorStop(0, "rgba(245,214,123,0.4)");
      g.addColorStop(0.45, "rgba(245,214,123,0.13)");
      g.addColorStop(1, "rgba(245,214,123,0)");
      c.fillStyle = g;
      c.beginPath();
      c.moveTo(turmX, turmKopf);
      c.lineTo(turmX + Math.cos(w - weite) * b * 1.6, turmKopf + Math.sin(w - weite) * b * 1.6);
      c.lineTo(turmX + Math.cos(w + weite) * b * 1.6, turmKopf + Math.sin(w + weite) * b * 1.6);
      c.closePath();
      c.fill();
    });
    c.restore();

    const meer = c.createLinearGradient(0, hor, 0, h);
    meer.addColorStop(0, "#1a232e");
    meer.addColorStop(0.35, "#0d151f");
    meer.addColorStop(1, "#050a11");
    c.fillStyle = meer;
    c.fillRect(0, hor, b, h - hor);

    for (let i = 0; i < 90; i++) {
      const tiefe = Math.pow(zufall(i * 2.3), 1.6);
      const y = hor + 3 + tiefe * (h - hor);
      const x = zufall(i * 9.1 + 4) * b;
      const w = (14 + zufall(i * 4.4) * 70) * (0.35 + tiefe);
      const a = (0.08 + zufall(i * 6.6) * 0.3) * (0.35 + tiefe);
      c.strokeStyle = "rgba(196,214,232," + a.toFixed(3) + ")";
      c.lineWidth = 0.8 + tiefe * 2.6;
      c.beginPath();
      c.moveTo(x, y);
      c.bezierCurveTo(x + w * 0.3, y - 2 - tiefe * 4, x + w * 0.6, y + 2 + tiefe * 4, x + w, y);
      c.stroke();
    }
    c.fillStyle = "rgba(212,175,55,0.07)";
    c.beginPath();
    c.moveTo(turmX - b * 0.05, hor);
    c.lineTo(turmX + b * 0.05, hor);
    c.lineTo(turmX + b * 0.16, h);
    c.lineTo(turmX - b * 0.16, h);
    c.closePath();
    c.fill();

    c.fillStyle = "#05080d";
    c.beginPath();
    c.moveTo(b * 0.33, h);
    c.lineTo(b * 0.4, turmFuss + h * 0.07);
    c.bezierCurveTo(b * 0.47, turmFuss - h * 0.02, b * 0.55, turmFuss - h * 0.035, b * 0.63, turmFuss - h * 0.03);
    c.bezierCurveTo(b * 0.72, turmFuss - h * 0.025, b * 0.8, turmFuss + h * 0.03, b * 0.86, turmFuss + h * 0.1);
    c.lineTo(b * 0.94, h);
    c.closePath();
    c.fill();
    c.strokeStyle = "rgba(150,168,190,0.16)";
    c.lineWidth = 1.4;
    c.beginPath();
    c.moveTo(b * 0.4, turmFuss + h * 0.07);
    c.bezierCurveTo(b * 0.47, turmFuss - h * 0.02, b * 0.55, turmFuss - h * 0.035, b * 0.63, turmFuss - h * 0.03);
    c.stroke();

    const stein = c.createLinearGradient(turmX - bR, 0, turmX + bR, 0);
    stein.addColorStop(0, "#5d6572");
    stein.addColorStop(0.35, "#b9b7ac");
    stein.addColorStop(0.72, "#8d8c85");
    stein.addColorStop(1, "#3f4650");
    c.fillStyle = stein;
    c.beginPath();
    c.moveTo(turmX - bR, turmFuss);
    c.lineTo(turmX - oR, turmKopf + h * 0.03);
    c.lineTo(turmX + oR, turmKopf + h * 0.03);
    c.lineTo(turmX + bR, turmFuss);
    c.closePath();
    c.fill();

    c.fillStyle = "rgba(28,32,40,0.72)";
    for (let i = 0; i < 3; i++) {
      const p0 = 0.12 + i * 0.3;
      const p1 = p0 + 0.13;
      const y0 = turmKopf + h * 0.03 + (turmFuss - turmKopf - h * 0.03) * p0;
      const y1 = turmKopf + h * 0.03 + (turmFuss - turmKopf - h * 0.03) * p1;
      const r0 = oR + (bR - oR) * p0;
      const r1 = oR + (bR - oR) * p1;
      c.beginPath();
      c.moveTo(turmX - r0, y0);
      c.lineTo(turmX + r0, y0);
      c.lineTo(turmX + r1, y1);
      c.lineTo(turmX - r1, y1);
      c.closePath();
      c.fill();
    }

    c.fillStyle = "#2b313b";
    c.fillRect(turmX - oR * 1.5, turmKopf + h * 0.012, oR * 3, h * 0.02);
    c.fillStyle = "#171c24";
    c.fillRect(turmX - oR * 1.25, turmKopf - h * 0.045, oR * 2.5, h * 0.058);
    c.strokeStyle = "#39404c";
    c.lineWidth = 1.2;
    for (let i = -1; i <= 1; i++) {
      c.beginPath();
      c.moveTo(turmX + i * oR * 0.8, turmKopf - h * 0.045);
      c.lineTo(turmX + i * oR * 0.8, turmKopf + h * 0.013);
      c.stroke();
    }
    const halo = c.createRadialGradient(turmX, turmKopf - h * 0.016, 0, turmX, turmKopf - h * 0.016, h * 0.14);
    halo.addColorStop(0, "rgba(255,238,190,0.95)");
    halo.addColorStop(0.16, "rgba(245,214,123,0.6)");
    halo.addColorStop(1, "rgba(245,214,123,0)");
    c.fillStyle = halo;
    c.beginPath();
    c.arc(turmX, turmKopf - h * 0.016, h * 0.14, 0, 6.3);
    c.fill();
    c.fillStyle = "#2b313b";
    c.beginPath();
    c.moveTo(turmX - oR * 1.45, turmKopf - h * 0.045);
    c.lineTo(turmX, turmKopf - h * 0.088);
    c.lineTo(turmX + oR * 1.45, turmKopf - h * 0.045);
    c.closePath();
    c.fill();

    c.save();
    c.globalCompositeOperation = "lighter";
    for (let i = 0; i < 120; i++) {
      const x = zufall(i * 13.7) * b * 1.2 - b * 0.1;
      const y = zufall(i * 3.9 + 7) * h;
      const l = 10 + zufall(i * 5.1) * 26;
      c.strokeStyle = "rgba(206,222,240," + (0.05 + zufall(i * 2.2) * 0.11).toFixed(3) + ")";
      c.lineWidth = 1;
      c.beginPath();
      c.moveTo(x, y);
      c.lineTo(x - l * 0.36, y + l);
      c.stroke();
    }
    c.restore();

    for (let i = 0; i < 22; i++) {
      const x = b * 0.34 + zufall(i * 4.7) * b * 0.58;
      const y = turmFuss + h * 0.02 + zufall(i * 8.3) * h * 0.1;
      const r = b * (0.008 + zufall(i * 6.1) * 0.028);
      const g = c.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, "rgba(222,234,246,0.2)");
      g.addColorStop(1, "rgba(222,234,246,0)");
      c.fillStyle = g;
      c.beginPath();
      c.arc(x, y, r, 0, 6.3);
      c.fill();
    }

    const dunkel = c.createRadialGradient(b * 0.55, h * 0.46, h * 0.24, b * 0.5, h * 0.5, h * 1.02);
    dunkel.addColorStop(0, "rgba(0,0,0,0)");
    dunkel.addColorStop(1, "rgba(0,0,0,0.62)");
    c.fillStyle = dunkel;
    c.fillRect(0, 0, b, h);

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, b, h);
    ctx.imageSmoothingEnabled = q > 0.55;
    ctx.drawImage(o, 0, 0, bb, hh, 0, 0, b, h);
  }

  const S = [];

  S.push({
    id: "kaltstart",
    von: 0,
    bis: 7,
    bau(w) {
      this.hg = w.appendChild(window.B.hintergrund());
      w.appendChild(window.B.schreibtischsymbole());
      w.appendChild(window.B.taskleiste("06:42", "01.09.2026"));
      this.mini = w.appendChild(window.B.miniJon(104));
      stil(this.mini, { left: "1596px", top: "882px" });
      this.blase = w.appendChild(window.B.sprechblase("", 342));
      stil(this.blase, { left: "1424px", top: "672px" });
    },
    zeig(t) {
      const p = ein(t, 0.15, 1.5);
      stil(this.hg.parentNode, { opacity: 1 });
      stil(this.hg, { opacity: 1 });
      this.hg.parentNode.style.filter = "none";
      stil(this.hg.parentNode, {
        transform: "scale(" + (1.012 - 0.012 * p).toFixed(4) + ")",
        transformOrigin: "50% 60%",
        opacity: p,
      });
      const q = ein(t, 1.55, 0.45);
      const wack = t > 2.45 && t < 3.0 ? Math.sin((t - 2.45) * 15) * 4.5 * (1 - (t - 2.45) / 0.55) : 0;
      stil(this.mini, {
        opacity: q,
        transform:
          "translateY(" + ((1 - q) * 12).toFixed(2) + "px) scale(" + (0.82 + 0.18 * q).toFixed(3) +
          ") rotate(" + wack.toFixed(2) + "deg)",
      });
      const s = stroeme(
        "Guten Morgen, Felix. Drei ungelesene Mails, ab 16 Uhr Regen — soll ich dir die Jacke auf die Merkliste setzen?",
        t, 3.05, 7.6,
      );
      window.B.miniStand(this.mini, {
        blinzeln: blinzeln(t, [2.08, 4.35, 6.28]),
        mund: reden(t, s.laeuft),
      });
      const bp = ein(t, 2.92, 0.28);
      this.blase.textContent = s.text;
      stil(this.blase, { opacity: bp, transform: "translateY(" + ((1 - bp) * 10).toFixed(2) + "px)" });
    },
  });

  S.push({
    id: "titel",
    von: 7,
    bis: 13,
    bau(w) {
      stil(w, { background: "#000" });
      this.t = w.appendChild(el("div", "gold", "Jon"));
      stil(this.t, {
        position: "absolute",
        left: "0",
        right: "0",
        top: "402px",
        textAlign: "center",
        fontSize: "152px",
        fontWeight: "200",
        lineHeight: "1",
      });
      this.linie = w.appendChild(el("div"));
      stil(this.linie, {
        position: "absolute",
        left: "960px",
        top: "594px",
        height: "1px",
        background: "linear-gradient(90deg, rgba(212,175,55,0), rgba(212,175,55,.85), rgba(212,175,55,0))",
      });
      this.u = w.appendChild(el("div", null, "Ein Assistent, der deinen PC wirklich bedient."));
      stil(this.u, {
        position: "absolute",
        left: "0",
        right: "0",
        top: "628px",
        textAlign: "center",
        fontSize: "31px",
        fontWeight: "300",
        letterSpacing: "0.14em",
        color: "rgba(246,242,232,0.62)",
      });
    },
    zeig(t) {
      const p = ein(t, 0.55, 1.3);
      const ls = 0.34 - 0.24 * p;
      stil(this.t, {
        opacity: p,
        letterSpacing: ls.toFixed(4) + "em",
        textIndent: (ls * 152).toFixed(1) + "px",
        filter: "drop-shadow(0 0 " + (46 * p).toFixed(1) + "px rgba(212,175,55," + (0.3 * p).toFixed(3) + "))",
      });
      const l = ein(t, 1.5, 1.1) * 440;
      stil(this.linie, { width: l.toFixed(1) + "px", marginLeft: (-l / 2).toFixed(1) + "px", opacity: ein(t, 1.5, 0.5) });
      const q = ein(t, 1.95, 0.9);
      stil(this.u, { opacity: 0.86 * q, transform: "translateY(" + ((1 - q) * 8).toFixed(2) + "px)" });
    },
  });

  function baueExplorer() {
    const f = el("div", "fenster");
    stil(f, {
      left: "64px", top: "152px", width: "690px", height: "648px",
      background: "rgba(24,24,29,0.96)", border: "1px solid rgba(255,255,255,0.1)",
      display: "flex", flexDirection: "column",
    });
    const kopf = el("div");
    stil(kopf, {
      height: "42px", display: "flex", alignItems: "center", gap: "10px", padding: "0 14px",
      borderBottom: "1px solid rgba(255,255,255,0.07)", color: "rgba(255,255,255,.8)", fontSize: "13.5px",
    });
    kopf.innerHTML =
      '<span style="transform:scale(.8);display:inline-flex">' + window.B.symbol("ordner") + "</span>Downloads" +
      '<span style="margin-left:auto;color:rgba(255,255,255,.35);font-size:13px">—  ▢  ✕</span>';
    f.appendChild(kopf);
    const pfad = el("div");
    stil(pfad, {
      height: "36px", display: "flex", alignItems: "center", padding: "0 14px", gap: "8px",
      fontSize: "12.5px", color: "rgba(255,255,255,.45)", borderBottom: "1px solid rgba(255,255,255,0.05)",
    });
    pfad.innerHTML = "Dieser PC  ›  Benutzer  ›  Felix  ›  <span style='color:rgba(255,255,255,.75)'>Downloads</span>";
    f.appendChild(pfad);
    const spalten = el("div");
    stil(spalten, {
      display: "grid", gridTemplateColumns: "1fr 150px 120px 90px", padding: "8px 14px",
      fontSize: "11.5px", color: "rgba(255,255,255,.32)", borderBottom: "1px solid rgba(255,255,255,0.06)",
    });
    spalten.innerHTML = "<div>Name</div><div>Änderungsdatum</div><div>Typ</div><div>Größe</div>";
    f.appendChild(spalten);
    const liste = el("div");
    stil(liste, { flex: "1", padding: "4px 6px", overflow: "hidden" });
    f.appendChild(liste);
    const fuss = el("div");
    stil(fuss, {
      height: "34px", display: "flex", alignItems: "center", padding: "0 14px", fontSize: "12px",
      color: "rgba(255,255,255,.4)", borderTop: "1px solid rgba(255,255,255,0.06)", gap: "12px",
    });
    f.appendChild(fuss);
    f.liste = liste;
    f.fuss = fuss;

    const dateien = [
      ["rechnung_august.pdf", "28.08.2026 14:02", "PDF-Datei", "218 KB"],
      ["urlaub_2026_047.jpg", "27.08.2026 21:19", "JPG-Datei", "4,2 MB"],
      ["setup_treiber.exe", "27.08.2026 09:44", "Anwendung", "142 MB"],
      ["projekt_final.zip", "26.08.2026 18:31", "ZIP-Archiv", "1,1 GB"],
      ["vertrag_scan.pdf", "26.08.2026 11:07", "PDF-Datei", "902 KB"],
      ["screenshot_042.png", "25.08.2026 22:55", "PNG-Datei", "1,8 MB"],
      ["hintergrund_4k.jpg", "25.08.2026 16:20", "JPG-Datei", "7,4 MB"],
      ["archiv_alt.rar", "24.08.2026 08:12", "RAR-Archiv", "612 MB"],
      ["notizen_meeting.pdf", "23.08.2026 19:48", "PDF-Datei", "76 KB"],
      ["installer_tool.msi", "23.08.2026 10:03", "Windows-Paket", "88 MB"],
    ];
    f.zeilen = dateien.map((d) => {
      const z = el("div");
      stil(z, {
        display: "grid", gridTemplateColumns: "1fr 150px 120px 90px", alignItems: "center",
        padding: "9px 8px", borderRadius: "7px", fontSize: "13px", color: "rgba(255,255,255,.72)",
      });
      z.innerHTML =
        '<div style="display:flex;align-items:center;gap:9px;overflow:hidden;white-space:nowrap">' +
        '<span style="width:15px;height:18px;border-radius:2px;background:rgba(255,255,255,.14);display:inline-block;flex:none"></span>' +
        d[0] + "</div>" +
        '<div style="font-size:12px;color:rgba(255,255,255,.38)">' + d[1] + "</div>" +
        '<div style="font-size:12px;color:rgba(255,255,255,.38)">' + d[2] + "</div>" +
        '<div style="font-size:12px;color:rgba(255,255,255,.38);text-align:right">' + d[3] + "</div>";
      liste.appendChild(z);
      return z;
    });
    f.ordner = [["Bilder", "63 Elemente"], ["PDFs", "48 Elemente"], ["Installer", "39 Elemente"], ["Archive", "64 Elemente"]].map((o) => {
      const z = el("div");
      stil(z, {
        display: "none", gridTemplateColumns: "1fr 150px 120px 90px", alignItems: "center",
        padding: "9px 8px", borderRadius: "7px", fontSize: "13px", color: "rgba(255,255,255,.88)", opacity: 0,
      });
      z.innerHTML =
        '<div style="display:flex;align-items:center;gap:9px"><span style="display:inline-flex;transform:scale(.78)">' +
        window.B.symbol("ordner") + "</span>" + o[0] + "</div>" +
        '<div style="font-size:12px;color:rgba(255,255,255,.38)">01.09.2026 06:43</div>' +
        '<div style="font-size:12px;color:rgba(255,255,255,.38)">Dateiordner</div>' +
        '<div style="font-size:12px;color:rgba(255,255,255,.38);text-align:right">' + o[1] + "</div>";
      liste.insertBefore(z, liste.firstChild);
      return z;
    });
    return f;
  }

  S.push({
    id: "aufraeumen",
    von: 13,
    bis: 23,
    bau(w) {
      w.appendChild(window.B.hintergrund());
      w.appendChild(window.B.taskleiste("06:43", "01.09.2026"));
      this.ex = w.appendChild(baueExplorer());
      this.f = w.appendChild(window.B.jonFenster({ x: 782, y: 176, b: 1076, h: 796 }));
      this.f.koerper.appendChild(
        window.B.seitenleiste([
          ["Downloads aufräumen", "gerade eben"],
          ["Tagesbriefing", "06:41"],
          ["Wissensbasis · Handbuch", "gestern"],
          ["Reise nach Lissabon", "Montag"],
        ]),
      );
      this.chat = this.f.koerper.appendChild(window.B.chatframe || window.B.chatflaeche());
      this.b1 = this.chat.liste.appendChild(window.B.blase("ich", ""));
      this.b2 = this.chat.liste.appendChild(window.B.blase("jon", ""));
      this.b3 = this.chat.liste.appendChild(window.B.blase("jon", ""));
      this.b3.innerHTML = '<div class="werkzeuge"></div><span class="txt"></span>';
      this.b3w = this.b3.querySelector(".werkzeuge");
      this.b3w.innerHTML =
        '<span class="wchip" style="border-color:rgba(143,208,90,.4);background:rgba(143,208,90,.1);color:#bfe89a">' +
        window.B.symbol("haken") + "214 Dateien verschoben</span>";
      this.b3t = this.b3.querySelector(".txt");

      this.modal = w.appendChild(el("div"));
      stil(this.modal, {
        position: "absolute", left: "782px", top: "176px", width: "1076px", height: "796px",
        display: "grid", placeItems: "center", background: "rgba(0,0,0,0.55)", backdropFilter: "blur(3px)",
        zIndex: 50, opacity: 0,
      });
      const karte = el("div", "glas goldrand");
      stil(karte, { width: "540px", borderRadius: "18px", padding: "26px 28px" });
      karte.innerHTML =
        '<div style="display:flex;align-items:center;gap:9px;margin-bottom:14px">' +
        '<span style="width:9px;height:9px;border-radius:50%;background:#d4af37"></span>' +
        '<span class="gold" style="font-size:16px;font-weight:600">Jon möchte etwas ausführen</span></div>' +
        '<div style="font-size:15px;color:rgba(255,255,255,.86);line-height:1.6">' +
        '<span style="display:inline-block;font-size:13px;padding:3px 10px;border-radius:9px;background:rgba(212,175,55,.1);border:1px solid rgba(212,175,55,.28);color:rgba(245,214,123,.92);margin-right:10px">📁 Dateien verschieben</span>' +
        "214 Dateien aus <b>C:\\Users\\Felix\\Downloads</b> in vier neue Ordner sortieren.</div>" +
        '<div style="margin-top:12px;font-size:12.5px;color:rgba(245,214,123,.6)">Details anzeigen</div>' +
        '<div style="display:flex;justify-content:flex-end;gap:12px;margin-top:26px">' +
        '<div class="ab" style="padding:11px 22px;border-radius:12px;border:1px solid rgba(255,255,255,.16);color:rgba(255,255,255,.7);font-size:14px">Ablehnen</div>' +
        '<div class="ok" style="padding:11px 24px;border-radius:12px;background:linear-gradient(135deg,#f5d67b,#9a7b1f);color:#0a0a0c;font-size:14px;font-weight:600">Erlauben</div></div>';
      this.modal.appendChild(karte);
      this.karte = karte;
      this.ok = karte.querySelector(".ok");
      this.zeiger = w.appendChild(window.B.zeiger());
      this.schild = w.appendChild(window.B.schild("Er fragt zuerst. Immer."));
      stil(this.schild, { right: "84px", top: "72px", textAlign: "right" });
    },
    zeig(t) {
      fensterAuf(this.f, ein(t, 0, 0.28));
      stil(this.ex, { opacity: ein(t, 0.1, 0.5) * 0.96 });

      const tp = tippe("Jon, räum meinen Downloads-Ordner auf und sortier alles nach Typ.", t, 0.45, 45);
      const gesendet = t >= 2.05;
      if (!gesendet) {
        this.chat.feld.className = "feld" + (tp.text ? "" : " leer");
        setzeText(this.chat.feld, tp.text || "Frag Jon...", tp.laeuft, t);
        if (!tp.text) this.chat.feld.textContent = "Frag Jon...";
      } else {
        this.chat.feld.className = "feld leer";
        this.chat.feld.textContent = "Frag Jon...";
      }
      this.b1.style.display = gesendet ? "block" : "none";
      this.b1.textContent = "Jon, räum meinen Downloads-Ordner auf und sortier alles nach Typ.";
      const e1 = ein(t, 2.05, 0.2);
      stil(this.b1, { opacity: e1, transform: "translateY(" + ((1 - e1) * 8).toFixed(1) + "px)" });

      const s2 = stroeme("Ich sehe 214 Dateien. Ich lege Ordner für Bilder, PDFs, Installer und Archive an. Soll ich?", t, 2.45, 7.4);
      this.b2.style.display = t >= 2.45 ? "block" : "none";
      setzeText(this.b2, s2.text, s2.laeuft, t);

      const m = ein(t, 4.88, 0.2) * (1 - ein(t, 6.12, 0.16));
      stil(this.modal, { opacity: m });
      stil(this.karte, { transform: "scale(" + (0.97 + 0.03 * ein(t, 4.88, 0.24)).toFixed(4) + ")" });
      const gedrueckt = t >= 5.98 && t < 6.14;
      stil(this.ok, {
        filter: gedrueckt ? "brightness(1.28)" : "none",
        transform: gedrueckt ? "scale(0.97)" : "scale(1)",
      });

      const zp = spanne(t, 5.18, 5.96);
      const zx = 1216 + (1494 - 1216) * weich(zp);
      const zy = 848 + (634 - 848) * weich(zp);
      stil(this.zeiger, {
        opacity: t > 5.1 && t < 6.5 ? 1 : 0,
        transform: "translate(" + zx.toFixed(1) + "px," + zy.toFixed(1) + "px)",
      });

      const sort = spanne(t, 6.2, 8.15);
      this.ex.zeilen.forEach((z, i) => {
        const p = klemm((sort * 10.6 - i) / 1.1, 0, 1);
        stil(z, {
          opacity: (1 - p).toFixed(3),
          transform: "translateX(" + (p * 42).toFixed(1) + "px)",
          height: p > 0.98 ? "0px" : "",
          padding: p > 0.98 ? "0px 8px" : "",
        });
      });
      this.ex.ordner.forEach((o, i) => {
        const p = ein(t, 6.55 + i * 0.36, 0.34);
        stil(o, { display: p > 0 ? "grid" : "none", opacity: p, transform: "translateY(" + ((1 - p) * 10).toFixed(1) + "px)" });
      });
      const proz = Math.round(sort * 100);
      this.ex.fuss.innerHTML =
        t < 6.2
          ? '<span>10 Elemente</span><span style="color:rgba(255,255,255,.28)">3,1 GB</span>'
          : sort < 1
            ? '<span style="color:rgba(245,214,123,.85)">Sortiert … ' + proz + " %</span>" +
              '<span style="flex:1;height:4px;border-radius:3px;background:rgba(255,255,255,.08);overflow:hidden;max-width:220px">' +
              '<span style="display:block;height:100%;width:' + proz + '%;background:linear-gradient(90deg,#f5d67b,#d4af37)"></span></span>'
            : '<span style="color:#8fd05a">Fertig · 4 Ordner · 3,1 GB</span>';

      const s3 = stroeme("Fertig. 214 Dateien in 4 Ordnern, 3,1 GB aufgeräumt.", t, 8.4, 7);
      this.b3.style.display = t >= 8.35 ? "block" : "none";
      const e3 = ein(t, 8.35, 0.2);
      stil(this.b3, { opacity: e3 });
      setzeText(this.b3t, s3.text, s3.laeuft, t);

      zeigeSchild(this.schild, t, 4.95, 9.5);
    },
  });

  S.push({
    id: "suche",
    von: 23,
    bis: 32,
    bau(w) {
      w.appendChild(window.B.hintergrund());
      w.appendChild(window.B.taskleiste("06:44", "01.09.2026"));
      this.f = w.appendChild(window.B.jonFenster({ x: 336, y: 128, b: 1248, h: 824 }));
      this.f.koerper.appendChild(
        window.B.seitenleiste([
          ["Preis nachschlagen", "gerade eben"],
          ["Downloads aufräumen", "06:43"],
          ["Tagesbriefing", "06:41"],
          ["Wissensbasis · Handbuch", "gestern"],
        ]),
      );
      this.chat = this.f.koerper.appendChild(window.B.chatflaeche());
      this.b1 = this.chat.liste.appendChild(window.B.blase("ich", ""));
      this.b2 = this.chat.liste.appendChild(window.B.blase("jon", ""));
      this.b2.innerHTML =
        '<div class="werkzeuge"><span class="wchip"><span class="lampe"></span>🔎 Websuche · DuckDuckGo · liest 3 Seiten</span></div>' +
        '<div class="seiten" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px"></div>' +
        '<span class="txt"></span><div class="quelle"></div>';
      this.chip = this.b2.querySelector(".wchip");
      this.lampe = this.b2.querySelector(".lampe");
      this.seiten = this.b2.querySelector(".seiten");
      this.b2t = this.b2.querySelector(".txt");
      this.quelle = this.b2.querySelector(".quelle");
      ["apple.com", "preisvergleich.de", "haendler-shop.de"].forEach((n) => {
        const z = el("div");
        stil(z, { display: "flex", alignItems: "center", gap: "9px", fontSize: "13px", color: "rgba(255,255,255,.42)", opacity: 0 });
        z.innerHTML = '<span style="display:inline-flex;transform:scale(.78)">' + window.B.symbol("haken") + "</span>" + n;
        this.seiten.appendChild(z);
      });
      this.schild = w.appendChild(window.B.schild("Kein Raten.", "Er schaut nach."));
      stil(this.schild, { left: "84px", top: "72px" });
    },
    zeig(t) {
      fensterAuf(this.f, ein(t, 0, 0.26));
      const tp = tippe("Was kostet das neue iPhone?", t, 0.35, 45);
      const gesendet = t >= 1.05;
      this.chat.feld.className = "feld" + (!gesendet && tp.text ? "" : " leer");
      if (!gesendet && tp.text) setzeText(this.chat.feld, tp.text, tp.laeuft, t);
      else this.chat.feld.textContent = "Frag Jon...";
      this.b1.style.display = gesendet ? "block" : "none";
      this.b1.textContent = "Was kostet das neue iPhone?";
      stil(this.b1, { opacity: ein(t, 1.05, 0.2) });

      this.b2.style.display = t >= 1.35 ? "block" : "none";
      stil(this.b2, { opacity: ein(t, 1.35, 0.22) });
      stil(this.lampe, {
        opacity: t < 3.0 ? (0.4 + 0.6 * Math.abs(Math.sin(t * 5.2))).toFixed(3) : 1,
        background: t < 3.0 ? "#d4af37" : "#8fd05a",
      });
      this.chip.childNodes[1].nodeValue = t < 3.0 ? "🔎 Websuche · DuckDuckGo · liest 3 Seiten" : "🔎 Websuche · 3 Seiten gelesen";
      Array.from(this.seiten.children).forEach((z, i) => {
        stil(z, { opacity: ein(t, 1.75 + i * 0.42, 0.26) });
      });

      const s = stroeme(
        "Stand heute, 1. September 2026: Ich rate nicht — ich habe eben drei Seiten gelesen: Herstellerseite, Preisvergleich und einen Händler.\n\nAlles, was ich dir gleich nenne, steht mit Quelle, Datum und Uhrzeit darunter.",
        t, 3.1, 7.2,
      );
      setzeText(this.b2t, s.text, s.laeuft, t);
      const qp = ein(t, 6.05, 0.3);
      this.quelle.textContent = "Quelle: 3 Seiten · abgerufen 01.09.2026, 06:44";
      stil(this.quelle, { opacity: qp });
      zeigeSchild(this.schild, t, 3.5, 7.7);
    },
  });

  S.push({
    id: "bild",
    von: 32,
    bis: 41,
    bau(w) {
      w.appendChild(window.B.hintergrund());
      w.appendChild(window.B.taskleiste("06:45", "01.09.2026"));
      this.f = w.appendChild(window.B.jonFenster({ x: 336, y: 128, b: 1248, h: 824 }));
      this.f.koerper.appendChild(
        window.B.seitenleiste([
          ["Leuchtturm im Sturm", "gerade eben"],
          ["Preis nachschlagen", "06:44"],
          ["Downloads aufräumen", "06:43"],
          ["Tagesbriefing", "06:41"],
        ]),
      );
      this.chat = this.f.koerper.appendChild(window.B.chatflaeche());
      this.b1 = this.chat.liste.appendChild(window.B.blase("ich", ""));
      this.b2 = this.chat.liste.appendChild(window.B.blase("jon", ""));
      stil(this.b2, { maxWidth: "84%" });
      this.b2.innerHTML =
        '<div class="werkzeuge"><span class="wchip"><span class="lampe"></span>🎨 Bild erzeugen</span></div>' +
        '<div class="rahmen" style="border-radius:14px;overflow:hidden;border:1px solid rgba(212,175,55,.24);position:relative;width:660px;height:420px;background:#05060a"></div>' +
        '<div class="knoepfe" style="display:flex;gap:10px;margin-top:12px"></div>';
      this.rahmen = this.b2.querySelector(".rahmen");
      this.lampe = this.b2.querySelector(".lampe");
      this.leinwand = el("canvas");
      this.leinwand.width = 660;
      this.leinwand.height = 420;
      stil(this.leinwand, { display: "block", width: "660px", height: "420px" });
      this.rahmen.appendChild(this.leinwand);
      this.strahl = this.rahmen.appendChild(el("div"));
      stil(this.strahl, {
        position: "absolute", left: 0, right: 0, height: "72px",
        background: "linear-gradient(180deg, rgba(245,214,123,0), rgba(245,214,123,.16), rgba(245,214,123,0))",
        opacity: 0,
      });
      this.knoepfe = this.b2.querySelector(".knoepfe");
      ["Herunterladen", "Groß ansehen", "Im Studio öffnen"].forEach((n) => {
        const k = el("div", null, n);
        stil(k, {
          padding: "9px 16px", borderRadius: "11px", fontSize: "13.5px",
          border: "1px solid rgba(212,175,55,.3)", background: "rgba(212,175,55,.09)",
          color: "rgba(245,214,123,.92)", opacity: 0,
        });
        this.knoepfe.appendChild(k);
      });
      this.schild = w.appendChild(window.B.schild("Bilder direkt im Chat.", "Ohne Schlüssel gratis."));
      stil(this.schild, { right: "84px", top: "76px", textAlign: "right" });
    },
    zeig(t) {
      fensterAuf(this.f, ein(t, 0, 0.26));
      const tp = tippe("Mal mir ein Bild von einem Leuchtturm im Sturm, nachts.", t, 0.3, 45);
      const gesendet = t >= 1.62;
      this.chat.feld.className = "feld" + (!gesendet && tp.text ? "" : " leer");
      if (!gesendet && tp.text) setzeText(this.chat.feld, tp.text, tp.laeuft, t);
      else this.chat.feld.textContent = "Frag Jon...";
      this.b1.style.display = gesendet ? "block" : "none";
      this.b1.textContent = "Mal mir ein Bild von einem Leuchtturm im Sturm, nachts.";
      stil(this.b1, { opacity: ein(t, 1.62, 0.2) });

      this.b2.style.display = t >= 1.95 ? "block" : "none";
      stil(this.b2, { opacity: ein(t, 1.95, 0.22) });

      const p = spanne(t, 2.25, 6.1);
      const fein = 0.055 + Math.pow(p, 1.55) * 0.945;
      if (t >= 1.95) malLeuchtturm(this.leinwand.getContext("2d"), 660, 420, fein);
      stil(this.leinwand, { opacity: klemm(0.25 + p * 1.1, 0, 1) });
      stil(this.lampe, {
        opacity: p < 1 ? (0.4 + 0.6 * Math.abs(Math.sin(t * 5.2))).toFixed(3) : 1,
        background: p < 1 ? "#d4af37" : "#8fd05a",
      });
      const sp = p < 1 ? ((t * 0.42) % 1) : 0;
      stil(this.strahl, { opacity: p < 1 && p > 0.02 ? 0.9 : 0, top: (sp * 420 - 36).toFixed(1) + "px" });

      Array.from(this.knoepfe.children).forEach((k, i) => {
        const q = ein(t, 6.3 + i * 0.12, 0.3);
        stil(k, { opacity: q, transform: "translateY(" + ((1 - q) * 6).toFixed(1) + "px)" });
      });
      zeigeSchild(this.schild, t, 5.5, 7.3);
    },
  });

  const CODE = [
    [["<", "z"], ["section", "t"], [" class", "a"], ["=", "z"], ['"anmeldung"', "s"], [">", "z"]],
    [["  <", "z"], ["form", "t"], [" class", "a"], ["=", "z"], ['"karte"', "s"], [">", "z"]],
    [["    <", "z"], ["h1", "t"], [">", "z"], ["Willkommen zurück", "x"], ["</", "z"], ["h1", "t"], [">", "z"]],
    [["    <", "z"], ["p", "t"], [">", "z"], ["Schön, dass du wieder da bist.", "x"], ["</", "z"], ["p", "t"], [">", "z"]],
    [["", "z"]],
    [["    <", "z"], ["label", "t"], [">", "z"], ["E-Mail", "x"], ["</", "z"], ["label", "t"], [">", "z"]],
    [["    <", "z"], ["input", "t"], [" type", "a"], ["=", "z"], ['"email"', "s"], [" placeholder", "a"], ["=", "z"], ['"du@beispiel.de"', "s"], [" />", "z"]],
    [["", "z"]],
    [["    <", "z"], ["label", "t"], [">", "z"], ["Passwort", "x"], ["</", "z"], ["label", "t"], [">", "z"]],
    [["    <", "z"], ["input", "t"], [" type", "a"], ["=", "z"], ['"password"', "s"], [" placeholder", "a"], ["=", "z"], ['"••••••••"', "s"], [" />", "z"]],
    [["", "z"]],
    [["    <", "z"], ["button", "t"], [" class", "a"], ["=", "z"], ['"weiter"', "s"], [">", "z"], ["Anmelden", "x"], ["</", "z"], ["button", "t"], [">", "z"]],
    [["    <", "z"], ["a", "t"], [" href", "a"], ["=", "z"], ['"#"', "s"], [">", "z"], ["Passwort vergessen?", "x"], ["</", "z"], ["a", "t"], [">", "z"]],
    [["  </", "z"], ["form", "t"], [">", "z"]],
    [["</", "z"], ["section", "t"], [">", "z"]],
  ];
  const CODEFARBE = { z: "rgba(255,255,255,.42)", t: "#f5d67b", a: "rgba(255,255,255,.6)", s: "#8fd05a", x: "#e9e6dc" };

  S.push({
    id: "code",
    von: 41,
    bis: 51,
    bau(w) {
      w.appendChild(window.B.hintergrund());
      w.appendChild(window.B.taskleiste("06:52", "01.09.2026"));
      this.f = w.appendChild(window.B.jonFenster({ x: 148, y: 104, b: 1624, h: 812, zusatz: "Jon Code" }));
      const baum = el("div");
      stil(baum, {
        width: "246px", borderRight: "1px solid rgba(255,255,255,.07)", padding: "16px 12px",
        background: "rgba(0,0,0,.25)", fontSize: "13.5px", color: "rgba(255,255,255,.6)",
      });
      baum.innerHTML =
        '<div style="font-size:11px;letter-spacing:.14em;color:rgba(255,255,255,.28);margin-bottom:12px">PROJEKT</div>' +
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;color:rgba(255,255,255,.85)"><span style="display:inline-flex;transform:scale(.72)">' +
        window.B.symbol("ordner") + "</span>landing</div>" +
        '<div style="padding-left:14px;display:flex;flex-direction:column;gap:6px">' +
        '<div class="aktiv" style="padding:7px 10px;border-radius:9px;background:rgba(212,175,55,.12);color:#f5d67b;display:flex;align-items:center;gap:8px">index.html<span class="mod" style="width:7px;height:7px;border-radius:50%;background:#d4af37;margin-left:auto;opacity:0"></span></div>' +
        '<div style="padding:7px 10px">style.css</div><div style="padding:7px 10px">app.js</div>' +
        '<div style="padding:7px 10px;display:flex;align-items:center;gap:8px"><span style="display:inline-flex;transform:scale(.6)">' +
        window.B.symbol("ordner") + "</span>bilder</div></div>";
      this.f.koerper.appendChild(baum);
      this.mod = baum.querySelector(".mod");

      const mitte = el("div");
      stil(mitte, { flex: "1", display: "flex", flexDirection: "column", minWidth: "0" });
      const reiter = el("div");
      stil(reiter, {
        height: "40px", display: "flex", alignItems: "center", gap: "12px", padding: "0 16px",
        borderBottom: "1px solid rgba(255,255,255,.06)", fontSize: "13px", color: "rgba(255,255,255,.75)",
      });
      reiter.innerHTML =
        '<span style="padding:5px 12px;border-radius:8px;background:rgba(255,255,255,.06)">index.html</span>' +
        '<span style="margin-left:auto;display:inline-flex;align-items:center;gap:7px;font-size:12px;color:rgba(245,214,123,.75);border:1px solid rgba(212,175,55,.28);background:rgba(212,175,55,.08);padding:4px 11px;border-radius:9px">' +
        window.B.symbol("schloss") + "C:\\Projekte\\landing</span>";
      mitte.appendChild(reiter);
      const editor = el("div");
      stil(editor, {
        flex: "1", padding: "18px 8px 18px 0", fontFamily: "var(--mono)", fontSize: "16.5px",
        lineHeight: "1.72", overflow: "hidden", background: "rgba(0,0,0,.18)",
      });
      mitte.appendChild(editor);
      this.f.koerper.appendChild(mitte);
      this.zeilen = CODE.map((_, i) => {
        const z = el("div");
        stil(z, { display: "flex", gap: "18px", padding: "0 14px" });
        const nr = el("span", null, String(i + 1).padStart(2, " "));
        stil(nr, { color: "rgba(255,255,255,.2)", width: "26px", textAlign: "right", flex: "none" });
        const inh = el("span");
        z.appendChild(nr);
        z.appendChild(inh);
        editor.appendChild(z);
        return inh;
      });

      const rechts = el("div");
      stil(rechts, {
        width: "396px", borderLeft: "1px solid rgba(255,255,255,.07)", padding: "18px 16px",
        display: "flex", flexDirection: "column", gap: "12px", background: "rgba(0,0,0,.22)",
      });
      this.jb1 = rechts.appendChild(window.B.blase("ich", ""));
      stil(this.jb1, { maxWidth: "100%", fontSize: "14.5px", alignSelf: "flex-end" });
      this.jb2 = rechts.appendChild(window.B.blase("jon", ""));
      stil(this.jb2, { maxWidth: "100%", fontSize: "14.5px" });
      this.f.koerper.appendChild(rechts);

      this.vorschau = w.appendChild(el("div", "fenster"));
      stil(this.vorschau, {
        left: "1046px", top: "406px", width: "660px", height: "470px", zIndex: 48,
        background: "rgba(7,7,11,0.96)", opacity: 0,
      });
      this.vorschau.innerHTML =
        '<div style="height:34px;display:flex;align-items:center;gap:8px;padding:0 12px;border-bottom:1px solid rgba(255,255,255,.07);font-size:11.5px;letter-spacing:.1em;color:rgba(255,255,255,.35)">VORSCHAU · index.html</div>' +
        '<div class="innen" style="height:436px;display:grid;place-items:center;background:radial-gradient(circle at 30% 0%,#141420,#06060a 60%,#000)"></div>';
      const karte = el("div", "glas");
      stil(karte, {
        width: "348px", borderRadius: "20px", padding: "30px 28px", border: "1px solid rgba(212,175,55,.28)",
        background: "rgba(255,255,255,0.045)",
      });
      karte.innerHTML =
        '<div style="font-size:24px;font-weight:300;letter-spacing:.02em;color:#f6f2e8;margin-bottom:6px">Willkommen zurück</div>' +
        '<div style="font-size:13px;color:rgba(255,255,255,.4);margin-bottom:22px">Schön, dass du wieder da bist.</div>' +
        '<div style="font-size:11.5px;letter-spacing:.1em;color:rgba(255,255,255,.42);margin-bottom:7px">E-MAIL</div>' +
        '<div style="height:44px;border-radius:12px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);margin-bottom:16px;display:flex;align-items:center;padding:0 14px;font-size:14px;color:rgba(255,255,255,.3)">du@beispiel.de</div>' +
        '<div style="font-size:11.5px;letter-spacing:.1em;color:rgba(255,255,255,.42);margin-bottom:7px">PASSWORT</div>' +
        '<div style="height:44px;border-radius:12px;background:rgba(255,255,255,.05);border:1px solid rgba(212,175,55,.4);margin-bottom:22px;display:flex;align-items:center;padding:0 14px;font-size:15px;letter-spacing:.2em;color:rgba(255,255,255,.5)">••••••••</div>' +
        '<div style="height:46px;border-radius:12px;background:linear-gradient(90deg,#f5d67b,#9a7b1f);color:#0b0a07;font-weight:600;font-size:15px;display:grid;place-items:center">Anmelden</div>' +
        '<div style="text-align:center;margin-top:16px;font-size:12.5px;color:rgba(245,214,123,.6)">Passwort vergessen?</div>';
      this.vorschau.querySelector(".innen").appendChild(karte);
      this.vkarte = karte;

      this.schild = w.appendChild(window.B.schild("Bleibt im Projektordner. Kommt da nicht raus."));
      stil(this.schild, { left: "0", right: "0", textAlign: "center", bottom: "72px" });
    },
    zeig(t) {
      fensterAuf(this.f, ein(t, 0, 0.26));
      const frage = "Schreib mir in index.html ein Login-Formular, modern, kein Grau.";
      const tp = tippe(frage, t, 0.4, 45);
      this.jb1.style.display = t >= 1.85 ? "block" : "none";
      this.jb1.textContent = frage;
      stil(this.jb1, { opacity: ein(t, 1.85, 0.2) });
      const s2 = stroeme("Ich schreibe direkt in index.html. Vorschau läuft nebenher.", t, 2.15, 6.4);
      this.jb2.style.display = t >= 2.15 ? "block" : "none";
      setzeText(this.jb2, s2.text, s2.laeuft, t);

      const gesamt = CODE.reduce((a, z) => a + z.reduce((b, s) => b + s[0].length, 0) + 1, 0);
      const n = klemm(Math.floor((t - 2.4) * 62), 0, gesamt);
      let rest = n;
      CODE.forEach((zeile, i) => {
        let html = "";
        for (const [txt, art] of zeile) {
          if (rest <= 0) break;
          const teil = txt.slice(0, rest);
          rest -= txt.length;
          if (teil)
            html +=
              '<span style="color:' + CODEFARBE[art] + '">' +
              teil.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") +
              "</span>";
        }
        rest -= 1;
        this.zeilen[i].innerHTML = html;
        if (rest > -1 && rest < 1 && n < gesamt && Math.floor(t * 2) % 2 === 0)
          this.zeilen[i].innerHTML += '<span class="schreiber" style="height:20px"></span>';
      });
      stil(this.mod, { opacity: n > 0 && n < gesamt ? 1 : 0 });

      const vp = ein(t, 5.85, 0.34);
      stil(this.vorschau, {
        opacity: vp,
        transform: "translateY(" + ((1 - vp) * 22).toFixed(1) + "px) scale(" + (0.97 + 0.03 * vp).toFixed(4) + ")",
      });
      zeigeSchild(this.schild, t, 4.3, 8.7);
    },
  });

  function handySchirm() {
    const s = el("div");
    stil(s, {
      position: "absolute", inset: "0", borderRadius: "34px", overflow: "hidden",
      background: "radial-gradient(circle at 20% -10%,#15151f 0%,#050506 55%,#000 100%)",
      color: "#f5f5f7", display: "flex", flexDirection: "column",
    });
    s.innerHTML =
      '<div style="padding:14px 18px 6px;display:flex;align-items:center;justify-content:space-between;font-size:13px;color:rgba(255,255,255,.75)">' +
      '<span>23:39</span><span style="display:flex;gap:7px;align-items:center">' + window.B.symbol("funk") + window.B.symbol("akku") + "</span></div>" +
      '<div style="padding:8px 16px 10px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.08)">' +
      '<div style="display:flex;align-items:center;gap:10px;font-weight:700;letter-spacing:2px">' +
      '<span style="width:12px;height:12px;border-radius:50%;background:#d4af37;box-shadow:0 0 16px rgba(212,175,55,.6)"></span>' +
      '<span class="gold" style="font-size:17px">JON</span></div>' +
      '<div style="display:flex;align-items:center;gap:8px"><span style="font-size:11px;color:rgba(255,255,255,.4)">Ollama · lokal</span>' +
      '<span style="width:32px;height:32px;border-radius:10px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);display:grid;place-items:center;font-size:13px">🔊</span></div></div>' +
      '<div style="display:flex;gap:8px;padding:11px 16px;border-bottom:1px solid rgba(255,255,255,.06);overflow:hidden">' +
      '<span style="flex:none;display:flex;align-items:center;gap:7px;padding:8px 14px;border-radius:999px;background:rgba(212,175,55,.15);border:1px solid rgba(212,175,55,.5);font-size:12.5px;color:#f5d67b"><span style="width:7px;height:7px;border-radius:50%;background:#d4af37"></span>Ollama</span>' +
      '<span style="flex:none;display:flex;align-items:center;gap:7px;padding:8px 14px;border-radius:999px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);font-size:12.5px;color:rgba(255,255,255,.75)"><span style="width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,.2)"></span>NVIDIA</span>' +
      '<span style="flex:none;display:flex;align-items:center;gap:7px;padding:8px 14px;border-radius:999px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);font-size:12.5px;color:rgba(255,255,255,.75)"><span style="width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,.2)"></span>Gemini</span></div>' +
      '<div class="msgs" style="flex:1;padding:16px;display:flex;flex-direction:column;gap:12px;justify-content:flex-end"></div>' +
      '<div style="display:flex;gap:8px;align-items:flex-end;padding:12px 16px 20px;border-top:1px solid rgba(255,255,255,.08);background:rgba(5,5,6,.8)">' +
      '<div class="feld" style="flex:1;min-height:46px;background:rgba(255,255,255,.06);border:1px solid rgba(212,175,55,.5);border-radius:14px;padding:13px 14px;font-size:14.5px;color:rgba(255,255,255,.28)">Frag Jon …</div>' +
      '<div style="flex:none;width:46px;height:46px;border-radius:14px;background:linear-gradient(135deg,#f5d67b,#9a7b1f);color:#000;font-size:19px;display:grid;place-items:center">➤</div></div>';
    s.msgs = s.querySelector(".msgs");
    s.feld = s.querySelector(".feld");
    return s;
  }

  function handyBlase(art, text) {
    const b = el("div");
    stil(b, {
      maxWidth: "85%", padding: "12px 15px", borderRadius: "16px", fontSize: "14.5px",
      lineHeight: "1.55", whiteSpace: "pre-wrap",
      alignSelf: art === "u" ? "flex-end" : "flex-start",
      background: art === "u" ? "linear-gradient(135deg,#f5d67b,#9a7b1f)" : "rgba(255,255,255,.06)",
      border: art === "u" ? "none" : "1px solid rgba(255,255,255,.08)",
      color: art === "u" ? "#000" : "#f5f5f7",
      borderBottomRightRadius: art === "u" ? "5px" : "16px",
      borderBottomLeftRadius: art === "u" ? "16px" : "5px",
    });
    b.textContent = text || "";
    return b;
  }

  S.push({
    id: "handy",
    von: 51,
    bis: 60,
    bau(w) {
      w.appendChild(window.B.hintergrund());
      this.pc = w.appendChild(el("div", "fenster"));
      stil(this.pc, { left: "88px", top: "252px", width: "744px", height: "556px", background: "rgba(9,9,13,0.94)" });
      this.pc.innerHTML =
        '<div class="leiste"><div class="marke"><span class="punkt"></span><span class="gold">JON</span></div>' +
        '<div class="knopfreihe"><span>—</span><span>▢</span><span>✕</span></div></div>' +
        '<div style="padding:14px 22px 0;font-size:12.5px;color:rgba(255,255,255,.4);display:flex;align-items:center;gap:8px">' +
        '<span style="display:inline-flex">' + window.B.symbol("zahnrad") + "</span>Zahnrad  ›  <span style='color:rgba(245,214,123,.85)'>Diagnose &amp; Handy koppeln</span></div>" +
        '<div style="display:flex;gap:26px;padding:22px 22px 0">' +
        '<div style="flex:none;padding:12px;border-radius:16px;background:#f4f1e8">' + qrBild(196) + "</div>" +
        '<div style="flex:1;padding-top:4px">' +
        '<div style="font-size:19px;color:#f5d67b;margin-bottom:10px">Handy verbinden</div>' +
        '<div style="font-size:13.5px;color:rgba(255,255,255,.55);line-height:1.7">QR-Code mit dem Handy scannen oder die Adresse im Browser öffnen. Die Verbindung läuft nur in deinem Netz.</div>' +
        '<div style="margin-top:16px;font-size:12px;color:rgba(255,255,255,.35)">ADRESSE</div>' +
        '<div style="font-family:var(--mono);font-size:15px;color:rgba(255,255,255,.85);margin-top:5px">http://192.168.178.<span style="filter:blur(6px)">42</span>:8756</div>' +
        '<div style="margin-top:14px;font-size:12px;color:rgba(255,255,255,.35)">GERÄTE-SCHLÜSSEL</div>' +
        '<div style="font-family:var(--mono);font-size:15px;color:rgba(255,255,255,.6);margin-top:5px;letter-spacing:.18em"><span style="filter:blur(7px)">7fa2-91c4-be08</span></div>' +
        "</div></div>" +
        '<div class="hinweis" style="margin:24px 22px 0;padding:14px 16px;border-radius:14px;border:1px solid rgba(143,208,90,.3);background:rgba(143,208,90,.08);display:flex;align-items:center;gap:12px;font-size:14px;color:#c8e8a6;opacity:0"></div>';
      this.hinweis = this.pc.querySelector(".hinweis");
      this.hinweis.innerHTML = window.B.symbol("haken") + "Herunterfahren geplant · 23:41";

      this.bruecke = w.appendChild(el("div"));
      stil(this.bruecke, { position: "absolute", left: "0", top: "0", width: "1920px", height: "1080px", zIndex: 12, opacity: 0 });
      this.bruecke.innerHTML =
        '<svg width="1920" height="1080" viewBox="0 0 1920 1080">' +
        '<path d="M840 500 Q1010 404 1166 470" fill="none" stroke="rgba(212,175,55,.42)" stroke-width="2" stroke-dasharray="9 11" stroke-linecap="round"/>' +
        "</svg>";
      this.schloss = w.appendChild(el("div", null, window.B.symbol("schloss")));
      stil(this.schloss, {
        position: "absolute", left: "978px", top: "406px", width: "44px", height: "44px",
        display: "grid", placeItems: "center", borderRadius: "13px", zIndex: 13, opacity: 0,
        background: "rgba(11,11,15,.9)", border: "1px solid rgba(212,175,55,.5)",
        boxShadow: "0 0 26px rgba(212,175,55,.2)",
      });

      this.arm = w.appendChild(el("div"));
      stil(this.arm, { position: "absolute", left: "0", top: "0", width: "1920px", height: "1080px", zIndex: 20 });
      this.arm.innerHTML =
        '<svg width="1920" height="1080" viewBox="0 0 1920 1080">' +
        '<defs><linearGradient id="hHaut" x1="0" y1="0" x2="1" y2="0.7">' +
        '<stop offset="0%" stop-color="#3a3a46"/><stop offset="22%" stop-color="#20202a"/>' +
        '<stop offset="62%" stop-color="#13131a"/><stop offset="100%" stop-color="#0b0b10"/></linearGradient></defs>' +
        '<path d="M1094 392 C1084 330 1122 292 1176 298 L1596 298 C1626 302 1642 322 1642 350 L1642 952 ' +
        'C1642 1038 1572 1080 1478 1080 L1232 1080 C1148 1080 1094 1024 1094 934 Z" ' +
        'fill="url(#hHaut)" stroke="rgba(245,214,123,.2)" stroke-width="2.4"/>' +
        '<path d="M1094 392 C1084 330 1122 292 1176 298" fill="none" stroke="rgba(255,236,182,.55)" stroke-width="3" stroke-linecap="round"/>' +
        '<path d="M1094 500 L1094 934 C1094 986 1112 1026 1146 1052" fill="none" stroke="rgba(245,214,123,.34)" stroke-width="2.6" stroke-linecap="round"/>' +
        "</svg>";

      this.finger = w.appendChild(el("div"));
      stil(this.finger, { position: "absolute", left: "0", top: "0", width: "1920px", height: "1080px", zIndex: 30 });
      var fs = "";
      var rand = "";
      [[336, 1244, 60], [462, 1256, 64], [588, 1248, 62], [702, 1226, 55]].forEach(function (f) {
        var y = f[0];
        var spitze = f[1];
        var dick = f[2];
        var x0 = 1046;
        var r = dick / 2;
        fs +=
          '<path d="M' + (x0 + 10) + " " + (y - r + 10) + " L" + (spitze - r + 10) + " " + (y - r + 10) +
          " A" + r + " " + r + " 0 0 1 " + (spitze - r + 10) + " " + (y + r + 10) + " L" + (x0 + 10) + " " + (y + r + 10) +
          ' Z" fill="rgba(0,0,0,.6)"/>';
        fs +=
          '<path d="M' + x0 + " " + (y - r) + " L" + (spitze - r) + " " + (y - r) +
          " A" + r + " " + r + " 0 0 1 " + (spitze - r) + " " + (y + r) + " L" + x0 + " " + (y + r) +
          ' Z" fill="url(#fFinger)"/>';
        rand +=
          '<path d="M' + x0 + " " + (y - r + 1.4) + " L" + (spitze - r) + " " + (y - r + 1.4) +
          " A" + (r - 1.4) + " " + (r - 1.4) + " 0 0 1 " + (spitze + r * 0.06) + " " + y +
          '" fill="none" stroke="rgba(255,236,182,.5)" stroke-width="2.6" stroke-linecap="round"/>';
        rand +=
          '<path d="M' + (x0 + 30) + " " + (y + r - 1) + " L" + (spitze - r * 1.3) + " " + (y + r - 1) +
          '" fill="none" stroke="rgba(0,0,0,.55)" stroke-width="2.2" stroke-linecap="round"/>';
      });
      this.finger.innerHTML =
        '<svg width="1920" height="1080" viewBox="0 0 1920 1080">' +
        '<defs><linearGradient id="fFinger" x1="0" y1="0" x2="0.25" y2="1">' +
        '<stop offset="0%" stop-color="#3e3e4b"/><stop offset="40%" stop-color="#1d1d26"/>' +
        '<stop offset="100%" stop-color="#0b0b10"/></linearGradient>' +
        '<linearGradient id="fDaumen" x1="0" y1="1" x2="0.55" y2="0">' +
        '<stop offset="0%" stop-color="#0d0d12"/><stop offset="55%" stop-color="#1f1f29"/>' +
        '<stop offset="100%" stop-color="#3c3c49"/></linearGradient></defs>' +
        fs +
        '<path d="M1676 1080 C1664 1010 1626 954 1556 924" fill="none" stroke="rgba(0,0,0,.6)" stroke-width="118" stroke-linecap="round"/>' +
        '<path d="M1666 1080 C1654 1004 1616 948 1546 918" fill="none" stroke="url(#fDaumen)" stroke-width="106" stroke-linecap="round"/>' +
        '<path d="M1614 1058 C1602 992 1570 944 1512 918" fill="none" stroke="rgba(255,236,182,.4)" stroke-width="2.8" stroke-linecap="round"/>' +
        rand +
        "</svg>";

      this.telefon = w.appendChild(el("div"));
      stil(this.telefon, {
        position: "absolute", left: "1176px", top: "116px", width: "428px", height: "850px",
        borderRadius: "46px", background: "linear-gradient(142deg,#33333d,#14141a 38%,#0b0b10)",
        border: "1px solid rgba(255,255,255,.2)",
        boxShadow: "0 60px 140px rgba(0,0,0,.9), 0 0 0 1px rgba(245,214,123,.14), inset 0 0 0 6px #050507",
        padding: "9px", zIndex: 25,
      });
      const schirm = handySchirm();
      this.telefon.appendChild(schirm);
      this.schirm = schirm;
      this.hb1 = schirm.msgs.appendChild(handyBlase("u", ""));
      this.hb2 = schirm.msgs.appendChild(handyBlase("a", ""));
      const kerbe = el("div");
      stil(kerbe, {
        position: "absolute", left: "50%", top: "22px", transform: "translateX(-50%)",
        width: "108px", height: "26px", borderRadius: "14px", background: "#050507", zIndex: 5,
      });
      this.telefon.appendChild(kerbe);

      this.schild = w.appendChild(window.B.schild("Dein Handy. Dein PC.", "Kein fremder Server."));
      stil(this.schild, { left: "80px", bottom: "108px" });
    },
    zeig(t) {
      const p = ein(t, 0, 0.3);
      stil(this.pc, { opacity: p * 0.98, transform: "translateY(" + ((1 - p) * 14).toFixed(1) + "px)" });
      const q = ein(t, 0.12, 0.42);
      const schweben = Math.sin(t * 0.9) * 4;
      const tr = "translateY(" + ((1 - q) * 26 + schweben).toFixed(2) + "px)";
      stil(this.arm, { opacity: q, transform: tr });
      stil(this.finger, { opacity: q, transform: tr });
      stil(this.telefon, { opacity: q, transform: tr });
      const bp = ein(t, 1.05, 0.6);
      stil(this.bruecke, { opacity: bp * 0.9 });
      stil(this.schloss, { opacity: bp, transform: "scale(" + (0.9 + 0.1 * bp).toFixed(3) + ")" });

      const frage = "Ist mein PC noch an? Fahr ihn in 10 Minuten runter.";
      const tp = tippe(frage, t, 1.45, 45);
      const gesendet = t >= 2.7;
      if (!gesendet && tp.text) {
        this.schirm.feld.style.color = "rgba(255,255,255,.92)";
        setzeText(this.schirm.feld, tp.text, tp.laeuft, t);
      } else {
        this.schirm.feld.style.color = "rgba(255,255,255,.28)";
        this.schirm.feld.textContent = "Frag Jon …";
      }
      this.hb1.style.display = gesendet ? "block" : "none";
      this.hb1.textContent = frage;
      stil(this.hb1, { opacity: ein(t, 2.7, 0.18) });

      const s = stroeme(
        "PC läuft seit 6 Stunden. Herunterfahren um 23:41 geplant — ich sag dir kurz vorher Bescheid.",
        t, 3.05, 6.6,
      );
      this.hb2.style.display = t >= 3.05 ? "block" : "none";
      setzeText(this.hb2, s.text, s.laeuft, t);

      stil(this.hinweis, { opacity: ein(t, 5.5, 0.3) });
      zeigeSchild(this.schild, t, 5.7, 8.5);
    },
  });

  S.push({
    id: "freunde",
    von: 60,
    bis: 69,
    bau(w) {
      w.appendChild(window.B.hintergrund());
      w.appendChild(window.B.taskleiste("20:12", "01.09.2026"));
      this.links = w.appendChild(window.B.jonFenster({ x: 78, y: 152, b: 828, h: 728, zusatz: "Freunde" }));
      this.rechts = w.appendChild(window.B.jonFenster({ x: 1014, y: 152, b: 828, h: 728, zusatz: "Freunde" }));
      [["Felix", this.links], ["Anna", this.rechts]].forEach(([name, f]) => {
        const kopf = el("div");
        stil(kopf, {
          padding: "13px 20px", borderBottom: "1px solid rgba(255,255,255,.06)",
          display: "flex", alignItems: "center", gap: "11px", fontSize: "14.5px", color: "rgba(255,255,255,.78)",
        });
        kopf.innerHTML =
          '<span style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#f5d67b,#9a7b1f);color:#0a0a0c;display:grid;place-items:center;font-weight:700;font-size:14px">' +
          name[0] + "</span>" + name +
          '<span style="margin-left:auto;display:inline-flex;align-items:center;gap:7px;font-size:12px;color:rgba(245,214,123,.7)">' +
          window.B.symbol("schloss") + "Ende-zu-Ende</span>";
        const spalte = el("div");
        stil(spalte, { flex: "1", display: "flex", flexDirection: "column", minWidth: "0" });
        spalte.appendChild(kopf);
        const c = window.B.chatflaeche();
        spalte.appendChild(c);
        f.koerper.appendChild(spalte);
        f.chat = c;
      });
      this.b1 = this.links.chat.liste.appendChild(window.B.blase("ich", ""));
      this.b2 = this.links.chat.liste.appendChild(window.B.blase("jon", ""));
      this.b3 = this.rechts.chat.liste.appendChild(window.B.blase("jon", ""));
      stil(this.b3, { alignSelf: "flex-start" });

      this.strahl = w.appendChild(el("div"));
      stil(this.strahl, {
        position: "absolute", left: "906px", top: "486px", width: "108px", height: "2px",
        background: "linear-gradient(90deg, rgba(212,175,55,0), rgba(245,214,123,.9), rgba(212,175,55,0))",
        opacity: 0, zIndex: 40,
      });
      this.schloss = w.appendChild(el("div", null, window.B.symbol("schloss")));
      stil(this.schloss, {
        position: "absolute", left: "946px", top: "462px", width: "28px", height: "28px",
        display: "grid", placeItems: "center", borderRadius: "9px",
        background: "rgba(212,175,55,.14)", border: "1px solid rgba(212,175,55,.45)", opacity: 0, zIndex: 41,
      });
      this.schild = w.appendChild(window.B.schild("Ende-zu-Ende verschlüsselt.", "PC zu PC."));
      stil(this.schild, { left: "0", right: "0", textAlign: "center", bottom: "108px" });
    },
    zeig(t) {
      fensterAuf(this.links, ein(t, 0, 0.26));
      fensterAuf(this.rechts, ein(t, 0.08, 0.26));
      const frage = "Sag Anna, dass ich später komme, so gegen acht.";
      const tp = tippe(frage, t, 0.4, 45);
      const gesendet = t >= 1.65;
      this.links.chat.feld.className = "feld" + (!gesendet && tp.text ? "" : " leer");
      if (!gesendet && tp.text) setzeText(this.links.chat.feld, tp.text, tp.laeuft, t);
      else this.links.chat.feld.textContent = "Frag Jon...";
      this.b1.style.display = gesendet ? "block" : "none";
      this.b1.textContent = frage;
      stil(this.b1, { opacity: ein(t, 1.65, 0.2) });
      const s = stroeme("Erledigt.", t, 1.95, 4);
      this.b2.style.display = t >= 1.95 ? "block" : "none";
      setzeText(this.b2, s.text, s.laeuft, t);

      const sp = spanne(t, 2.25, 2.62);
      stil(this.strahl, { opacity: sp > 0 && sp < 1 ? 1 : 0, transform: "scaleX(" + weich(sp).toFixed(3) + ")", transformOrigin: "0 50%" });
      stil(this.schloss, { opacity: ein(t, 2.4, 0.2) * (1 - ein(t, 4.6, 0.5)) });

      const bp = ein(t, 2.66, 0.24);
      this.b3.style.display = t >= 2.66 ? "block" : "none";
      this.b3.textContent = "Ich werd später — so gegen acht. 🙂";
      stil(this.b3, { opacity: bp, transform: "translateY(" + ((1 - bp) * 9).toFixed(1) + "px)" });
      zeigeSchild(this.schild, t, 3.2, 7.2);
    },
  });

  S.push({
    id: "spiele",
    von: 69,
    bis: 76,
    bau(w) {
      w.appendChild(window.B.hintergrund());
      w.appendChild(window.B.taskleiste("20:14", "01.09.2026"));
      this.f = w.appendChild(window.B.jonFenster({ x: 336, y: 128, b: 1248, h: 824 }));
      this.f.koerper.appendChild(
        window.B.seitenleiste([
          ["Spiele", "gerade eben"],
          ["Anna · Freunde", "20:12"],
          ["Leuchtturm im Sturm", "06:45"],
          ["Downloads aufräumen", "06:43"],
        ]),
      );
      this.chat = this.f.koerper.appendChild(window.B.chatflaeche());
      this.b1 = this.chat.liste.appendChild(window.B.blase("ich", ""));
      stil(this.b1, { fontFamily: "var(--mono)" });
      this.kacheln = this.chat.liste.appendChild(el("div"));
      stil(this.kacheln, { display: "flex", gap: "14px", alignSelf: "flex-start", maxWidth: "100%" });
      this.liste = [["ECHO", "echo"], ["AETHERIA", "aetheria"], ["STARFALL", "starfall"], ["Harmonische Inseln", "harmonie"], ["Blockwelt", "blockwelt"]].map(([n, a]) => {
        const k = el("div", "glas");
        stil(k, { width: "168px", borderRadius: "15px", overflow: "hidden", opacity: 0 });
        k.innerHTML =
          '<div style="height:104px;overflow:hidden">' + kachelBild(a) + "</div>" +
          '<div style="padding:11px 12px;font-size:13.5px;color:rgba(255,255,255,.86);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + n + "</div>";
        this.kacheln.appendChild(k);
        return k;
      });

      this.befehl = this.chat.liste.parentNode.insertBefore(el("div", "glas"), this.chat.liste.nextSibling);
      stil(this.befehl, {
        position: "absolute", left: "620px", top: "746px", width: "420px", borderRadius: "14px",
        overflow: "hidden", zIndex: 20, opacity: 0,
      });
      this.befehl.innerHTML =
        '<div style="padding:7px 12px;font-size:10.5px;letter-spacing:.14em;color:rgba(255,255,255,.32);border-bottom:1px solid rgba(255,255,255,.08)">BEFEHLE</div>' +
        '<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:rgba(255,255,255,.05)"><span>🕹️</span>' +
        '<span style="color:rgba(245,214,123,.92);font-size:13.5px">/spiele</span>' +
        '<span style="color:rgba(255,255,255,.45);font-size:12.5px">Alle Spiele</span></div>';

      this.spiel = w.appendChild(el("div", "fenster"));
      stil(this.spiel, { left: "608px", top: "282px", width: "784px", height: "502px", zIndex: 46, opacity: 0 });
      this.spiel.innerHTML =
        '<div style="height:38px;display:flex;align-items:center;gap:10px;padding:0 14px;border-bottom:1px solid rgba(255,255,255,.07);font-size:12.5px;letter-spacing:.08em;color:rgba(255,255,255,.5)">BLOCKWELT' +
        '<span style="margin-left:auto;color:rgba(255,255,255,.3)">—  ▢  ✕</span></div>' +
        '<div class="welt" style="height:464px;position:relative;overflow:hidden;background:linear-gradient(180deg,#0b1220,#06080d)"></div>';
      const welt = this.spiel.querySelector(".welt");
      let sv = "";
      for (let x = 0; x < 6; x++)
        for (let y = 0; y < 6; y++) {
          const px = 392 + (x - y) * 52;
          const py = 150 + (x + y) * 27;
          const hoehe = Math.floor(zufall(x * 4.4 + y * 7.1) * 2);
          const o = -hoehe * 22;
          sv +=
            '<path d="M' + px + " " + (py + o) + " L" + (px + 52) + " " + (py + 27 + o) + " L" + px + " " + (py + 54 + o) + " L" + (px - 52) + " " + (py + 27 + o) +
            ' Z" fill="' + (hoehe ? "#4c7a3f" : "#3f6a35") + '"/>' +
            '<path d="M' + (px - 52) + " " + (py + 27 + o) + " L" + px + " " + (py + 54 + o) + " L" + px + " " + (py + 108 + o) + " L" + (px - 52) + " " + (py + 81 + o) + ' Z" fill="#33512b"/>' +
            '<path d="M' + (px + 52) + " " + (py + 27 + o) + " L" + px + " " + (py + 54 + o) + " L" + px + " " + (py + 108 + o) + " L" + (px + 52) + " " + (py + 81 + o) + ' Z" fill="#27411f"/>';
        }
      welt.innerHTML = '<svg width="784" height="464" viewBox="0 0 784 464" style="position:absolute;left:0;top:0">' + sv + "</svg>";
      this.block = welt.appendChild(el("div"));
      stil(this.block, { position: "absolute", left: "0", top: "0", width: "784px", height: "464px", opacity: 0 });
      this.block.innerHTML =
        '<svg width="784" height="464" viewBox="0 0 784 464">' +
        '<path d="M444 245 L496 272 L444 299 L392 272 Z" fill="#e0bb63"/>' +
        '<path d="M392 272 L444 299 L444 339 L392 312 Z" fill="#a5851f"/>' +
        '<path d="M496 272 L444 299 L444 339 L496 312 Z" fill="#82661a"/>' +
        '<path d="M444 245 L496 272 L444 299 L392 272 Z" fill="none" stroke="rgba(245,214,123,.5)" stroke-width="1.4"/></svg>';
      this.mini = welt.appendChild(window.B.miniJon(78));
      stil(this.mini, { left: "314px", top: "212px", opacity: 0, zIndex: 5 });
      this.zeiger = w.appendChild(window.B.zeiger());
      this.schild = w.appendChild(window.B.schild("Fünf Spiele.", "Zu zweit über einen sechsstelligen Code."));
      stil(this.schild, { left: "0", right: "0", textAlign: "center", bottom: "86px" });
    },
    zeig(t) {
      fensterAuf(this.f, ein(t, 0, 0.24));
      const tp = tippe("/spiele", t, 0.3, 26);
      const gesendet = t >= 0.85;
      this.chat.feld.className = "feld" + (!gesendet && tp.text ? "" : " leer");
      if (!gesendet && tp.text) setzeText(this.chat.feld, tp.text, tp.laeuft, t);
      else this.chat.feld.textContent = "Frag Jon...";
      stil(this.befehl, { opacity: t > 0.36 && t < 0.85 ? 1 : 0 });
      this.b1.style.display = gesendet ? "block" : "none";
      this.b1.textContent = "/spiele";
      stil(this.b1, { opacity: ein(t, 0.85, 0.18) });
      this.liste.forEach((k, i) => {
        const p = ein(t, 1.1 + i * 0.09, 0.3);
        stil(k, { opacity: p, transform: "translateY(" + ((1 - p) * 16).toFixed(1) + "px)" });
      });
      const gewaehlt = t >= 2.55;
      stil(this.liste[4], {
        borderColor: gewaehlt ? "rgba(212,175,55,.6)" : "rgba(255,255,255,.1)",
        boxShadow: gewaehlt ? "0 0 26px rgba(212,175,55,.25)" : "none",
      });
      const zp = spanne(t, 1.85, 2.52);
      const zx = 700 + (1360 - 700) * weich(zp);
      const zy = 890 + (612 - 890) * weich(zp);
      stil(this.zeiger, {
        opacity: t > 1.8 && t < 3.0 ? 1 : 0,
        transform: "translate(" + zx.toFixed(1) + "px," + zy.toFixed(1) + "px)",
      });
      const sp = ein(t, 2.75, 0.34);
      stil(this.spiel, {
        opacity: sp,
        transform: "translateY(" + ((1 - sp) * 24).toFixed(1) + "px) scale(" + (0.97 + 0.03 * sp).toFixed(4) + ")",
      });
      const mp = ein(t, 3.15, 0.3);
      const huepf = t > 3.6 && t < 3.95 ? -Math.sin((t - 3.6) / 0.35 * Math.PI) * 16 : 0;
      stil(this.mini, { opacity: mp, transform: "translateY(" + huepf.toFixed(1) + "px)" });
      window.B.miniStand(this.mini, { blinzeln: blinzeln(t, [3.5, 5.1]), mund: 0 });
      const bp = ein(t, 3.92, 0.22);
      stil(this.block, { opacity: bp, transform: "translateY(" + ((1 - bp) * -14).toFixed(1) + "px)" });
      zeigeSchild(this.schild, t, 4.1, 6.6);
    },
  });

  S.push({
    id: "minijon",
    von: 76,
    bis: 84,
    bau(w) {
      w.appendChild(window.B.hintergrund());
      w.appendChild(window.B.schreibtischsymbole());
      w.appendChild(window.B.taskleiste("20:18", "01.09.2026"));
      this.boden = w.appendChild(el("div"));
      stil(this.boden, {
        position: "absolute", left: "620px", top: "760px", width: "680px", height: "90px",
        background: "radial-gradient(ellipse at 50% 50%, rgba(212,175,55,.1), rgba(212,175,55,0) 70%)",
      });
      this.katze = w.appendChild(window.B.katze(150));
      this.mini = w.appendChild(window.B.miniJon(340));
      stil(this.mini, { left: "790px", top: "398px" });
      this.blase = w.appendChild(window.B.sprechblase("", 430));
      stil(this.blase, { left: "1152px", top: "352px", fontSize: "19px", borderRadius: "18px 18px 4px 18px" });

      this.waehler = w.appendChild(el("div", "glas"));
      stil(this.waehler, {
        position: "absolute", left: "402px", top: "436px", width: "268px", borderRadius: "16px",
        padding: "16px", opacity: 0, zIndex: 47,
      });
      this.waehler.innerHTML =
        '<div style="font-size:11.5px;letter-spacing:.13em;color:rgba(255,255,255,.4);margin-bottom:12px">FARBE</div>' +
        '<div class="felder" style="display:flex;gap:11px"></div>';
      this.felder = ["#d4af37", "#ff9bb0", "#7fb2ff", "#8fd05a", "#f2f2f2"].map((c, i) => {
        const s = el("div");
        stil(s, {
          width: "40px", height: "40px", borderRadius: "12px", background: c,
          border: "2px solid " + (i === 0 ? "rgba(255,255,255,.85)" : "rgba(255,255,255,.12)"),
        });
        this.waehler.querySelector(".felder").appendChild(s);
        return s;
      });
      this.zeiger = w.appendChild(window.B.zeiger());
      this.schild = w.appendChild(window.B.schild(""));
      this.schild.innerHTML = '<span class="taste">Strg</span> <span class="taste">Alt</span> <span class="taste">K</span>';
      stil(this.schild, { left: "0", right: "0", textAlign: "center", bottom: "112px" });
    },
    zeig(t) {
      const p = ein(t, 0, 0.35);
      const dp = weich(spanne(t, 0.35, 3.4));
      const dreh = dp * Math.PI * 2;
      const rosa = t >= 3.62 && t < 4.72;
      const farbe = rosa ? "#ff9bb0" : "#d4af37";
      const s = stroeme("Ich bin Jons Sohn. Ich kann alles, was Papa kann — nur kleiner.", t, 5.05, 6.4);
      const sicht = klemm((Math.cos(dreh) - 0.02) / 0.3, 0, 1);
      stil(this.mini, { opacity: p, transform: "scale(" + (0.94 + 0.06 * p).toFixed(3) + ")" });
      window.B.miniStand(this.mini, {
        blinzeln: blinzeln(t, [1.45, 3.05, 5.6, 7.3]),
        mund: reden(t, s.laeuft),
        dreh: dreh,
        farbe: farbe,
        schein: rosa ? "rgba(255,155,176,0.14)" : "rgba(212,175,55,0.13)",
        backen: 0,
      });
      const q = this.mini.querySelector(".augen");
      q.style.opacity = sicht;
      this.mini.querySelector(".laecheln").style.opacity = sicht * (reden(t, s.laeuft) > 0.02 ? 0 : 1);
      this.mini.querySelector(".mund").style.opacity = sicht * (reden(t, s.laeuft) > 0.02 ? 1 : 0);
      stil(this.boden, { opacity: p });

      const kp = ein(t, 0.9, 0.5);
      const kw = spanne(t, 0.9, 7.6);
      const winkel = kw * Math.PI * 2 - 0.6;
      const kx = 960 + Math.cos(winkel) * 330 - 75;
      const ky = 742 + Math.sin(winkel) * 74;
      const vorn = Math.sin(winkel) > -0.1;
      const richtung = Math.sin(winkel + 1.57) > 0 ? -1 : 1;
      stil(this.katze, {
        left: kx.toFixed(1) + "px",
        top: (ky + Math.abs(Math.sin(kw * 34)) * -7).toFixed(1) + "px",
        opacity: kp,
        zIndex: vorn ? 46 : 43,
        transform: "scaleX(" + richtung + ") scale(" + (0.9 + (vorn ? 0.16 : 0)).toFixed(2) + ")",
      });

      const wp = ein(t, 2.95, 0.3) * (1 - ein(t, 5.5, 0.4));
      stil(this.waehler, { opacity: wp, transform: "translateY(" + ((1 - ein(t, 2.95, 0.3)) * 12).toFixed(1) + "px)" });
      this.felder.forEach((f, i) => {
        const aktiv = (rosa && i === 1) || (!rosa && i === 0);
        stil(f, { border: "2px solid " + (aktiv ? "rgba(255,255,255,.9)" : "rgba(255,255,255,.12)"), transform: aktiv ? "scale(1.12)" : "scale(1)" });
      });
      const zp1 = spanne(t, 3.15, 3.58);
      const zp2 = spanne(t, 4.3, 4.68);
      const zx = zp2 > 0 ? 470 + (430 - 470) * weich(zp2) : 560 + (470 - 560) * weich(zp1);
      const zy = 560 + (474 - 560) * weich(Math.max(zp1, zp2));
      stil(this.zeiger, {
        opacity: t > 3.05 && t < 5.0 ? 1 : 0,
        transform: "translate(" + zx.toFixed(1) + "px," + zy.toFixed(1) + "px)",
      });

      const bp = ein(t, 4.95, 0.26) * (1 - ein(t, 7.55, 0.35));
      this.blase.textContent = s.text;
      stil(this.blase, { opacity: bp, transform: "translateY(" + ((1 - ein(t, 4.95, 0.26)) * 10).toFixed(1) + "px)" });
      zeigeSchild(this.schild, t, 6.05, 7.7);
    },
  });

  S.push({
    id: "abspann",
    von: 84,
    bis: 90,
    bau(w) {
      stil(w, { background: "#000" });
      this.t = w.appendChild(el("div", "gold", "Jon"));
      stil(this.t, {
        position: "absolute", left: "0", right: "0", top: "352px", textAlign: "center",
        fontSize: "128px", fontWeight: "200", lineHeight: "1", letterSpacing: ".08em", textIndent: ".08em",
      });
      this.z1 = w.appendChild(el("div", null, "Kostenlos. Läuft auf deinem PC. Auch komplett offline mit Ollama."));
      stil(this.z1, {
        position: "absolute", left: "0", right: "0", top: "540px", textAlign: "center",
        fontSize: "29px", fontWeight: "300", letterSpacing: ".05em", color: "rgba(246,242,232,.72)",
      });
      this.z2 = w.appendChild(el("div", "gold", "getjon.info"));
      stil(this.z2, {
        position: "absolute", left: "0", right: "0", top: "610px", textAlign: "center",
        fontSize: "40px", fontWeight: "400", letterSpacing: ".1em", textIndent: ".1em",
      });
      this.z3 = w.appendChild(el("div", null, "FelWorks · Version 4.36.4 · Windows 10/11"));
      stil(this.z3, {
        position: "absolute", left: "0", right: "0", bottom: "76px", textAlign: "center",
        fontSize: "18px", letterSpacing: ".12em", color: "rgba(255,255,255,.3)",
      });
      this.mini = w.appendChild(window.B.miniJon(146));
      stil(this.mini, { left: "1826px", top: "748px" });
    },
    zeig(t) {
      const p = ein(t, 0.5, 0.9);
      stil(this.t, { opacity: p, filter: "drop-shadow(0 0 " + (40 * p).toFixed(1) + "px rgba(212,175,55,.28))" });
      stil(this.z1, { opacity: ein(t, 1.35, 0.7) * 0.95 });
      stil(this.z2, { opacity: ein(t, 2.1, 0.7) });
      stil(this.z3, { opacity: ein(t, 2.9, 0.8) * 0.8 });
      const mp = ein(t, 4.2, 0.5);
      stil(this.mini, {
        opacity: mp,
        transform: "translateX(" + ((1 - mp) * 70).toFixed(1) + "px)",
      });
      window.B.miniStand(this.mini, { blinzeln: blinzeln(t, [5.0, 5.45]), mund: 0 });
    },
  });

  return S;
})();
