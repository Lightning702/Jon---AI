# Jons Fachteam

Stand: 2. Oktober 2026, Jon 4.58.0.

Das Fachteam ist jetzt fest in Jon eingebaut. Jon setzt es selbst ein, wenn eine Aufgabe mehrere Perspektiven braucht oder du ausdrücklich nach Agenten, Experten oder einem Team fragst – in der App, im Web, am Handy bei Funke und überall, wo Jon chattet.

## So arbeitet das Team

1. **Verteilen:** Jon zerlegt die Aufgabe in bis zu vier unabhängige Teilfragen und wählt passende Fachprofile: Latein, Lernen & Mathe, Programmierung, Recherche, Planung, Schreiben, Gestaltung oder Fachanalyse.
2. **Arbeiten:** Die Fachagenten arbeiten gleichzeitig.
3. **Gegenprüfen:** Eine unabhängige Prüfung sucht Fehler, Widersprüche und fehlende Teilfragen.
4. **Bündeln:** Jon fasst alles zu einer Antwort zusammen und nennt offene Punkte ausdrücklich.

Das Team arbeitet nur lesend und braucht deshalb keine Freigabe. Mit Webrecherche-Erlaubnis darf es vorhandene Suchwerkzeuge nutzen.

## Live-Animation

Sobald Jon das Team startet, erscheint im Chat eine Live-Karte: Jons Kern in der Mitte, die Fachagenten fliegen heraus, Datenströme laufen entlang der Verbindungen, die Gegenprüfung läuft als Radar-Scan, beim Bündeln fließen die Ergebnisse zurück. Jeder Agent zeigt Status, Dauer und sein Ergebnis zum Aufklappen. Laufende Teams lassen sich direkt in der Karte stoppen.

Läufe, die nicht im aktuellen Chat sichtbar sind – zum Beispiel aus Telegram, von Funke am Handy oder aus dem Terminal –, zeigt das **Agenten-Dock** unten rechts in der Desktop-App. Ein Tipp darauf öffnet kompakte Live-Karten aller laufenden Fachteams und Harness-Aufträge.

## Schnittstellen

- `GET /api/agents/live` liefert laufende und gerade beendete Fachteams und Harness-Aufträge.
- `GET /api/agents/runs/{id}` liefert einen Lauf mit allen Teilergebnissen.
- Das Chat-Ereignis des Werkzeugs `team` enthält `card` (`kind: "agenten"`) und `agent_run_id`, bevor das Team startet.
- Private Läufe aus temporären Chats werden nicht gespeichert, bleiben aber 15 Minuten für die Live-Karte abrufbar.

## Werkzeuge → Fachteam

Unter **Werkzeuge → Jon Fachteam** lässt sich das Team auch direkt beauftragen: Fachrichtungen wählen, Anzahl der Agenten festlegen, Webrecherche erlauben und frühere Aufträge erneut ansehen.
