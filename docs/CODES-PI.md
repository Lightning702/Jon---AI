# Admin- und Entwickler-Codes über den Pi

Stand: 4. Oktober 2026, Jon 4.61.1.

Der FelWorks-Codeserver läuft auf deinem Raspberry Pi und vergibt drei Arten von Codes:

| Code | Beginnt mit | Was er freischaltet |
|---|---|---|
| Admin | `ADM-` | Volle Rechte wie dein eigener Admin-Code, auch Codes erzeugen und die Team-Zentrale steuern. |
| Entwickler | `ENT-` | Alles unbegrenzt und die Team-Zentrale für Entwickler, aber keine Codes. In Jon steht oben links „Entwickler“. |
| Premium | `PRE-` | Alle Premium-Funktionen, für 7 Tage, 30 Tage, 3 Monate, 1 Jahr oder für immer ab dem Einlösen. Ohne Team-Zentrale. |

Dein eigener Admin-Code ist der Haupt-Admin und lässt sich nicht sperren. Admin-Codes kannst du jederzeit sperren.

## Team-Zentrale

Admins und Entwickler sehen im Dialog oben links die Team-Zentrale:

| Bereich | Admin | Entwickler |
|---|---|---|
| Codes | erzeugen, umbenennen, Art und Laufzeit ändern, sperren, Geräte entfernen | – |
| Team | Rundschreiben, Antworten, Status für Ideen | Ideen, Fehler und Nachrichten an den Admin oder ans Team, Stimmen für Ideen |
| Fehler melden | – | Version, System, Protokoll ohne Geheimnisse und Bildschirmfoto mit einem Klick |
| Geräte & Nutzung | Geräte, Versionen, Anfragen, Tokens, Modelle, Werkzeuge, FelWorks-Kontingent | – |
| Beta-Schalter | Funktionen für alle oder ausgewählte Entwickler, eigene Schalter | – |
| Pi | Dienste, Neustart, Protokolle, RAM, Platte, Temperatur, Aktualisieren | – |
| Skills | teilen, installieren, entfernen | teilen, installieren, eigene entfernen |
| Inspektor | jede Modellanfrage im Detail | jede Modellanfrage im Detail |
| Einstellungen | Beta-Versionen | Beta-Versionen, Übersicht der Vorteile |

Neue Team-Nachrichten von Entwicklern, neu eingelöste Team-Codes und geteilte Skills meldet dir Jon auf dem Pi per Telegram, wenn dort ein Telegram-Chat verbunden ist.

Der Modellzugang über FelWorks läuft unter `/codes/llm/v1` als OpenAI-kompatible Schnittstelle. Der Pi gibt Anfragen mit seinem eigenen NVIDIA-Schlüssel weiter, der Schlüssel verlässt den Pi nicht. Das Tageskontingent pro Gerät stellst du unter „Geräte & Nutzung“ ein (Standard 300), Admins haben kein Limit.

Weitere Dateien im geheimen Ordner auf dem Pi: `team.json` (Nachrichten), `flags.json` (Beta-Schalter), `statistik.json` (Nutzungszahlen ohne Inhalte), `skills.json` (geteilte Skills) und `llm.json` (Kontingent).

## Benutzen

- Admin werden: In Jon oben links auf „Standard“ → „Schon einen Lizenzschlüssel, Entwickler- oder Admin-Code?“ → Admin-Code eingeben → „Einlösen“.
- Codes erzeugen: Als Admin oben links auf „Admin“ klicken. Ganz oben steht „Entwickler-Codes“. Name eintragen, Anzahl Geräte wählen, „Code erzeugen“. Der Code (`ENT-XXXX-XXXX-XXXX-XXXX-XXXX`) wird genau einmal angezeigt.
- Code einlösen: Auf dem anderen Gerät genauso wie beim Admin-Code, nur mit dem `ENT-…`-Code.
- Admin- und Entwickler-Codes gelten für immer, Premium-Codes so lange wie gewählt. Sperren: In der Liste auf „Sperren“. Das Gerät fällt bei der nächsten Prüfung auf Standard zurück, sobald es online ist. Mit „Freigeben“ geht es wieder.

## Wie Codes geschützt sind

- Im Git und in `jon.zip` steht nur der öffentliche Schlüssel des Pi (`CODE_OEFFENTLICH` in `backend/app/services/premium.py` und `netlify/lib/basis.mjs`). Damit kann man Lizenzen prüfen, aber keine erzeugen.
- Alles Geheime liegt nur auf dem Pi in `~/.local/share/jon-codes/`. Der Ordner hat die Rechte 700, jede Datei 600. Er liegt außerhalb des Jon-Ordners, deshalb landet er nie im Git, in einer Sicherung des Repos oder in `jon.zip`:
  - `schluessel.pem`: privater Ed25519-Signierschlüssel. Er wurde auf dem Pi erzeugt und hat ihn nie verlassen.
  - `admin.json`: nur ein scrypt-Hash des Admin-Codes mit eigenem Salz, nicht der Code selbst.
  - `codes.json`: Entwickler-Codes nur als HMAC-SHA256-Fingerabdruck mit einem geheimen Pfeffer. Dazu Name, letzte vier Zeichen, Geräte und Datum. Den Code selbst sieht nur der Admin einmal beim Erzeugen.
- Ein Code hat 20 Zeichen aus 30 Buchstaben und Ziffern, also etwa 98 Bit Zufall. Raten ist aussichtslos. Zusätzlich bremst der Server: nach 8 falschen Versuchen in 15 Minuten ist für diese Adresse Pause, und insgesamt nimmt er höchstens 120 Fehlversuche pro Stunde an. Jeder Fehlversuch wartet 1,2 Sekunden.
- Wer einen Code einlöst, bekommt eine signierte Lizenz (`JON1.…`) für genau sein Gerät. Jon prüft sie offline mit dem öffentlichen Schlüssel. Admin- und Entwickler-Lizenzen haben kein Ablaufdatum und gelten für immer, auch wenn der Pi nicht erreichbar ist.
- Damit Sperren trotzdem wirken, fragt Jon alle 6 Stunden beim Pi nach. Antwortet der Pi „gesperrt“ oder „Admin-Code geändert“, löscht Jon die Lizenz und läuft als Standard weiter. Ist der Pi nicht erreichbar, bleibt alles, wie es ist.
- Auf anderen Geräten funktioniert das, weil Jon den Pi über die feste Tailscale-Funnel-Adresse `https://felworks.tail661828.ts.net/codes` erreicht, auch außerhalb deines Heimnetzes. Eine andere Adresse setzt man mit der Umgebungsvariable `JON_CODES_URL`.
- Cloud-Sync gilt auch für Admin und Entwickler. Netlify prüft deren Lizenzen mit demselben öffentlichen Schlüssel.

## Einrichten auf dem Pi

```text
ssh felworks@felworks.local
cd ~/Jon---AI
bash scripts/codes-pi-einrichten.sh
```

Das Skript legt den Benutzerdienst `jon-codes` an (Port 8791, nur lokal), fragt beim ersten Mal nach dem Admin-Code und gibt den Server über Tailscale Funnel unter `/codes` frei. Andere Funnel-Pfade bleiben unverändert.

Admin-Code ändern: `cd ~/Jon---AI/backend && .venv/bin/python -m app.codeserver admin` und den neuen Code eingeben. Alte Admin-Lizenzen enden bei der nächsten Prüfung.

Admin-Lizenz für ein Gerät direkt ausstellen, ohne Code: `.venv/bin/python -m app.codeserver lizenz <Geräte-ID>`. Die Geräte-ID steht im Premium-Dialog unter „Lizenz oder Code eingeben“.

## Sichern

Wenn `~/.local/share/jon-codes/schluessel.pem` verloren geht, sind alle Admin- und Entwickler-Lizenzen ungültig und Jon braucht einen neuen öffentlichen Schlüssel. Sichere den Ordner deshalb verschlüsselt, zum Beispiel auf einem USB-Stick, aber nie im Jon-Ordner oder im Git.

## Prüfung

- 10 Python-Tests für den Codeserver: Admin-Code, Codes nur als Hash, Entwickler darf keine Codes erzeugen, Gerätegrenze, Sperren und Freigeben, neuer Admin-Code beendet alte Lizenzen, Bremse gegen Durchprobieren, Dateirechte, Kommandozeile, Ablauf in Jon.
- 1 Node-Test: Netlify nimmt Admin- und Entwickler-Lizenzen vom Pi für den Cloud-Sync an und lehnt fremd signierte ab.
