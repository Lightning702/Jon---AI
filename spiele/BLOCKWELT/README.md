# Blockwelt — bauen mit Mini Jon

Die Voxel-Sandbox aus Jon, jetzt als eigenes Programm statt als Browserseite. Sie startet aus
Jons Spiele-Tab wie ECHO, AETHERIA, STARFALL und die Harmonischen Inseln.

Geschrieben in C++20 ohne Spiel-Engine. Fenster, OpenGL-Anbindung, Mathematik, Netzbau,
Schriftatlas und Ton liegen in `../felwerk` und werden mit HARMONIE geteilt.

## Bauen

```
build.bat
```

Braucht die Visual Studio Build Tools mit C++-Workload. Ergebnis: `bin\BLOCKWELT.exe`.

## Spielen

| Taste | Wirkung |
| --- | --- |
| Maus | Umsehen, Linksklick abbauen, Rechtsklick setzen |
| WASD | Laufen, Shift rennt |
| Leertaste | Springen, im Flugmodus steigen |
| Strg | Im Flugmodus sinken |
| 1 – 9 | Block in der Hand, Mausrad blättert |
| T | Mini Jon beauftragen (Haus, Turm, Brücke, Baum, Leuchtfeuer) |
| F | Flugmodus |
| H | Anzeige ein und aus |
| F5 / F6 | Sichtweite |
| F11 | Vollbild |
| P | Bild nach `blockwelt-bild.bmp` |
| Esc | Maus freigeben, nochmal beendet |

Die Welt liegt in `saves/blockwelt.txt`. Gespeichert werden nur deine Änderungen gegenüber der
erzeugten Welt, deshalb bleibt die Datei klein.

## Mini Jon

Mini Jon schwebt neben dir her. Auf T öffnet sich sein Baumenü; nach der Wahl sucht er sich
vor dir einen freien Platz, fliegt hin und setzt die Blöcke einzeln — man kann ihm beim Bauen
zusehen. Er sagt Bescheid, wenn er fertig ist.

## Startschalter

```
bin\BLOCKWELT.exe -tests
bin\BLOCKWELT.exe -fenster -neu -saat 11
bin\BLOCKWELT.exe -schnell -ohneanzeige -bilder 400 -bild bild.bmp
bin\BLOCKWELT.exe -zeit 0.75 -baue 1 -blick 0.6 -0.1 -grafik 2
```

`-neu` ignoriert den Speicherstand, `-zeit` setzt die Tageszeit (0 Mitternacht, 0.25 Mittag),
`-baue 0..4` gibt Mini Jon sofort einen Auftrag, `-tests` läuft ohne Fenster.

## Aufbau

| Datei | Inhalt |
| --- | --- |
| `src/spiel/Bloecke.hpp` | Blockarten mit Farben je Seite |
| `src/spiel/Welt.*` | Weltdaten, Landschaft, Höhlen, Bäume, Netzbau, Strahl, Speichern |
| `src/spiel/Figuren.*` | Spielerbewegung und Mini Jon mit seinen Bauplänen |
| `src/spiel/Himmel.*` | Himmel, Sonne, Sterne, Wolken |
| `src/spiel/Spiel.*` | Schleife, Anzeige, Steuerung |
| `tests/` | Prüfungen für `-tests` |

Jedes Feld aus 16 mal 16 Blöcken bekommt ein eigenes Netz. Sichtbar sind nur Flächen, hinter
denen kein fester Block steht; an jeder Ecke wird gezählt, wie viele Nachbarn sie verdecken —
daraus entsteht die weiche Verschattung in den Kanten. Wird ein Block gesetzt oder abgebaut,
werden nur die betroffenen Felder neu gebaut.
