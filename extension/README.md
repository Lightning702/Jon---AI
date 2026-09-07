# Jon Browser Extension

Die offizielle Verbindung zwischen deinem Browser und dem Jon, der auf deinem
Rechner läuft. Die Erweiterung enthält keinen zweiten Jon — sie schickt deine
Anfragen an die vorhandene Jon-API und zeigt die Antwort.

Unterstützt werden Chromium-Browser: Chrome, Edge, Brave (Manifest V3).

## Einrichten

1. In Jon: **Einstellungen → Diagnose → Kopplung** öffnen und den Geräte-Schlüssel kopieren.
2. Im Browser `chrome://extensions` öffnen, **Entwicklermodus** einschalten.
3. **Entpackte Erweiterung laden** und diesen Ordner (`extension/`) auswählen.
4. Auf das Jon-Symbol klicken → ⚙ → Adresse (Standard `http://127.0.0.1:8756`)
   und Geräte-Schlüssel eintragen → **Speichern** → **Verbindung testen**.

## Was die Erweiterung kann

Klick auf das Jon-Symbol:

- Diese Seite zusammenfassen
- Diese Seite erklären
- Recherchiere dieses Thema
- Text verbessern (markierten Text)
- Zu Wissen hinzufügen (Jons Wissensbasis)
- In Projekt speichern (Jon Projects)
- Mit Jon öffnen
- Freies Fragen im Eingabefeld

Rechtsklick auf eine Seite oder markierten Text → **Mit Jon …**:

- Erklären · Zusammenfassen · Übersetzen · Recherchieren · Zu Jon senden ·
  Zu Projekt hinzufügen · Als Notiz speichern

## Datenschutz

- Kein dauerhaftes Content-Script: Seiteninhalte werden nur gelesen, wenn du
  eine Aktion auslöst oder das Popup öffnest (abschaltbar in den Einstellungen).
- Übertragen werden nur URL, Titel, Metadaten, markierter Text und der sichtbare
  Hauptinhalt der aktuellen Seite.
- Es werden keine Passwörter, keine API-Schlüssel und keine Zugangsdaten im
  Erweiterungscode gespeichert. Der Geräte-Schlüssel liegt ausschließlich im
  lokalen Speicher dieses Browsers.
- Im Chat nutzt die Erweiterung nur Jons Gast-Werkzeuge (z. B. Websuche); sie
  darf keine Dateien oder Systembefehle auf deinem Rechner auslösen.
