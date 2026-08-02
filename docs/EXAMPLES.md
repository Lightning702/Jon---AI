# Beispiele & Rezepte

Konkrete Dinge, die du Jon sagen kannst.

## Dateien & Ordner

- „Erstelle einen Ordner `Projekte\Website` und leg darin eine leere `index.html` an."
- „Suche alle PDFs in meinem Downloads-Ordner."
- „Pack meinen Ordner `Fotos` in ein ZIP auf den Desktop."
- „Lies die Datei `notizen.txt` und fasse sie zusammen."

## System

- „Welche Prozesse verbrauchen am meisten Speicher?"
- „Zeig mir meine Systeminfos."
- „Sperr den Bildschirm."
- „Was ist gerade in meiner Zwischenablage?"

## Ollama (lokale Modelle)

Einrichten im Zahnrad-Menü unter **Ollama** — die komplette Anleitung steht in
[OLLAMA.md](OLLAMA.md).

- Ollama auf demselben PC: Host `127.0.0.1`, Port `11434` — Voreinstellung, nichts zu tun.
- Ollama auf dem Rechner im Arbeitszimmer: Host `192.168.1.50`, Port `11434`, vorher dort
  `OLLAMA_HOST=0.0.0.0` setzen und den Port freigeben.
- Ollama über Tailscale vom Laptop aus: Host `100.x.x.x` (aus `tailscale ip -4`), Port
  `11434`.
- Modell nachinstallieren (auf dem Server): `ollama pull qwen2.5-coder:7b`, danach in Jon
  auf **Neu laden**.
- Sofort-Antworten ohne Ladezeit: **Keep Alive** auf `30m` stellen.
- Immer gleiche Antwort auf dieselbe Frage: **Seed** auf z. B. `42` und **Temperatur** auf
  `0`.
- Langes Dokument zusammenfassen lassen: **Context Length** auf `16384` erhöhen (kostet
  Speicher).
- Kurze, sachliche Antworten: **System Prompt** auf „Antworte kurz, sachlich und ohne
  Einleitung."

Server freigeben und mitbenutzen:

- Freigeben: **Serverfreigabe** einschalten, Sichtbarkeit **Öffentlich**, Code `AB39KD12`
  weitergeben.
- Nur für bestimmte Leute: Sichtbarkeit **Nur Eingeladene**, dann pro Person eine
  Einladung erstellen — jede gilt einmal.
- Verbinden: Beim anderen unter **Freigegebene Server nutzen** `AB39KD12` eintragen (im
  Heimnetz) oder `AB39KD12@192.168.1.50:8758` (über Tailscale oder von außerhalb).
- Danach im Chat Anbieter `ollama` wählen und unter „Freigabe AB39KD12" das Modell nehmen.
- Zugriff beenden: beim Benutzer auf **entfernen** oder **Allen Zugriff entziehen**.

Über die API geht dasselbe:

```bash
curl -X PUT http://127.0.0.1:8756/api/ollama/config   -H "Content-Type: application/json"   -d '{"url":"http://192.168.1.50:11434","model":"llama3.2","keep_alive":"30m"}'

curl -X POST http://127.0.0.1:8756/api/ollama/test

curl -X PUT http://127.0.0.1:8756/api/ollama/share   -H "Content-Type: application/json"   -d '{"enabled":true,"visibility":"public","name":"Werkstatt-PC"}'

curl -X POST http://127.0.0.1:8756/api/ollama/remote   -H "Content-Type: application/json"   -d '{"code":"AB39KD12@192.168.1.50:8758"}'
```

## Web & Recherche

- „Ruf die Wetterseite ab und sag mir die Aussichten für morgen." (nutzt `http_get`)
- „Lade dieses Bild herunter und speichere es auf dem Desktop."
- „Öffne YouTube und suche nach Lofi-Musik."

## Websites bauen (Skill web-design)

- „Bau mir eine moderne Landing-Page für einen Kaffeeladen, dunkles Design."

Jon liest zuerst den Skill `web-design`, schreibt eine vollständige `index.html` mit
eingebettetem CSS und öffnet sie im Browser.

## Präsentationen (Skill powerpoint)

- „Mach mir eine Präsentation über den Klimawandel, 10 Folien."
- „Bau ein Pitch-Deck für meine App-Idee, Farbwelt teal."
- „Fass die Präsentation auf dem Desktop zusammen." (nutzt `read_pptx`)

Jon liest den Skill `powerpoint`, plant die Folien, ruft `create_pptx` auf und öffnet die
fertige `.pptx` — mit Titelfolie, wechselnden Layouts, Kennzahlen und Sprechernotizen.

## Coden im Projektordner (Jon Code)

- „Schreib mir in index.html ein Login-Formular." → landet direkt in dieser Datei
- „Mach den Header schöner." → gilt für die Datei, die gerade im Editor offen ist
- „/goal Baue eine Suchfunktion ein und lass die Tests laufen."

Jon arbeitet ausschließlich im geöffneten Ordner; Pfade und Shell-Sprünge nach draußen
werden blockiert.

## Automatisierung

- „Öffne WhatsApp und schreib meiner Schwester, dass ich später komme."
- „Mach einen Screenshot und beschreib mir, was auf dem Bildschirm ist."

## Gedächtnis

- „Merk dir, dass mein Bruder Max heißt."
- „Was weißt du über mich?"

## Konten & Nutzung

- Tippe `/konten`, um Anbieter per API-Key zu verbinden.
- Tippe `/usage`, um deinen Token-Verbrauch zu sehen.
- Tippe `/skills`, um Anleitungen zu bearbeiten.

## Handy

- „Öffne die Kamera." · „Teile diesen Text mit meinen Freunden." · „Lies mir das vor."
- Foto anhängen und fragen: „Was steht auf diesem Schild?"
