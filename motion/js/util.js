window.JON = window.JON || {};

JON.U = (function () {
  const CFG = JON.CFG;

  const clamp = (v, a, b) => v < a ? a : (v > b ? b : v);
  const lerp = (a, b, t) => a + (b - a) * t;
  const smoothstep = (e0, e1, x) => { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); };
  const TAU = Math.PI * 2;

  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  function css(hex, a) {
    const n = typeof hex === 'string' ? parseInt(hex.replace('#', ''), 16) : hex;
    return 'rgba(' + (n >> 16 & 255) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + (a === undefined ? 1 : a) + ')';
  }

  function canvas2d(w, h) {
    const c = document.createElement('canvas');
    c.width = Math.max(1, Math.ceil(w));
    c.height = Math.max(1, Math.ceil(h));
    return { c, x: c.getContext('2d') };
  }

  function toTexture(c) {
    const t = new THREE.CanvasTexture(c);
    t.minFilter = THREE.LinearMipmapLinearFilter;
    t.magFilter = THREE.LinearFilter;
    t.generateMipmaps = true;
    t.anisotropy = 8;
    t.needsUpdate = true;
    return t;
  }

  const TS = 2;

  function fontStr(weight, size, family) {
    return weight + ' ' + (size * TS) + 'px ' + (family || CFG.FONT);
  }

  function textTexture(runs, o) {
    o = o || {};
    const size = o.size || 100;
    const weight = o.weight || 300;
    const tracking = (o.tracking === undefined ? 0.02 : o.tracking) * size * TS;
    const items = (typeof runs === 'string') ? [{ text: runs }] : runs;

    const m = canvas2d(8, 8).x;
    let total = 0;
    const widths = items.map(function (it) {
      m.font = fontStr(it.weight || weight, size, it.family);
      if ('letterSpacing' in m) m.letterSpacing = tracking + 'px';
      const w = m.measureText(it.text).width + ('letterSpacing' in m ? 0 : tracking * it.text.length);
      total += w;
      return w;
    });

    const pad = size * TS * (o.glow ? 0.55 : 0.28);
    const H = size * TS * 1.45 + pad * 2;
    const W = total + pad * 2;
    const { c, x } = canvas2d(W, H);

    x.textBaseline = 'middle';
    x.textAlign = 'left';

    function paint(pass) {
      let cx = pad;
      items.forEach(function (it, i) {
        x.font = fontStr(it.weight || weight, size, it.family);
        if ('letterSpacing' in x) x.letterSpacing = tracking + 'px';

        if (pass === 'glow') {

          x.shadowColor = css(it.color === undefined ? CFG.C.goldHi : it.color, .5);
          x.shadowBlur = size * TS * 0.45;
          x.fillStyle = css(CFG.C.white, .25);
        } else {
          x.shadowBlur = 0;
          if (it.grad) {
            const g = x.createLinearGradient(cx, H * 0.25, cx, H * 0.78);
            g.addColorStop(0, css(CFG.C.goldPale));
            g.addColorStop(.45, css(CFG.C.goldHi));
            g.addColorStop(1, css(CFG.C.gold));
            x.fillStyle = g;
          } else {
            x.fillStyle = css(it.color === undefined ? CFG.C.white : it.color, 1);
          }
        }

        if ('letterSpacing' in x) {
          x.fillText(it.text, cx, H / 2);
        } else {
          let p = cx;
          for (const ch of it.text) { x.fillText(ch, p, H / 2); p += x.measureText(ch).width + tracking; }
        }
        cx += widths[i];
      });
    }

    if (o.glow) { paint('glow'); paint('glow'); }
    paint('fill');

    return { texture: toTexture(c), aspect: W / H, w: W, h: H, unit: H / (size * TS) };
  }

  const ICONS = {
    ai(x) {
      circle(x, 50, 50, 11);
      [[50,16],[82,34],[82,68],[50,86],[18,68],[18,34]].forEach(function (p, i) {
        line(x, 50, 50, p[0], p[1]); circle(x, p[0], p[1], i % 2 ? 5 : 7);
      });
    },
    code(x) {
      poly(x, [[38,28],[16,50],[38,72]]);
      poly(x, [[62,28],[84,50],[62,72]]);
      line(x, 56, 20, 44, 80);
    },
    web(x) {
      circle(x, 50, 50, 34); line(x, 16, 50, 84, 50);
      x.beginPath(); x.ellipse(50, 50, 15, 34, 0, 0, Math.PI * 2); x.stroke();
      x.beginPath(); x.moveTo(23, 34); x.quadraticCurveTo(50, 47, 77, 34); x.stroke();
      x.beginPath(); x.moveTo(23, 66); x.quadraticCurveTo(50, 53, 77, 66); x.stroke();
    },
    apps(x) {
      [[26,26],[62,26],[26,62],[62,62]].forEach(function (p, i) {
        rr(x, p[0], p[1], 22, 22, 6, i === 0);
      });
    },
    chat(x) {
      rr(x, 16, 22, 68, 46, 14);
      poly(x, [[36,68],[36,84],[52,68]]);
      dot(x, 36, 45); dot(x, 50, 45); dot(x, 64, 45);
    },
    image(x) {
      rr(x, 16, 22, 68, 56, 10);
      circle(x, 36, 40, 6);
      poly(x, [[22,72],[44,50],[58,64],[68,54],[80,72]]);
    },
    automate(x) {
      arc(x, 50, 50, 30, 0.08, 0.78); arc(x, 50, 50, 30, 0.58, 1.28);
      poly(x, [[74,26],[80,20],[82,32]]); poly(x, [[26,74],[20,80],[18,68]]);
      circle(x, 50, 50, 8);
    },
    game(x) {
      rr(x, 14, 34, 72, 36, 16);
      line(x, 30, 52, 42, 52); line(x, 36, 46, 36, 58);
      dot(x, 64, 46, 4.5); dot(x, 72, 56, 4.5);
    },
    server(x) {
      rr(x, 20, 22, 60, 22, 6); rr(x, 20, 54, 60, 22, 6);
      dot(x, 32, 33); dot(x, 32, 65);
      line(x, 46, 33, 68, 33); line(x, 46, 65, 68, 65);
    },
    cloud(x) {
      x.beginPath();
      x.moveTo(28, 66); x.bezierCurveTo(12, 66, 12, 44, 30, 44);
      x.bezierCurveTo(32, 26, 62, 24, 66, 42);
      x.bezierCurveTo(84, 42, 84, 66, 70, 66);
      x.closePath(); x.stroke();
      line(x, 50, 78, 50, 54); poly(x, [[42,62],[50,54],[58,62]]);
    }
  };

  function line(x, a, b, c, d) { x.beginPath(); x.moveTo(a, b); x.lineTo(c, d); x.stroke(); }
  function circle(x, a, b, r) { x.beginPath(); x.arc(a, b, r, 0, Math.PI * 2); x.stroke(); }
  function dot(x, a, b, r) { x.beginPath(); x.arc(a, b, r || 3.6, 0, Math.PI * 2); x.fill(); }
  function arc(x, a, b, r, s, e) { x.beginPath(); x.arc(a, b, r, s * Math.PI, e * Math.PI); x.stroke(); }
  function poly(x, pts) { x.beginPath(); x.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) x.lineTo(pts[i][0], pts[i][1]); x.stroke(); }
  function rr(x, a, b, w, h, r, fill) {
    x.beginPath(); x.roundRect(a, b, w, h, r);
    if (fill) { x.save(); x.globalAlpha = .5; x.fill(); x.restore(); }
    x.stroke();
  }

  function cardTexture(key, label, o) {
    o = o || {};
    const W = 512, H = o.tall === false ? 512 : 620, r = 74;
    const { c, x } = canvas2d(W, H);

    const g = x.createLinearGradient(0, 0, W * .35, H);
    g.addColorStop(0, css(CFG.C.white, .13));
    g.addColorStop(.42, css(CFG.C.white, .045));
    g.addColorStop(1, css(CFG.C.gold, .05));
    x.fillStyle = g;
    x.beginPath(); x.roundRect(10, 10, W - 20, H - 20, r); x.fill();

    const gb = x.createLinearGradient(0, 0, W, H);
    gb.addColorStop(0, css(CFG.C.goldPale, .85));
    gb.addColorStop(.5, css(CFG.C.gold, .25));
    gb.addColorStop(1, css(CFG.C.goldHi, .6));
    x.strokeStyle = gb; x.lineWidth = 3.5;
    x.beginPath(); x.roundRect(10, 10, W - 20, H - 20, r); x.stroke();

    const sg = x.createLinearGradient(0, 0, 0, H * .5);
    sg.addColorStop(0, css(CFG.C.white, .22)); sg.addColorStop(1, css(CFG.C.white, 0));
    x.fillStyle = sg;
    x.beginPath(); x.roundRect(24, 24, W - 48, H * .42, r * .8); x.fill();

    const S = 250, ix = (W - S) / 2, iy = label ? 130 : (H - S) / 2;
    x.save();
    x.translate(ix, iy); x.scale(S / 100, S / 100);
    x.lineWidth = 4.6; x.lineJoin = 'round'; x.lineCap = 'round';
    x.strokeStyle = css(CFG.C.goldHi, .95);
    x.fillStyle = css(CFG.C.goldPale, .95);
    x.shadowColor = css(CFG.C.goldHi, .9); x.shadowBlur = 26;
    (ICONS[key] || ICONS.ai)(x);
    x.restore();

    if (label) {
      x.shadowBlur = 0;
      x.textAlign = 'center'; x.textBaseline = 'middle';
      if ('letterSpacing' in x) x.letterSpacing = '2.5px';
      let fs = o.labelSize || 54;
      do { x.font = '500 ' + fs-- + 'px ' + CFG.FONT; } while (x.measureText(label).width > W - 70 && fs > 20);
      x.fillStyle = css(CFG.C.white, .92);
      x.fillText(label, W / 2, H - 92);
    }

    return { texture: toTexture(c), aspect: W / H };
  }

  function windowTexture(kind) {
    const W = 760, H = 470, r = 26;
    const { c, x } = canvas2d(W, H);

    x.fillStyle = css(0x0a0a10, .78);
    x.beginPath(); x.roundRect(4, 4, W - 8, H - 8, r); x.fill();
    x.strokeStyle = css(CFG.C.gold, .5); x.lineWidth = 2.5;
    x.beginPath(); x.roundRect(4, 4, W - 8, H - 8, r); x.stroke();

    x.fillStyle = css(CFG.C.white, .07);
    x.beginPath(); x.roundRect(4, 4, W - 8, 54, [r, r, 0, 0]); x.fill();
    [30, 54, 78].forEach(function (px, i) {
      x.fillStyle = css(i === 0 ? CFG.C.goldHi : CFG.C.white, i === 0 ? .8 : .18);
      x.beginPath(); x.arc(px, 31, 7, 0, Math.PI * 2); x.fill();
    });
    x.font = '500 20px ' + CFG.FONT; x.fillStyle = css(CFG.C.white, .4);
    x.textBaseline = 'middle'; x.textAlign = 'left';
    x.fillText({ chat: 'Jon · Chat', code: 'app.js', web: 'getjon.info' }[kind] || 'Jon', 112, 31);

    const rnd = rng(kind.length * 977 + 13);

    if (kind === 'chat') {
      const rows = [[.62, 1], [.78, 0], [.45, 0], [.7, 1], [.55, 0]];
      let y = 86;
      rows.forEach(function (row) {
        const w = (W - 80) * row[0], h = 44 + Math.floor(rnd() * 26);
        const bx = row[1] ? W - 40 - w : 40;
        if (row[1]) {
          const g = x.createLinearGradient(bx, y, bx + w, y + h);
          g.addColorStop(0, css(CFG.C.goldPale, .9)); g.addColorStop(1, css(CFG.C.goldDeep, .9));
          x.fillStyle = g;
        } else x.fillStyle = css(CFG.C.white, .08);
        x.beginPath(); x.roundRect(bx, y, w, h, 16); x.fill();

        x.fillStyle = css(row[1] ? 0x000000 : CFG.C.white, row[1] ? .35 : .32);
        for (let i = 0; i * 22 < h - 22; i++) {
          x.fillRect(bx + 18, y + 16 + i * 22, w * (.35 + rnd() * .5), 7);
        }
        y += h + 16;
      });
    } else if (kind === 'code') {
      x.font = '400 21px ' + CFG.MONO; x.textBaseline = 'top';
      CFG.CODE_LINES.slice(0, 12).forEach(function (l, i) {
        if (86 + i * 30 > H - 40) return;
        x.fillStyle = css(CFG.C.white, .17); x.fillText(String(i + 1).padStart(2, '0'), 30, 82 + i * 30);
        x.fillStyle = css(i % 3 === 0 ? CFG.C.goldHi : CFG.C.white, i % 3 === 0 ? .85 : .55);
        x.fillText(l, 76, 82 + i * 30);
      });
    } else {

      x.fillStyle = css(CFG.C.white, .06);
      x.beginPath(); x.roundRect(40, 78, W - 80, 40, 20); x.fill();
      x.font = '400 19px ' + CFG.MONO; x.fillStyle = css(CFG.C.goldHi, .75);
      x.textBaseline = 'middle'; x.fillText('https://getjon.info', 62, 99);
      x.fillStyle = css(CFG.C.white, .10);
      x.beginPath(); x.roundRect(40, 140, W - 80, 150, 14); x.fill();
      for (let i = 0; i < 3; i++) {
        x.fillStyle = css(CFG.C.gold, .16);
        x.beginPath(); x.roundRect(40 + i * ((W - 80) / 3), 310, (W - 80) / 3 - 18, 110, 14); x.fill();
      }
    }
    return { texture: toTexture(c), aspect: W / H };
  }

  function glyphAtlas() {
    const CH = '01<>{}[]();=+-*/#$&|_.:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'.split('');
    const cols = 16, rows = 8, cell = 64;
    const { c, x } = canvas2d(cols * cell, rows * cell);
    x.font = '700 42px ' + CFG.MONO;
    x.textAlign = 'center'; x.textBaseline = 'middle';
    x.fillStyle = '#fff';
    for (let i = 0; i < cols * rows; i++) {
      const ch = CH[i % CH.length];
      x.fillText(ch, (i % cols) * cell + cell / 2, Math.floor(i / cols) * cell + cell / 2);
    }
    const t = toTexture(c);
    t.generateMipmaps = true;
    return { texture: t, cols, rows };
  }

  return { clamp, lerp, smoothstep, TAU, rng, css, canvas2d, toTexture, textTexture, cardTexture, windowTexture, glyphAtlas, ICONS };
})();
