# Web-Design

Anleitung, wie Jon (oder jede KI) moderne, hochwertige Websites baut. Lies diese
Anleitung vollständig, bevor du die erste Zeile Code schreibst. Diese Datei ist frei
bearbeitbar: Passe Farben, Regeln und Beispiele an deinen Geschmack an — Jon liest immer
die aktuelle Version.

## Grundprinzipien

1. **Mobile-first und responsiv.** Baue zuerst für kleine Bildschirme, erweitere dann mit
   Media-Queries. Nutze `max-width`, `clamp()`, Flexbox und CSS-Grid statt fester Pixel.
2. **Ein System, kein Flickenteppich.** Definiere Design-Tokens als CSS-Variablen ganz oben
   (`:root`) und verwende sie überall. Nie Farben oder Abstände hart im Markup verstreuen.
3. **Weniger, aber gezielt.** Großzügiger Weißraum, klare Hierarchie, maximal zwei
   Schriftfamilien, eine Akzentfarbe.
4. **Zugänglich.** Kontrastverhältnis mindestens 4.5:1 für Text, sichtbarer Fokus-Ring,
   `alt`-Texte, semantische Tags (`header`, `nav`, `main`, `section`, `footer`).
5. **Selbstständig lauffähig.** Liefere standardmäßig eine einzelne `index.html` mit
   eingebettetem CSS (und JS), damit man sie sofort im Browser öffnen kann.

## Design-Tokens (Vorlage, anpassbar)

```css
:root {
  --bg: #0b0b0d;
  --surface: #16161a;
  --text: #f5f5f7;
  --muted: #a1a1aa;
  --accent: #e5b53a;
  --accent-2: #b8862a;
  --radius: 16px;
  --gap: clamp(1rem, 2vw, 2rem);
  --font: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
```

Für ein helles Theme zusätzlich `@media (prefers-color-scheme: light)` überschreiben.

## Layout-Rezept

1. Sticky-Header mit Logo links, Navigation rechts, Blur-Hintergrund
   (`backdrop-filter: blur(12px)`).
2. Hero: große Überschrift (`font-size: clamp(2.5rem, 6vw, 5rem)`), ein Satz Untertitel,
   ein bis zwei Call-to-Action-Buttons.
3. Inhaltssektionen als zentrierter Container (`max-width: 1100px; margin-inline: auto;
   padding-inline: var(--gap)`).
4. Feature-Karten in einem responsiven Grid:
   `grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))`.
5. Footer mit Sekundär-Links und Copyright.

## Optik-Details

- Weiche Schatten statt harter Ränder: `box-shadow: 0 10px 40px rgba(0,0,0,.25)`.
- Abgerundete Ecken über `--radius`.
- Sanfte Übergänge: `transition: transform .2s ease, background .2s ease`; beim Hover
  leicht anheben (`transform: translateY(-2px)`).
- Farbverläufe sparsam für Akzente: `linear-gradient(135deg, var(--accent), var(--accent-2))`.
- Respektiere `@media (prefers-reduced-motion: reduce)` und schalte Animationen ab.

## Bewegung, Animation und 3D — Pflicht, nicht Kür

Eine Seite ohne Bewegung wirkt wie ein Entwurf. Jede Website, App-Oberfläche oder jedes
Spiel, das Jon baut, bekommt echte, flüssige Animationen:

- **Einstieg:** Hero-Elemente blenden gestaffelt ein (`@keyframes` mit `opacity` und
  `transform: translateY()`; `animation-delay` pro Element 80–120 ms versetzt).
- **Scroll-Reveal:** Sektionen erscheinen beim Scrollen. `IntersectionObserver` setzt eine
  Klasse `.sichtbar`, CSS übernimmt den Übergang. Wo verfügbar zusätzlich
  `animation-timeline: view()`.
- **Mikrointeraktionen:** Buttons mit Hover-Glanz, leichtem Anheben und Klick-Federung
  (`transform: scale(.97)`), Links mit wachsender Unterstreichung.
- **3D mit CSS:** `perspective: 1000px` auf dem Container, Karten kippen mit
  `rotateX/rotateY` der Maus nach (Tilt-Effekt per `pointermove`), `transform-style:
  preserve-3d` für echte Tiefe, Flip-Karten mit `backface-visibility: hidden`.
- **Echtes 3D mit Three.js** (per CDN `https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js`
  als ES-Modul): rotierende Objekte, Partikelfelder, Glas-Material
  (`MeshPhysicalMaterial` mit `transmission`), Licht mit Schatten, Kamera folgt der Maus,
  `renderer.setPixelRatio(Math.min(devicePixelRatio, 2))`, Größe bei `resize` anpassen.
- **Weitere Effekte:** Parallax-Ebenen, animierte Farbverläufe (`background-size: 400%`
  + `@keyframes`), Glassmorphism (`backdrop-filter: blur()`), Glow per `box-shadow`,
  Canvas-Partikel, SVG-Linien, die sich zeichnen (`stroke-dasharray`/`dashoffset`),
  Zähler, die hochlaufen.
- **Nur performante Eigenschaften animieren:** `transform`, `opacity`, `filter`. Nie
  `top`, `left`, `width` in Schleifen. `requestAnimationFrame` statt `setInterval`.
- **Barrierefrei:** Alles unter `@media (prefers-reduced-motion: reduce)` ruhigstellen.

Beispiel Tilt-Karte:

```js
document.querySelectorAll(".karte").forEach(k => {
  k.addEventListener("pointermove", e => {
    const r = k.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - .5;
    const y = (e.clientY - r.top) / r.height - .5;
    k.style.transform = `perspective(900px) rotateY(${x * 14}deg) rotateX(${-y * 14}deg) translateZ(0)`;
  });
  k.addEventListener("pointerleave", () => k.style.transform = "");
});
```

## Vorgehen für Jon

1. Kläre in einem Satz Ziel und Stil (falls unklar, nimm dunkel + eine Akzentfarbe).
2. Erzeuge die Ordnerstruktur, z. B. `write_file` auf `index.html`.
3. Schreibe das komplette Dokument mit `<!doctype html>`, `<head>` (Meta-Viewport, Titel,
   `<style>`), semantischem `<body>`.
4. Öffne das Ergebnis mit `open_url` (Datei-Pfad) oder `open_in_vscode`, damit der Nutzer
   es sofort sieht.
5. Frage nach gewünschten Anpassungen und iteriere.

## Checkliste vor der Übergabe

- [ ] Öffnet sich fehlerfrei im Browser
- [ ] Sieht auf 360 px Breite und auf Desktop gut aus
- [ ] Kontrast und Fokus sichtbar
- [ ] Kein horizontales Scrollen
- [ ] Tokens statt Magic-Numbers
- [ ] Echte Animationen: Einstieg, Scroll-Reveal, Hover, mindestens ein 3D- oder Tiefeneffekt
- [ ] Kein Platzhaltertext, keine Kommentare im Code
