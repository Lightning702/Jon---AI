# Leistung und Sparmodus

## Warum es einen Sparmodus gibt

Der teuerste Teil von STARFALL ist der Void-Heart-Pass: pro Pixel wird eine Nullgeodäte
integriert, jeder Runge-Kutta-4-Schritt wertet die Kerr-Metrik viermal aus. Bei 520 Schritten
und voller Auflösung sind das auf 1080p über 400 Milliarden Metrikauswertungen pro Sekunde
bei 60 fps. Auf einer RTX 3060 ist das machbar, auf Notebook-Grafik nicht.

Der Sparmodus senkt den Aufwand um das Vierzehnfache, ohne die Physik zu verändern.

## Was der Sparmodus tut

| Stellschraube | Ultra | Sparmodus | Faktor |
|---|---|---|---|
| Void-Heart-Auflösung | 100 % | 28 % | 12,8× weniger Pixel |
| Schritte pro Strahl | 520 | 96 | 5,4× |
| Metrikauswertungen pro Schritt | 4 (RK4) | 2 (Mittelpunkt) | 2× |
| Schrittbruchteil | 0,014 | 0,062 | gröber |
| Szenenauflösung | 100 % | 62 % | 2,6× weniger Pixel |
| Sternschichten | 3 | 1 | |
| Nebel-Oktaven | 5 + 4 + 3 | keine | |
| Bloom-Stufen | 5 | 0 | |
| Atmosphärenschalen | an | aus | |
| Ringe | an | aus | |
| Kugelunterteilung | 6 (81920 Dreiecke) | 2 (320 Dreiecke) | 256× |
| Jets | an | aus | |
| Sichtbare Körper | 128 | 12 | |
| Kartensterne | 1400 | 180 | |

Unverändert bleiben: Kerr-Metrik, ZAMO-Anfangsbedingungen, Temperaturprofil der Scheibe,
Doppler-Beaming, Gravitationsrotverschiebung, Zeitdilatation, Zonenmechanik, gesamte
Simulation mit 60 Hz Fixschritt.

## Automatische Erkennung

`AdaptiveQualityController::detectStartingPreset` liest die OpenGL-Renderer- und
Herstellerkennung:

| Erkennung | Startstufe |
|---|---|
| llvmpipe, SwiftShader, GDI Generic | Sparmodus |
| Intel UHD/HD/Iris, AMD Vega 8, Radeon Graphics, Hersteller Intel | Sparmodus |
| GTX 10xx/16xx, MX, RX 5xxx | Niedrig |
| RTX 40xx/50xx, RX 7xxx/9xxx | Hoch |
| alles andere | Mittel |

## Automatische Anpassung im Betrieb

Die Bildzeit wird exponentiell geglättet (Faktor 0,9). Regeln:

- Liegt die geglättete Bildzeit **1,2 s lang** über dem 1,35-fachen Ziel, wird zuerst die
  dynamische Auflösung um 16 Prozentpunkte gesenkt. Ist sie schon bei 36 % angekommen,
  fällt die Stufe eine Position.
- Liegt sie **4 s lang** unter dem 0,72-fachen Ziel, steigt die Auflösung um 10 Punkte
  zurück, bis der Vorgabewert der Stufe erreicht ist.
- Die Stufe steigt nie automatisch. Wer hochstufen will, drückt F6.

Die dynamische Auflösung wirkt auf Void-Heart-Auflösung, Szenenauflösung, Schrittzahl und
Schrittbruchteil gleichzeitig. Jede Änderung wird 1,5 s lang im HUD eingeblendet und
protokolliert.

## Gemessen

Intel UHD 620, 1280×720, Menüszene bei T+68 s (Nahumkreisung, teuerster Moment):

| Stufe | 60 Bilder | Bildrate |
|---|---|---|
| Sparmodus | 3,4 s | ~43 fps |
| Niedrig | 4,0 s | ~30 fps |
| Mittel | 7,1 s | ~12 fps |
| Hoch | 10,9 s | ~7 fps |
| Ultra | 21,3 s | ~3 fps |

Im normalen Flug ohne das Schwarze Loch im Bild liegt der Sparmodus auf derselben Hardware
über 60 fps.

## Terrain auf der Oberfläche

Der zweite teure Pfad ist die Kachelerzeugung. Jede Kachel wertet ein 27×27-Randgitter aus,
jeder Punkt kostet in voller Detailstufe rund 16 Simplex- und 162 Worley-Zellauswertungen.

Drei Maßnahmen:

1. **Normalen aus dem Gitter.** Vorher wurden je Vertex vier zusätzliche volle
   Höhenfeldauswertungen für die Normale gemacht. Jetzt entstehen die Normalen aus
   Differenzen der bereits berechneten Nachbarhöhen im Randgitter. Faktor 5 auf den
   Höhenfeldanteil.
2. **Detailstufe nach Kachelgröße.** `PlanetGenerator::detailLevelForChunkSize` schaltet
   Oktaven und Feature-Schichten nach Weltgröße der Kachel:

   | Kachelgröße | Kontinent-Oktaven | Gebirge | Vulkanismus | Krater |
   |---|---|---|---|---|
   | > 260 km | 3, ohne Domain-Warp | aus | aus | aus |
   | > 26 km | 4 | 4 Oktaven | aus | aus |
   | > 2,6 km | 6 | 7 Oktaven | an | 2 Schichten |
   | sonst | 6 | 7 Oktaven | an | 4 Schichten |

   Kollisionsabfragen (`elevationAt`) laufen immer in voller Detailstufe, damit der Spieler
   nicht einsinkt oder schwebt. In Spielernähe ist die Kachel ohnehin auf der feinsten
   Stufe, dort stimmen Mesh und Kollision exakt überein.
3. **Parallelisierung.** Rand- und Vertexgitter laufen über `parallelFor` auf dem
   Work-Stealing-Scheduler. Die Punkte sind voneinander unabhängig, das Ergebnis bleibt
   bitidentisch.

Gemessen auf Intel UHD 620, 1280×720, gelandet:

| | vorher | nachher |
|---|---|---|
| Bildrate auf der Oberfläche | ~14 fps | ~42 fps |
| Vorladen beim Landen | 3,4 s | 1,5 s |
| 450 Bilder gesamt | — | 11,9 s |

Damit ist das 60-fps-Ziel auf dieser Notebook-Grafik weiter nicht erreicht, aber die
Oberfläche ist spielbar. Der nächste Schritt wäre asynchrone Kachelerzeugung: die Kachel
im Hintergrundjob bauen und erst beim Fertigwerden hochladen, statt den Frame zu blockieren.

## Speicher

`MemoryTracker` führt Budgets je Kategorie und meldet Überschreitungen beim Beenden.
Der Frame-Allokator arbeitet mit drei Ringen zu 32 MB. Die Bloom-Kette belegt in
Sparmodus null Ziele, in Ultra fünf Paare.
