# THE VOID HEART — Physik und Rendering

## Kennzahlen

| Größe | Wert |
|---|---|
| Masse | 4,1 · 10⁶ Sonnenmassen |
| Gravitationsradius r_g = GM/c² | 6,055 · 10⁹ m |
| Schwarzschild-Radius r_s = 2 r_g | 1,211 · 10¹⁰ m ≈ 12,1 Mio. km |
| Kerr-Parameter a | 0,94 |
| Ereignishorizont r₊ = M + √(M² − a²) | 1,341 r_g |
| Ergosphäre (Äquator) | 2,0 r_g |
| Photonensphäre (prograd) | 1,56 r_g |
| ISCO (prograd) | 1,92 r_g |

Alle Werte werden zur Laufzeit aus Masse und Spin berechnet, nicht als Konstanten hinterlegt.
Die Testsuite prüft sie gegen die analytischen Formeln.

## Geodäten-Integration

Der `BlackHolePass` löst pro Pixel die Nullgeodäte in der Kerr-Metrik in
Boyer-Lindquist-Koordinaten. Zustandsvektor: `(r, θ, φ, p_r, p_θ)`; `E` und `L_z` sind
Erhaltungsgrößen.

Mit
```
Σ = r² + a² cos²θ
Δ = r² − 2r + a²
P = (r² + a²) E − a L
K = (L/sinθ − a E sinθ)²
```
und der Mino-Zeit-Hamiltonfunktion
```
H = ½ [ Δ p_r² + p_θ² − P²/Δ + K ]
```
ergeben sich
```
dr/dλ  = Δ p_r
dθ/dλ  = p_θ
dφ/dλ  = a P/Δ + L/sin²θ − a E
dp_r/dλ = −½ [ Δ'(r) p_r² − d/dr(P²/Δ) ]
dp_θ/dλ = −(L/sinθ − a E sinθ) · d/dθ(L/sinθ − a E sinθ)
```

Integriert wird mit Runge-Kutta 4 (Sparmodus: Mittelpunktverfahren) und adaptiver
Schrittweite: pro Schritt wird ein fester Bruchteil des aktuellen Radius zurückgelegt,
zusätzlich begrenzt durch die Winkeländerung in θ und φ. Abbruch bei
`r ≤ r₊ · 1,0009` (Einfall) oder `r > 4200 r_g` (Flucht).

## Anfangsbedingungen

Der Strahl wird aus dem Ruhesystem eines lokal nicht rotierenden Beobachters (ZAMO) gestartet.
Mit `A = (r²+a²)² − a² Δ sin²θ`, `ω = 2ar/A`, `α = √(ΣΔ/A)` und der lokalen Richtung
`n = (n_r, n_θ, n_φ)` des **einlaufenden** Photons gilt:

```
p_r = n_r √(Σ/Δ)
p_θ = n_θ √Σ
L   = n_φ sinθ √(A/Σ)
E   = α + ω L
```

Die lokale Energie ist damit auf 1 normiert. Integriert wird rückwärts im affinen Parameter,
sodass der Marsch entlang der Blickrichtung läuft und `E` und `L` die des real ankommenden
Photons sind. Der ZAMO ist bis zum Horizont wohldefiniert, deshalb funktioniert der Renderer
auch innerhalb der Ergosphäre.

## Akkretionsscheibe

Geometrisch dünn, optisch dick, von r_ISCO bis 26 r_g. Der Schnittpunkt mit der Äquatorebene
wird zwischen zwei Schritten über den Vorzeichenwechsel von cos θ linear interpoliert.

Temperaturprofil nach Shakura-Sunyaev/Novikov-Thorne:
```
T(r) = T_innen · (r_in/r)^(3/4) · (1 − √(r_in/r))^(1/4)
```

Für eine prograde Kreisbahn in der Kerr-Äquatorebene gilt
```
u^t = (r^{3/2} + a) / √(r³ − 3r² + 2a r^{3/2})
u^φ = 1 / √(r³ − 3r² + 2a r^{3/2})
```
und damit der Verschiebungsfaktor
```
g = 1 / (E u^t − L u^φ)
```
Er enthält Doppler-Effekt und Gravitationsrotverschiebung in einem Term. Beobachtet wird
`T_obs = g · T(r)`, die Helligkeit skaliert mit `g⁴` (relativistisches Beaming). Daraus folgt
ohne Zusatzregel, dass die auf den Betrachter zulaufende Scheibenseite heller und blauer
erscheint als die abgewandte.

Die Farbe entsteht aus der Planckschen Kurve: Temperatur → Planckscher Ort in CIE-xy →
XYZ → lineares sRGB. `T_innen` ist ein Gestaltungsparameter (Standard 9800 K), damit die
Scheibe im Bild den geforderten rot-orangen Charakter behält; Profilform, Verschiebung und
Beaming bleiben physikalisch.

## Weitere Effekte

- **Gravitationslinse und Einstein-Ring** entstehen automatisch aus der Integration; Sterne,
  Nebel und die Scheibe hinter dem Horizont werden korrekt verzerrt.
- **Photonenring** ergibt sich aus Strahlen nahe der instabilen Photonenbahn.
- **Scheibe über und unter dem Horizont** gleichzeitig sichtbar, weil Strahlen, die oberhalb
  vorbeilaufen, die Ebene hinter dem Loch von unten schneiden.
- **Hintergrundverschiebung**: einfallendes Sternlicht wird mit `1/E` blauverschoben und in
  der Helligkeit mit der vierten Potenz skaliert.
- **Relativistische Jets** entlang der Spinachse, volumetrisch entlang des Strahlwegs
  akkumuliert, mit Schockknoten aus einer logarithmischen Phasenfunktion.

## Zeitdilatation im Spiel

`TimeDilationZone` liefert nach Vorgabe
```
dt_lokal / dt_fern = √(1 − r_s/r)
```
Die Weltzeit (`universeSeconds`) läuft autoritativ weiter, die persönliche Zeit
(`personalSeconds`) wird mit dem Faktor skaliert. Forschung und Fortschritt des Spielers
hängen an der persönlichen Zeit, Bahnbewegungen und Produktion an der Weltzeit. Im Koop
wird der eigene Faktor mit jedem Zustandspaket übertragen.

## Zonen

| Zone | Grenze | Wirkung |
|---|---|---|
| 5 Fernfeld | > 600 r_g | nur visuell |
| 4 Gravitationsdrift | ≤ 600 r_g | Bahnzug, Treibstoff ×1,35 |
| 3 Verzerrungszone | ≤ 90 r_g | Instrumentenrauschen 0,42, Ladezeit ×2,4 |
| 2 Ergosphäre | ≤ 2 r_g | Zeitdilatation, Frame-Dragging, Schildverlust 4,5/s, Void-Antrieb nötig |
| 1 Horizontnähe | ≤ 1,35 r₊ | Gezeitenkräfte am Rumpf, Schildverlust 12/s |
| 0 Ereignishorizont | ≤ r₊ | keine Rückkehr, narrativer Übergang |
