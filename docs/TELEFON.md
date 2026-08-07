# Jon ruft dich an

Jon kann dein Handy anrufen: es klingelt wie ein normaler Anruf, du nimmst ab, und dann
redet ihr. Kein Twilio, kein Anbieter, keine Kosten pro Anruf — der Anruf läuft über SIP
direkt aus Jons Backend über dein eigenes Netz.

## Wie es aufgebaut ist

```
Jon (Backend)                          Android
  Zeitplan  ──► SIP-Registrar ──INVITE──► Linphone   📞 klingelt
                     │                        │
                RTP 8 kHz  ◄──── Sprache ─────┘
                     │
   faster-whisper ──► Jons Sprachmodell ──► edge-tts ──► RTP
```

Jon ist selbst die Telefonanlage. Dein Handy meldet sich bei Jon an (SIP-REGISTER mit
Digest-Authentifizierung), Jon schickt zum geplanten Zeitpunkt ein INVITE, das Handy
klingelt. Nach dem Abheben laufen Sprachpakete (RTP, G.711) in beide Richtungen.

**Warum kein Asterisk?** Asterisk gibt es für Windows nicht. Es bräuchte WSL2 oder
Docker, und beides steckt hinter einem NAT-Netz, durch das SIP und vor allem die
dynamischen RTP-Ports nur mit Portproxy- und Firewall-Basteleien kommen. Der eingebaute
Stack startet einfach mit dem Backend mit.

## Einrichtung

In Jon: **Werkzeuge → 📞 Telefonanrufe → Einrichtung**. Dort stehen alle Werte, die du
brauchst, und eine Ampel zeigt, was noch fehlt.

### 1. App aufs Handy

[Linphone](https://f-droid.org/packages/org.linphone/) — quelloffen, kostenlos, in
F-Droid und im Play Store.

### 2. Konto eintragen

| Feld | Wert |
|---|---|
| Benutzername | `jon-phone` (steht im Einrichtungs-Tab) |
| Passwort | wird von Jon erzeugt, im Tab ablesbar |
| Domain / Server | die IP deines PCs, z. B. `192.168.0.42:5060` |
| Transport | UDP |

In Linphone: *Assistent → SIP-Konto verwenden*. Benutzername, Passwort und Domain
eintragen, Transport auf UDP.

### 3. Telefonfunktion einschalten

Im Modal oben den Schalter **Eingeschaltet** setzen. Jon öffnet dann Port 5060/UDP.
Beim ersten Mal fragt die Windows-Firewall — **Zugriff zulassen** für private Netzwerke.

### 4. Testanruf

Knopf **Testanruf**. Dein Handy muss klingeln, und nach dem Abheben sagt Jon:

> „Hey Felix! Das ist ein Testanruf von Jon. Deine Telefonfunktion funktioniert."

## Anrufe planen

Per Sprache oder Chat:

- „Jon, ruf mich jetzt an."
- „Jon, ruf mich in 10 Minuten an."
- „Ruf mich heute um 18 Uhr an."
- „Ruf mich morgen um 9 Uhr an."
- „Ruf mich jeden Montag um 18 Uhr an."
- „Welche Anrufe sind geplant?"
- „Lösch meinen Anruf um 18 Uhr."
- „Ändere den Anruf auf 19 Uhr."

Oder von Hand im Modal unter **Geplante Anrufe**.

Zeitpunkte werden mit Zeitzone gespeichert (Standard `Europe/Vienna`), Sommer- und
Winterzeit sind damit abgedeckt. Geplante Anrufe überleben einen Neustart — sie liegen in
`data/phone_calls.json`.

## Nicht im selben WLAN

Den SIP-Port **nicht** im Router freigeben. Stattdessen ein VPN:

1. [Tailscale](https://tailscale.com/download) auf dem PC und auf dem Handy
   installieren, beide mit demselben Konto anmelden.
2. Auf dem PC `tailscale ip -4` — das ergibt eine Adresse wie `100.x.y.z`.
3. Diese Adresse in Jon unter **Einstellungen → phone_advertise_host** eintragen und in
   Linphone als Domain verwenden.

Dann läuft der Anruf verschlüsselt durchs Tailnet, ohne offenen Port nach außen.

## Was im Gespräch passiert

Jon hört durchgehend zu. Eine Sprecherkennung (Energie mit mitlaufendem Grundrauschen)
merkt, wann du zu sprechen aufgehört hast, und schickt erst dann das Stück Audio an
faster-whisper. Die Antwort kommt satzweise aus edge-tts, damit der erste Ton schnell da
ist.

**Unterbrechen geht.** Sagst du „warte", „stopp" oder „Moment", während Jon spricht,
bricht die Sprachausgabe sofort ab und Jon hört zu.

Mit „tschüss", „auf Wiederhören" oder „leg auf" beendet Jon das Gespräch.

## Datenschutz

Audio wird nur im Arbeitsspeicher verarbeitet und nach dem Anruf verworfen. Es wird
**nichts** aufgezeichnet. Ein Gesprächsprotokoll landet nur dann im Verlauf, wenn du
`phone_keep_transcript` einschaltest — standardmäßig ist das aus. Den Verlauf kannst du
jederzeit löschen.

## Sicherheit

- Das SIP-Passwort erzeugt Jon zufällig (24 Zeichen). Klartext-Passwörter gibt es nicht,
  die Anmeldung läuft über Digest (MD5 mit `qop=auth`).
- Jede Anmeldung wird gefordert und geprüft; ein falsches Passwort bekommt 401.
- Nonces laufen nach 5 Minuten ab, damit aufgezeichnete Anmeldungen nicht wiederverwendbar
  sind.
- Jon nimmt **keine** eingehenden Anrufe an (antwortet mit 486) — der Port ist nur zum
  Anmelden und für Jons eigene Anrufe da.
- Standardmäßig lauscht Jon auf allen Schnittstellen im lokalen Netz. Willst du das
  einschränken, setze `phone_bind_host` auf eine feste Adresse.

## Einstellungen

| Schlüssel | Standard | Bedeutung |
|---|---|---|
| `phone_enabled` | `false` | Telefonfunktion an/aus |
| `phone_sip_user` | `jon-phone` | SIP-Benutzername |
| `phone_sip_password` | zufällig | SIP-Passwort |
| `phone_sip_port` | `5060` | SIP-Port (UDP) |
| `phone_bind_host` | `0.0.0.0` | Woran der SIP-Dienst lauscht |
| `phone_advertise_host` | leer | Adresse, die Jon ansagt (für Tailscale) |
| `phone_caller_name` | `Jon` | Name, der auf dem Handy erscheint |
| `phone_timezone` | `Europe/Vienna` | Zeitzone für geplante Anrufe |
| `phone_keep_transcript` | `false` | Gesprächsprotokoll speichern |
| `phone_max_seconds` | `600` | Höchstdauer eines Gesprächs |

## Wenn etwas nicht geht

Der Einrichtungs-Tab zeigt für jeden Baustein eine Ampel. Häufige Fälle:

| Meldung | Ursache |
|---|---|
| Telefon nicht angemeldet | Linphone offline, falsches Passwort oder falsche Server-Adresse |
| SIP-Port belegt | Ein anderes Programm hat 5060 — `phone_sip_port` ändern |
| Spracherkennung fehlt | `pip install faster-whisper` |
| Sprachausgabe fehlt | ffmpeg fehlt im PATH |
| Es wurde nicht abgenommen | Handy stumm, oder Linphone läuft im Hintergrund nicht |

Klingelt das Handy gar nicht, obwohl es angemeldet ist: In Linphone unter
*Einstellungen → Netzwerk* prüfen, ob Push aktiv ist, und die App von der
Akku-Optimierung ausnehmen. Android schläfert sonst den SIP-Dienst ein.
