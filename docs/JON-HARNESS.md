# Jon Harness und MiniJon

Stand: 3. Oktober 2026, Jon 4.59.0. Der Harness öffnet in der App einen eigenen Arbeitsbereich mit Sitzungsleiste, Eingabefeld unten, animierter Live-Ansicht, Diff-Ansicht und Projektvorschau. Er arbeitet immer mit Jons Modell aus den Einstellungen – auch wenn der Auftrag aus MiniJon kommt. MiniJon kann den Fortschritt nur noch als Begleiter anzeigen.

## Einstieg

Jon aus diesem Checkout neu starten, damit Backend und MiniJon die neuen Dateien laden. Ein bereits installiertes älteres App-Paket enthält diese Änderungen erst nach einem neuen Paket-Build.

Im Projektordner ein Terminal öffnen:

```text
jon-code
jon-code "Behebe den Fehler und prüfe die Änderung"
jon-harness -C "C:\Projekte\MeineApp" "Ergänze die Suchfunktion"
```

Beide Befehle starten denselben Coding-Harness. Im bestehenden Jon-Terminal öffnet `agent <Auftrag>` ebenfalls den Harness. Die Befehle wurden über Jons vorhandenen Installer in den Benutzerpfad installiert. Sie verwenden den aktuellen Arbeitsordner und die vorhandene Modellkonfiguration. Mit `--provider`, `--model` und `--max-steps` lassen sich diese Werte pro Aufruf wählen.

Der Terminal-Client nutzt ein erreichbares Jon-Backend. Wenn keine Verbindung aufgebaut werden kann, startet er den lokalen Harness. Authentifizierungsfehler führen nicht zu einem stillen Wechsel. Ein älteres laufendes Backend muss neu gestartet werden.

## Sitzungen

Ein Auftrag im Harness eröffnet eine Sitzung. Jeder weitere Auftrag, den du im Eingabefeld schickst, bleibt in dieser Sitzung: Jon bekommt die früheren Aufträge, ihre Zusammenfassungen, die geänderten Dateien und die Prüfergebnisse mit und liest betroffene Dateien vor einer Änderung erneut. Frühere Aufträge erscheinen im Verlauf eingeklappt, der aktuelle vollständig. **Änderungen** zeigt alle Dateien der Sitzung. Solange ein Auftrag läuft, wartet das Eingabefeld, bis er fertig ist. **Neue Sitzung** beginnt ein neues Thema.

Startet Jon im normalen Chat einen Harness-Auftrag, setzt er die zuletzt aktive Sitzung desselben Projekts fort, wenn sie in den letzten drei Stunden benutzt wurde. Mit `new_session` im Werkzeug `harness_task` beginnt er bewusst neu. In Telegram setzt `/harness <Auftrag>` die laufende Sitzung fort, `/hneu <Auftrag>` beginnt eine neue.

```text
GET  /api/harness/threads
GET  /api/harness/threads/{id}
POST /api/harness/tasks   {"root": "...", "goal": "...", "thread": "<Sitzung oder leer>"}
```

## Projektvorschau

**Vorschau** in der oberen Leiste oder in der linken Schiene öffnet dein Projekt neben dem Verlauf. Die Gerätewahl schaltet zwischen Desktop, Tablet (820 px) und Handy (390 px).

- **Statische Seiten:** Findet Jon eine `index.html` im Projekt oder in `dist`, `build`, `public`, `docs`, `www`, `site` oder `out` (sonst die erste HTML-Datei), startet er einen lokalen Server auf `127.0.0.1` mit zufälligem Port. Der Server liefert keine versteckten Dateien, keine `.env`, keine Schlüssel- und Zugangsdateien und beantwortet nur Anfragen an seine eigene Adresse.
- **Node-Projekte:** Hat `package.json` ein Skript `dev`, `start`, `preview` oder `serve`, zeigt Jon den Befehl und startet ihn erst nach deinem Klick, bei fehlendem `node_modules` mit vorherigem `npm install`. Die Adresse liest Jon aus der Ausgabe. Der Server läuft mit deinen Benutzerrechten und lässt sich jederzeit stoppen; beim Beenden von Jon wird er mit allen Unterprozessen beendet.
- Nach jedem Auftrag mit Änderungen lädt die Vorschau automatisch neu.

```text
GET  /api/harness/preview?root=...
POST /api/harness/preview        {"root": "..."}
POST /api/harness/preview/stop   {"root": "..."}
```

## Modelle: NVIDIA und Ollama

Der Harness verwendet einen eigenen, geduldigeren Modellzugang als der Chat:

- Bis zu 150 Sekunden Wartezeit auf das erste Token. Bei 429, 500 bis 504, 529, Überlastung und Verbindungsabbrüchen bis zu drei Wiederholungen nach 2, 5 und 12 Sekunden, danach Jons Ersatzroute mit bis zu vier Modellen. Jeder Versuch steht als Hinweis im Aktivitätsverlauf.
- `<think>`-Blöcke werden entfernt. Liefert ein Modell sein Ergebnis nur im Reasoning-Kanal, wird dieses gelesen.
- Für Ollama fordert der Harness mindestens 16.384 Token Kontext an. Meldet Ollama zu wenig Speicher, arbeitet er mit der eingestellten Kontextlänge und einer kompakten Anleitung weiter. Dateiliste, Verlauf und frühere Aufträge werden passend zum Fenster gekürzt; die letzte Aktion bleibt vollständig.
- Für Coding-Aufträge eignen sich Modelle ab etwa 7 bis 8 Milliarden Parametern, zum Beispiel `qwen2.5-coder:7b` lokal oder ein großes NVIDIA-Modell.
- Unter Windows laufen Befehle in PowerShell 5.1 mit `-ExecutionPolicy Bypass`. Das Modell erfährt die Shell und trennt Befehle mit `;`.
- Ändert ein Modell eine Datei ohne vorherigen Plan, gilt der Auftrag als Plan. Viermal derselbe Werkzeugfehler hintereinander beendet den Auftrag mit `needs_review` und einer klaren Meldung.

## App, MiniJon und Telegram

In der App unter **Werkzeuge → Jon Harness** einen Projektordner und Auftrag wählen. Die Werkzeugliste hat eine Suche. Der Harness zeigt Plan, Änderungen, Prüfungen und konkrete Befehlsfreigaben. Der Schalter **MiniJon begleitet** im Eingabefeld lässt MiniJon den Fortschritt auf dem Bildschirm zeigen; das Modell bleibt Jons Modell. MiniJons Bildschirm- und Privatsphäre-Einstellungen liegen jetzt unter **Mini Jon anpassen**.

Startet Jon im normalen Chat einen Harness-Auftrag, erscheint dort eine Live-Karte mit Jon-Kern, kreisendem Werkzeug-Satelliten (lesen, ändern, testen …), Fachagenten, Arbeitsplan, Freigabe-Knöpfen und Änderungszahlen. **Im Harness öffnen** springt direkt in den Arbeitsbereich.

Der Harness kann bis zu vier begrenzte Fachaufträge delegieren. Diese Teilagenten nutzen die Fachprofile des Fachteams (zum Beispiel Programmierung, Recherche, Gestaltung), lesen die ausgewählten Projektdateien und liefern Analysen; Änderungen und Prüfungen bleiben im Hauptauftrag nachvollziehbar. Antwortet das Modell mehrfach nicht im Werkzeugformat, bricht der Harness mit einem klaren Hinweis auf ein stärkeres Modell ab. JSON mit Begleittext oder Codeblock wird toleriert. Für komplexe Alltagsfragen gibt es außerdem das Fachteam-Werkzeug. Spezialisierung ersetzt keine fachliche Kontrolle.

```text
/hhelp
/projekte
/projekt MeinProjekt
/harness Behebe den Fehler in der Suche und führe passende Tests aus
/aufgaben
/hstatus AUFGABEN_ID
/diff AUFGABEN_ID
/hstop AUFGABEN_ID
```

Projekte müssen zuvor in Jon gespeichert werden. Die Auswahl bleibt pro Kanal erhalten. Im normalen Jon- und MiniJon-Chat steht zusätzlich das Werkzeug `harness_task` bereit: Ein ausdrücklicher mehrschrittiger Coding-Auftrag kann damit im geöffneten oder ausgewählten Projekt gestartet werden. Fehlt der Ordner, liefert das Werkzeug eine Projektauswahl statt einen Pfad zu erfinden. Shellbefehle können vom Modell nicht selbst freigegeben werden.

Telegram verwendet den bereits verbundenen privaten Chat. Andere Kanäle können dessen Aufträge nicht steuern. Telegram meldet anstehende Freigaben und Endergebnisse; Status und Änderungen sind abrufbar. `/stopp` bricht auch die laufenden Harness-Aufträge dieses Chats ab. Über den normalen Telegram-Modellaufruf werden keine Aufträge mit verlorenem Chatbezug gestartet; dafür dienen die expliziten Befehle oben.

Vor jedem Shellbefehl zeigt Jon den konkreten Befehl und Arbeitsordner. `/erlauben AUFGABEN_ID FREIGABE_ID` bestätigt ausschließlich diese Freigabe, `/ablehnen ...` lehnt sie ab. In MiniJon genügt bei der gerade angezeigten Freigabe `/ja` beziehungsweise `/nein`. Diese Eingaben funktionieren auch für freigabepflichtige Werkzeuge des normalen MiniJon-Chats. Ein Shellprozess läuft mit Benutzerrechten; der Arbeitsordner ist keine Sandbox.

## Verlässlichkeit

Der Harness arbeitet in begrenzten Schritten: planen, suchen, lesen, ändern, prüfen und Ergebnis melden. Er protokolliert Pläne, Änderungen, Diffs, Prüfergebnisse und Status. Pro Arbeitsordner verhindert eine Prozesssperre konkurrierende Harness-Aufträge. Änderungen benötigen einen vorherigen Lesezugriff und unveränderte Dateihashes. Neue Dateien überschreiben keine vorhandenen Dateien. Vor dem Überschreiben vorhandener Dateien greift Jons bestehende Sicherung im Papierkorb-Dienst.

Pfadwechsel aus dem gewählten Ordner, Symlinks, Junctions, Hardlinks, typische Geheimnisdateien und Abhängigkeitsverzeichnisse sind bei den direkten Dateiwerkzeugen ausgeschlossen. Ausgaben und Dateigrößen sind begrenzt. Abbruch beendet auch gestartete Prozessnachkommen. Nach einem Backend-Neustart werden unterbrochene Aufgaben als unterbrochen angezeigt und nicht erneut ausgeführt.

Ein geändertes Projekt gilt nur nach erfolgreichen Prüfungen auf dem aktuellen Änderungsstand als erledigt. Fehlgeschlagene oder fehlende Prüfungen ergeben `needs_review`. Ein erfolgreicher Test ist kein Beweis, dass jede Produkteigenschaft korrekt ist. Die Qualität der Planung und der gewählten Tests hängt weiterhin vom konfigurierten Modell ab.

Auch der allgemeine Jon-Chat erkennt strukturierte Werkzeugfehler, fehlgeschlagene Exitcodes und Zeitüberschreitungen. Nach einem bereits begonnenen Werkzeugaufruf wiederholt ein Providerwechsel den Auftrag nicht. Datenschutzentscheidungen werden vor einem Cachetreffer geprüft; veränderliche Projekt- und Dokumentinhalte werden nicht aus diesem Antwortcache geliefert.

## MiniJon im Alltag

Laufende Harness-Aufträge bleiben bei kurzzeitiger Verbindungsunterbrechung erhalten. MiniJon verbindet sich erneut und zeigt den aktuellen Stand. Nach einem Fensterneustart stellt er die Anzeige des gespeicherten Auftrags wieder her. Ein fehlgeschlagener Stopp wird ausdrücklich als unbestätigt angezeigt. Wiederkehrende Vorschläge werden dedupliziert und nach Ablehnung seltener gezeigt.

```text
/kontext an
/kontext aus
/privat an
/privat aus
/ruhe
/modus coden
/modus schreiben
/modus recherchieren
/modus planen
/modus design
/modus lernen
/modus dateien
/modus sprechen
/modus automatisieren
/modus ideen
/modus auto
```

Kontexterkennung ist standardmäßig aus. Eingeschaltet liest sie lokal unter Windows den Prozessnamen, Fenstertitel, Fensterbereich und die Leerlaufzeit. Eine konfigurierbare Sperrliste unterdrückt private Anwendungen. Vollbildfenster unterdrücken proaktive Vorschläge. `/privat an` löscht den aktuellen Kontext und pausiert die Beobachtung.

Die zusätzliche Bildschirmanalyse wird separat eingeschaltet. `/bildschirm` erfasst das aktive Fenster; MiniJon wird dabei ausgeblendet. Bilder werden nur im Arbeitsspeicher verarbeitet. Externe Vision-Anbieter benötigen eine ausdrückliche Freigabe für den jeweiligen Anbieter und Endpunkt. Die Erkennung prüft vor und nach der Aufnahme den Fensterkontext und die Privatsphäre-Einstellung. Unsichere Erkennung führt zur Rückfrage. Bei manuellen fachlichen Fragen folgt auf die Texterkennung eine gesonderte fachliche Modellprüfung. Automatische Beobachtung führt keine erkannten Anweisungen aus.

MiniJon lässt sich über Monitorgrenzen ziehen. Erst beim Loslassen wird seine Position auf dem Zielbildschirm begrenzt. Auf dem Handy übernimmt [Funke](FUNKE-HANDY.md) die Rolle des Begleiters.

Die zehn Auftritte sind über `/modus` wählbar. Automatisch erkannte Tätigkeiten decken die erkennbaren App-Kategorien ab; ein Harness-Auftrag zeigt den Coding-Auftritt. Ideen und Automatisieren lassen sich bewusst wählen. Der manuelle Auftritt gilt für das aktuelle Fenster. Der 3D-Modus bleibt über die vorhandenen MiniJon-Einstellungen auswählbar.

Die Figur rendert höchstens 30 Bilder pro Sekunde, schlafend 15. Verborgene Fenster pausieren das Rendering. Reduzierte Bewegung wird berücksichtigt. Die alte lokale Unterhaltung unter `emil_memory` wird in `mini_jon_memory` übernommen; der alte Schlüssel bleibt als Rückfall erhalten.

Jon spricht als warmer, direkter Kollege mit trockenem Humor. MiniJon bleibt kürzer und verspielter. Beide erhalten einen gemeinsamen Verhaltenskompass: Ergebnisse prüfen, Grenzen und Stopps beachten, Fehler eingestehen, keine erfundenen Erinnerungen oder Gefühle behaupten. Das implementiert Verhalten, kein erlebtes Gewissen.

## Prüfung

Für 4.59.0 bestanden 95 gezielte Harness-, Fachteam- und Zuverlässigkeitstests, darunter neue Tests für Sitzungen, Vorschau (inklusive gesperrter `.env` und fremdem Host), Wiederholungen bei 429/503, Ausweichmodelle, Reasoning-Antworten, den Ollama-Speicherrückfall und das Kontextbudget. Im Browser lief ein vollständiger Ablauf mit einem lokalen Testmodell: Startseite anlegen, Folgeauftrag in derselben Sitzung, Vorschau öffnen und Handybreite. Echte NVIDIA- und Ollama-Modelle wurden in dieser Umgebung nicht angesprochen; die Fehlerfälle wurden mit nachgebauten Anbieterantworten geprüft.

Frühere Prüfung (4.58.0):

Der vollständige Backend-Lauf ergab 1.087 bestandene Tests, einen übersprungenen Test und einen Timeout im Live-Wikipedia-Browsertest unter gleichzeitiger Build-Last. Dieser Test bestand beim separaten Wiederholen. Anschließend bestanden 95 gezielte Nachtests und nach der letzten Bildschirmkorrektur nochmals 48 betroffene Tests. Fünf Node-Tests prüfen Aufgabenfreigaben und Monitorwechsel. Desktop- und Mobile-Build waren erfolgreich. Die zehn 3D-Varianten, die mobile Navigation und der Harness wurden im Browser geprüft. Ein synthetisches Lateinbild deckte einen fachlichen Fehler des Vision-Modells auf; die daraufhin getrennte fachliche Prüfung erkannte das AcI-Subjekt korrekt. Das bestätigt dieses Beispiel, nicht die Richtigkeit beliebiger Hausaufgaben.

Es wurden keine Nachrichten an einen echten Telegram-Empfänger gesendet. Kein Live-Modell wurde für einen kostenpflichtigen Coding-Auftrag verwendet. Langzeittests im täglichen Betrieb sowie Tests der installierten Desktop-Version stehen noch aus. Es wird weder Funktionsgleichheit mit Claude Code oder Codex noch vollständige autonome Bedienung aller Desktop-Anwendungen zugesichert.
