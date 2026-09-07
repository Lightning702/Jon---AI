from __future__ import annotations

MAX_ELEMENTE = 60
TEXT_LIMIT = 4000

ELEMENTE_JS = r"""
(grenze) => {
  const alt = document.querySelectorAll('[data-jon-el]');
  for (const el of alt) el.removeAttribute('data-jon-el');

  const sichtbar = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return false;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none') return false;
    if (parseFloat(s.opacity || '1') < 0.05) return false;
    if (el.closest('[aria-hidden="true"]')) return false;
    if (r.bottom < -600 || r.top > window.innerHeight + 3000) return false;
    return true;
  };

  const rolleVon = (el) => {
    const explizit = (el.getAttribute('role') || '').trim().toLowerCase();
    if (explizit) return explizit;
    const tag = el.tagName.toLowerCase();
    if (tag === 'a') return el.hasAttribute('href') ? 'link' : 'generic';
    if (tag === 'button') return 'button';
    if (tag === 'select') return 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'summary') return 'disclosure';
    if (tag === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (t === 'range') return 'slider';
      if (t === 'file') return 'fileupload';
      if (t === 'hidden') return 'generic';
      if (t === 'button' || t === 'submit' || t === 'reset' || t === 'image')
        return 'button';
      return 'textbox';
    }
    if (el.isContentEditable) return 'textbox';
    return 'button';
  };

  const kurz = (wert) => (wert || '').replace(/\s+/g, ' ').trim().slice(0, 90);

  const nameVon = (el) => {
    const aria = el.getAttribute('aria-label');
    if (aria) return kurz(aria);
    const von = el.getAttribute('aria-labelledby');
    if (von) {
      const teile = von.split(/\s+/).map((id) => {
        const ziel = document.getElementById(id);
        return ziel ? ziel.innerText || ziel.textContent || '' : '';
      });
      const text = kurz(teile.join(' '));
      if (text) return text;
    }
    if (el.id) {
      const label = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (label) {
        const text = kurz(label.innerText || label.textContent);
        if (text) return text;
      }
    }
    const huelle = el.closest('label');
    if (huelle) {
      const text = kurz(huelle.innerText || huelle.textContent);
      if (text) return text;
    }
    const eigen = kurz(el.innerText || el.textContent);
    if (eigen) return eigen;
    const bild = el.querySelector('img[alt]');
    if (bild) {
      const text = kurz(bild.getAttribute('alt'));
      if (text) return text;
    }
    return kurz(el.getAttribute('title') || el.getAttribute('name') || '');
  };

  const sensibelPruefen = (el) => {
    const tag = el.tagName.toLowerCase();
    if (tag !== 'input' && tag !== 'textarea') return false;
    if ((el.getAttribute('type') || '').toLowerCase() === 'password') return true;
    const merkmale = [
      el.getAttribute('autocomplete') || '',
      el.getAttribute('name') || '',
      el.getAttribute('id') || '',
      el.getAttribute('placeholder') || '',
    ]
      .join(' ')
      .toLowerCase();
    return /pass|kennwor|cc-|card|kredit|credit|cvv|cvc|iban|bic|security-code|sicherheitscode/.test(
      merkmale
    );
  };

  const auswahl = document.querySelectorAll(
    'a[href], button, input, select, textarea, summary, [contenteditable="true"],' +
      '[role="button"], [role="link"], [role="tab"], [role="checkbox"],' +
      '[role="radio"], [role="menuitem"], [role="option"], [role="switch"],' +
      '[role="combobox"], [role="searchbox"], [role="textbox"], [onclick]'
  );

  const treffer = [];
  const gesehen = new Set();
  let nummer = 0;
  for (const el of auswahl) {
    if (treffer.length >= grenze) break;
    if (!sichtbar(el)) continue;
    const rolle = rolleVon(el);
    if (rolle === 'generic') continue;
    const name = nameVon(el);
    const tag = el.tagName.toLowerCase();
    const typ =
      tag === 'input' ? (el.getAttribute('type') || 'text').toLowerCase() : tag;
    const eingabe =
      rolle === 'textbox' || rolle === 'combobox' || rolle === 'fileupload';
    if (!name && !eingabe) continue;
    const schluessel = rolle + '|' + name + '|' + typ;
    if (gesehen.has(schluessel)) continue;
    gesehen.add(schluessel);
    nummer += 1;
    const id = 'e' + nummer;
    el.setAttribute('data-jon-el', id);
    const eintrag = { id: id, typ: typ, rolle: rolle, text: name };
    const platzhalter = kurz(el.getAttribute('placeholder'));
    if (platzhalter) eintrag.platzhalter = platzhalter;
    if (tag === 'a') {
      const ziel = el.getAttribute('href') || '';
      if (ziel) eintrag.ziel = ziel.slice(0, 120);
    }
    if (tag === 'select') {
      eintrag.optionen = Array.from(el.options || [])
        .slice(0, 12)
        .map((o) => kurz(o.label || o.text || o.value));
    }
    if (el.disabled || el.getAttribute('aria-disabled') === 'true') {
      eintrag.gesperrt = true;
    }
    if (el.checked === true) eintrag.gewaehlt = true;
    if (sensibelPruefen(el)) eintrag.sensibel = true;
    else if ((tag === 'input' || tag === 'textarea') && el.value) {
      eintrag.wert = kurz(el.value);
    }
    treffer.push(eintrag);
  }
  return treffer;
}
"""

SEITE_JS = r"""
(grenze) => {
  const kurz = (wert) => (wert || '').replace(/[ \t]+/g, ' ').trim();
  const beschreibung = document.querySelector('meta[name="description"]');
  const ueberschriften = Array.from(document.querySelectorAll('h1, h2'))
    .slice(0, 10)
    .map((el) => kurz(el.innerText).slice(0, 120))
    .filter((t) => t.length > 1);
  const haupt =
    document.querySelector('main') ||
    document.querySelector('[role="main"]') ||
    document.querySelector('article') ||
    document.body;
  let text = kurz(haupt ? haupt.innerText || '' : '');
  text = text.replace(/\n{3,}/g, '\n\n');
  const dialoge = Array.from(
    document.querySelectorAll('[role="dialog"], [role="alertdialog"], dialog[open]')
  ).length;
  const roh = document.body ? document.body.innerText.slice(0, 3000) : '';
  return {
    titel: document.title || '',
    url: location.href,
    beschreibung: beschreibung ? kurz(beschreibung.content).slice(0, 240) : '',
    ueberschriften: ueberschriften,
    text: text.slice(0, grenze),
    gekuerzt: text.length > grenze,
    dialoge: dialoge,
    zustimmung_moeglich: /cookie|consent|datenschutz|tracking|einwillig/i.test(roh),
  };
}
"""

ZUSTIMMUNG_JS = r"""
() => {
  const kurz = (wert) => (wert || '').replace(/\s+/g, ' ').trim();
  const kandidaten = Array.from(
    document.querySelectorAll(
      '[id*="consent" i], [class*="consent" i], [id*="cookie" i],' +
        '[class*="cookie" i], [role="dialog"], [aria-modal="true"]'
    )
  ).filter((el) => {
    const r = el.getBoundingClientRect();
    return r.width > 120 && r.height > 60;
  });
  if (!kandidaten.length) return null;
  const wurzel = kandidaten[0];
  const knoepfe = Array.from(
    wurzel.querySelectorAll(
      'button, a[href], [role="button"], input[type="button"], input[type="submit"]'
    )
  )
    .map((el) => kurz(el.innerText || el.value || el.getAttribute('aria-label') || ''))
    .filter((t) => t.length > 1)
    .slice(0, 12);
  return { text: kurz(wurzel.innerText).slice(0, 400), knoepfe: knoepfe };
}
"""

BESCHREIBUNG_JS = r"""
(el) => {
  const kurz = (wert) => (wert || '').replace(/\s+/g, ' ').trim().slice(0, 90);
  const tag = el.tagName.toLowerCase();
  const typ = tag === 'input' ? (el.getAttribute('type') || 'text').toLowerCase() : tag;
  const merkmale = [
    el.getAttribute('autocomplete') || '',
    el.getAttribute('name') || '',
    el.getAttribute('id') || '',
    el.getAttribute('placeholder') || '',
  ]
    .join(' ')
    .toLowerCase();
  const sensibel =
    typ === 'password' ||
    ((tag === 'input' || tag === 'textarea') &&
      /pass|kennwor|cc-|card|kredit|credit|cvv|cvc|iban|bic|security-code|sicherheitscode/.test(
        merkmale
      ));
  return {
    text:
      kurz(el.getAttribute('aria-label')) ||
      kurz(el.innerText || el.textContent) ||
      kurz(el.getAttribute('placeholder')) ||
      kurz(el.getAttribute('title')) ||
      kurz(el.getAttribute('name')),
    typ: typ,
    rolle: kurz(el.getAttribute('role')) || tag,
    sensibel: sensibel,
    gesperrt: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
  };
}
"""
