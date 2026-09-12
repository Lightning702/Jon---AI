# PowerPoint

Anleitung, wie Jon echte PowerPoint-Dateien (.pptx) baut, die aussehen und wirken wie
von Hand gemacht — mit Übergängen, Animationen, Diagrammen und Bildern. Lies diese Datei
ganz, bevor du die erste Folie planst. Sie ist frei bearbeitbar; Jon liest immer die
aktuelle Version.

## Grundregel

Nutze **immer das Werkzeug `create_pptx`**. Schreibe niemals XML von Hand, entpacke keine
ZIP-Archive und starte kein Python-Skript dafür. Eine vorhandene Datei liest du mit
`read_pptx`.

`create_pptx` erwartet:

- `title`, `subtitle` — für die Titelfolie
- `theme` — Farbwelt, siehe unten
- `path` — Zieldatei (`.pptx`); ohne Angabe Jons Präsentationen-Ordner
- `slides` — die Folien als Liste von Objekten
- `bilder` — `false` schaltet das Malen der Bilder ab
- `effekte` — `false` lässt Übergänge und Animationen weg

Übergänge und Animationen kommen **automatisch**. Du musst nichts dafür tun.

## Die wichtigste Regel: schreib richtig aus

Das war bisher der größte Fehler. Eine Folie mit fünf Stichwörtern ist keine
Präsentation, sondern eine Gliederung.

- **Jede Inhaltsfolie braucht einen `text`** — ein bis drei Sätze, die den Gedanken
  wirklich erklären. Der steht als Einleitung über dem Inhalt.
- **Stichpunkte sind ganze Aussagen.** Schreib `Begriff: Erklärung in einem vollen
  Satz`, nicht nur `Begriff`. 10–25 Wörter pro Punkt sind richtig, nicht 3.
- **Sprechernotizen sind Pflicht**: 2–4 Sätze pro Folie, was man dazu sagt, inklusive
  Übergang zur nächsten Folie.
- **Niemals Platzhalter.** Kein `X Prozent`, kein `Wert eintragen`, kein `Lorem ipsum`,
  kein `2X PB/Monat`. Kennst du eine Zahl nicht, such sie mit `web_search` oder lass
  den Punkt weg. Eine erfundene Zahl ist schlimmer als keine.
- Faustregel für die Textmenge: **400–900 Zeichen sichtbarer Text pro Inhaltsfolie**.

## Layouts

| `layout` | Wofür | Wichtige Felder |
| --- | --- | --- |
| `title` | Titelfolie, dunkel | `title`, `subtitle`, `footer` |
| `agenda` | Nummerierte Gliederung mit Erklärung | `items[{titel, text}]` |
| `bullets` | Punkte mit Einleitung | `title`, `text`, `bullets`, `image` |
| `text` | Fließtext, wenn ein Gedanke Raum braucht | `title`, `absaetze[...]` |
| `cards` | 2–4 nummerierte Karten nebeneinander | `title`, `items[{titel, text}]` |
| `stat` | 1–3 große Kennzahlen, farbiger Grund | `title`, `items[{titel, text}]` |
| `chart` | **Echtes Diagramm** | `title`, `text`, `diagramm`, `footer` |
| `table` | **Echte Tabelle** | `title`, `text`, `tabelle` |
| `two_columns` | Zwei Karten nebeneinander | `title`, `items[{titel, text, bullets}]` |
| `compare` | Gegenüberstellung mit Kopfleisten | `title`, `items[{titel, text, bullets}]` |
| `image` | Bild halbseitig rechts, Text links | `title`, `text`, `bullets`, `image`/`bild_prompt` |
| `quote` | Zitat groß und zentriert, dunkel | `text`, `subtitle` |
| `timeline` | Nummerierte Schritte untereinander | `title`, `items[{titel, text}]` |
| `closing` | Abschluss, dunkel | `title`, `subtitle` |

### Diagramme

```json
{"layout": "chart", "title": "Strombedarf der Rechenzentren",
 "text": "Der Verbrauch wächst schneller als die Effizienzgewinne.",
 "diagramm": {"art": "balken",
              "kategorien": ["2018", "2020", "2022", "2024"],
              "reihen": [{"name": "TWh pro Jahr", "werte": [198, 220, 240, 260]}]},
 "footer": "Quelle: IEA, 2024",
 "notes": "Hier lohnt ein Blick auf die Steigung ..."}
```

`art`: `balken`, `bar`, `linie`, `flaeche`, `kreis`, `donut`, `gestapelt`.
Mehrere `reihen` sind erlaubt (bis 4). **Nur echte Zahlen** — nichts schätzen.

### Tabellen

```json
{"layout": "table", "title": "Maßnahmen im Vergleich",
 "text": "Drei Hebel, sortiert nach Wirkung pro investiertem Euro.",
 "tabelle": [["Maßnahme", "Aufwand", "Wirkung"],
             ["Abwärmenutzung", "hoch", "sehr hoch"],
             ["Lastverschiebung", "mittel", "hoch"]]}
```

Erste Zeile sind die Spaltentitel, höchstens 8 Zeilen und 6 Spalten.

### Bilder

- `image` nimmt einen echten Pfad auf dem PC.
- **`bild_prompt` lässt Jon das Bild selbst malen** — beschreibe das Motiv auf Englisch,
  bildhaft und ohne Text im Bild (`"wind turbines on a green hill at sunrise"`). Das
  passt gut auf `image`-Folien und als Auflockerung.
- Nimm Bilder sparsam: zwei bis vier pro Präsentation, nicht auf jeder Folie.

## Aufbau einer guten Präsentation

1. `title` — Thema und ein Satz, worum es geht.
2. `agenda` — was kommt, mit je einem erklärenden Halbsatz.
3. Hauptteil: pro Gedanke eine Folie, **Layouts abwechseln**.
4. Mindestens ein `chart` oder `table`, wenn es Zahlen gibt.
5. `quote`, `stat` oder `compare` als Rhythmuswechsel.
6. `closing` — Fazit mit einer klaren Aussage, nicht nur „Danke".

Weitere Regeln:

- 10–16 Folien für einen 10-Minuten-Vortrag.
- Nie zweimal hintereinander dasselbe Layout.
- Dunkle Folien (`title`, `stat`, `quote`, `closing`) als Anker zwischen hellen.
- Höchstens 6 Stichpunkte pro Folie — aber die dann ausformuliert.

## Farbwahl

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

## Übergänge und Animationen

Jon setzt sie automatisch: einen ruhigen Wechsel je Folie und ein Einblenden der
Elemente, Stichpunkte einzeln. Eingreifen brauchst du nur, wenn der Nutzer es will:

- `uebergang` pro Folie: `fade`, `push`, `wipe`, `cover`, `split`, `zoom`, `morph`,
  `reveal`, `glitter`, `wind`, `keiner`
- `tempo`: `langsam`, `mittel`, `schnell`
- `effekte: false` schaltet alles ab, wenn jemand eine nüchterne Datei will

## Ablauf für Jon

1. Kläre in einem Satz Thema, Zielgruppe und Länge. Ist es klar, frag nicht — leg los.
2. **Recherchiere mit `web_search`, sobald echte Zahlen vorkommen.** Lieber einmal
   suchen als einmal raten.
3. Plane die Folien: Layout + Kernaussage + welche Zahl darauf gehört.
4. Rufe `create_pptx` einmal mit allen Folien auf.
5. Öffne die Datei mit `datei_oeffnen` auf dem zurückgegebenen Pfad.
6. Antworte knapp: wo sie liegt, wie viele Folien, was drin ist. Biete an, einzelne
   Folien zu ändern.

## Checkliste vor der Übergabe

- [ ] Jede Inhaltsfolie hat einen erklärenden `text`
- [ ] Stichpunkte sind ausformuliert, nicht nur Begriffe
- [ ] Keine einzige erfundene Zahl und kein Platzhalter
- [ ] Mindestens ein Diagramm oder eine Tabelle, wenn es Zahlen gibt
- [ ] Sprechernotizen mit 2–4 Sätzen auf jeder Folie
- [ ] Layouts wechseln sich ab
- [ ] Abschlussfolie mit echter Aussage
- [ ] Datei geöffnet und Pfad genannt
