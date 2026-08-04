# Architektur

## Abweichungen vom Masterprompt

Zwei Vorgaben waren auf dieser Maschine technisch nicht erfüllbar; nach Regel R12/V12 sind sie
hier benannt statt still umgangen.

1. **Vulkan 1.3 statt OpenGL.** Es ist kein Vulkan-SDK installiert, ebenso wenig CMake, Ninja
   oder DXC. Der Renderer nutzt stattdessen OpenGL-Core über einen eigenen Loader
   (`engine/render/GLApi`), gebaut mit `build.bat` und MSVC — derselbe Weg wie bei ECHO und
   AETHERIA. Der Kerr-Raymarcher verliert dadurch nichts an Genauigkeit, wohl aber an
   theoretischem Durchsatz (kein Async-Compute, keine Bindless-Deskriptoren).
2. **Keine Drittbibliotheken.** Die in Sektion 3 erlaubten Bibliotheken (volk, VMA, FreeType,
   Harfbuzz, zstd, libsodium, Catch2, …) sind nicht vorhanden und ohne Netzzugriff nicht
   beschaffbar. Mathematik, Container, Allokatoren, JSON, Sockets, HTTP, Font-Rendering und
   Testrahmen sind deshalb selbst implementiert.

## Schichten

```
engine/core       Typen, Log (lock-freier Ring + Writer-Thread), Result, Handle, StringId,
                  Zeit (Fixschritt-Akkumulator), Kommandozeile, Konfiguration
engine/memory     Allocator-Schnittstelle, Arena, Pool, Stack, Frame-Allokator, MemoryTracker
engine/container  Array, SparseSet, HashMap, RingBuffer, FreeList, BitSet
engine/math       Vec2/3/4, DVec3, Mat3/4, Quat, Transform, AABB/Sphere/Plane/Ray/Frustum,
                  Simplex-/Gradienten-/Worley-Rauschen, PCG-Zufall, Kugelkoordinaten
engine/job        Work-Stealing-Scheduler, JobHandle, ParallelFor
engine/ecs        Archetyp-basiert: Entity, ComponentStorage, Archetype, World, Query,
                  System, SystemScheduler mit Lese-/Schreibkonflikt-Auflösung
engine/event      EventBus mit Warteschlange und Verlauf
engine/platform   Win32-Fenster mit WGL-Kontext, Eingabe, Dateisystem
engine/render     GLApi, Shader, Mesh, RenderTarget, Camera, QualitySettings,
                  StarfieldPass, CelestialBodyPass, BlackHolePass, PostProcessPass
engine/ui         UIRenderer (Batching, 5x7-Bitmap-Atlas), Localization (de/en)
engine/net        JSON, TCP-Socket, HTTP-Client
```

```
game/universe     UniverseSeed (Hash-Kette), CoordinateSpace, FloatingOrigin,
                  GalaxyGenerator, StarSystemGenerator, PlanetGenerator, NameGenerator
game/space        OrbitalMechanics (Kepler), SpaceFlightController (6-DOF + Aerodynamik),
                  HyperdriveSystem, HyperRouteSolver (A*)
game/ship         Ship mit PowerGrid, Schilden, Waffengruppen, Scanner, Schadensmodell
game/voidheart    VoidHeart, VoidStation, ExoticResource, EndgameCampaign
game/jon          JonContextBuilder, JonOfflineBrain, JonCompanion (Bridge zum Jon-Backend)
game/map          GalaxyMapState mit sechs Zoomstufen
game/screens      MainMenuScreen mit der 90-Sekunden-Kamerafahrt
game/hud          HudRoot
game/multiplayer  CoopSession über die bestehende Jon-Infrastruktur
```

## Zeitachsen

| Achse | Rate |
|---|---|
| Simulation | fest 60 Hz, deterministisch |
| Rendering | variabel, entkoppelt |
| Koop-Zustand | 20 Hz senden, 100 ms Interpolationspuffer |
| Jon-Bridge | asynchron, 4 s Timeout |

## Determinismus

Jeder Knoten leitet seinen Seed aus der Elternkette ab:

```
seed(galaxie) = hash(universeSeed, index)
seed(system)  = hashCoordinate(seed(galaxie), x, y, z)
seed(planet)  = hash(seed(system), index)
seed(mond)    = hash(seed(planet), index)
seed(kachel)  = hashCoordinate(hash(seed(planet), face, level), x, y, level)
```

Alle Generatoren sind reine Funktionen ihres Seeds. Der Build nutzt `/fp:precise`, damit
Simulationspfade bitidentisch bleiben. Die Testsuite prüft Reproduzierbarkeit von Galaxie,
System, Planetenradius und Rauschen.

## Koordinaten

| Ebene | Typ | Einheit |
|---|---|---|
| GalaxyCoord | int64 | Lichtjahre im Galaxiengitter |
| SystemCoord | int64 | Lichtjahre innerhalb der Galaxie |
| LocalCoord | double | Meter relativ zum Bezugskörper |
| RenderCoord | float | Meter relativ zum Floating Origin |

`FloatingOrigin` rebased die Renderwelt bei 4096 m Abstand. Physik läuft durchgehend in
`double`, Rendering in `float` relativ zum Ursprung.

## Anbindung an Jon

- **Arcade:** `jon-spiele.json` im Projektordner. Jons `arcade_service` findet den Ordner
  unter `spiele/` automatisch, zeigt Titel, Beschreibung, Steuerung und Vorschaubild und
  kann über `build.bat` bauen.
- **KI:** `JonCompanion` spricht `POST /api/chat` auf `127.0.0.1:8756` und liest den
  SSE-Strom. Schlägt das fehl, bleibt das Offline-Gehirn zuständig; das Spiel ist ohne
  Netzwerk voll spielbar.
- **Koop:** `CoopSession` spricht das bestehende JSON-Zeilenprotokoll des Jon-Koop-Servers
  auf TCP 8759, dasselbe wie ECHO und AETHERIA. Nachrichten: `host`, `join`, `ready`,
  `start`, `state`, `chat`, `leave`; vom Server `lobby`, `start`, `snapshot`, `chat`,
  `leave`, `error`.

## Stand

Vollständig und im Spiel benutzbar: Fundament, Rendering-Pipeline, Universumsgenerierung,
Void Heart mit allen sechs Zonen, vier Stationen, fünf exotischen Ressourcen und sechs
Endgame-Missionen, Raumflug mit Orbitalmechanik, Hyperantrieb mit Routenlöser und
Transitgefahren, Schiffssysteme, Galaxiekarte, Startbildschirm, HUD, Jon, Koop-Anbindung,
Qualitätsstufen mit Sparmodus.

Noch nicht umgesetzt (aus dem Masterprompt, klar abgegrenzt): begehbare Planetenoberflächen
mit Quad-Sphere-Terrain-Meshing, Höhlen, Vegetation, Kreaturen, Basenbau, Crafting,
Alien-Diplomatie, Audio-Engine und der autoritative C++-Shard-Server. Die Datenmodelle dafür
(Biome, Ressourcenprofile, Zivilisationsstufen, Planetenparameter) sind vorhanden und werden
bereits erzeugt.
