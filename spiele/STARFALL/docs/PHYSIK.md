# Physik der Simulation

Alle Längen in Vielfachen des Gravitationsradius `r_g = GM/c²`. Alle Kennzahlen werden zur
Laufzeit aus Masse und Spin gerechnet, nichts ist als Konstante hinterlegt. Die Testsuite
prüft sie gegen die analytischen Formeln.

## Charakteristische Radien

Für die Kerr-Metrik mit dimensionslosem Spin `a`:

```
Horizont              r₊ = 1 + √(1 − a²)
Ergosphäre            r_E(θ) = 1 + √(1 − a² cos²θ)
Photonensphäre        r_ph = 2 (1 + cos[ (2/3) arccos(−a) ])
ISCO                  r_isco = 3 + Z₂ − √[(3 − Z₁)(3 + Z₁ + 2Z₂)]
   mit                Z₁ = 1 + (1 − a²)^{1/3} [ (1+a)^{1/3} + (1−a)^{1/3} ]
                      Z₂ = √(3a² + Z₁²)
Schattenradius        r_shadow = √27 ≈ 5,196 (Schwarzschild)
```

Für `a = 0` ergibt das r₊ = 2, r_ph = 3, r_isco = 6 — die Schwarzschild-Werte. Der Spin
wird auf 0,998 begrenzt: das ist die Thorne-Grenze, oberhalb derer die Akkretion selbst
den Drehimpuls nicht weiter steigern kann.

## Geodäten-Integration

Der Raymarcher löst pro Bildpunkt die Nullgeodäte in Boyer-Lindquist-Koordinaten.
Zustandsvektor `(r, θ, φ, p_r, p_θ)`; `E` und `L_z` sind Erhaltungsgrößen.

Mit
```
Σ = r² + a² cos²θ
Δ = r² − 2r + a²
P = (r² + a²) E − a L
K = (L/sinθ − a E sinθ)²
```
und der Hamiltonfunktion in Mino-Zeit
```
H = ½ [ Δ p_r² + p_θ² − P²/Δ + K ]
```
folgen
```
dr/dλ   = Δ p_r
dθ/dλ   = p_θ
dφ/dλ   = a P/Δ + L/sin²θ − a E
dp_r/dλ = −½ [ Δ′(r) p_r² − d/dr(P²/Δ) ]
dp_θ/dλ = −(L/sinθ − a E sinθ) · d/dθ(L/sinθ − a E sinθ)
```

Integriert wird mit Runge-Kutta 4, im Sparmodus mit dem Mittelpunktverfahren. Die
Schrittweite ist adaptiv: pro Schritt wird ein fester Bruchteil des aktuellen Radius
zurückgelegt, zusätzlich begrenzt durch die Winkeländerung in θ und φ. Abbruch bei
`r ≤ r₊ · 1,0009` (Einfall) oder `r > 4200 r_g` (Flucht).

## Anfangsbedingungen

Der Strahl startet im Ruhesystem eines lokal nicht rotierenden Beobachters (ZAMO). Mit
`A = (r²+a²)² − a² Δ sin²θ`, `ω = 2ar/A`, `α = √(ΣΔ/A)` und der lokalen Richtung `n` des
**einlaufenden** Photons:

```
p_r = n_r √(Σ/Δ)
p_θ = n_θ √Σ
L   = n_φ sinθ √(A/Σ)
E   = α + ω L
```

Die lokale Energie ist damit auf 1 normiert. Integriert wird rückwärts im affinen
Parameter, sodass der Marsch entlang der Blickrichtung läuft und `E` und `L` die des real
ankommenden Photons sind. Der ZAMO ist bis zum Horizont wohldefiniert — der Renderer
funktioniert deshalb auch innerhalb der Ergosphäre.

## Akkretionsscheibe

Geometrisch dünn, optisch dick, von r_isco bis zum einstellbaren Außenrand. Der Schnitt
mit der Äquatorebene wird zwischen zwei Integrationsschritten über den Vorzeichenwechsel
von cos θ linear interpoliert.

Das Strahlungsprofil folgt dem relativistischen Fluss nach Page und Thorne (1974), nicht
der newtonschen Näherung. Mit `x = √r`, `x₀ = √r_isco` und den Wurzeln von `x³ − 3x + 2a = 0`

```
x₁ = 2 cos( (1/3) arccos(a) − π/3 )
x₂ = 2 cos( (1/3) arccos(a) + π/3 )
x₃ = −2 cos( (1/3) arccos(a) )
```

gilt

```
F(r) ∝ 1 / ( x⁷ (x³ − 3x + 2a) ) ·
       [ x − x₀ − (3a/2) ln(x/x₀)
         − 3(x₁−a)² / (x₁(x₁−x₂)(x₁−x₃)) · ln((x−x₁)/(x₀−x₁))
         − 3(x₂−a)² / (x₂(x₂−x₁)(x₂−x₃)) · ln((x−x₂)/(x₀−x₂))
         − 3(x₃−a)² / (x₃(x₃−x₁)(x₃−x₂)) · ln((x−x₃)/(x₀−x₃)) ]
```

und `T(r) ∝ F(r)^{1/4}`. Der Fluss verschwindet exakt an der ISCO und fällt weit außen mit
`r⁻³`, die Temperatur damit mit `r^{−3/4}`.

Für Schwarzschild (a = 0, r_isco = 6) liegt das Maximum bei **8,39 r_g** — etwas weiter
außen als die newtonsche Näherung mit `(49/36) r_in = 8,17 r_g`. Genau diese relativistische
Verschiebung prüft die Testsuite. Mit Spin wandert die ganze Scheibe nach innen und wird
heißer, weil die ISCO näher an den Horizont rückt.

Für eine prograde Kreisbahn in der Äquatorebene gilt
```
u^t = (r^{3/2} + a) / √(r³ − 3r² + 2a r^{3/2})
u^φ = 1 / √(r³ − 3r² + 2a r^{3/2})
```
und damit der Verschiebungsfaktor
```
g = 1 / (E u^t − L u^φ)
```
Er enthält Doppler-Effekt und Gravitationsrotverschiebung in einem Term. Beobachtet wird
`T_obs = g · T(r)`, die Helligkeit skaliert mit `g⁴` (relativistisches Beaming). Daraus
folgt ohne Zusatzregel, dass die auf den Betrachter zulaufende Scheibenseite heller und
blauer erscheint als die abgewandte.

Die Farbe entsteht aus der Planckschen Kurve: Temperatur → Planckscher Ort in CIE-xy →
XYZ → lineares sRGB. Der Reglerwert „Scheibentemperatur" verankert die Skala am Radius
`(49/36) r_in`; Profilform, Verschiebung und Beaming bleiben davon unberührt.

**Randverdunklung.** Die Emission ist nicht isotrop. Für eine streuungsdominierte
Scheibenatmosphäre gilt Chandrasekhars Gesetz

```
I(μ) ∝ (1 + 2,06 μ) / 3,06
```

mit μ als Kosinus des Abstrahlwinkels zur Scheibennormalen. Flach gesehene Bereiche
erscheinen dadurch dunkler als senkrecht gesehene — bei steiler Blickrichtung auf die
Scheibe ein sichtbarer Unterschied.

**Endliche Dicke.** Die Scheibe hat eine Skalenhöhe `h = d · r`. Die optische Tiefe entlang
des Strahls folgt der tatsächlichen Weglänge durch die Schicht, `L = h / |cos θ_Strahl|`.
Bei streifendem Einfall wird die Schicht dadurch länger durchlaufen und die Scheibe
erscheint dicker; am Innenrand kommt eine Kantenaufhellung dazu.

**Scherung.** Reale Scheiben rotieren differentiell: innen schneller als außen. Das
Turbulenzmuster wird entsprechend in Umfangsrichtung geschert abgetastet, sodass Strukturen
zu Spiralfäden ausgezogen werden statt rund zu bleiben.

## Beobachterkennzahlen

```
Zeitdilatation        dτ/dt = √(1 − r_s/r) = √(1 − 2/r)   [in r_g]
Kreisbahngeschwindigkeit  v/c = 1/√r
Fluchtgeschwindigkeit     v/c = √(2/r)
Umlaufzeit            T = 2π (r^{3/2} + a) · r_g/c
Gezeitenbeschleunigung   Δa = 2GM/r³ je Meter Ausdehnung
Eigenbeschleunigung zum Schweben   a = GM/r² / √(1 − 2/r)
```

## Hawking-Strahlung

```
T_H = ħc³ / (8π G M k_B)
t_evap = 5120 π G² M³ / (ħ c⁴)
```

Für M87* mit 6,5 Milliarden Sonnenmassen ergibt das 9,49 · 10⁻¹⁸ K und eine
Verdampfungszeit von 5,76 · 10⁹⁶ Jahren — beides weit außerhalb jeder Messbarkeit, aber
korrekt aus denselben Formeln gerechnet wie alles andere.

## Weitere Effekte

- **Gravitationslinse und Einstein-Ring** entstehen automatisch aus der Integration;
  Sterne und Nebel hinter dem Loch werden korrekt verzerrt.
- **Photonenring** ergibt sich aus Strahlen nahe der instabilen Photonenbahn.
- **Scheibe über und unter dem Horizont** gleichzeitig sichtbar, weil Strahlen, die
  oberhalb vorbeilaufen, die Ebene hinter dem Loch von unten schneiden.
- **Hintergrundverschiebung**: einfallendes Sternlicht wird mit `1/E` blauverschoben, die
  Helligkeit mit der vierten Potenz skaliert.
- **Relativistische Jets** entlang der Spinachse, volumetrisch entlang des Strahlwegs
  akkumuliert, mit Schockknoten aus einer logarithmischen Phasenfunktion.

## Zeitliche Akkumulation

Der Raymarch läuft beim Bewegen in reduzierter Auflösung, damit die Kamera reagiert. Sobald
0,3 Sekunden lang nichts mehr verändert wird — Kamera, Regler, Grafikstufe —, friert die
Simulationszeit ein und das Bild wird in **voller Auflösung** aufgebaut: jedes Bild wird mit
einem Subpixel-Versatz aus einer Halton-Folge (Basen 2 und 3) abgetastet und als laufender
Mittelwert dazugerechnet.

```
Akkumulation ← (1/(n+1)) · aktuelles Bild + (n/(n+1)) · Akkumulation
```

Nach 192 Bildern (96 im Sparmodus) ist das Ergebnis konvergiert. Das ist der Unterschied
zwischen einem weichen Photonenring und einem gestochen scharfen: bei 28 % Auflösung ist der
Ring nur wenige Pixel breit, akkumuliert steht er sauber im Bild. Jede Änderung setzt den
Zähler zurück und die Animation läuft weiter.

## Was nicht simuliert wird

Ehrlichkeitshalber: die Scheibe ist ein stationäres Emissionsmodell, keine
Magnetohydrodynamik. Es gibt keine Strahlungstransportrechnung durch optisch dünnes
Plasma, keine Selbstgravitation der Scheibe, keine zeitliche Entwicklung der Akkretion und
keine Rückkopplung der Jets auf die Umgebung. Die Lichtausbreitung dagegen ist voll
allgemeinrelativistisch.
