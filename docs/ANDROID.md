# Handy-App (Android/PWA)

Die Handy-App liegt unter `website/app/` und läuft als installierbare PWA im Browser:
[getjon.netlify.app/app](https://getjon.netlify.app/app/). Sie braucht kein Backend — sie
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

Eine native Android-App mit erweiterten (offiziell erlaubten) Intents ist in der
[Roadmap](ROADMAP.md) vorgesehen.

## CORS-Hinweis

Manche Provider blockieren direkte Browser-Aufrufe (CORS). NVIDIA läuft über einen
Netlify-Proxy (`/nvidia/*`). OpenAI, Gemini, GLM, DeepSeek, Qwen und Mistral funktionieren
direkt. Bei „Verbindung fehlgeschlagen" einen dieser Provider wählen.
