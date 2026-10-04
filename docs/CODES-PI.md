# Admin- und Entwickler-Codes über den Pi

Stand: 4. Oktober 2026, Jon 4.59.1.

Der FelWorks-Codeserver läuft auf deinem Raspberry Pi und vergibt zwei Stufen:

| Stufe | Wer | Was |
|---|---|---|
| Admin | du, mit dem Admin-Code | Alles unbegrenzt. Im Premium-Dialog erzeugst und sperrst du Entwickler-Codes. |
| Entwickler | wer einen Entwickler-Code von dir bekommt | Alles unbegrenzt wie Admin, aber keine Codes erzeugen. In Jon steht oben links „Entwickler“. |

## Benutzen

- Admin werden: In Jon oben links auf „Standard“ → „Schon einen Lizenzschlüssel, Entwickler- oder Admin-Code?“ → Admin-Code eingeben → „Einlösen“.
- Codes erzeugen: Als Admin oben links auf „Admin“ klicken. Ganz oben steht „Entwickler-Codes“. Name eintragen, Anzahl Geräte wählen, „Code erzeugen“. Der Code (`ENT-XXXX-XXXX-XXXX-XXXX-XXXX`) wird genau einmal angezeigt.
- Code einlösen: Auf dem anderen Gerät genauso wie beim Admin-Code, nur mit dem `ENT-…`-Code.
- Sperren: In der Liste auf „Sperren“. Das Gerät fällt bei der nächsten Erneuerung auf Standard zurück, spätestens nach 14 Tagen. Mit „Freigeben“ geht es wieder.

## Wie Codes geschützt sind

- Im Git und in `jon.zip` steht nur der öffentliche Schlüssel des Pi (`CODE_OEFFENTLICH` in `backend/app/services/premium.py` und `netlify/lib/basis.mjs`). Damit kann man Lizenzen prüfen, aber keine erzeugen.
- Alles Geheime liegt nur auf dem Pi in `~/.local/share/jon-codes/`. Der Ordner hat die Rechte 700, jede Datei 600. Er liegt außerhalb des Jon-Ordners, deshalb landet er nie im Git, in einer Sicherung des Repos oder in `jon.zip`:
  - `schluessel.pem`: privater Ed25519-Signierschlüssel. Er wurde auf dem Pi erzeugt und hat ihn nie verlassen.
  - `admin.json`: nur ein scrypt-Hash des Admin-Codes mit eigenem Salz, nicht der Code selbst.
  - `codes.json`: Entwickler-Codes nur als HMAC-SHA256-Fingerabdruck mit einem geheimen Pfeffer. Dazu Name, letzte vier Zeichen, Geräte und Datum. Den Code selbst sieht nur der Admin einmal beim Erzeugen.
- Ein Code hat 20 Zeichen aus 30 Buchstaben und Ziffern, also etwa 98 Bit Zufall. Raten ist aussichtslos. Zusätzlich bremst der Server: nach 8 falschen Versuchen in 15 Minuten ist für diese Adresse Pause, und insgesamt nimmt er höchstens 120 Fehlversuche pro Stunde an. Jeder Fehlversuch wartet 1,2 Sekunden.
- Wer einen Code einlöst, bekommt eine signierte Lizenz (`JON1.…`) für genau sein Gerät. Jon prüft sie offline mit dem öffentlichen Schlüssel. Admin-Lizenzen gelten 90 Tage, Entwickler-Lizenzen 14 Tage, beide erneuern sich automatisch über den Pi.
- Auf anderen Geräten funktioniert das, weil Jon den Pi über die feste Tailscale-Funnel-Adresse `https://felworks.tail661828.ts.net/codes` erreicht, auch außerhalb deines Heimnetzes. Eine andere Adresse setzt man mit der Umgebungsvariable `JON_CODES_URL`.
- Cloud-Sync gilt auch für Admin und Entwickler. Netlify prüft deren Lizenzen mit demselben öffentlichen Schlüssel.

## Einrichten auf dem Pi

```text
ssh felworks@felworks.local
cd ~/Jon---AI
bash scripts/codes-pi-einrichten.sh
```

Das Skript legt den Benutzerdienst `jon-codes` an (Port 8791, nur lokal), fragt beim ersten Mal nach dem Admin-Code und gibt den Server über Tailscale Funnel unter `/codes` frei. Andere Funnel-Pfade bleiben unverändert.

Admin-Code ändern: `cd ~/Jon---AI/backend && .venv/bin/python -m app.codeserver admin` und den neuen Code eingeben. Alte Admin-Lizenzen enden bei der nächsten Erneuerung.

Admin-Lizenz für ein Gerät direkt ausstellen, ohne Code: `.venv/bin/python -m app.codeserver lizenz <Geräte-ID>`. Die Geräte-ID steht im Premium-Dialog unter „Lizenz oder Code eingeben“.

## Sichern

Wenn `~/.local/share/jon-codes/schluessel.pem` verloren geht, sind alle Admin- und Entwickler-Lizenzen ungültig und Jon braucht einen neuen öffentlichen Schlüssel. Sichere den Ordner deshalb verschlüsselt, zum Beispiel auf einem USB-Stick, aber nie im Jon-Ordner oder im Git.

## Prüfung

- 10 Python-Tests für den Codeserver: Admin-Code, Codes nur als Hash, Entwickler darf keine Codes erzeugen, Gerätegrenze, Sperren und Freigeben, neuer Admin-Code beendet alte Lizenzen, Bremse gegen Durchprobieren, Dateirechte, Kommandozeile, Ablauf in Jon.
- 1 Node-Test: Netlify nimmt Admin- und Entwickler-Lizenzen vom Pi für den Cloud-Sync an und lehnt fremd signierte ab.
