(function () {
  const { el, stil, klemm, spanne, ein, raus } = window.B;
  const p = new URLSearchParams(location.search);
  const BREITE = Number(p.get("breite") || 1920);
  const HOEHE = Number(p.get("hoehe") || 1080);
  const KURZ = HOEHE > BREITE;

  const rahmen = document.getElementById("rahmen");
  const kamera = document.getElementById("kamera");
  const buehne = document.getElementById("buehne");
  const szeneNode = document.getElementById("szene");
  const blende = document.getElementById("blende");
  const untertitel = document.getElementById("untertitel");
  const korn = document.getElementById("korn");
  const hkKopf = document.getElementById("hkKopf");
  const hkFuss = document.getElementById("hkFuss");

  stil(rahmen, { width: BREITE + "px", height: HOEHE + "px" });
  if (KURZ) document.body.classList.add("portraet");

  (function kornBild() {
    const c = document.createElement("canvas");
    c.width = 160;
    c.height = 160;
    const x = c.getContext("2d");
    const d = x.createImageData(160, 160);
    for (let i = 0; i < d.data.length; i += 4) {
      const v = 118 + Math.floor(window.B.zufall(i * 0.37) * 74);
      d.data[i] = d.data[i + 1] = d.data[i + 2] = v;
      d.data[i + 3] = 255;
    }
    x.putImageData(d, 0, 0);
    korn.style.backgroundImage = "url(" + c.toDataURL() + ")";
  })();

  const GRENZEN = [7, 13, 23, 32, 41, 51, 60, 69, 76, 84];
  const UNTERTITEL = window.VO || [
    [13.2, 2.0, "Die meisten Assistenten reden."],
    [20.0, 1.2, "Jon macht."],
    [27.4, 4.0, "Er weiß, welcher Tag heute ist — und schaut nach, statt zu raten."],
    [51.4, 3.0, "Am PC. Am Handy. Ohne Cloud, ohne Abo."],
    [76.3, 2.0, "Und er kommt nicht allein."],
    [86.0, 2.0, "Jon. Auf getjon.info."],
  ];

  const KURZFILM = [
    { von: 0, bis: 4, quelle: 2.9, rect: { x: 1398, y: 628, w: 486, h: 400 }, mitte: 1035,
      kopf: "Er sitzt auf deinem Desktop.\nUnd hört zu.", fuss: "MINI JON" },
    { von: 4, bis: 8, quelle: 25.6, rect: { x: 604, y: 512, w: 1000, h: 430 }, mitte: 1005,
      kopf: "Kein Raten.\nEr schaut nach.", fuss: "WEBSUCHE MIT DATUM" },
    { von: 8, bis: 12, quelle: 46.8, rect: { x: 646, y: 250, w: 1110, h: 660 }, mitte: 1020,
      kopf: "Er schreibt Code.\nIn deinen Projektordner.", fuss: "JON CODE" },
    { von: 12, bis: 16, quelle: 78.5, rect: { x: 672, y: 352, w: 700, h: 545 }, mitte: 1010,
      kopf: "Und er kommt\nnicht allein.", fuss: "STRG + ALT + K" },
    { von: 16, bis: 20, quelle: 85.0, endkarte: true },
  ];

  let aktiv = null;
  let endkarte = null;

  function baueEndkarte() {
    const k = el("div");
    stil(k, { position: "absolute", inset: "0", background: "#000", zIndex: 66 });
    const t = k.appendChild(el("div", "gold", "Jon"));
    stil(t, {
      position: "absolute", left: "0", right: "0", top: "720px", textAlign: "center",
      fontSize: "170px", fontWeight: "200", lineHeight: "1", letterSpacing: ".08em", textIndent: ".08em",
    });
    const z1 = k.appendChild(el("div"));
    z1.innerHTML = "Kostenlos.<br>Läuft auf deinem PC.<br>Auch komplett offline mit Ollama.";
    stil(z1, {
      position: "absolute", left: "70px", right: "70px", top: "952px", textAlign: "center",
      fontSize: "40px", fontWeight: "300", lineHeight: "1.55", letterSpacing: ".03em", color: "rgba(246,242,232,.74)",
    });
    const z2 = k.appendChild(el("div", "gold", "getjon.info"));
    stil(z2, {
      position: "absolute", left: "0", right: "0", top: "1188px", textAlign: "center",
      fontSize: "56px", fontWeight: "400", letterSpacing: ".1em", textIndent: ".1em",
    });
    const z3 = k.appendChild(el("div", null, "FelWorks · Version 4.36.4 · Windows 10/11"));
    stil(z3, {
      position: "absolute", left: "0", right: "0", bottom: "150px", textAlign: "center",
      fontSize: "24px", letterSpacing: ".12em", color: "rgba(255,255,255,.32)",
    });
    const mini = k.appendChild(window.B.miniJon(200));
    stil(mini, { left: "820px", top: "1420px" });
    k.mini = mini;
    k.teile = [t, z1, z2, z3];
    return k;
  }

  function stelle(t) {
    let s = window.SZENEN[0];
    for (const k of window.SZENEN) if (t >= k.von) s = k;
    if (aktiv !== s) {
      szeneNode.innerHTML = "";
      szeneNode.removeAttribute("style");
      stil(szeneNode, { position: "absolute", inset: "0" });
      aktiv = s;
      s.bau(szeneNode);
    }
    s.zeig(klemm(t - s.von, 0, s.bis - s.von));
  }

  function setzeKamera(rect, mitte) {
    if (!rect) {
      stil(kamera, { transform: "none" });
      return;
    }
    const sk = BREITE / rect.w;
    const oben = mitte - (rect.h * sk) / 2;
    stil(kamera, {
      transform: "translate(" + (-rect.x * sk).toFixed(2) + "px," + (-rect.y * sk + oben).toFixed(2) + "px) scale(" + sk.toFixed(5) + ")",
    });
  }

  function langeFassung(t) {
    stelle(t);
    let dunkel = 0;
    for (const g of GRENZEN) {
      const d = Math.abs(t - g);
      if (d < 0.17) dunkel = Math.max(dunkel, 1 - d / 0.17);
    }
    dunkel = Math.max(dunkel, 1 - spanne(t, 0.0, 0.28), spanne(t, 89.4, 90));
    stil(blende, { opacity: dunkel.toFixed(4) });

    let text = "";
    let sicht = 0;
    for (const [von, dauer, s] of UNTERTITEL) {
      if (t >= von - 0.12 && t <= von + dauer + 0.34) {
        text = s;
        sicht = Math.min(ein(t, von - 0.12, 0.16), 1 - ein(t, von + dauer + 0.1, 0.24));
      }
    }
    if (untertitel.textContent !== text) untertitel.textContent = text;
    stil(untertitel, { opacity: sicht.toFixed(3) });
    setzeKamera(null);
  }

  function kurzeFassung(t) {
    const seg = KURZFILM.find((s) => t >= s.von && t < s.bis) || KURZFILM[KURZFILM.length - 1];
    const lokal = t - seg.von;
    if (seg.endkarte) {
      if (!endkarte) {
        endkarte = rahmen.appendChild(baueEndkarte());
      }
      endkarte.style.display = "block";
      stil(kamera, { opacity: 0 });
      const q = ein(lokal, 0.15, 0.8);
      endkarte.teile.forEach((n, i) => stil(n, { opacity: ein(lokal, 0.15 + i * 0.28, 0.7) }));
      stil(endkarte.teile[0], {
        opacity: q,
        filter: "drop-shadow(0 0 " + (46 * q).toFixed(1) + "px rgba(212,175,55,.3))",
      });
      const mp = ein(lokal, 2.2, 0.5);
      stil(endkarte.mini, { opacity: mp, transform: "translateY(" + ((1 - mp) * 24).toFixed(1) + "px)" });
      window.B.miniStand(endkarte.mini, { blinzeln: (function () {
        let w = 1;
        for (const z of [3.0, 3.45]) {
          const d = lokal - z;
          if (d >= 0 && d < 0.16) w = Math.min(w, 1 - Math.sin((d / 0.16) * Math.PI));
        }
        return klemm(w, 0, 1);
      })(), mund: 0 });
      hkKopf.textContent = "";
      hkFuss.textContent = "";
      stil(blende, { opacity: (1 - ein(lokal, 0, 0.2)) * 0 + spanne(t, 19.5, 20) });
      return;
    }
    if (endkarte) endkarte.style.display = "none";
    stil(kamera, { opacity: 1 });
    stelle(seg.quelle + lokal);
    setzeKamera(seg.rect, seg.mitte);
    const zeilen = seg.kopf.split("\n");
    hkKopf.innerHTML = zeilen.join("<br>");
    hkFuss.textContent = seg.fuss;
    const a = ein(lokal, 0.1, 0.32);
    const b = 1 - ein(lokal, seg.bis - seg.von - 0.3, 0.28);
    const s = Math.min(a, b);
    stil(hkKopf, { opacity: s, transform: "translateY(" + ((1 - a) * 14).toFixed(1) + "px)" });
    stil(hkFuss, { opacity: s * 0.92 });
    stil(blende, { opacity: (1 - ein(lokal, 0, 0.09)).toFixed(3) });
    untertitel.textContent = "";
  }

  window.__seek = function (t) {
    if (KURZ) kurzeFassung(t);
    else langeFassung(t);
    const k = Math.floor(t * 60);
    stil(korn, {
      backgroundPosition: Math.floor(window.B.zufall(k) * 160) + "px " + Math.floor(window.B.zufall(k + 91) * 160) + "px",
    });
    return new Promise((auf) => requestAnimationFrame(() => auf(1)));
  };

  window.__seek(0);
})();
