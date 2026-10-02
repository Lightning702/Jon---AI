# Jon Gerät veröffentlichen

Die Android-App „Jon Gerät“ liegt im Android-Projekt `C:\Users\felix\AndroidStudioProjects\Jon`,
Modul `device-app`, Paket `at.felworks.jon.device`. Es gibt zwei Varianten:

| Variante | Wofür | Besonderheit |
|---|---|---|
| `direkt` | APK zum Selbstinstallieren (eigene Handys, Download über Jon am PC/Pi) | darf sich selbst aktualisieren, nur arm64 und x86_64 |
| `play` | App Bundle für Google Play | ohne `REQUEST_INSTALL_PACKAGES`, keine Selbst-Updates |

## Bauen

```bash
./gradlew :device-app:jonAusgabe
```

Ergebnis in `device-app/ausgabe/`:

- `Jon-Geraet-<version>.apk` – signierte APK (Variante direkt)
- `Jon-Geraet-<version>-play.aab` – signiertes App Bundle für Google Play
- `SHA256SUMS.txt` und `jon-geraet.json` – Prüfsummen und Versionsangaben für das Update über Jon

Signiert wird mit dem Schlüssel aus `~/.android/jon-device-signing.properties`
(Schlüsselspeicher `~/.android/jon-device-release.jks`). **Diesen Schlüssel sicher aufbewahren** –
ohne ihn lassen sich installierte Apps nicht mehr aktualisieren. Bei Google Play dient er als
Upload-Schlüssel (Play App Signing aktivieren).

## Automatisch über GitHub bauen

Das Android-Projekt enthält `.github/workflows/jon-geraet.yml`. So nutzt du es:

1. Ein **privates** GitHub-Repository für das Android-Projekt anlegen und das Projekt hochladen
   (die `.gitignore` hält Schlüssel, Builds und `local.properties` heraus).
2. Unter *Settings → Secrets and variables → Actions* vier Secrets anlegen:
   - `JON_GERAET_KEYSTORE_BASE64` – der Schlüsselspeicher als Base64
     (`base64 -w0 ~/.android/jon-device-release.jks`)
   - `JON_GERAET_STORE_PASSWORD`, `JON_GERAET_KEY_ALIAS`, `JON_GERAET_KEY_PASSWORD` – die Werte aus
     `jon-device-signing.properties`
3. Einen Tag wie `geraet-v1.4.1` pushen. Der Workflow testet, baut APK und App Bundle und hängt
   beides an ein GitHub-Release.

## Angaben für Google Play

### Datensicherheit

| Frage | Antwort |
|---|---|
| Werden Daten an Dritte weitergegeben? | Nur an Dienste, die der Nutzer selbst wählt (KI-Anbieter mit eigenem Schlüssel, eigener PC/Pi). FelWorks erhält nichts. |
| Werden Daten erhoben? | Die App verarbeitet Nachrichten, Audio (Sprache), Fotos, Dateien, App-Aktivität (Bildschirmzeit), Fitnessdaten (Schritte) und – nur beim SOS und nur wenn eingeschaltet – den ungefähren/genauen Standort. |
| Verschlüsselung bei der Übertragung | Ja (TLS zu KI-Anbietern, AES-256-GCM Ende-zu-Ende zum eigenen PC/Pi) |
| Kann der Nutzer die Löschung verlangen? | Ja – Einstellungen → Datenschutz → „Alle Daten löschen“ |
| Konto erforderlich? | Nein |

Datenschutzerklärung: `https://getjon.info/datenschutz-app` (Datei `website/datenschutz-app.html`).

### Berechtigungen, die Google begründet haben möchte

| Berechtigung | Begründung |
|---|---|
| `USE_EXACT_ALARM` | Die App enthält einen Wecker und Timer (Uhr-Funktion). |
| `PACKAGE_USAGE_STATS` | Kindersicherung: Bildschirmzeit und Tageslimits für freigegebene Apps. |
| `FOREGROUND_SERVICE_MICROPHONE` | Sprachassistent („Hey Jon“ und Gespräche) während der Nutzung. |
| `FOREGROUND_SERVICE_MEDIA_PLAYBACK` | Wecker-, Timer- und Suchton, Vorlesen. |
| `FOREGROUND_SERVICE_REMOTE_MESSAGING` | Benachrichtigungen aus Jon Chat und von Jon am PC/Pi im Hintergrund. |
| `ACTIVITY_RECOGNITION` | Schrittzähler im Fitness-Tagebuch. |
| `ACCESS_FINE_LOCATION` | Nur für den SOS-Knopf, nur wenn eingeschaltet, nie im Hintergrund. |
| `CALL_PHONE` | Optionaler Anruf bei einer Vertrauensperson nach einem SOS. |
| Geräteadministrator / Device Owner | Kiosk-Modus der Kindersicherung, wird von Eltern bewusst eingerichtet. |
| Benachrichtigungszugriff | Mediensteuerung von Amazon Music auf Wunsch. |

### Zielgruppe

Jon ist ein Assistent für alle Altersgruppen mit Kindersicherung. Für die Play-Einstufung
„ab 13 Jahren“ wählen; wer die App ausdrücklich für Kinder anbietet, muss zusätzlich die
Familien-Richtlinien von Google Play erfüllen.
