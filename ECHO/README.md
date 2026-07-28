# ECHO

**by FelWorks**

Ein First-Person-Psychological-Horror-Spiel in einem verlassenen Krankenhaus.
Komplett in C++ geschrieben, ohne Engine, ohne externe Bibliotheken.

---

## Starten

Doppelklick auf **`ECHO.bat`**

Beim ersten Start wird das Spiel automatisch kompiliert (dauert ca. 1 Minute).

Alternativ:

```
build.bat          Kompiliert das Spiel
build.bat clean    Kompiliert komplett neu
build.bat debug    Debug-Build
bin\ECHO.exe       Startet direkt
```

### Startparameter

| Parameter | Wirkung |
|---|---|
| `-windowed` | Fenstermodus statt Vollbild |
| `-console` | Konsole mit Log sichtbar lassen |
| `-preset 0..3` | Grafik erzwingen (0 niedrig, 3 ultra) |

---

## Steuerung

| Taste | Aktion |
|---|---|
| W A S D | Bewegen |
| Maus | Umsehen |
| Shift | Sprinten |
| Strg | Ducken |
| Leertaste | Springen |
| E / Linksklick | Interagieren |
| Rechtsklick | Fokussieren (langsamer, ruhiger) |
| **F** | Taschenlampe an/aus |
| R | Batterie wechseln |
| Tab | Tagebuch (Inventar, Dokumente, Aufnahmen) |
| Esc | Pause |
| F5 / F9 | Schnell speichern / laden |
| F11 | Vollbild umschalten |

---

## Technik

Keine Engine, keine externen Abhängigkeiten. Alles selbst geschrieben:

- **Plattform** – eigener Win32/WGL-Layer, eigener OpenGL-Loader, Raw-Mouse-Input
- **Mathematik** – eigene Vektor-/Matrix-/Frustum-Bibliothek
- **Renderer** – Deferred PBR (Cook-Torrance GGX), HDR, Shadow-Atlas,
  SSAO, SSR, Volumetric Fog mit Schattenwurf, Bloom, ACES-Tonemapping,
  Color Grading, FXAA, Film Grain, chromatische Aberration
- **Assets** – 34 PBR-Materialien, 47 Props, Schriftart, Charaktere
  und 40 Sounds werden zur Laufzeit prozedural erzeugt. Keine Asset-Dateien.
- **Physik** – eigene Kollision (Capsule-Sweep gegen AABB/OBB),
  Uniform-Grid-Broadphase, Stufen-Erkennung
- **Audio** – eigener WASAPI-Backend, 64-Stimmen-3D-Mixer,
  Schroeder-Reverb, Distanz-Lowpass, prozedurale Klangsynthese
- **Welt** – 4 Etagen, ~470 Räume, ~400 Türen, ~1500 Lampen, ~5600 Objekte,
  vollständig prozedural generiert, Portal-Culling über den Raumgraphen

### Projektstruktur

```
src/core/        Mathematik, Logging, Dateisystem, Threading
src/platform/    Fenster, OpenGL-Loader, Eingabe
src/render/      Renderer, Shader, Meshes, Texturen, Materialien
src/physics/     Kollision, Physikwelt
src/world/       Krankenhausgenerierung, Props, Charaktere
src/audio/       WASAPI-Gerät, Synthese, 3D-Mixer
src/ai/          Verhaltensanalyse, Regie, Mutationen, Schreckmomente
src/ui/          Schrift, 2D-Renderer, HUD, Menüs
src/game/        Spieler, Taschenlampe, Story, Spielschleife
src/save/        Speicherstände
shaders/         GLSL
```

---

## Horror-Design

Der Horror ist psychologisch. Das Gebäude ist die eigentliche Figur.

**Adaptive Regie** – das Spiel misst laufend das Verhalten des Spielers
und reagiert darauf:

| Verhalten | Reaktion |
|---|---|
| viel Sprinten | Türen schließen sich hinter dem Spieler, Wege werden länger |
| häufiges Stehenbleiben | Geräusche werden lauter und näher |
| häufiges Umdrehen | Möbel stehen anders, wenn man wegsieht |
| immer dieselben Räume | genau diese Räume verändern sich |
| nervöse Mausbewegung | Licht beginnt zu flackern |
| ignorierte Türen | dort erscheinen später Hinweise und Licht |
| viel Dunkelheit | Anspannung, Herzschlag, Wahrnehmungsverzerrung |

**Schreckmomente** – genau 8 im ganzen Spiel, jeder nur einmal,
keine Wiederholungen, mit langen Sperrzeiten dazwischen:

1. Tür geöffnet – Krankenschwester steht regungslos dahinter, Licht geht aus, sie ist weg
2. Langer Flur – Patient am Ende, beim Wegsehen leer
3. Badezimmerspiegel – Gestalt dahinter, beim Umdrehen niemand
4. Rollstuhl rollt langsam über den Flur und hält an, Räder drehen nach
5. Aufzug öffnet sich – Arzt regungslos, Tür schließt, danach leer
6. Lautsprecherdurchsage – Person am Flurende, beim Näherkommen leer
7. Schlüssel aufgehoben – beim Umdrehen steht jemand da, Licht flackert, weg
8. Schnelle Schritte hinter dem Spieler – niemand da, aber ein Bett steht jetzt im Flur

**Figuren** – keine Monster. Ärzte, Krankenschwestern, Patienten,
Reinigungspersonal, Sicherheitsdienst. Prozedural erzeugte Menschen mit
Skelett-Animation, Atmung, langsamen Kopfbewegungen, abgenutzter Kleidung.
Sie stehen meistens einfach nur da.

---

## Story

Der Spieler wacht ohne Erinnerung in einem seit Jahren geschlossenen
Krankenhaus auf. Neun Dokumente und sechs Bandaufnahmen erzählen die
Geschichte in drei Wahrheitsebenen, die einander widersprechen.

**Fünf Enden**, bestimmt durch Verhalten, nicht durch Entscheidungen:

| Ende | Bedingung |
|---|---|
| AUSGANG | ruhig gespielt, Dokumente gelesen |
| VERWEIGERUNG | viel gerannt, Dokumente ignoriert |
| KREIS | immer dieselben Räume, kaum erkundet |
| AUFLÖSUNG | lange im Dunkeln, hohe Anspannung, tiefe Etagen |
| ZEUGE | alle Wahrheitsebenen gefunden, Gestalten nicht gemieden |

---

## Systemanforderungen

- Windows 10/11 (64-Bit)
- OpenGL 3.3
- Visual Studio Build Tools mit C++ Workload (nur zum Kompilieren)

Das Spiel erkennt die Grafikkarte und wählt automatisch eine passende
Qualitätsstufe. Läuft auf integrierten Grafikchips mit 60 FPS.
