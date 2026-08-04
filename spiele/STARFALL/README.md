# STARFALL: BEYOND THE VOID

Sci-Fi-Open-World in C++20 ohne Engine. Eigene Mathematik, eigener Speicher-Layer, eigenes ECS,
eigener Renderer, eigenes Netzwerk. Im Zentrum steht **THE VOID HEART**, ein supermassives
Schwarzes Loch mit 4,1 Millionen Sonnenmassen, das pro Pixel durch Integration von Nullgeodäten
in der Kerr-Metrik gerendert wird.

By FelWorks.

## Bauen

```bash
build.bat
```

Braucht die Visual Studio Build Tools mit C++-Workload. Ergebnis: `bin/STARFALL.exe`.
Alternativ über Jon: Reiter *Spiele* → STARFALL → **Bauen**.

## Starten

```bash
bin\STARFALL.exe
```

In Jon erscheint STARFALL automatisch neben ECHO und AETHERIA, sobald `bin/STARFALL.exe` existiert.

## Grafikstufen und Sparmodus

STARFALL erkennt beim Start die Grafikkarte und wählt eine passende Stufe. Auf Notebook-Grafik
(Intel UHD/Iris, AMD Vega 8, Software-Rasterizer) startet es direkt im **Sparmodus**.

| Stufe | Void-Heart-Auflösung | Geodäten-Schritte | Integrator | Bloom | Atmosphären | Gemessen auf Intel UHD 620 |
|---|---|---|---|---|---|---|
| Sparmodus | 28 % | 96 | Mittelpunkt (RK2) | aus | aus | ~43 fps |
| Niedrig | 36 % | 160 | Mittelpunkt (RK2) | 2 Stufen | an | ~30 fps |
| Mittel | 50 % | 280 | Runge-Kutta 4 | 4 Stufen | an | ~12 fps |
| Hoch | 70 % | 400 | Runge-Kutta 4 | 5 Stufen | an | ~7 fps |
| Ultra | 100 % | 520 | Runge-Kutta 4 | 5 Stufen | an | ~3 fps |

Der Sparmodus ändert **nicht** die Physik: Kerr-Metrik, Gravitationslinse, Doppler-Beaming,
Rotverschiebung und Zeitdilatation bleiben identisch. Reduziert werden nur Abtastdichte,
Auflösung und Effekte.

Die Automatik misst laufend die Bildrate und senkt zuerst die Auflösung, dann die Stufe,
wenn das Ziel (Standard 60 fps) über 1,2 s verfehlt wird. Erholt sich die Bildrate über
4 s deutlich, steigt die Auflösung wieder.

Tasten im Spiel:

| Taste | Wirkung |
|---|---|
| F5 | Stufe niedriger (schaltet Automatik ab) |
| F6 | Stufe höher (schaltet Automatik ab) |
| F7 | Automatik an/aus |
| F8 | Sofort in den Sparmodus |
| F11 | Vollbild |

## Kommandozeile

| Schalter | Bedeutung |
|---|---|
| `-grafik spar\|niedrig\|mittel\|hoch\|ultra` | Feste Grafikstufe |
| `-sparmodus` | Kurzform für `-grafik spar` |
| `-autografik 0\|1` | Automatische Anpassung an/aus |
| `-zielfps 30` | Zielbildrate der Automatik |
| `-windowed`, `-width`, `-height`, `-fullscreen` | Fenster |
| `-vsync 0\|1` | Vertikale Synchronisation |
| `-seed 0x...` | Universums-Seed |
| `-flug` | Menü überspringen, direkt fliegen |
| `-voidzone` | Start nahe am Void Heart |
| `-menuzeit 68` | Startpunkt der 90-Sekunden-Kamerafahrt |
| `-frames N` | Nach N Bildern beenden |
| `-shot datei.ppm` | Bildschirmfoto schreiben |
| `-tests` | Testsuite laufen lassen, ohne Fenster |
| `-host` / `-join CODE` | Koop über den Jon-Server |
| `-coophost`, `-coopport`, `-name` | Koop-Server und Spielername |

## Auf einem Planeten

`L` im Flug landet auf dem nächsten festen Körper in Reichweite. Danach läuft man zu Fuß
über die Kugeloberfläche: Gravitation zeigt immer zum Planetenzentrum, das Terrain wird
als Quad-Sphere mit Quadtree-LOD bis Kachelgröße ~115 m erzeugt (25×25 Vertices je Kachel,
Skirts gegen Risse), Höhenfeld aus Plattentektonik, Gebirgsketten, Vulkanismus und Kratern.

| Taste | Wirkung |
|---|---|
| WASD / Shift / Strg | Laufen, Sprint, Ducken |
| Leertaste | Springen, gehalten Jetpack |
| Linke Maustaste | Werkzeug benutzen (Abbau oder Scan) |
| Q | Werkzeug wechseln (Abbaustrahl, Geländeformer, Scanner, Baumodus) |
| Tab | Inventar, 1–5 verbrauchen |
| X | Herstellung |
| B | Baumodus, LMB setzen, RMB abbauen |
| T | Handel am Handelsposten |
| K | Entdeckungen, U alles melden |
| E | Schiff besteigen (kostet Startbrennstoff) |

Systeme dahinter: 40 Gegenstände in sechs Kategorien, 24 Rezepte (Handwerk, Raffinerie,
Küche), Überleben mit Lebenserhaltung, Gefahrenschutz, Sauerstoff, Ausdauer und Jetpack
gegen sechs Gefahrentypen (Hitze, Kälte, Gift, Strahlung, Vakuum, Druck), 28 Bauteile in
acht Kategorien mit Statik- und Energiebilanz, Marktpreise mit Angebot, Nachfrage und
Marktimpact, Entdeckungskatalog mit Namensrecht und Meldeprämie.

## Steuerung

**Im Schiff:** W/S Schub · A/D Gieren · Q/E Rollen · Maus Nick/Gier · Shift Nachbrenner ·
Strg Bremsen · X Schub null · Leertaste Schub halten · 1–5 Waffengruppen · F1–F4 Flugmodus ·
C Scanner · `,`/`.` Scanner abstimmen · H Hyperantrieb · M Galaxiekarte · J Jon rufen ·
K Auftrag anfordern · Esc Menü

**Galaxiekarte:** Linksziehen rotieren · Mausrad zoomen · Mittlere Taste schwenken ·
Linksklick auswählen · Rechtsklick Sprung · R Route · F Filter · Leertaste zurück zur Position

## Jon

Jon fliegt als KI-Begleiter mit. Er läuft vollständig offline über ein regelbasiertes
Utility-Modell (`JonOfflineBrain`): Planetenanalyse, Gefahrenwarnungen mit Dringlichkeitsstufen,
Navigationsempfehlungen, Missionsgenerierung. Ist das Jon-Backend auf `127.0.0.1:8756`
erreichbar, ergänzt `JonBridgeClient` freie Gespräche über `/api/chat` — asynchron, 4 s Timeout,
stiller Rückfall auf das Offline-Gehirn. Jon verändert nie den Spielzustand, er schlägt vor.

## Tests

```bash
bin\STARFALL.exe -tests
```

130 Prüfungen über Mathematik, Container, Allokatoren, ECS, Rauschen, deterministische
Universumsgenerierung, Orbitalmechanik, Void-Heart-Kennzahlen, Endgame, Hyperantrieb,
Qualitätsstufen und JSON.

## Aufbau

```
src/engine/   core, memory, container, math, job, ecs, event, platform, render, ui, net
src/game/     universe, space, ship, voidheart, jon, map, screens, hud, multiplayer
tests/        TestSuite.cpp
docs/         ARCHITEKTUR.md, VOIDHEART.md, LEISTUNG.md
```

Siehe `docs/` für die Details zur Physik des Schwarzen Lochs und zur Architektur.
