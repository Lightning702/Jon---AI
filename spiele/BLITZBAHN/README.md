# BLITZBAHN

Stuntrennen von FelWorks als eigenes Windows-Programm in C++, gebaut auf der gemeinsamen
Engine `spiele/felwerk`.

## Spielen

- **Spielen**: acht Strecken (Auftakt, Doppelkehre, Sprungbrett, Hochbahn, Wellenreiter,
  Turbotal, Himmelsleiter, Grosser Preis) oder eine Zufallsstrecke.
- **Editor**: Strecken aus Geraden, Kurven, Rampen, Steilrampen, Schanzen, Turbofeldern,
  Wellen, Platten, Start, Kontrollpunkten und Ziel bauen, testen und speichern.
- **Garage**: Grundfarbe, Akzent, Felgen und Rahmen waehlen, Fahrername setzen.
- **Mehrspieler**: Rennen eroeffnen und den Code teilen, Freunde treten bei. Jon verbindet
  euch ueber seinen Mehrspieler-Dienst.

Steuerung: W Gas, S Bremse, A/D lenken, Leertaste driften, R Neustart, Q zum letzten
Kontrollpunkt, C Kamera, G Geist, Esc Pause, F11 Vollbild.

Fahrgefühl: Kurven gehen mit rund 100 km/h, an der Leitplanke rutscht das Auto entlang statt
abzuprallen. Die **Fahrhilfe** (Einstellungen, standardmäßig an) richtet das Auto sanft aus,
wenn es ohne Lenken auf die Leitplanke zufährt, und gleicht schräge Absprünge an Schanzen aus.
Wer selbst gegen die Wand lenkt oder driftet, wird nicht korrigiert.

## Bauen und Pruefen

```
build.bat
bin\BLITZBAHN.exe -tests
bin\BLITZBAHN.exe -fenster -ansicht rennen -strecke o3 -autopilot -bilder 600 -bild bild.bmp
```

`-ansicht` kennt haupt, auswahl, rennen, editor, garage, mehrspieler und einstellungen.
Spielstaende, Rekorde, Geister und eigene Strecken liegen unter `saves/`.
