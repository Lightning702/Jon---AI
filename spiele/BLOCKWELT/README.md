# Blockwelt — endlose Welt, bauen mit Mini Jon

Die Voxel-Sandbox aus Jon, als eigenes Programm statt als Browserseite. Sie startet aus Jons
Spiele-Tab wie ECHO, AETHERIA, STARFALL und die Harmonischen Inseln.

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
| 1 – 9, Mausrad | Block in der Hand (16 Sorten) |
| Linksklick auf TNT | Zündet die Lunte |
| Rechtsklick mit Enderperle | Wirft sie; wo sie landet, stehst du |
| T | Mini Jon beauftragen (Haus, Turm, Brücke, Baum, Leuchtfeuer) |
| K | Zusammen spielen (Koop) |
| F | Flugmodus |
| F5 / F6 | Sichtweite in Feldern |
| H | Anzeige ein und aus |
| F11 | Vollbild |
| P | Bild nach `blockwelt-bild.bmp` |
| Esc | Maus freigeben, nochmal beendet |

## Die endlose Welt

Es gibt keinen Rand. Die Welt ist in Felder von 16 × 16 Blöcken geteilt, 100 Blöcke hoch. Beim
Laufen werden die Felder im Umkreis erzeugt und vernetzt, weiter entfernte wieder freigegeben —
im Speicher liegen immer nur ein paar hundert Felder, egal wie weit du gehst.

Die Landschaft entsteht aus Perlin-Rauschen: eine grobe Lage formt Täler und Höhenzüge, eine
feine die Hügel, eine dritte hebt Gebirge heraus. Daraus ergeben sich Ebene, Wald, Wüste mit
Kakteen, Schneeland und Gebirge; unter Höhe 32 steht Wasser, am Ufer liegt Sand. Alles hängt nur
an der Saat und der Position, deshalb sieht dieselbe Stelle nach dem Neuladen wieder gleich aus.

Gespeichert wird in `saves/blockwelt.txt` nur, was du geändert hast — die Datei bleibt klein,
auch wenn du weit gelaufen bist.

## Texturen

Die 20 Kacheln des Atlas werden beim Start Bildpunkt für Bildpunkt gemalt: Grasnarbe über Erde,
Jahresringe im Stamm, Fugen im Ziegel, Rillen im Sandstein, die weiße Binde am TNT. Nichts davon
liegt als Bilddatei bei.

## Zu zweit

**K** öffnet die Koop-Anzeige. Einer erstellt ein Spiel und gibt den sechsstelligen
Freundschaftscode weiter, der andere tippt ihn ein und drückt Enter. Der Gast bekommt die Welt
des Gastgebers (gleiche Saat), ihr seht euch gegenseitig laufen, und jeder gesetzte oder
abgebaute Block erscheint auch beim anderen. Jon muss dafür laufen — er ist der Server.

## Mini Jon

Mini Jon schwebt neben dir her. Auf T öffnet sich sein Baumenü; nach der Wahl sucht er sich vor
dir einen Platz, fliegt hin und setzt die Blöcke einzeln — man kann ihm beim Bauen zusehen.

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
| `src/spiel/Bloecke.hpp` | 16 Blocksorten mit ihren Kacheln je Seite |
| `src/spiel/Atlas.*` | Der zur Laufzeit gemalte Texturatlas |
| `src/spiel/Welt.*` | Felder, Landschaft, Nachladen, Netzbau, Strahl, Speichern |
| `src/spiel/Figuren.*` | Spielerbewegung und Mini Jon mit seinen Bauplänen |
| `src/spiel/Himmel.*` | Himmel, Sonne, Sterne, Wolken |
| `src/spiel/Spiel.*` | Schleife, Anzeige, Steuerung, TNT und Enderperle |
| `tests/` | Prüfungen für `-tests` |

Sichtbar sind nur Flächen, hinter denen kein fester Block steht; an jeder Ecke wird gezählt, wie
viele Nachbarn sie verdecken — daraus entsteht die weiche Verschattung in den Kanten. Wird ein
Block gesetzt oder abgebaut, werden nur die betroffenen Felder neu gebaut.
