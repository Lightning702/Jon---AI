# Leistung und Sparmodus

## Warum es einen Sparmodus gibt

Der teure Teil ist der Raymarch: pro Bildpunkt wird eine Nullgeodäte integriert, jeder
Runge-Kutta-4-Schritt wertet die Kerr-Metrik viermal aus. Bei 520 Schritten und voller
Auflösung sind das auf 1080p über 400 Milliarden Metrikauswertungen pro Sekunde bei
60 fps. Auf einer aktuellen Grafikkarte ist das machbar, auf Notebook-Grafik nicht.

Der Sparmodus senkt den Aufwand um mehr als das Zehnfache, ohne die Physik zu ändern.

## Was der Sparmodus tut

| Stellschraube | Ultra | Sparmodus |
|---|---|---|
| Auflösung des Raymarchs | 100 % | 28 % |
| Schritte pro Strahl | 520 | 96 |
| Metrikauswertungen pro Schritt | 4 (RK4) | 2 (Mittelpunkt) |
| Schrittbruchteil | 0,014 | 0,062 |
| Szenenauflösung | 100 % | 62 % |
| Sternschichten | 3 | 1 |
| Nebel-Oktaven | 5 + 4 + 3 | keine |
| Bloom-Stufen | 5 | 0 |
| Filmkorn, chromatische Aberration | an | aus |

Unverändert bleiben: Kerr-Metrik, ZAMO-Anfangsbedingungen, Temperaturprofil der Scheibe,
Doppler-Beaming, Gravitationsrotverschiebung, alle Kennzahlen im Anzeigefeld.

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

Die dynamische Auflösung wirkt auf Raymarch-Auflösung, Szenenauflösung, Schrittzahl und
Schrittbruchteil gleichzeitig.

## Gemessen

Intel UHD 620, 1280×720:

| Stufe | Objekt | Abstand | Bildrate |
|---|---|---|---|
| Sparmodus | The Void Heart | 42 r_g | ~68 fps |
| Hoch | M87* | 46 r_g | ~69 fps |

Die Bildrate hängt stark vom Abstand ab: je näher am Horizont, desto mehr Strahlen laufen
in die Nähe der Photonensphäre und brauchen dort die volle Schrittzahl. Bei sehr kleinen
Abständen (unter 10 r_g) fällt sie deutlich, dort greift die Automatik.

## Speicher

Der Raymarch schreibt in ein einzelnes HDR-Ziel in reduzierter Auflösung, die
Bloom-Kette belegt in Sparmodus null Ziele, in Ultra fünf Paare. Es gibt keine
Asset-Ladung: alle Texturen und Formen entstehen prozedural im Shader.
