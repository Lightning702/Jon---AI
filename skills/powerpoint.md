# PowerPoint

Anleitung, wie Jon echte PowerPoint-Dateien (.pptx) baut, die nach etwas aussehen.
Lies diese Datei ganz, bevor du die erste Folie planst. Sie ist frei bearbeitbar —
Farben, Regeln und Layouts kannst du jederzeit anpassen, Jon liest immer die aktuelle
Version.

## Grundregel

Nutze **immer das Werkzeug `create_pptx`**. Schreibe niemals XML von Hand, entpacke keine
ZIP-Archive und starte kein Python-Skript dafür — `create_pptx` bringt Layouts, Farben,
Typografie und Sprechernotizen schon mit. Eine vorhandene Datei liest du mit `read_pptx`.

`create_pptx` erwartet:

- `title`: Titel der Präsentation
- `subtitle`: Untertitel für die Titelfolie (optional)
- `theme`: eines von `midnight`, `forest`, `coral`, `terracotta`, `ocean`, `charcoal`,
  `teal`, `berry`, `sage`, `cherry`, `gold`
- `path`: Zieldatei (`.pptx`). Ohne Angabe landet sie in Jons Präsentationen-Ordner.
  Im Code-Modus immer eine Datei im geöffneten Projektordner.
- `slides`: die Folien als Liste von Objekten

Fehlt die Titelfolie, wird sie automatisch aus `title` und `subtitle` erzeugt.

## Layouts

| `layout` | Wofür | Felder |
| --- | --- | --- |
| `title` | Titelfolie, dunkel | `title`, `subtitle`, `footer` |
| `bullets` | Klassische Punkte in einer Karte | `title`, `text`, `bullets`, `image` |
| `cards` | 2–4 nummerierte Karten nebeneinander | `title`, `items[{title, text}]` |
| `stat` | 1–3 große Kennzahlen, farbiger Grund | `title`, `items[{title, text}]` |
| `two_columns` | Gegenüberstellung, zwei Karten | `title`, `items[{title, text, bullets}]` |
| `image` | Bild halbseitig rechts, Text links | `title`, `text`, `bullets`, `image` |
| `quote` | Zitat groß und zentriert, dunkel | `text`, `subtitle` |
| `timeline` | Nummerierte Schritte untereinander | `title`, `items[{title, text}]` |
| `closing` | Abschluss, dunkel | `title`, `subtitle` |

Jede Folie darf zusätzlich `notes` haben — das werden die Sprechernotizen.

## Aufbau einer guten Präsentation

1. `title` — Thema und ein Satz, worum es geht.
2. Ein Überblick (`bullets` oder `cards`) mit den 3 Kernpunkten.
3. Der Hauptteil: pro Gedanke eine Folie, **Layouts abwechseln**.
4. Zahlen, wenn es welche gibt (`stat`) — Zahlen bleiben hängen.
5. `quote` oder `timeline` als Rhythmuswechsel.
6. `closing` — Fazit oder Danke.

Faustregeln:

- 8–14 Folien für einen 10-Minuten-Vortrag, im Zweifel weniger.
- Maximal 5 Stichpunkte pro Folie, maximal 12 Wörter pro Stichpunkt.
- Stichpunkte sind Stichpunkte, keine Sätze. Kein Punkt am Ende.
- Schreibe `Begriff: Erklärung` — der Teil vor dem Doppelpunkt wird automatisch fett.
- Nie zweimal hintereinander dasselbe Layout.
- Dunkle Folien (`title`, `stat`, `quote`, `closing`) als Anker zwischen hellen Folien.
- Sprechernotizen (`notes`) mitliefern: 1–3 Sätze, was man dazu sagt.
- Kein Fülltext, kein „Lorem ipsum", keine leeren Platzhalterfolien.

## Farbwahl

Wähle das Theme passend zum Thema, nicht immer dasselbe:

| Theme | Passt zu |
| --- | --- |
| `midnight` | Business, Technik, Strategie |
| `ocean` | Daten, Forschung, Bildung |
| `forest` | Umwelt, Nachhaltigkeit, Biologie |
| `sage` | Gesundheit, Achtsamkeit, Beratung |
| `teal` | Startups, Produkt, Innovation |
| `coral` | Marketing, Kreatives, Social Media |
| `terracotta` | Handwerk, Kultur, Geschichte |
| `berry` | Mode, Food, Lifestyle |
| `cherry` | Sport, Wettbewerb, Dringlichkeit |
| `charcoal` | Technik, Recht, sachliche Berichte |
| `gold` | Jon selbst, Premium, Jubiläum |

## Bilder

- `image` nimmt einen echten Pfad zu einer Bilddatei auf dem PC.
- Fehlt das Bild oder ist der Pfad falsch, füllt Jon die Fläche farbig — die Folie
  bleibt heil, sieht aber leerer aus. Prüfe den Pfad vorher mit `list_dir`.
- Lade keine Bilder aus dem Netz herunter, ohne dass der Nutzer es will.

## Ablauf für Jon

1. Kläre in einem Satz Thema, Zielgruppe und Länge. Ist es klar, frag nicht nach —
   leg los.
2. Recherchiere nur, wenn der Inhalt Fakten braucht, die du nicht sicher weißt
   (`web_search`).
3. Plane die Folien kurz im Kopf: Layout + Kernaussage pro Folie.
4. Rufe `create_pptx` einmal mit allen Folien auf.
5. Öffne die fertige Datei mit `start_program` auf dem zurückgegebenen Pfad, damit der
   Nutzer sie sofort sieht.
6. Antworte knapp: wo die Datei liegt, wie viele Folien, was drin ist. Biete an,
   einzelne Folien zu ändern (dann baust du die Präsentation neu).

## Checkliste vor der Übergabe

- [ ] Titelfolie mit Thema und Untertitel
- [ ] Layouts wechseln sich ab
- [ ] Keine Folie mit mehr als 5 Stichpunkten
- [ ] Mindestens eine Zahlen- oder Zitatfolie
- [ ] Sprechernotizen gesetzt
- [ ] Abschlussfolie vorhanden
- [ ] Datei geöffnet und Pfad genannt
