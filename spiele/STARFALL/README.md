# STARFALL — Schwarzloch-Simulation

Echtzeit-Simulation eines rotierenden Schwarzen Lochs in C++20. Keine Engine, keine
Fremdbibliotheken: Mathematik, Fensterverwaltung, Renderer, Schriftdarstellung und
Testrahmen sind selbst geschrieben.

Für jeden Bildpunkt wird eine Nullgeodäte in der Kerr-Metrik integriert. Alles, was man
sieht — die Gravitationslinse, der Photonenring, die Scheibe, die durch die Lichtkrümmung
gleichzeitig über und unter dem Horizont erscheint — entsteht aus dieser Integration und
ist nicht nachgestellt.

By FelWorks.

## Bauen und starten

```bash
build.bat
```

Braucht die Visual Studio Build Tools mit C++-Workload. Ergebnis: `bin/STARFALL.exe`.
In Jon erscheint die Simulation unter *Werkzeuge → Spiele*, sobald die Exe existiert.

## Steuerung

| Taste | Wirkung |
|---|---|
| 1–6 | Objekt wählen |
| Linke Maustaste ziehen | Um das Loch drehen |
| Mausrad, W/S | Abstand ändern |
| V | Ansicht wechseln: Orbit, Freiflug, 90-Sekunden-Kamerafahrt |
| Pfeile ↑ ↓ | Regler wählen |
| Pfeile ← → | Wert ändern, mit Shift schneller |
| `,` `.` | Bildwinkel |
| C | Reglerfeld ein/aus |
| Tab | Gesamte Anzeige ein/aus |
| P | Bild als PPM speichern |
| R | Objekt zurücksetzen |
| F5 / F6 | Grafikstufe |
| F7 | Automatik ein/aus |
| F8 | Sparmodus |
| F11 | Vollbild |
| Esc | Beenden |

## Objekte

| Taste | Objekt | Masse | Spin |
|---|---|---|---|
| 1 | Sagittarius A* | 4,297 · 10⁶ M☉ | 0,90 |
| 2 | M87* | 6,5 · 10⁹ M☉ | 0,94 |
| 3 | Cygnus X-1 | 21,2 M☉ | 0,95 |
| 4 | Schwarzschild | 10⁶ M☉ | 0,00 |
| 5 | Nahezu extremal | 4,1 · 10⁶ M☉ | 0,998 |
| 6 | The Void Heart | 4,1 · 10⁶ M☉ | 0,94 |

Alle Kennzahlen werden zur Laufzeit aus Masse und Spin gerechnet, nichts ist als Konstante
hinterlegt. Sagittarius A* und M87* tragen die gemessenen Werte; Schwarzschild, Nahezu
extremal und The Void Heart sind Studienfälle.

## Regler

Masse, Spin, Akkretionsrate, Scheibentemperatur am Innenrand, Scheibenaußenrand,
Scheibendicke, Jetstärke und Beobachterabstand lassen sich während der laufenden
Simulation verstellen. Horizont, Ergosphäre, Photonensphäre und ISCO folgen sofort.

## Grafikstufen und Sparmodus

Beim Start wird die Grafikkarte erkannt. Auf Notebook-Grafik startet die Simulation im
**Sparmodus**; die Automatik senkt bei verfehlter Zielbildrate erst die Auflösung, dann
die Stufe.

| Stufe | Auflösung des Raymarchs | Schritte | Integrator | gemessen auf Intel UHD 620 |
|---|---|---|---|---|
| Sparmodus | 28 % | 96 | Mittelpunkt (RK2) | ~68 fps |
| Niedrig | 36 % | 160 | Mittelpunkt (RK2) | |
| Mittel | 50 % | 280 | Runge-Kutta 4 | |
| Hoch | 70 % | 400 | Runge-Kutta 4 | ~69 fps bei 46 r_g |
| Ultra | 100 % | 520 | Runge-Kutta 4 | |

Der Sparmodus ändert die Physik nicht — Metrik, Linse, Doppler-Beaming, Rotverschiebung
und Zeitdilatation rechnen identisch, nur gröber abgetastet.

## Kommandozeile

| Schalter | Bedeutung |
|---|---|
| `-objekt 0..5` | Objekt vorwählen |
| `-abstand 42` | Startabstand in r_g |
| `-neigung 84` | Blickwinkel auf die Scheibe in Grad |
| `-kamerafahrt` | Mit der 90-Sekunden-Fahrt starten |
| `-freiflug` | Mit freier Kamera starten |
| `-grafik spar\|niedrig\|mittel\|hoch\|ultra` | Feste Grafikstufe |
| `-sparmodus` | Kurzform |
| `-autografik 0\|1` | Automatik |
| `-zielfps 30` | Zielbildrate |
| `-ohnehud` | Ohne Anzeige |
| `-windowed`, `-width`, `-height`, `-fullscreen`, `-vsync` | Fenster |
| `-frames N` | Nach N Bildern beenden |
| `-shot datei.ppm` | Bild schreiben |
| `-tests` | Testsuite, ohne Fenster |

## Tests

```bash
bin\STARFALL.exe -tests
```

124 Prüfungen: Mathematik, Horizontgeometrie gegen die analytischen Kerr-Formeln,
Zeitdilatation, Massenskalierung, Scheibenprofil, Beobachterkennzahlen, Voreinstellungen
und Grafikstufen.

## Aufbau

```
src/engine/core       Typen, Log, Result, Zeit, Kommandozeile
src/engine/math       Vec2/3/4, DVec3, Mat3/4, Quat, Skalarhilfen
src/engine/platform   Win32-Fenster mit OpenGL-Kontext, Eingabe, Dateisystem
src/engine/render     GL-Loader, Shader, Rendertarget, Kamera, Qualitätsstufen,
                      Sternenhintergrund, Kerr-Raymarcher, Postprocessing
src/engine/ui         Oberfläche mit eigenem Bitmap-Font
src/sim               Physikmodell, Beobachtersteuerung, Anwendung
tests                 Testsuite
docs                  PHYSIK.md, LEISTUNG.md
```

Die Physik im Detail steht in [docs/PHYSIK.md](docs/PHYSIK.md).
