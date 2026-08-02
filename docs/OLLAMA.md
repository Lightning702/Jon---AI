# Ollama in Jon

Jon kann seine Antworten komplett auf deinem eigenen Rechner erzeugen — ohne API-Schlüssel,
ohne Konto, ohne Cloud. Dafür sorgt **Ollama**. Der Server darf auf demselben PC laufen,
auf einem zweiten Rechner im Heimnetz, auf einem Server im Keller oder über **Tailscale**
auf einer Maschine ganz woanders.

Alles, was Jon mit Ollama austauscht, läuft über die **offizielle Ollama-API**
(`/api/chat`, `/api/tags`, `/api/version`).

---

## Was ist Ollama?

Ollama ist ein kleines, kostenloses Programm, das große Sprachmodelle auf deiner eigenen
Hardware ausführt. Du lädst ein Modell einmal herunter (`ollama pull llama3.2`) und kannst
es danach beliebig oft nutzen:

- **Kostenlos** — keine Token, keine Rechnung, kein Limit.
- **Privat** — kein Text verlässt deinen Rechner oder dein Netzwerk.
- **Offline** — funktioniert ohne Internet, sobald das Modell geladen ist.

Der Preis dafür: Die Antworten kommen aus deiner eigenen Grafikkarte bzw. CPU. Kleine
Modelle sind blitzschnell, große brauchen entsprechend Speicher.

## Voraussetzungen

| | Minimum | Empfohlen |
|---|---|---|
| Arbeitsspeicher | 8 GB | 16 GB und mehr |
| Grafikspeicher | keiner (läuft auf der CPU) | 8 GB VRAM und mehr |
| Festplatte | 2 GB je kleinem Modell | 20 GB und mehr |
| Betriebssystem | Windows 10/11, macOS, Linux | — |

Faustregel: Ein Modell braucht ungefähr so viel Speicher wie seine Datei groß ist. Ein
3B-Modell passt fast überall, ein 70B-Modell braucht eine dicke Grafikkarte.

## Installation

1. **Ollama holen:** <https://ollama.com/download> — Installer starten, fertig. Ollama
   läuft danach als Dienst im Hintergrund und lauscht auf Port **11434**.
2. **Erstes Modell laden**, im Terminal oder in PowerShell:

   ```bash
   ollama pull llama3.2
   ```

3. **Prüfen**, ob der Server antwortet:

   ```bash
   curl http://127.0.0.1:11434/api/version
   ```

   Kommt eine Versionsnummer zurück, ist alles bereit.

## Einrichtung in Jon

1. Jon starten → **Zahnrad-Menü** oben rechts.
2. Bereich **Ollama** → Schalter **Ollama verwenden** auf an.
3. Auf **Server & Modelle …** klicken. Es öffnet sich das Ollama-Fenster.
4. **Verbindung testen** drücken. Steht oben **Online**, hat es geklappt.
5. Unter **Modell** dein Modell auswählen und **Speichern** drücken.
6. Oben im Chatfenster als Anbieter `ollama` wählen — Jon antwortet ab jetzt lokal.

Alle Einstellungen liegen in `data/ollama.json` und werden beim Start automatisch geladen.

## Server konfigurieren

Läuft Ollama auf demselben PC wie Jon, musst du nichts einstellen — `127.0.0.1:11434` ist
die Voreinstellung.

Soll Ollama von **anderen Geräten** erreichbar sein, muss der Server auf allen
Netzwerkkarten lauschen. Das stellst du auf dem **Ollama-Rechner** ein:

**Windows** (PowerShell, danach Ollama neu starten):

```bash
setx OLLAMA_HOST 0.0.0.0
```

**macOS / Linux**:

```bash
export OLLAMA_HOST=0.0.0.0
```

Als systemd-Dienst unter Linux gehört stattdessen in
`/etc/systemd/system/ollama.service.d/override.conf`:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
```

Danach `sudo systemctl daemon-reload && sudo systemctl restart ollama`.

## Port konfigurieren

Standard ist **11434**. Einen anderen Port setzt du auf dem Server über
`OLLAMA_HOST=0.0.0.0:11500` und trägst ihn in Jon im Feld **Port** ein.

Vergiss die Firewall nicht. Unter Windows auf dem Ollama-Rechner:

```bash
netsh advfirewall firewall add rule name="Ollama" dir=in action=allow protocol=TCP localport=11434
```

## Host konfigurieren

Im Ollama-Fenster gibt es drei Felder, die dasselbe beschreiben — du kannst nehmen, was dir
lieber ist:

- **Server-URL** — komplette Adresse, z. B. `http://192.168.1.50:11434`.
- **Host / IP** — nur der Rechner, z. B. `192.168.1.50`.
- **Port** — nur die Nummer, z. B. `11434`.

Tippst du oben eine vollständige URL ein, füllen sich Host, Port und Protokoll von selbst —
und umgekehrt. Unter den Feldern schlägt Jon die Adressen dieses PCs zum Anklicken vor
(localhost, Heimnetz, Tailscale).

## Verbindung von Jon zum Server

| Szenario | Host | Port |
|---|---|---|
| Ollama auf demselben PC | `127.0.0.1` | `11434` |
| Anderer PC im Heimnetz | `192.168.x.x` bzw. `10.x.x.x` | `11434` |
| Rechner über Tailscale | `100.x.x.x` | `11434` |
| Eigener Server mit HTTPS-Proxy | `ollama.meinedomain.de` + Protokoll `https` | `443` |

### Nutzung über LAN

1. Auf dem Ollama-Rechner `OLLAMA_HOST=0.0.0.0` setzen und Ollama neu starten.
2. Dessen IP-Adresse herausfinden — Windows: `ipconfig`, macOS/Linux: `ip addr`.
3. Firewall für Port 11434 öffnen.
4. In Jon Host und Port eintragen, **Verbindung testen** drücken.

### Nutzung über Tailscale

[Tailscale](https://tailscale.com) verbindet deine Geräte verschlüsselt, egal wo sie
stehen — ohne Portfreigabe im Router.

1. Tailscale auf beiden Rechnern installieren und mit demselben Konto anmelden.
2. Auf dem Ollama-Rechner `OLLAMA_HOST=0.0.0.0` setzen.
3. Die Tailscale-Adresse ablesen: `tailscale ip -4` — sie beginnt mit `100.`.
4. Diese Adresse in Jon als **Host** eintragen, Port `11434`.

So läuft dein Modell zu Hause auf der großen Grafikkarte, während Jon unterwegs auf dem
Laptop damit arbeitet.

## Verbindung testen

Der Knopf **Verbindung testen** speichert deine Serverdaten und fragt den Server sofort ab.
Danach steht oben im Fenster jederzeit:

- **Online / Offline / Verbinde … / Ausgeschaltet**
- **Antwortzeit** in Millisekunden
- **Ollama-Version** des Servers
- **Gewähltes Modell**
- **Anzahl installierter Modelle**
- **Zeitpunkt der letzten erfolgreichen Verbindung**

Der Status aktualisiert sich alle 15 Sekunden von selbst; **Status aktualisieren** fragt
sofort nach.

## Modelle installieren

Modelle werden immer auf dem **Server** installiert, nicht in Jon:

```bash
ollama pull llama3.2
ollama pull qwen2.5-coder:7b
ollama list
```

Danach in Jon auf **Neu laden** klicken — die Liste kommt frisch von `/api/tags`.

Gute Startpunkte:

| Modell | Größe | Wofür |
|---|---|---|
| `llama3.2` | ~2 GB | Allrounder, läuft fast überall |
| `qwen2.5-coder:7b` | ~4,7 GB | Programmieren |
| `mistral` | ~4,1 GB | Schnelle Alltagsantworten |
| `llama3.3:70b` | ~40 GB | Sehr stark, braucht viel VRAM |

## Modelle wechseln

Zwei Wege, beide führen zum selben Ergebnis:

- Im Ollama-Fenster unter **Modell** auswählen und speichern.
- Oben im Chat den Anbieter `ollama` wählen und daneben das Modell.

Jon hält beide Stellen synchron: Was du an der einen Stelle wählst, steht auch an der
anderen.

## Werkzeuge (Tools)

Nicht jedes lokale Modell kann Werkzeuge aufrufen. Meldet der Server
`does not support tools`, wiederholt Jon die Anfrage automatisch ohne Werkzeuge und
antwortet trotzdem — statt mit einem Fehler abzubrechen. Modelle mit Tool-Unterstützung
sind z. B. `llama3.1`, `llama3.3`, `qwen2.5` und `mistral-nemo`.

## Server für andere freigeben

Läuft auf deinem Rechner eine starke Grafikkarte, kannst du deinen Ollama-Server für
andere Jon-Nutzer freigeben. Sie chatten dann über dein Modell, ohne selbst etwas
installieren zu müssen — und ohne Zugriff auf irgendetwas anderes auf deinem PC.

### Freigeben (als Besitzer)

1. **Zahnrad-Menü → Ollama → Server & Modelle …**
2. Ganz unten im Bereich **Serverfreigabe** den Schalter **Meinen Ollama-Server
   freigeben** einschalten.
3. **Freigabename** und **Beschreibung** eintragen — das sehen die anderen.
4. **Sichtbarkeit** wählen:

   | Einstellung | Bedeutung |
   |---|---|
   | **Privat** | Niemand kommt neu herein. Bereits verbundene Benutzer behalten ihren Zugang, bis du ihn widerrufst. |
   | **Nur Eingeladene** | Nur wer eine persönliche Einladung von dir hat. Jede Einladung gilt für genau einen Benutzer und verfällt nach der ersten Nutzung. |
   | **Öffentlich** | Jeder mit deinem Freigabecode darf sich verbinden. |

5. **Freigabecode** oder **Einladungslink** kopieren und weitergeben.

Der Code sieht aus wie `AB39KD12`, der Link wie
`jon://ollama/AB39KD12@192.168.1.50:8758`. Im Heimnetz genügt der Code allein — Jon sucht
den Server im Netzwerk. Über Tailscale oder von außerhalb nimmt man den Link mit Adresse.

### Verbinden (als Gast)

1. **Zahnrad-Menü → Ollama → Server & Modelle …**
2. Im Bereich **Freigegebene Server nutzen** den Code oder Link eintragen und auf
   **Verbinden** klicken.
3. Fertig: Die Modelle des fremden Servers stehen ab sofort oben in der KI-Auswahl unter
   dem Anbieter **ollama**, gruppiert unter „Freigabe <Code>".

Im Chat verhält sich alles wie gewohnt: Verlauf, Streaming und deine eigenen
Ollama-Einstellungen (Temperatur, Top P, Top K, Max Tokens, Context Length, Keep Alive,
Seed, System Prompt, Timeout) gelten weiter — sie werden bei jeder Anfrage mitgeschickt.

### Verwalten

Unter **Verbundene Benutzer** siehst du für jeden Gast:

- Name und Adresse
- Verbindungsstatus: **aktiv** (schreibt gerade), **verbunden** oder **offline**
- das gerade genutzte Modell
- Anzahl der Sitzungen und Anfragen
- Zeitpunkt der letzten Aktivität

**entfernen** wirft einen einzelnen Benutzer hinaus, **Allen Zugriff entziehen** alle auf
einmal. Beides gilt sofort — auch mitten in einer laufenden Antwort. Mit **Neuen Code
erzeugen** wird der alte Freigabecode ungültig.

### Sicherheit der Freigabe

- **Nichts ist offen zugänglich.** Jeder Gast bekommt beim Beitritt ein eigenes,
  zufälliges Zugriffstoken (256 Bit). Ohne gültiges Token beantwortet Jon keine einzige
  Anfrage — auch nicht bei öffentlicher Sichtbarkeit.
- Tokens werden **nur als Hash** gespeichert (`data/ollama_share.json`) und beim Vergleich
  zeitkonstant geprüft.
- Freigegeben wird **ausschließlich das Antworten deines Ollama-Servers**. Der Gast kann
  weder deine Chats lesen noch Dateien sehen, Programme starten oder Jons Werkzeuge auf
  deinem PC benutzen — seine Werkzeuge laufen auf seinem eigenen Rechner.
- Die Freigabe hängt am **Chat-Port 8758**, nicht an Jons Steuer-API (127.0.0.1:8756).
  Die Steuer-API bleibt unerreichbar.
- Zu viele Fehlversuche in Folge werden pro Adresse gebremst.
- **Schalter aus = alle draußen.** Deaktivierst du die Freigabe, sind sämtliche Tokens
  augenblicklich ungültig.
- Gib den Port trotzdem nicht im Router nach außen frei. Für Freunde außerhalb deines
  Heimnetzes ist Tailscale der richtige Weg.

### Freigabe im Netzwerk erreichbar machen

Damit Gäste dich finden, muss auf deinem Rechner der Chat-Port **8758** (TCP) offen sein;
für die Suche allein per Code zusätzlich **8762** (UDP). Unter Windows:

```bash
netsh advfirewall firewall add rule name="Jon Ollama-Freigabe" dir=in action=allow protocol=TCP localport=8758
netsh advfirewall firewall add rule name="Jon Ollama-Suche" dir=in action=allow protocol=UDP localport=8762
```

## Einstellungen im Detail

| Einstellung | Bedeutung | Standard |
|---|---|---|
| Ollama verwenden | Schaltet Ollama als Anbieter an/aus | an |
| Server-URL / Host / Port / Protokoll | Wo der Server läuft | `http://127.0.0.1:11434` |
| Modell | Das Modell, mit dem Jon antwortet | — |
| Modelle automatisch laden | Modell-Liste selbstständig vom Server holen | an |
| Temperatur | 0 = nüchtern und gleichbleibend, 2 = sehr kreativ | 0.7 |
| Top P | Anteil der berücksichtigten Wortwahrscheinlichkeiten | 0.9 |
| Top K | Wie viele Wortkandidaten pro Schritt betrachtet werden | 40 |
| Max Tokens | Maximale Länge der Antwort (`num_predict`), `-1` = ohne Limit | 32768 |
| Context Length | Größe des Gedächtnisfensters (`num_ctx`) | 4096 |
| Keep Alive | Wie lange das Modell im Speicher bleibt | `5m` |
| Seed | Feste Zahl = reproduzierbare Antworten, `-1` = zufällig | -1 |
| System Prompt | Zusatzanweisung für jedes Ollama-Gespräch | leer |
| Streaming | Antwort live mitschreiben statt am Stück | an |
| Timeout | Wie lange Jon auf eine Antwort wartet (Sekunden) | 120 |
| Automatisch neu verbinden | Bei Verbindungsabbruch bis zu dreimal erneut versuchen | an |

`Keep Alive` versteht `5m`, `30s`, `1h`, `0` (sofort entladen) und `-1` (dauerhaft
geladen). Eine größere `Context Length` kostet spürbar Speicher.

## Fehlerbehebung

| Meldung | Ursache | Lösung |
|---|---|---|
| „Keine Verbindung zu Ollama unter …" | Server läuft nicht oder falsche Adresse | Ollama starten, Host/Port prüfen |
| „Kein Server mit diesem Code im Netzwerk gefunden" | Freigabe aus, anderes Netz oder Port 8762 zu | Einladungslink mit Adresse verwenden (`CODE@ip:8758`) |
| „Der Zugriff wurde widerrufen" | Der Besitzer hat dich entfernt oder die Freigabe abgeschaltet | Neuen Freigabecode erfragen |
| „Diese Freigabe ist privat" | Sichtbarkeit steht auf Privat | Besitzer bittet um Umstellung oder schickt eine Einladung |
| „Diese Einladung wurde bereits verwendet" | Einladungen gelten einmalig | Neue Einladung erstellen lassen |
| „… antwortet nicht" | Firewall blockt oder `OLLAMA_HOST` fehlt | `OLLAMA_HOST=0.0.0.0` setzen, Port freigeben |
| „Das Modell X ist nicht installiert" | Modell fehlt auf dem Server | `ollama pull X` auf dem Server |
| „Ollama hat zu lange gebraucht" | Modell zu groß für die Hardware | Timeout erhöhen oder kleineres Modell |
| „… das Modell passt nicht in den Speicher" | Zu wenig RAM/VRAM | Kleineres Modell oder Context Length senken |
| „Ollama ist ausgeschaltet" | Schalter steht auf aus | Im Zahnrad-Menü → Ollama einschalten |
| Keine Modelle in der Liste | Noch keins installiert | `ollama pull llama3.2`, dann **Neu laden** |

Jon stürzt bei keinem dieser Fälle ab: Die Meldung erscheint als Text im Chat bzw. im
Ollama-Fenster, und du kannst es nach der Korrektur direkt wieder versuchen.

## Sicherheit

- **Ollama kennt keine Passwörter.** Wer den Port erreicht, darf den Server benutzen.
- Setze `OLLAMA_HOST=0.0.0.0` nur, wenn du den Zugriff wirklich brauchst — im reinen
  Einzelplatzbetrieb bleibt `127.0.0.1` die sicherste Wahl.
- **Gib den Port niemals im Router nach außen frei.** Für den Zugriff von unterwegs ist
  Tailscale (oder ein VPN) der richtige Weg, weil dort nur deine eigenen Geräte
  hineinkommen.
- Brauchst du doch einen öffentlichen Server, setze einen Reverse-Proxy mit HTTPS und
  Passwortschutz davor und trage in Jon `https` als Protokoll ein.
- Deine Gespräche bleiben zwischen Jon und deinem Ollama-Server; sie gehen an keinen
  Anbieter.

## Tipps zur optimalen Nutzung

- **Keep Alive hochsetzen** (`30m`), wenn du oft mit Jon sprichst: Das Modell bleibt
  geladen, und die erste Antwort kommt sofort statt nach 10 Sekunden Ladezeit.
- **Context Length nur so groß wie nötig.** 4096 reicht für normale Gespräche; 32768
  belegt ein Vielfaches an Speicher.
- **Zum Programmieren** ein Coder-Modell wählen (`qwen2.5-coder`) und die Temperatur auf
  0.2 senken.
- **Für reproduzierbare Antworten** einen festen Seed setzen und die Temperatur auf 0.
- **Zwei Rechner nutzen:** Ollama auf dem Rechner mit der starken Grafikkarte, Jon auf dem
  Laptop — über LAN oder Tailscale verbunden.
- **„Anbieter wechseln" beachten:** Ist die Ausweich-Automatik an und dein lokales Modell
  streikt, kann Jon zu einem Cloud-Anbieter wechseln. Wer strikt lokal bleiben will,
  schaltet sie im Zahnrad-Menü unter „Jon" aus.

## FAQ

**Kostet Ollama etwas?**
Nein. Programm und Modelle sind kostenlos, es gibt keine Token-Abrechnung.

**Braucht Jon dann noch einen API-Schlüssel?**
Für Ollama nicht. Andere Anbieter bleiben unberührt und funktionieren weiter wie bisher.

**Muss ich online sein?**
Nur zum Herunterladen der Modelle. Danach funktioniert alles offline.

**Kann ich Ollama und Cloud-Modelle parallel nutzen?**
Ja. Der Anbieter oben im Chat ist jederzeit umschaltbar; Mini Jon und Telegram können
sogar ein anderes Modell verwenden als das Hauptfenster.

**Warum antwortet mein lokales Modell langsamer als NVIDIA oder OpenAI?**
Weil es auf deiner Hardware rechnet statt in einem Rechenzentrum. Kleine Modelle
(1B – 8B) sind auf einer normalen Grafikkarte trotzdem sehr flott.

**Warum ruft mein Modell keine Werkzeuge auf?**
Es unterstützt keine. Jon merkt das und antwortet ohne Werkzeuge weiter. Nimm ein Modell
mit Tool-Unterstützung, wenn du PC-Steuerung per Ollama willst.

**Kann Jon Bilder mit Ollama ansehen?**
Ja, mit einem Vision-Modell wie `llava` oder `llama3.2-vision`.

**Wo liegen meine Einstellungen?**
In `data/ollama.json` neben Jons übrigen Daten, die Freigabe in `data/ollama_share.json`.
Ein Backup über das Zahnrad-Menü nimmt sie mit.

**Kann jemand über meine Freigabe meinen PC steuern?**
Nein. Freigegeben ist nur das Antworten des Modells. Werkzeuge, Dateien und PC-Steuerung
laufen immer auf dem Rechner des jeweiligen Nutzers, nie auf deinem.

**Sieht der Besitzer meine Chats, wenn ich seinen Server nutze?**
Er sieht, was jeder Betreiber eines Sprachmodells sieht: dass angefragt wird, mit welchem
Modell und wann. Die Inhalte laufen durch seinen Ollama-Server — teile also nichts
Vertrauliches über einen fremden Server.

**Kostet die Freigabe den Besitzer etwas?**
Nur Strom und Rechenzeit. Solange jemand über den Server schreibt, ist dessen Grafikkarte
beschäftigt.

## API

Jon stellt die Ollama-Verwaltung auch über seine eigene REST-API bereit — siehe
[API.md](API.md#ollama).
