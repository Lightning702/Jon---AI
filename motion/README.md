# Jon — Motion Graphics (Instagram Reels & TikTok)

Ein cinematischer 20-Sekunden-Werbespot für **Jon**, komplett im Browser gerendert.
Kein After Effects, keine Videodatei als Vorlage, keine Bilddateien: jedes Pixel
entsteht zur Laufzeit aus WebGL-Shadern, jeder Ton aus Oszillatoren.

| | |
|---|---|
| **Format** | 1080 × 1920 (9:16), 60 FPS, 20,000 s |
| **Look** | Tiefschwarz, Gold `#d4af37` / `#FFD700`, Liquid-Glass, Neon-Glow |
| **Technik** | HTML + CSS + JavaScript, three.js, GSAP, WebAudio, WebCodecs |
| **Ausgabe** | fertige MP4-Datei mit Ton — direkt aus der Seite heraus |

---

## Starten

Doppelklick auf `index.html`. Das genügt — die Seite läuft ohne Webserver.
Beim ersten Start wird eine Internetverbindung gebraucht, weil three.js, GSAP und
der MP4-Muxer über ein CDN geladen werden. Danach liegen sie im Browser-Cache.

Alternativ mit lokalem Server (nötig für den Ordner-Export der Bildfolge):

```bash
python -m http.server 8791 --directory motion
```

Empfohlener Browser: **Chrome oder Edge**. Firefox und Safari spielen die
Animation ab, können aber (noch) kein MP4 schreiben.

---

## Video exportieren

### ⬇ MP4 exportieren — der Weg, den du willst

Rendert die Timeline **Bild für Bild** und codiert jedes Bild einzeln mit H.264,
die Tonspur wird offline gerendert und als AAC dazugemuxt.

* Ergebnis: sendefertige `.mp4`, exakt 60,000 FPS, exakt 20,000 s
* Völlig unabhängig davon, wie schnell dein Rechner rendert — es gibt keine
  ausgelassenen Bilder und kein Ruckeln, auch wenn der Export länger dauert
  als das Video
* **Kein ffmpeg nötig.** Die Datei kann direkt hochgeladen werden.

Rechne mit 1–4 Minuten für die 1200 Bilder. Das Fenster muss dabei sichtbar
bleiben (im Hintergrund drosselt der Browser die Bildschleife).

### ● Live-Aufnahme

Nimmt in Echtzeit auf (`MediaRecorder`), inklusive Ton. Schnell und bequem,
aber die Bildrate hängt an der Leistung des Rechners. Falls dein Browser dabei
WebM liefert:

```bash
ffmpeg -i jon-live.webm -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k jon.mp4
```

### ▦ Bildfolge

Schreibt 1200 Einzelbilder in einen selbst gewählten Ordner — für Premiere,
DaVinci Resolve oder eigene ffmpeg-Ketten. Zusammen mit der WAV-Tonspur:

```bash
ffmpeg -framerate 60 -i frame_%05d.jpg -i jon-ton.wav -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -shortest jon.mp4
```

### ♪ WAV

Nur die Tonspur, 48 kHz Stereo, exakt 20 s.

---

## Bedienung

| Taste | Wirkung |
|---|---|
| `Leertaste` | Abspielen / Pause |
| `R` | Zurück auf Anfang |
| `M` | Ton an / aus |
| `1` – `5` | Szene 1–5 anspringen |
| `H` | Bedienfeld ausblenden (reine Vorschau) |

Der Schieberegler scrubbt die Timeline. Jede Zeitposition ist reproduzierbar:
`tl.time(x)` liefert immer exakt dasselbe Bild — Voraussetzung für den
Bild-für-Bild-Export.

In der Konsole steht ein offener Griff bereit:

```js
JON.app.seek(7.2)              // auf Sekunde 7,2 springen
JON.app.world.state            // Kamera- und Look-Werte live ansehen
JON.app.world.logo.u.uRing.value = 0.4   // das Logo halb gezeichnet
```

---

## Storyboard

| Zeit | Szene | Inhalt |
|---|---|---|
| 0,0 – 3,4 s | **Entstehung** | Schwarz. Goldstaub sammelt sich. Ein Lichtstrahl zeichnet den Jon-Ring im Uhrzeigersinn, das Glas füllt sich, Augen und Mund erscheinen. `Meet Jon` |
| 3,4 – 6,6 s | **Fähigkeiten** | Das Logo tritt vor. Sieben Glaskacheln (KI, Programmieren, Webseiten, Apps, Chat, Bilder, Automatisierung) schweben in zwei Spuren vorbei, goldene Datenlinien verbinden sie mit dem Kern. `Your personal AI` |
| 6,6 – 10,6 s | **Datenstrom** | Die Kamera taucht in einen Code-Regen. Hologramm-Fenster öffnen sich: Chat, Editor, Browser. `Create.` `Code.` `Learn.` |
| 10,6 – 15,6 s | **Ökosystem** | Jon in der Mitte, drei rotierende Lichtringe, sieben Knoten (Webseiten, Apps, Spiele, KI, Server, Cloud, Code) kreisen harmonisch. |
| 15,6 – 20,0 s | **Finale** | Alles löst sich nach außen auf. Nur das Logo bleibt, atmender Goldschein. `One AI.` — Pause — `Unlimited possibilities.` — `getjon.info` |

---

## Aufbau des Codes

```
motion/
├── index.html          Bühne + Bedienfeld
├── css/style.css       nur die Oberfläche (nie Teil des Videos)
└── js/
    ├── config.js       Timing, Farben, Texte, Inhalte  ← hier anpassen
    ├── util.js         Text-, Icon- und Fenster-Texturen aus Canvas2D
    ├── gfx.js          Render-Pipeline: HDR, Bloom, Grade, Korn
    ├── objects.js      Bausteine: Logo, Partikel, Kacheln, Code-Regen …
    ├── scene.js        Layout der Welt + Zustand → Uniforms pro Bild
    ├── timeline.js     die Regie (eine GSAP-Timeline)
    ├── audio.js        Musik und Sounddesign, rein synthetisch
    ├── recorder.js     MP4 / Live-Aufnahme / Bildfolge
    └── main.js         Zusammenbau, Schleife, Bedienung
```

### Warum klassische Skripte statt ES-Modulen

Damit die Datei per Doppelklick läuft. ES-Module verweigern unter `file://`
den Dienst; klassische `<script>`-Tags nicht.

### Warum eine eigene Nachbearbeitung statt `EffectComposer`

Zwei CDN-Dateien statt einem Dutzend, kein Import-Map-Gefummel — und der
Gold-Bloom lässt sich exakt so abstimmen, wie ein Werbespot ihn braucht:
zwei getrennte Unschärfestufen (eng + weit), warm eingefärbt, dazu Filmkurve,
Vignette, Korn, dezente chromatische Aberration und eine zuschaltbare
Bewegungsunschärfe über das Vorbild.

### Warum jede Animation `fromTo` benutzt

Anfangs- **und** Endwert stehen fest, nichts wird zur Laufzeit eingefangen.
Nur so liefert ein Sprung an eine beliebige Zeitposition zuverlässig dasselbe
Bild wie das Durchlaufen von vorn — die Grundlage für den Export.

---

## Anpassen

**Texte, Farben, Timing** stehen alle in `js/config.js`:

```js
const T = { s1: 0.0, s2: 3.40, s3: 6.60, s4: 10.60, s5: 15.60, end: 20.0 };
const TXT = { s1: 'Meet Jon', s2: 'Your personal AI', … };
const SKILLS = [ { icon: 'ai', label: 'KI' }, … ];
```

**Neues Icon**: eine Zeichenfunktion in `JON.U.ICONS` ergänzen (Zeichenfläche
100 × 100, reine Linienkunst) und den Schlüssel in `SKILLS` oder `ORBIT` nutzen.

**Anderes Format** (z. B. 1:1 für den Feed): in `config.js` `WIDTH`/`HEIGHT`
ändern. Das Layout in `scene.js` ist auf 9:16 gerechnet und braucht dann
angepasste y-Werte.

**Musik austauschen**: `js/audio.js` erzeugt alles selbst. Wer eine eigene
Tonspur will, lässt den Ton beim Export weg (Stummschaltung) und mischt die
Musik im Schnittprogramm dazu.

---

## Lizenz und Verwendung

Der Code gehört zum Jon-Projekt. Die benutzten Bibliotheken sind frei:
three.js (MIT), GSAP (Standard-Lizenz, kostenlos für diesen Einsatz),
mp4-muxer (MIT), Inter und JetBrains Mono (SIL Open Font License).

Musik und Sounddesign entstehen vollständig synthetisch im Browser — es gibt
also keine Sample-Lizenzen und keine Ansprüche Dritter auf der Tonspur. Genau
deshalb ist der Clip ohne Rückfragen für bezahlte Werbung auf TikTok und
Instagram nutzbar.
