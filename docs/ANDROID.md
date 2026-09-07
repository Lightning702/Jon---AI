# Handy-App (Android/PWA)

Die Handy-App liegt unter `website/app/` und läuft als installierbare PWA im Browser:
[getjon.info/app](https://getjon.info/app/). Sie braucht kein Backend — sie
spricht die Provider-APIs direkt an. Der API-Key bleibt ausschließlich lokal
(`localStorage`).

## Installieren

Im mobilen Browser „Zum Startbildschirm hinzufügen" wählen. Danach startet Jon wie eine
native App im Vollbild.

## Fähigkeiten

Über echtes Function-Calling kann Jon auf dem Handy:

| Tool | Wirkung | Offizielle Methode |
|------|---------|--------------------|
| `open_app` | App oder Web-Version öffnen | Deep-Links / `wa.me`, `maps.google.com`, … |
| `open_url` | Webseite öffnen | `window.open` |
| `share` | Teilen-Menü öffnen | Web Share API |
| `speak` | Antwort vorlesen | SpeechSynthesis |
| `get_location` | Standort abfragen | Geolocation API (mit Erlaubnis) |
| `get_time` | Uhrzeit/Datum | lokal |
| `http_get` | Web-Inhalt abrufen | `fetch` |

Weitere Bedienelemente:

- **🎤 Spracheingabe** über die Web Speech API (Deutsch)
- **🔊 Vorlesen** aller Antworten (umschaltbar)
- **🖼️ Bildanalyse**: Foto anhängen → an ein Vision-fähiges Modell senden
- **Kamera** öffnen über das Datei-Capture-Feld

## Was aus Sicherheitsgründen nicht geht

Ein Browser darf aus gutem Grund **nicht** auf Kontakte, SMS/WhatsApp-Nachrichten,
Benachrichtigungen, den Kalender oder Dateien anderer Apps zugreifen. Es gibt dafür keine
offizielle Web-Schnittstelle. Jon umgeht das **nicht**, sondern nutzt die bestmögliche
offizielle Alternative — etwa die jeweilige App per Deep-Link öffnen — und sagt ehrlich,
wenn etwas nicht möglich ist.

Die native Jon-App (siehe unten) kann mehr, weil Android dort echte Berechtigungen
vergibt — aber auch sie umgeht nichts.

## CORS-Hinweis

Manche Provider blockieren direkte Browser-Aufrufe (CORS). NVIDIA läuft über einen
Netlify-Proxy (`/nvidia/*`). OpenAI, Gemini, GLM, DeepSeek, Qwen und Mistral funktionieren
direkt. Bei „Verbindung fehlgeschlagen" einen dieser Provider wählen.

---

# Android Connector (native Jon-App)

Neben der PWA gibt es die native Companion-App (`at.felworks.jon`, Kotlin + Compose,
Quellen unter `AndroidStudioProjects/Jon`). Sie ist **kein zweiter Jon**: Die KI und alle
Werkzeuge bleiben auf dem PC. Die App ist die verschlüsselte Brücke zwischen Android und
Jon.

```
Jon PC  ──  AES-GCM über Heimnetz (HTTP) oder Jon-Relay (MQTT)  ──  Jon Companion  ──  Android
```

## Kopplung

1. Am PC: **Einstellungen → 🔌 Verbindungen → 📱 Geräte → „Handy verbinden …“**
2. Jon zeigt einen QR-Code und einen 12-stelligen Tippcode (10 Minuten gültig, einmalig).
3. In der App: **Mit Jon verbinden** → scannen oder tippen.
4. Der PC fragt nach und zeigt Name und Plattform des Handys. Erst nach **Bestätigen am
   PC** bekommt das Handy einen eigenen 32-Byte-Schlüssel und ein eigenes Token.
5. Danach steht das Handy in Jon unter **Geräte** mit Akku, Verbindung, letztem Kontakt
   und allen Berechtigungen.

Details zum Protokoll: [ARCHITECTURE.md](ARCHITECTURE.md) und
`backend/app/services/handy_service.py`.

## Berechtigungsstufen

Jede Funktion braucht **zwei** Freigaben: den Schalter am PC **und** die Android-Berechtigung
am Handy. Fehlt eine, sagt Jon verständlich, welche.

| Stufe | Funktionen | Vorgabe |
|-------|-----------|---------|
| Standard | Gerätestatus, Akku, Dateiübertragung | an |
| Persönlich | Benachrichtigungen, Zwischenablage, Standort, Kontakte | aus |
| Sensibel | Kamera, Mikrofon | aus, zusätzlich Rückfrage am Handy |

Sperren geht von beiden Seiten (PC-Oberfläche oder App → **Verbinder**). Freischalten geht
nur am PC.

## Werkzeuge

Der `AndroidConnector` meldet seine Werkzeuge **dynamisch** an Jons Tool-System an. Die KI
sieht nur, was für mindestens ein Gerät freigegeben ist.

| Tool | Wirkung | Recht |
|------|---------|-------|
| `android_devices` | Gekoppelte Geräte mit Status auflisten | – |
| `android_device_status` | Name, online, Akku, Verbindung, Android-Version, letzter Kontakt | status |
| `android_battery_status` | Akkustand und Ladezustand | status |
| `android_notifications_list` | Offene Benachrichtigungen lesen | hinweise |
| `android_files_list` | Dateien in einem freigegebenen Ordner | dateien |
| `android_files_send` | Datei vom PC aufs Handy (Downloads/Jon) | dateien |
| `android_files_receive` | Datei vom Handy auf den PC | dateien |
| `android_clipboard_send` | Text in die Zwischenablage des Handys | zwischenablage |
| `android_location_get` | Aktueller Standort | standort |
| `android_contacts_search` | Kontakte durchsuchen | kontakte |
| `android_camera_request_photo` | Sichtbare Bitte um ein Foto | kamera |

Beispiele: „Jon, schick die PDF auf mein Handy.“ · „Welche Benachrichtigungen habe ich?“ ·
„Wo ist mein Handy?“ · „Wie voll ist der Akku vom Pixel?“

## Was Android nicht erlaubt — und was Jon stattdessen tut

- **Zwischenablage lesen.** Seit Android 10 darf keine App im Hintergrund die
  Zwischenablage mitlesen. Jon kann deshalb nur *hineinschreiben*. Umgekehrt teilst du
  Inhalte über das normale Teilen-Menü an Jon.
- **Fremde Downloads und Dokumente auflisten.** Unter Scoped Storage sieht die App im
  Download-Ordner nur, was sie selbst abgelegt hat. Fotos, Videos und Musik gehen mit der
  Medien-Berechtigung; alles andere kommt über das Teilen-Menü oder den Dateidialog.
- **Heimlich fotografieren.** Technisch möglich wäre eine stille Aufnahme — Jon macht das
  bewusst **nicht**. `android_camera_request_photo` legt eine sichtbare Anfrage mit
  Begründung auf das Handy; erst nach dem Tippen öffnet sich die Kamera-App. Ohne
  Bestätigung kommt kein Bild. Welche Linse benutzt wird, entscheidet die Kamera-App.
- **Mikrofon aus der Ferne.** Dafür gibt es bewusst **kein** Werkzeug. Sprachaufnahmen
  startest du selbst in der App.
- **SMS und WhatsApp lesen.** Der SMS-Zugriff ist in Google Play stark eingeschränkt und
  für einen Assistenten nicht vorgesehen. Über den Benachrichtigungszugriff siehst du
  eingehende Nachrichten als Hinweis — mehr nicht.
- **Nach dem Neustart des Handys** meldet sich das Gerät erst wieder, wenn die App einmal
  geöffnet wurde: Android 14+ lässt Dauerdienste nicht mehr automatisch beim Systemstart
  loslaufen. Danach hält der Vordergrunddienst („Jon ist verbunden“) die Verbindung.
  Android 15 begrenzt solche Dienste zusätzlich auf 6 Stunden pro Tag.

## Sicherheit

- Ende-zu-Ende verschlüsselt (AES-256-GCM, Schlüssel per HKDF aus dem Kopplungscode),
  auch über das öffentliche Relay.
- Jedes Gerät hat einen eigenen Schlüssel und ein eigenes Token; Trennen am PC entwertet
  beides sofort.
- Der Kopplungscode gilt einmal, zehn Minuten, und wird nach 12 Fehlversuchen gesperrt.
- Auf dem Handy liegt der Zugang im Android Keystore (`security/Tresor.kt`), nie im
  Klartext.
- Die App fordert Android-Berechtigungen erst an, wenn du die Funktion wirklich nutzt.
- Der Vordergrunddienst zeigt dauerhaft an, dass das Handy mit Jon verbunden ist.

## Bauen und testen

```bash
cd AndroidStudioProjects/Jon
gradlew :app:assembleDebug        # APK unter app/build/outputs/apk/debug/
gradlew :app:installDebug         # auf ein angestecktes Handy
```

PC-Seite prüfen:

```bash
cd backend
python -m pytest tests/test_handy.py tests/test_android_connector.py -q
```

Der Test `test_android_connector.py` koppelt ein Gerät, spielt das Handy nach (Ereignis-
Strom + Antworten) und prüft Rechte, Werkzeugsichtbarkeit, Fehlermeldungen und die
Dateiübertragung in Teilen.
