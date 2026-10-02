# Stimmen und Transkripte

In Jon unter Werkzeuge **Stimmen & Transkripte** öffnen. Aufträge laufen im Hintergrund; die App kann währenddessen weiter verwendet werden.

## Audio in Text

Eine MP3 oder andere Audiodatei im Chat anhängen und `/transkript` senden. Alternativ im Medienfenster **Audio → Text** wählen. Unterstützt werden MP3, WAV, M4A, OGG, OPUS, FLAC, AAC, WMA und Videodateien mit Ton. Pro Datei gelten 200 MB und höchstens vier Stunden Aufnahme.

Die gesamte Tonspur wird mit dem lokalen Whisper-Modell transkribiert. Das Windows-Paket enthält dieses Modell. Im Quellcodebetrieb wird es beim ersten Gebrauch heruntergeladen; hierfür ist einmalig Internet nötig. Bei langsamen Rechnern dauern lange Aufnahmen entsprechend länger.

Für einen Pi aus dem Quellcode müssen die aktuellen Abhängigkeiten aus `backend/requirements-pi.txt` in seiner bestehenden Python-Umgebung installiert sein. Ein reines Code-Update installiert keine fehlenden Bibliotheken.

**Vollständiges Transkript herunterladen** liefert die gesamte Textdatei. Bei langen Ergebnissen ist nur die Bildschirmvorschau gekürzt. Die optionale Zusammenfassung übergibt das Transkript abschnittsweise an das eingestellte KI-Modell. Erkennungsfehler können vorkommen.

## YouTube zusammenfassen

Einen YouTube-Videolink im Chat senden oder **YouTube erklären** im Medienfenster wählen. Jon ruft verfügbare manuelle oder automatisch erzeugte Untertitel ab, bevorzugt Deutsch oder Englisch. Die Zusammenfassung entsteht aus diesen Untertiteln. Automatische Untertitel können Fehler enthalten. Fehlen zugängliche Untertitel, meldet Jon das; eine eigene Audiodatei kann dann lokal transkribiert werden.

In diesem Ablauf werden keine Videobilder analysiert. Jons bestehende Bildfunktionen bleiben separat verfügbar. Die vollständigen Untertitel lassen sich im Medienfenster als Text herunterladen.

## Text als Audio

`/podcast Dein vollständiger Text` oder `/tts Dein Text` öffnet die Sprachausgabe und startet die Erstellung einer MP3. Ohne Text öffnet sich das Eingabefenster. **Text → Audio** bietet deutsche und englische Stimmen. Bis zu 80.000 Zeichen werden abschnittsweise gesprochen und in einer MP3 gespeichert.

Der Text wird hierfür an Microsofts Sprachausgabe übermittelt; Internet ist erforderlich. Diese Funktion vertont einen Text oder ein fertiges Podcast-Skript. Für einen Podcast mit zwei Sprechern gibt es außerdem Jons vorhandenes Studio-Werkzeug.

## Mehrere Aufträge

Zwei Medienaufträge können gleichzeitig laufen. Zusätzliche Fachteam- oder Harness-Aufträge bleiben möglich. Ein Harness arbeitet exklusiv in seinem Projektordner, damit zwei Aufträge dieselben Dateien nicht gleichzeitig verändern. Über **Stoppen** wird ein Medienauftrag nach dem aktuellen Abschnitt beendet. Ein Fehler beim Zusammenfassen entfernt ein bereits erstelltes vollständiges Transkript nicht.

Medienaufträge und erzeugte Dateien liegen im lokalen Jon-Datenordner unter `medienauftraege`. Der Zugriff erfolgt über Jons vorhandene Authentifizierung.
