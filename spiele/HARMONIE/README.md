# Harmonische Inseln — Vereinte Inseln

Ein ruhiges Aufbauspiel in isometrischer Schrägsicht. Vier schwebende Inseln liegen in der
Abendsonne, verbunden durch Holzbrücken. Auf der Werft steht ein unfertiger Leuchtturm — jede
Gabe, die du oder die Bewohner dorthin bringen, lässt ihn ein Stück wachsen. Nach sechs Stufen
brennt sein Licht, und die Inseln sind vereint.

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
| F | Bewohner grüßen |
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
