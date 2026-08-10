# Harmonische Inseln — Vereinte Inseln

Ein ruhiges Aufbauspiel in isometrischer Schrägsicht. Vier schwebende Inseln liegen in der
Abendsonne, verbunden durch Holzbrücken.

**Worum es geht:** Auf der Werft steht ein unfertiger Leuchtturm, und er sagt dir, was ihm
fehlt — mal drei Korn von der Farm, mal Stein aus dem Berg, mal Bretter aus der Werkstatt. Die
Anzeige oben nennt immer den nächsten Auftrag. Was du bringst, zählt; das Gewünschte zählt
doppelt. Nach sechs Stufen brennt das Licht, alle Bewohner kommen an der Werft zusammen und es
wird gefeiert.

**Nebenbei:** Über dem Kopf mancher Bewohner schwebt ein Wunsch. Hast du das Passende dabei,
schenkst du es mit **F** — das gibt ein Herz. Die Herzen stehen am Ende unter dem Abspann.

**Zu zweit:** **K** öffnet die Koop-Anzeige. Einer erstellt ein Spiel und gibt den
Freundschaftscode weiter, der andere tippt ihn ein. Ihr lauft in derselben Welt, seht euch
gegenseitig, und was einer abliefert, zählt für beide.

Geschrieben in C++20 ohne Spiel-Engine und ohne Fremdbibliotheken. Fenster, OpenGL-Anbindung,
Mathematik, Netzbau, Schriftatlas und Ton liegen in `../felwerk` und werden mit BLOCKWELT geteilt.

## Bauen

```
build.bat
```

Braucht die Visual Studio Build Tools mit C++-Workload. Ergebnis: `bin\HARMONIE.exe`.
`build.bat clean` räumt vorher auf, `build.bat debug` baut ohne Optimierung.

## Spielen

Am einfachsten über Jons Spiele-Tab. Direkt geht auch `bin\HARMONIE.exe`.

| Taste | Wirkung |
| --- | --- |
| WASD | Laufen, Shift rennt |
| Leertaste | Hüpfen |
| E | Sammeln, am Leuchtturm abgeben |
| F | Schenken und grüßen |
| K | Zusammen spielen (Koop) |
| Q / R oder Pfeile links/rechts | Kamera drehen |
| Pfeile oben/unten | Kamera neigen |
| Mausrad | Näher und weiter |
| Tab | Übersicht über das ganze Archipel |
| H | Anzeige ein und aus |
| F5 / F6 | Grafikstufe |
| F11 | Vollbild |
| P | Bild nach `harmonie-bild.bmp` |
| Esc | Beenden |

Der Fortschritt landet in `saves/harmonie.txt` und wird beim nächsten Start weitergeführt.

## Startschalter

Nützlich zum Prüfen ohne Eingabe:

```
bin\HARMONIE.exe -tests
bin\HARMONIE.exe -fenster -schnell -bilder 200 -bild bild.bmp
bin\HARMONIE.exe -stufe 6 -uebersicht -ohneanzeige -grafik 2
bin\HARMONIE.exe -ort 44 -34 -saat 12
```

`-tests` läuft ohne Fenster und prüft Mathematik, Rauschen, Weltaufbau und Leuchtturmstufen.

## Aufbau

| Ordner | Inhalt |
| --- | --- |
| `src/spiel/Welt.*` | Inseln, Gelände, Brücken, Häuser, Wasser, Regenbogen, Leuchtturm |
| `src/spiel/Bewohner.*` | Figuren, ihr Tagesablauf, Tiere und Haustiere |
| `src/spiel/Partikel.*` | Blätter, Gischt, Herzen, Funkeln |
| `src/spiel/Himmel.*` | Himmel, Sonne, Wolken |
| `src/spiel/Spiel.*` | Kamera, Steuerung, Anzeige, Speicherstand |
| `tests/` | Prüfungen für `-tests` |

Das Gelände entsteht aus einer Höhenfunktion je Insel: eine weiche Randmaske, darüber je nach
Bezirk Terrassen, sanfte Hügel oder ein gestufter Berg. Dieselbe Funktion liefert dem Spiel den
Boden unter den Füßen, deshalb passen Bild und Bewegung immer zusammen. Unter jeder Insel hängt
ein Felskegel — daher schweben sie.
