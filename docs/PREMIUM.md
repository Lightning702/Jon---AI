# Jon Premium

Stand: 3. Oktober 2026, Jon 4.58.1.

Jon gibt es in drei Stufen. Welche aktiv ist, steht in der Desktop-App oben links neben „JON“ und am Handy im Chat-Kopf.

| Stufe | Was sie bedeutet |
|---|---|
| Standard | Kostenlos. Chat mit eigenen Modellen, Werkzeuge, Gedächtnis, Kalender, Erinnerungen, Beobachten, MiniJon in der Grundform, Blockwelt. Harness 3 Aufträge und Fachteam 1 Lauf pro Tag. |
| Premium | Abo über Stripe, 6,99 € im Monat oder 59,99 € im Jahr inkl. MwSt. Alles unten ist freigeschaltet, ohne Tageslimit. |
| Admin | Für FelWorks. Alles unbegrenzt. Nur mit dem Admin-Passwort des Lizenzservers erhältlich und an ein Gerät gebunden. |

## Premium-Funktionen

Jon Harness Pro (unbegrenzt, Projektvorschau, Fachagenten), Fachteam ohne Limit, Funke am Handy, Fernsteuerung per Telegram und Handy-App, Deep Learning und Recherche, Studio (Video, Foto, Präsentationen), Stimmen und Transkripte, Bildschirmanalyse, Browser-Agent, MiniJon-Aussehen (zehn Auftritte, 3D, Katze, Hund), Familienpaket (Regeln und Durchsagen für Familiengeräte), Cloud-Sync und Backup, Alltags-Automatisierung (Inbox, Wochenbericht, Routinen, Auslöser) und alle Spiele.

Der Kinderschutz selbst bleibt in jeder Stufe aktiv. Premium betrifft nur das Verwalten mehrerer Familiengeräte.

## Wie die Prüfung funktioniert

- Eine Lizenz ist ein Text der Form `JON1.<Inhalt>.<Signatur>`. Der Inhalt nennt Stufe, Ablaufdatum, Abo und die freigeschalteten Geräte. Die Signatur ist Ed25519.
- Signieren kann nur der Lizenzserver (Netlify-Funktionen unter `netlify/functions`). Der private Schlüssel liegt ausschließlich in der Netlify-Umgebungsvariable `JON_LIZENZ_SCHLUESSEL`, nie im Repo, im Download oder in der App.
- Jon enthält nur den öffentlichen Schlüssel (`backend/app/services/premium.py`). Damit kann Jon prüfen, aber keine Lizenz erzeugen. Wer den Inhalt verändert, zum Beispiel `premium` in `admin`, macht die Signatur ungültig, und Jon bleibt Standard.
- Jede Lizenz ist an Geräte gebunden. Die Geräte-ID ist ein Hash der Windows-MachineGuid beziehungsweise `/etc/machine-id`. Ein Abo gilt auf bis zu drei Geräten. Die Liste steht in den Metadaten des Stripe-Abos.
- Premium-Lizenzen laufen sieben Tage nach dem Ende der bezahlten Periode ab. Jon erneuert sie im Hintergrund, solange das Abo aktiv ist. Ohne Internet läuft Premium bis zum Ablaufdatum weiter.
- Admin-Lizenzen stellt die Funktion `premium-admin` nur gegen das richtige Passwort aus (`JON_ADMIN_PASSWORT`, mindestens 12 Zeichen, Vergleich in konstanter Zeit, 1,5 Sekunden Pause bei falschem Passwort). Sie gelten 90 Tage und erneuern sich automatisch. Ein neues Passwort beendet alle alten Admin-Lizenzen bei der nächsten Erneuerung.
- Gesperrt wird im Backend an den zentralen Stellen: beim Ausführen von Chat-Werkzeugen, beim Start von Harness, Fachteam, Recherche, Studio und Medien, bei der Bildschirmanalyse, für Telegram, für Fernbefehle vom Handy und in den Routen. Die Desktop-App bekommt dann HTTP 402 und öffnet den Premium-Dialog, Telegram und Chat bekommen eine freundliche Meldung.

Ehrlich gesagt: Jon läuft lokal, und der Quellcode liegt offen im Download. Die Signatur verhindert gefälschte Lizenzen, aber wer den Code selbst umschreibt, kann die Prüfung entfernen. Wirklich nicht umgehbar sind nur Funktionen, die auf einem Server laufen, etwa der Cloud-Sync.

## Kaufen

In Jon: oben links auf „Standard“ → Tarif wählen → „Premium holen“. Stripe Checkout öffnet sich im Browser. Jon fragt alle drei Sekunden beim Lizenzserver nach und schaltet sich nach der Zahlung selbst frei.

Auf der Website: `getjon.info/premium/`. Nach der Zahlung zeigt die Dankesseite den Lizenzschlüssel. In Jon unter „Lizenz eingeben oder Admin“ einfügen.

Stripe übernimmt Zahlung (Checkout im Abo-Modus), Rechnungen (jede Abo-Zahlung erzeugt eine Rechnung, Kundenportal mit Rechnungsverlauf) und Steuer (Stripe Tax mit `automatic_tax`, Preise inklusive MwSt., Steuer-ID-Abfrage für Firmen). Das Produkt „Jon Premium“ und beide Preise legt der Lizenzserver beim ersten Kauf selbst an (Lookup-Keys `jon_premium_monat` und `jon_premium_jahr`).

## Einrichten

1. In Netlify (Site getjon) die Umgebungsvariablen `STRIPE_SECRET_KEY`, `JON_LIZENZ_SCHLUESSEL` und `JON_ADMIN_PASSWORT` setzen und neu veröffentlichen.
2. Im Stripe-Dashboard Stripe Tax mit Firmenadresse aktivieren, das Kundenportal einmal speichern und Rechnungs-E-Mails einschalten.
3. Testkauf mit der Karte 4242 4242 4242 4242.
4. Für Live: einen Restricted Key mit Rechten für Products, Prices, Checkout Sessions, Subscriptions, Customer Portal und Customers anlegen und als `STRIPE_SECRET_KEY` eintragen.

Den Schlüssel neu erzeugen: `python scripts/lizenz-schluessel.py`. Der öffentliche Teil gehört dann nach `OEFFENTLICH` in `backend/app/services/premium.py`, der private nach Netlify. Alte Lizenzen werden damit ungültig.

## Cloud-Sync

Premium-Nutzer sichern Gedächtnis, Persona, Alltagsgedächtnis und Einstellungen (ohne Passwörter, Tokens und gerätebezogene Werte) über den Premium-Dialog. Jon verschlüsselt das Paket auf dem Gerät mit AES-256-GCM. Der Schlüssel wird mit scrypt aus deinem Sicherungspasswort abgeleitet. Der Server (Netlify Blobs, höchstens 4 MB) sieht nur verschlüsselte Daten. Beim Holen werden Einstellungen übernommen und nur neue Erinnerungen ergänzt.

## Prüfung

Bestanden sind:
- 8 Node-Tests für die Lizenzfunktionen gegen einen nachgebauten Stripe-Server: Checkout mit Stripe Tax, Lizenz erst nach Zahlung, gefälschte Lizenzen, Erneuerung, Gerätelimit, Admin-Passwort, Kundenportal, Cloud-Sicherung.
- 11 Lizenz-, 5 Sperr- und 3 Sync-Tests in Python.
- Ein Test, dass eine von Node signierte Lizenz in Python erkannt wird.

Der echte Stripe-Server und das echte Netlify wurden aus der Entwicklungsumgebung nicht erreicht. Der erste echte Testkauf steht noch aus.
