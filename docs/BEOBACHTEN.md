# Beobachten

Stand: 3. Oktober 2026, Jon 4.58.1.

Sag Jon im Chat zum Beispiel „Erinnere mich, wenn das Tiiny AI Pocket Lab rauskommt.“ Jon legt dann über das Werkzeug `beobachten` eine Beobachtung an, prüft sie selbstständig und meldet sich, sobald es so weit ist. Unter **Werkzeuge → Beobachten** siehst du alle Beobachtungen mit Status, letzter Prüfung und Treffer mit Link. Dort kannst du auch selbst welche anlegen, sofort prüfen lassen, stoppen oder löschen.

Jon prüft nur, solange er läuft, auf deinem PC oder deinem Pi.

## Ablauf

- Gespeichert wird in `beobachtungen.json` im Datenordner mit `id`, `frage`, `bedingung`, `intervall_stunden` (Standard 24), `letzter_check`, `status` (aktiv, erfuellt, gestoppt) und `treffer`.
- Alle zehn Minuten schaut eine Hintergrundschleife nach fälligen Beobachtungen. Jede fällige startet eine Websuche mit Jons vorhandener Suche (`search_web`, mit gelesenen Seiten).
- Ein kurzer JSON-Prompt an Jons Modell entscheidet: `{"erfuellt": bool, "beweis": "...", "quelle": "url"}`. Es zählt nur ein eindeutiger Beleg mit Quelle. Die Quelle muss eine der gefundenen URLs sein, erfundene Links werden verworfen. Das Modell läuft über den Harness-Zugang mit Wiederholungen und Ersatzmodellen.
- Ist die Bedingung erfüllt, meldet sich Jon in der App (Chatnachricht und Systembenachrichtigung) und, falls verbunden, über Telegram. Danach steht die Beobachtung auf `erfuellt`. Jede Meldung kommt genau einmal.
- Netz-, Such- und Modellfehler stoppen die Schleife nie. Sie werden geloggt, an der Beobachtung angezeigt und beim nächsten Intervall erneut versucht.

## API

```text
GET    /api/beobachten
POST   /api/beobachten              {"frage": "...", "bedingung": "...", "intervall_stunden": 24}
DELETE /api/beobachten/{id}
POST   /api/beobachten/{id}/pruefen
POST   /api/beobachten/{id}/stoppen
GET    /api/beobachten/meldungen
```

Das Chat-Werkzeug `beobachten` (Aktionen `anlegen`, `liste`, `stoppen`) gilt als nur lesend und braucht keine Freigabe.

## Prüfung

8 Tests mit nachgebauter Suche und nachgebautem Modell decken ab:
- Anlegen
- Fällige Prüfung, erfüllt und nicht erfüllt
- Das Intervall wird eingehalten
- Genau eine Benachrichtigung
- Erfundene Quellen zählen nicht
- Such- und Modellfehler stoppen den Dienst nicht
- Ein Telegram-Fehler blockiert die App-Meldung nicht
- Werkzeug und API

Eine echte Beobachtung über mehrere Tage mit einem Live-Modell wurde nicht getestet.
