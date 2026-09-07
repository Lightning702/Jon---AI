window.B = (function () {
  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html !== undefined) n.innerHTML = html;
    return n;
  }
  function stil(n, o) {
    for (const k in o) n.style[k] = o[k];
    return n;
  }
  function setze(n, o) {
    for (const k in o) n.setAttribute(k, o[k]);
    return n;
  }
  function klemm(x, a, b) {
    return x < a ? a : x > b ? b : x;
  }
  function spanne(t, a, b) {
    return klemm((t - a) / (b - a), 0, 1);
  }
  function raus(x) {
    return 1 - Math.pow(1 - klemm(x, 0, 1), 3);
  }
  function ein(t, a, dauer) {
    return raus(spanne(t, a, a + dauer));
  }
  function weich(x) {
    x = klemm(x, 0, 1);
    return x * x * (3 - 2 * x);
  }
  function zufall(i) {
    const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
  }

  function tippe(text, t, start, cps) {
    const n = klemm(Math.floor((t - start) * cps), 0, text.length);
    return { text: text.slice(0, n), fertig: n >= text.length, laeuft: t >= start && n < text.length };
  }
  function stroeme(text, t, start, wps) {
    const worte = text.split(" ");
    const n = klemm(Math.floor((t - start) * wps), 0, worte.length);
    return { text: worte.slice(0, n).join(" "), fertig: n >= worte.length, laeuft: t >= start && n < worte.length };
  }

  function hintergrund() {
    const d = el("div", "schicht");
    stil(d, {
      background:
        "radial-gradient(circle at 22% -6%, #16161f 0%, #08080b 48%, #000 100%)",
    });
    const schein = el("div");
    stil(schein, {
      position: "absolute",
      right: "3%",
      bottom: "0",
      width: "780px",
      height: "620px",
      background: "radial-gradient(ellipse at 60% 80%, rgba(212,175,55,0.075), rgba(212,175,55,0) 62%)",
    });
    d.appendChild(schein);
    return d;
  }

  function symbol(name) {
    const g = {
      start:
        '<svg width="22" height="22" viewBox="0 0 22 22"><rect x="1" y="1" width="9" height="9" rx="1.6" fill="#cfd3dd"/><rect x="12" y="1" width="9" height="9" rx="1.6" fill="#cfd3dd"/><rect x="1" y="12" width="9" height="9" rx="1.6" fill="#cfd3dd"/><rect x="12" y="12" width="9" height="9" rx="1.6" fill="#cfd3dd"/></svg>',
      lupe:
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c8ccd6" stroke-width="1.9"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.4 15.4 L21 21" stroke-linecap="round"/></svg>',
      ordner:
        '<svg width="24" height="24" viewBox="0 0 24 24"><path d="M2.6 6.4a1.6 1.6 0 0 1 1.6-1.6h4.6l1.9 2.2h8.7a1.6 1.6 0 0 1 1.6 1.6v9.4a1.6 1.6 0 0 1-1.6 1.6H4.2a1.6 1.6 0 0 1-1.6-1.6z" fill="#e2b866"/><path d="M2.6 9.6h18.8v8a1.6 1.6 0 0 1-1.6 1.6H4.2a1.6 1.6 0 0 1-1.6-1.6z" fill="#f2cf8b"/></svg>',
      welt:
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#9fb6d4" stroke-width="1.7"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 3 2.6 15 0 18M12 3c-2.6 3-2.6 15 0 18"/></svg>',
      pfeil:
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#b9bec9" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 15l6-6 6 6"/></svg>',
      funk:
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#b9bec9" stroke-width="1.9" stroke-linecap="round"><path d="M2.6 8.6a15 15 0 0 1 18.8 0M6 12.4a10 10 0 0 1 12 0M9.4 16.2a5 5 0 0 1 5.2 0"/><circle cx="12" cy="19.4" r="1.2" fill="#b9bec9" stroke="none"/></svg>',
      ton:
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#b9bec9" stroke-width="1.8" stroke-linejoin="round"><path d="M4 9.4h3.4L12 5.6v12.8L7.4 14.6H4z" fill="#b9bec9"/><path d="M15.6 9.4a4 4 0 0 1 0 5.2" stroke-linecap="round"/></svg>',
      akku:
        '<svg width="24" height="17" viewBox="0 0 30 17" fill="none" stroke="#b9bec9" stroke-width="1.5"><rect x="1" y="3.4" width="24" height="10.2" rx="2.6"/><rect x="3" y="5.4" width="18" height="6.2" rx="1.4" fill="#b9bec9" stroke="none"/><path d="M27.4 7v3" stroke-linecap="round"/></svg>',
      schloss:
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#f5d67b" stroke-width="2"><rect x="4.5" y="10.4" width="15" height="10" rx="2.4"/><path d="M8 10.4V7.6a4 4 0 0 1 8 0v2.8"/></svg>',
      haken:
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8fd05a" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 12.6l4.8 4.8L19.5 7.2"/></svg>',
      zahnrad:
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f5d67b" stroke-width="1.8"><circle cx="12" cy="12" r="3.2"/><path d="M12 2.6v3M12 18.4v3M21.4 12h-3M5.6 12h-3M18.6 5.4l-2.1 2.1M7.5 16.5l-2.1 2.1M18.6 18.6l-2.1-2.1M7.5 7.5L5.4 5.4" stroke-linecap="round"/></svg>',
    };
    return g[name] || "";
  }

  function taskleiste(uhr, datum) {
    const t = el("div");
    stil(t, {
      position: "absolute",
      left: 0,
      right: 0,
      bottom: 0,
      height: "52px",
      background: "rgba(11,11,15,0.86)",
      backdropFilter: "blur(26px)",
      borderTop: "1px solid rgba(255,255,255,0.07)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 30,
    });
    const mitte = el("div");
    stil(mitte, { display: "flex", gap: "6px", alignItems: "center" });
    const felder = [
      symbol("start"),
      symbol("lupe"),
      symbol("ordner"),
      symbol("welt"),
      '<span style="width:13px;height:13px;border-radius:50%;background:#d4af37;box-shadow:0 0 14px rgba(212,175,55,.7);display:block"></span>',
    ];
    felder.forEach((s, i) => {
      const k = el("div", null, s);
      stil(k, {
        width: "42px",
        height: "40px",
        borderRadius: "9px",
        display: "grid",
        placeItems: "center",
        background: i === 4 ? "rgba(212,175,55,0.1)" : "transparent",
        position: "relative",
      });
      if (i === 4) {
        const strich = el("div");
        stil(strich, {
          position: "absolute",
          bottom: "3px",
          width: "16px",
          height: "3px",
          borderRadius: "2px",
          background: "rgba(212,175,55,0.85)",
        });
        k.appendChild(strich);
      }
      mitte.appendChild(k);
    });
    t.appendChild(mitte);

    const rechts = el("div");
    stil(rechts, {
      position: "absolute",
      right: "18px",
      display: "flex",
      alignItems: "center",
      gap: "14px",
      color: "#c3c8d2",
      fontSize: "13px",
    });
    rechts.appendChild(el("div", null, symbol("pfeil")));
    rechts.appendChild(el("div", null, symbol("funk")));
    rechts.appendChild(el("div", null, symbol("ton")));
    rechts.appendChild(el("div", null, symbol("akku")));
    const zeit = el("div", null, uhr + "<br>" + datum);
    stil(zeit, { textAlign: "right", lineHeight: "1.28", fontSize: "12.5px", letterSpacing: ".01em" });
    rechts.appendChild(zeit);
    t.appendChild(rechts);
    return t;
  }

  function schreibtischsymbole() {
    const w = el("div");
    stil(w, { position: "absolute", left: "34px", top: "30px", display: "flex", flexDirection: "column", gap: "8px" });
    [["Projekte", "ordner"], ["Bilder", "ordner"], ["Jon", "jon"]].forEach(([name, art]) => {
      const k = el("div");
      stil(k, {
        width: "104px",
        padding: "12px 6px 9px",
        borderRadius: "10px",
        textAlign: "center",
        color: "rgba(255,255,255,0.66)",
        fontSize: "12.5px",
        textShadow: "0 1px 4px rgba(0,0,0,.9)",
      });
      const bild =
        art === "jon"
          ? '<span style="display:inline-block;width:34px;height:34px;border-radius:50%;background:radial-gradient(circle at 34% 30%,#f5d67b,#9a7b1f);box-shadow:0 0 18px rgba(212,175,55,.45)"></span>'
          : '<span style="display:inline-block;transform:scale(1.5)">' + symbol("ordner") + "</span>";
      k.innerHTML = '<div style="height:38px;display:grid;place-items:center">' + bild + "</div>" + name;
      w.appendChild(k);
    });
    return w;
  }

  function miniJon(groesse) {
    const w = el("div");
    stil(w, { position: "absolute", width: groesse + "px", height: groesse + "px", zIndex: 45 });
    w.innerHTML =
      '<svg viewBox="0 0 120 120" width="' + groesse + '" height="' + groesse + '" style="overflow:visible">' +
      '<defs><linearGradient id="mjgold" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="120" y2="120">' +
      '<stop offset="0%" stop-color="#f5d67b"/><stop offset="55%" stop-color="#d4af37"/><stop offset="100%" stop-color="#9a7b1f"/></linearGradient>' +
      '<radialGradient id="mjglanz" cx="34%" cy="26%" r="52%"><stop offset="0%" stop-color="rgba(255,255,255,0.16)"/><stop offset="100%" stop-color="rgba(255,255,255,0)"/></radialGradient>' +
      "</defs>" +
      '<g class="dreh">' +
      '<circle class="schein" cx="60" cy="60" r="56" fill="rgba(212,175,55,0.13)"/>' +
      '<circle class="gesicht" cx="60" cy="60" r="52" fill="#0a0a0e"/>' +
      '<circle class="ring" cx="60" cy="60" r="52" fill="none" stroke="url(#mjgold)" stroke-width="4" stroke-linecap="round"/>' +
      '<circle cx="60" cy="60" r="52" fill="url(#mjglanz)"/>' +
      '<g class="backen" opacity="0"><ellipse cx="38" cy="70" rx="8" ry="5" fill="#ff9bb0" opacity="0.5"/><ellipse cx="82" cy="70" rx="8" ry="5" fill="#ff9bb0" opacity="0.5"/></g>' +
      '<g class="augen">' +
      '<ellipse class="augeL" cx="43" cy="53" rx="8" ry="8" fill="#f7f2e4"/>' +
      '<ellipse class="augeR" cx="77" cy="53" rx="8" ry="8" fill="#f7f2e4"/>' +
      '<circle class="lichtL" cx="45.5" cy="50.5" r="2.5" fill="#fff"/>' +
      '<circle class="lichtR" cx="79.5" cy="50.5" r="2.5" fill="#fff"/>' +
      "</g>" +
      '<path class="laecheln" d="M44 76 Q60 90 76 76" fill="none" stroke="url(#mjgold)" stroke-width="5" stroke-linecap="round"/>' +
      '<ellipse class="mund" cx="60" cy="80" rx="13" ry="0" fill="url(#mjgold)"/>' +
      "</g></svg>";
    stil(w, { filter: "drop-shadow(0 10px 26px rgba(0,0,0,.75))" });
    return w;
  }

  function miniStand(w, o) {
    const q = (s) => w.querySelector(s);
    const blinzel = o.blinzeln === undefined ? 1 : o.blinzeln;
    const rx = 8;
    const ry = 8 * blinzel;
    setze(q(".augeL"), { ry: Math.max(0.5, ry) });
    setze(q(".augeR"), { ry: Math.max(0.5, ry) });
    q(".lichtL").style.opacity = blinzel > 0.45 ? 1 : 0;
    q(".lichtR").style.opacity = blinzel > 0.45 ? 1 : 0;
    const mund = o.mund || 0;
    if (mund > 0.02) {
      q(".laecheln").style.opacity = 0;
      q(".mund").style.opacity = 1;
      setze(q(".mund"), { ry: (2.6 + mund * 10.5).toFixed(2) });
    } else {
      q(".laecheln").style.opacity = 1;
      q(".mund").style.opacity = 0;
    }
    if (o.farbe) {
      q(".ring").setAttribute("stroke", o.farbe);
      q(".laecheln").setAttribute("stroke", o.farbe);
      q(".mund").setAttribute("fill", o.farbe);
      q(".schein").setAttribute("fill", o.schein || "rgba(212,175,55,0.13)");
    }
    if (o.backen !== undefined) q(".backen").style.opacity = o.backen;
    const dreh = o.dreh || 0;
    const s = Math.cos(dreh);
    const g = q(".dreh");
    g.setAttribute("transform", "translate(60,60) scale(" + s.toFixed(4) + ",1) translate(-60,-60)");
    const versatz = Math.sin(dreh) * 7;
    q(".augen").setAttribute("transform", "translate(" + (-versatz).toFixed(2) + ",0)");
    q(".laecheln").setAttribute("transform", "translate(" + (-versatz * 0.7).toFixed(2) + ",0)");
    q(".mund").setAttribute("transform", "translate(" + (-versatz * 0.7).toFixed(2) + ",0)");
    return w;
  }

  function sprechblase(text, breite) {
    const b = el("div");
    stil(b, {
      position: "absolute",
      maxWidth: (breite || 300) + "px",
      padding: "13px 16px",
      borderRadius: "16px 16px 16px 4px",
      background: "rgba(14,14,18,0.93)",
      border: "1px solid rgba(212,175,55,0.4)",
      color: "#f4f0e6",
      fontSize: "15.5px",
      lineHeight: "1.45",
      boxShadow: "0 12px 34px rgba(0,0,0,0.6)",
      whiteSpace: "pre-wrap",
      zIndex: 46,
    });
    b.textContent = text || "";
    return b;
  }

  function katze(groesse) {
    const w = el("div");
    stil(w, { position: "absolute", width: groesse + "px", height: groesse + "px", zIndex: 44 });
    w.innerHTML =
      '<svg viewBox="0 0 64 64" width="' + groesse + '" height="' + groesse + '" style="overflow:visible"><g class="kdreh">' +
      "<defs>" +
      '<radialGradient id="kBody" cx="34%" cy="28%" r="78%"><stop offset="0%" stop-color="#e0b483"/><stop offset="55%" stop-color="#b98a55"/><stop offset="100%" stop-color="#7d5a31"/></radialGradient>' +
      '<radialGradient id="kHead" cx="32%" cy="26%" r="76%"><stop offset="0%" stop-color="#efcb9c"/><stop offset="52%" stop-color="#caa06a"/><stop offset="100%" stop-color="#8e6a3c"/></radialGradient>' +
      '<radialGradient id="kEar" cx="40%" cy="30%" r="80%"><stop offset="0%" stop-color="#a97a45"/><stop offset="100%" stop-color="#6a4726"/></radialGradient>' +
      '<radialGradient id="kGround" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="rgba(0,0,0,0.55)"/><stop offset="100%" stop-color="rgba(0,0,0,0)"/></radialGradient>' +
      "</defs>" +
      '<ellipse cx="32" cy="59" rx="19" ry="4.5" fill="url(#kGround)"/>' +
      '<path class="schwanz" d="M50 52 Q62 47 57 38" fill="none" stroke="url(#kBody)" stroke-width="6.5" stroke-linecap="round"/>' +
      '<ellipse cx="32" cy="46" rx="18" ry="14" fill="url(#kBody)"/>' +
      '<ellipse cx="26" cy="41" rx="9" ry="6" fill="rgba(255,255,255,0.13)"/>' +
      '<g class="kopf">' +
      '<path d="M18 30 L14 16 L26 26 Z" fill="url(#kEar)"/>' +
      '<path d="M46 30 L50 16 L38 26 Z" fill="url(#kEar)"/>' +
      '<path d="M19 29 L17 21 L24 27 Z" fill="#ffb3c1"/>' +
      '<path d="M45 29 L47 21 L40 27 Z" fill="#ffb3c1"/>' +
      '<circle cx="32" cy="34" r="15" fill="url(#kHead)"/>' +
      '<ellipse cx="26" cy="27" rx="7" ry="5" fill="rgba(255,255,255,0.18)"/>' +
      '<circle cx="26" cy="32" r="2.9" fill="#0d0d12"/><circle cx="25.2" cy="31.1" r="0.9" fill="#fff" opacity="0.85"/>' +
      '<circle cx="38" cy="32" r="2.9" fill="#0d0d12"/><circle cx="37.2" cy="31.1" r="0.9" fill="#fff" opacity="0.85"/>' +
      '<path d="M30 37 Q32 39 34 37" fill="none" stroke="#111" stroke-width="1.6" stroke-linecap="round"/>' +
      '<path d="M32 36 l0 2" stroke="#ffb3c1" stroke-width="1.6"/>' +
      '<path d="M20 36 h-9 M20 39 h-8" stroke="#2c2c34" stroke-width="1.2" stroke-linecap="round"/>' +
      '<path d="M44 36 h9 M44 39 h8" stroke="#2c2c34" stroke-width="1.2" stroke-linecap="round"/>' +
      "</g></g></svg>";
    return w;
  }

  function zeiger() {
    const z = el("div");
    z.id = "zeiger";
    z.innerHTML =
      '<svg width="26" height="34" viewBox="0 0 26 34"><path d="M2 1.4 L2 26.2 L8.4 20.4 L12.4 29.8 L16.4 28 L12.4 18.8 L21 18.6 Z" fill="#ffffff" stroke="#0a0a0c" stroke-width="1.4" stroke-linejoin="round"/></svg>';
    return z;
  }

  function jonFenster(o) {
    const f = el("div", "fenster");
    stil(f, {
      left: o.x + "px",
      top: o.y + "px",
      width: o.b + "px",
      height: o.h + "px",
      display: "flex",
      flexDirection: "column",
    });
    const leiste = el("div", "leiste");
    leiste.innerHTML =
      '<div class="marke"><span class="punkt"></span><span class="gold">JON</span>' +
      (o.zusatz
        ? '<span style="margin-left:14px;font-size:12.5px;font-weight:400;letter-spacing:.04em;color:rgba(245,214,123,.72);border:1px solid rgba(212,175,55,.3);background:rgba(212,175,55,.09);padding:3px 9px;border-radius:8px">' +
          o.zusatz +
          "</span>"
        : "") +
      "</div>" +
      '<div class="knopfreihe"><span>—</span><span>▢</span><span>◍</span><span>✕</span></div>';
    f.appendChild(leiste);
    const koerper = el("div");
    stil(koerper, { flex: "1", display: "flex", minHeight: "0" });
    f.appendChild(koerper);
    f.koerper = koerper;
    return f;
  }

  function seitenleiste(eintraege) {
    const s = el("div", "seitenleiste");
    s.innerHTML =
      '<div class="neuerchat">Neuer Chat</div><div class="suchfeld">Chats durchsuchen …</div>';
    const v = el("div", "verlauf");
    eintraege.forEach((e, i) => {
      const d = el("div", i === 0 ? "aktiv" : null);
      d.innerHTML = e[0] + "<small>" + e[1] + "</small>";
      v.appendChild(d);
    });
    s.appendChild(v);
    const fuss = el("div");
    stil(fuss, {
      marginTop: "auto",
      paddingTop: "12px",
      borderTop: "1px solid rgba(255,255,255,0.08)",
      fontSize: "11.5px",
      color: "rgba(255,255,255,0.28)",
    });
    fuss.textContent = "Jon 4.36.4 · lokal";
    s.appendChild(fuss);
    return s;
  }

  function chatflaeche() {
    const c = el("div", "chatflaeche");
    const liste = el("div", "verlaufsliste");
    const eing = el("div", "eingabe");
    eing.innerHTML =
      '<div class="klammer">+</div><div class="feld leer">Frag Jon...</div><div class="senden">Senden</div>';
    c.appendChild(liste);
    c.appendChild(eing);
    c.liste = liste;
    c.feld = eing.querySelector(".feld");
    return c;
  }

  function blase(art, text) {
    const b = el("div", "blase " + art);
    b.textContent = text || "";
    return b;
  }

  function schild(text, unter) {
    const s = el("div", "schild");
    s.innerHTML = text + (unter ? '<span class="unter">' + unter + "</span>" : "");
    return s;
  }

  return {
    el, stil, setze, klemm, spanne, raus, ein, weich, zufall,
    tippe, stroeme, hintergrund, taskleiste, schreibtischsymbole, symbol,
    miniJon, miniStand, sprechblase, katze, zeiger, jonFenster, seitenleiste,
    chatflaeche, blase, schild,
  };
})();
