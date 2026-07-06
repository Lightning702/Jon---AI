# Skills (Plugin-Dokumentation)

Skills sind Jons Plugin-Mechanismus: **bearbeitbare Markdown-Anleitungen**, die Jon vor
einer Aufgabe liest und befolgt. Kein Code, kein Neustart — eine Datei genügt.

## Wo liegen Skills?

Im Ordner `skills/` im Projekt- bzw. entpackten ZIP-Verzeichnis. Jede `.md`-Datei ist ein
Skill; der Dateiname (ohne Endung) ist der Skill-Name.

## Wie nutzt Jon sie?

1. Beim Chatstart hängt Jon einen Katalog aller Skills an den System-Prompt.
2. Passt eine Aufgabe zu einem Skill, ruft Jon `read_skill(name)` auf und folgt der
   Anleitung.
3. Mit `write_skill(name, content)` kann Jon sich neue Arbeitsweisen selbst merken.

## Skills bearbeiten

Drei Wege:

- **In der App:** Konten-Symbol → Tab „Skills" → Skill wählen → bearbeiten → Speichern.
- **Als Datei:** `skills/<name>.md` in einem beliebigen Editor öffnen und speichern.
- **Per API:** `PUT /api/skills/<name>` mit `{ "content": "..." }`.

## Einen neuen Skill anlegen

Lege `skills/mein-skill.md` an:

```markdown
# Mein Skill

Kurze Beschreibung, wann Jon diesen Skill nutzen soll.

## Vorgehen
1. Schritt eins
2. Schritt zwei

## Regeln
- Was immer gilt
```

Der Name muss klein geschrieben sein und darf Buchstaben, Ziffern, `-` und `_` enthalten.

## Mitgelieferte Skills

| Name | Zweck |
|------|-------|
| `web-design` | Moderne, responsive Websites bauen (Tokens, Layout, Checkliste) |
| `pc-automation` | Zuverlässige Maus-/Tastatur-Steuerung, Rezepte |
| `research` | Sauber im Web nachschlagen und zusammenfassen |

## Gute Skills schreiben

- Sag klar, **wann** der Skill greift.
- Gib ein **nummeriertes Vorgehen** statt vager Prinzipien.
- Nenne konkrete Tools (`write_file`, `open_url`, …).
- Ende mit einer **Checkliste**, damit Jon das Ergebnis prüfen kann.
