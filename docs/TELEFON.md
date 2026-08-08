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

## Einrichtung Schritt für Schritt

In Jon: **Werkzeuge → 📞 Telefonanrufe → Einrichtung**. Dort stehen deine echten Werte
und eine Ampel für jeden Baustein. Diese Anleitung erklärt jeden Schritt genau.

### 1. Die richtige Serveradresse wählen

**Das ist der häufigste Stolperstein.** Ein PC hat meist mehrere Netzwerkadressen —
WLAN, LAN, dazu virtuelle Adapter von VirtualBox oder Hyper-V und VPN-Tunnel. Dein Handy
erreicht **nur** die Adresse aus dem Netz, in dem es selbst hängt.

Läuft auf dem PC ein VPN (Proton, NordVPN, Mullvad …), ist dessen Adresse die
„Standardroute" — und genau die ist für dein Handy **wertlos**.

Im Einrichtungs-Tab stehen deshalb alle gefundenen Adressen zur Auswahl. Jon markiert
selbst die richtige, VPN- und virtuelle Adapter sind als *„vom Handy nicht erreichbar"*
gekennzeichnet. Nimm die Adresse deines **WLAN**-Adapters.

> **Tipp:** Diese Adresse kommt vom Router per DHCP und kann sich nach einem Neustart
> ändern. Dann klingelt nichts mehr. Vergib im Router eine feste Adresse für deinen PC
> (oft „DHCP-Reservierung" oder „statische Zuordnung").

### 2. Firewall öffnen

Windows blockt eingehende UDP-Pakete stillschweigend — kein Fehler, es passiert
einfach nichts. Besonders streng ist es, wenn dein WLAN als **öffentliches Netzwerk**
eingestuft ist.

Der Einrichtungs-Tab zeigt den passenden Befehl mit Kopierknopf. Führe ihn in
**PowerShell als Administrator** aus:

```powershell
New-NetFirewallRule -DisplayName "Jon Telefon (SIP)" -Direction Inbound -Protocol UDP -LocalPort 5060 -Action Allow -Profile Any
```

Für den Sprachkanal zusätzlich:

```powershell
New-NetFirewallRule -DisplayName "Jon Telefon (RTP)" -Direction Inbound -Protocol UDP -LocalPort 16384-32768 -Action Allow -Profile Any
```

`-Profile Any` ist wichtig: ohne das gilt die Regel nur im privaten Profil, und dein
WLAN läuft womöglich als öffentlich.

### 3. App aufs Handy

[Linphone](https://f-droid.org/packages/org.linphone/) — quelloffen und kostenlos, in
F-Droid und im Play Store.

### 4. Konto in Linphone eintragen

Beim ersten Start: **Assistent → „SIP-Konto verwenden"** (nicht „Konto erstellen"!).
Läuft der Assistent nicht mehr: *Menü → Einstellungen → Konten → Konto hinzufügen*.

| Feld in Linphone | Was hinein muss |
|---|---|
| **Benutzername** | `jon-phone` |
| **Passwort** | das lange Passwort aus dem Einrichtungs-Tab |
| **Domain** | die gewählte Adresse **mit Port**, z. B. `10.0.0.253:5060` |
| **Anzeigename** | frei, z. B. `Jon` |
| **Transport** | **UDP** |

Ist die Verbindung da, zeigt Linphone oben **„Verbunden"** in Grün — und in Jon springt
die Ampel **Handy** auf 🟢.

### 5. Android am Einschlafen hindern

Android schläfert Hintergrund-Apps ein; dann klingelt es nicht. Zwei Einstellungen:

- **Akku:** *Android-Einstellungen → Apps → Linphone → Akku → „Nicht optimiert"* bzw.
  „Uneingeschränkt".
- **Linphone:** *Einstellungen → Netzwerk* → „Dienst im Vordergrund" aktivieren.

### 6. Testanruf

In Jon auf **Testanruf**. Dein Handy muss klingeln, und nach dem Abheben sagt Jon:

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

### Linphone bleibt auf „Verbindung wird hergestellt"

Das heißt: Die Pakete kommen bei Jon nicht an. In dieser Reihenfolge prüfen —

1. **Erreicht dein Handy den PC überhaupt?** Im Handy-Browser
   `http://<Adresse>:8756/api/health` aufrufen. Kommt dort nichts, ist es das Netzwerk,
   nicht die Telefonfunktion: gleiches WLAN? Gast-WLAN? Manche Router trennen Geräte
   voneinander („AP-Isolation" oder „Client-Isolation") — das muss aus.
2. **Stimmt die Adresse?** Steht im Einrichtungs-Tab noch eine VPN-Adresse (`10.2.x.x`
   bei Proton) oder eine virtuelle (`192.168.56.x` von VirtualBox, `172.30.x.x` von
   Hyper-V), dann die WLAN-Adresse auswählen.
3. **Firewall?** Der Befehl aus Schritt 2 — mit `-Profile Any`.
4. **Läuft der Dienst?** Ampel *SIP* im Modal. Auf dem PC gegenprüfen:
   `Get-NetUDPEndpoint -LocalPort 5060`.
5. **Passwort exakt?** Es enthält Groß- und Kleinbuchstaben, Ziffern, Binde- und
   Unterstriche. Autokorrektur des Handys schreibt gern den ersten Buchstaben groß.
   Notfalls im Tab ein neues erzeugen.

### Es klingelt, aber niemand hört etwas

SIP steht dann, nur der Sprachkanal (RTP) kommt nicht durch: die RTP-Firewallregel für
UDP 16384–32768 aus Schritt 2 fehlt.

Klingelt das Handy gar nicht, obwohl es angemeldet ist: In Linphone unter
*Einstellungen → Netzwerk* prüfen, ob Push aktiv ist, und die App von der
Akku-Optimierung ausnehmen. Android schläfert sonst den SIP-Dienst ein.
