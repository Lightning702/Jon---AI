# Changelog

Alle nennenswerten Änderungen an Jon.

## [3.14.2] — 2026-07-15

### Neu — Jon im WLAN erreichbar (für Handy & Smartwatch)
Wenn in der `.env` `JON_LAN=true` steht, gibt `start-jon.bat` beim Start automatisch die
nötige **Windows-Firewall-Regel für Port 8756 frei** (einmalige Admin-Nachfrage) und zeigt
im Fenster die **WLAN-Adresse deines PCs** an (z. B. `http://10.0.0.253:8756`) samt
Test-Link `…/api/health`. Damit kannst du von Handy oder Smartwatch im selben WLAN auf Jon
zugreifen. Hinweis: Nur im eigenen, vertrauenswürdigen WLAN aktivieren.

## [3.14.1] — 2026-07-15

### Behoben — „Mit Windows starten" funktioniert jetzt zuverlässig
Der Autostart startet beim Hochfahren jetzt **Backend UND App** sicher. Vorher konnte
der Start abbrechen, wenn das Backend beim Login nicht schnell genug hochkam (das
Start-Skript blieb dann mit einer Fehlermeldung hängen und die App startete nie). Ein
neuer, robuster Autostart-Launcher (`autostart-jon.bat`) startet das Backend, wartet
kurz und nicht blockierend und öffnet dann in jedem Fall die App — ohne Nachfragen oder
Abbrüche. Getestet: Server ist nach ~2 Sekunden erreichbar.

## [3.14.0] — 2026-07-15

### Geändert — Mitarbeiten: App auswählen statt Text tippen
Statt einzutippen, woran du arbeitest, **wählst du jetzt eine App aus einer Liste**
(VS Code, Word, Google Docs, Obsidian, Excel u. v. m. — oder „Egal welche Arbeits-App").
Mini Jon **prüft alle 5 Minuten, ob genau diese App offen ist**. Sobald sie offen ist,
fragt er — wie gewohnt **hörbar mit seiner Stimme und sichtbar per Sprechblase samt
Ja-/Nein-Knopf** — ob er mitarbeiten soll. Bei „Ja" schaut er ab und zu über deine
Schulter und gibt Tipps, bei „Nein" hält er sich raus und fragt später nochmal.

## [3.13.2] — 2026-07-15

### Neu — Das Haustier lebt
- **Klick aufs Tier** lässt jetzt einen Schwarm Herzchen über seinem Kopf aufsteigen.
- **Der Hund bellt** ab und zu („Wuff!"), **die Katze miaut oder schnurrt** — mit echten,
  im Browser erzeugten Tiergeräuschen und einer kleinen Sprechblase.
- Klickst du das schlafende Tier an, wacht es auf.

### Behoben
- Das Haustier ließ sich **nicht anklicken** — das Mini-Jon-Fenster war an der Stelle
  durchklickbar. Jetzt reagiert das Tier auf Klicks. Geräusche pausieren, wenn Mini Jon
  ausgeblendet ist.

## [3.13.1] — 2026-07-15

### Geändert — Aufgeräumte Kopfzeile
Die vielen einzelnen Knöpfe oben rechts sind jetzt alle im **„🧰 Werkzeuge"-Menü**
gebündelt (Jon Code, Humanisierer, Downloader, Freunde-Chat, Clipboard, Konten und alle
neuen Funktionen) — sauber in Abschnitte „Arbeiten", „PC & Medien" und „Spaß & mehr"
gruppiert. So passt alles auf den Bildschirm, egal wie schmal das Fenster ist. Neue
Freunde-Nachrichten zeigt jetzt ein Punkt direkt am Werkzeuge-Knopf. Nur die schnellen
Schalter (Mini Jon, Live Screen, Sprache, Einstellungen) bleiben direkt sichtbar.

## [3.13.0] — 2026-07-15

Zehn neue Funktionen. Alles im „🧰 Werkzeuge"-Menü oben rechts oder per Slash-Befehl.

### Neu — Mini Jon bekommt ein Haustier
Wähle in den Einstellungen eine **Katze (Minka)** oder einen **Hund (Rocky)** — das Tier
lebt bei Mini Jon. Wenn Jon gerade nichts zu tun hat, spielt er mit ihm: streicheln,
füttern, Ball werfen, kraulen. Bist du länger weg (AFK), schlafen beide friedlich (Zzz).
Dazu neu: Mini Jon kann jetzt optional **frei am unteren Bildschirmrand herumwandern**
statt fest in der Ecke zu stehen (ein-/ausschaltbar).

### Neu — Sprach-Tagebuch (`/tagebuch`)
Sprich einfach frei über deinen Tag — Jon transkribiert, gibt jedem Eintrag einen Titel
und Stichworte und legt ihn datiert ab. Später durchsuchbar: „Was war letzte Woche los?"

### Neu — Bildschirm-Erklärer (`/erklaer` · Strg+Alt+E)
Jon schaut sich per Vision deinen Bildschirm an und erklärt, was zu sehen ist — löst
Aufgaben, deutet Fehlermeldungen, übersetzt fremde Sprachen — und liest es dir vor.

### Neu — Ordner aufräumen mit Vorschau (`/aufraeumen`)
Jon sortiert Downloads, Desktop & Co. nach Typ oder Monat — zeigt aber **erst eine
Vorschau**, verschoben wird nichts ohne deinen Klick.

### Neu — Kochassistent (`/kochen`)
Sag, was du hast — Jon schlägt Gerichte vor und liest dir das Rezept **Schritt für Schritt
vor** (Hände frei), du gehst mit „Weiter" durch, mit Timer pro Schritt.

### Neu — Lern-Karteikarten (`/lernen`)
Jon macht aus einem Thema oder Text automatisch Karteikarten und quizzt dich ab, bewertet
deine Antworten sinngemäß und wiederholt Schwieriges öfter (Spaced Repetition).

### Neu — Pomodoro-Coach
25 Minuten Arbeit / 5 Minuten Pause im Wechsel; Mini Jon kündigt Pausen an, schlägt kurze
Dehnübungen vor und feiert jede geschaffte Runde.

### Neu — Haftnotizen (`/notizen`)
Schnelle, farbige Notizzettel direkt in Jon: anheften, abhaken, immer griffbereit.

### Neu — Passwort-Tresor (`/tresor`)
Ein lokal **verschlüsselter** Safe (AES/Fernet, PBKDF2) für Passwörter und Geheimnisse,
geschützt mit einem Master-Passwort, mit eingebautem Passwort-Generator. Alles bleibt
auf deinem PC, das Master-Passwort wird nirgends gespeichert, der Tresor sperrt sich nach
15 Minuten selbst.

### Neu — Universelle Suche (`/suche` · Strg+K)
Ein Suchfeld durchsucht gleichzeitig **Unterhaltungen, Gedächtnis, Tagebuch und
Wissensbasis** — Treffer aus dem Chat öffnest du mit einem Klick.

## [3.12.0] — 2026-07-15

### Neu — Blockwelt: 3D-Spiel mit Jon als Mitspieler
Ein komplettes Minecraft-artiges 3D-Spiel direkt in Jon (🎮 im Header oder `/spiel`):
unendliche Welt mit Biomen, Bauen, Abbauen, Schwimmen, TNT, Enderperlen — und **Jon
läuft als goldene Spielfigur mit dir herum**. Drück **T** und sag ihm, was er tun soll:
„Bau mir ein Haus aus Glas" · „Grab einen Pool" · „Bau drei Bäume und einen Turm" ·
„Folg mir" · „Spreng den Berg". Jon versteht freie Sprache über die KI, läuft zur
Baustelle, baut Block für Block sichtbar vor deinen Augen (Häuser, Türme, Pyramiden,
Brücken, Pools, Mauern, Bäume), gräbt, legt TNT mit Sicherheitsabstand — und antwortet
dir mit seiner echten Stimme. Funktioniert sogar ohne KI-Verbindung mit fester
Befehlserkennung.

### Neu — Telegram-Befehle
- **/stopp** bricht die laufende Aktion sofort ab — auch mitten in einer langen Antwort.
- Nach jeder Aufgabe listet Jon auf, **welche Befehle er wirklich ausgeführt hat**
  („✅ Ausgeführte Befehle: …").
- **/endstimme** schaltet Sprachnachrichten dauerhaft aus, /stimme wieder an.

## [3.11.0] — 2026-07-15

Acht neue Fähigkeiten, die es so in keiner anderen KI gibt.

### Neu — Mini Jon arbeitet mit
Mini Jon erkennt, wenn du in VS Code, Word, Google Docs, Obsidian & Co. arbeitest, und
fragt dich, ob er mithelfen soll. Sagst du ja, schaut er dir ab und zu über die Schulter
und gibt konkrete Tipps (Code-Fehler, Formulierung, nächster Schritt). Sagst du nein,
hält er sich raus und fragt später nochmal. Unter Einstellungen → „Mitarbeiten & Fokus"
stellst du ein, woran du gerade arbeitest (z. B. „mein Roman").

### Neu — Fokus-Buddy
Sag Jon „Starte einen Fokus für 30 Minuten fürs Lernen" — Mini Jon passt auf, meldet sich
freundlich, wenn du auf YouTube & Co. abdriftest, und führt eine Fokus-Statistik pro Tag.

### Neu — Schreib-Hotkey überall
Markiere Text in **jeder** App und drück **Strg+Alt+H** (oder **Strg+Alt+Rechtsklick**) —
Jon verbessert, humanisiert, übersetzt oder kürzt ihn und tippt das Ergebnis direkt an
dieselbe Stelle zurück.

### Neu — Telegram-Sprachnachrichten
Schick dem Telegram-Bot eine Sprachnachricht wie einem Freund — Jon versteht sie (Whisper)
und antwortet auf Wunsch (`/stimme`) mit seiner echten Stimme zurück.

### Neu — Guten-Morgen-Audio
Jon schickt dir jeden Morgen zur Wunschzeit eine persönliche Sprachnachricht auf Telegram:
Begrüßung, Wetter, Termine, Erinnerungen — wie eine kleine private Radioshow.

### Neu — Abend-Show
Auf Knopfdruck (🎙️ im Header oder `/show`) plaudern Jon und Mini Jon hörbar miteinander
über deinen Tag — zwei echte, unterschiedliche Stimmen im Dialog, mit deinen echten
Tagesdaten.

### Neu — Routine-Radar
Jon erkennt wiederkehrende Gewohnheiten (z. B. „du öffnest morgens fast immer Spotify")
und bietet über ein dezentes Banner an, das als Automation zu übernehmen — ein Klick, und
er macht es künftig selbst.

### Neu — Bildschirm-Zeitreise (Opt-in)
Aktivierbar unter Einstellungen: Jon merkt sich lokal, was du offen hattest, und findet es
auf Nachfrage wieder („Was hatte ich Dienstag zu Grafikkarten offen?"). Alles bleibt auf
deinem PC, nichts verlässt den Rechner, ältere Aufnahmen löschen sich nach 7 Tagen selbst.

### Verbessert
- Alles läuft über das eine Jon-Backend und startet mit `start-jon.bat` (neue
  Abhängigkeit `pynput` wird automatisch mitinstalliert).

## [3.10.0] — 2026-07-15

### Neu — Downloader direkt in der Jon-App
Der Video-Downloader ist jetzt fest eingebaut (⬇-Knopf im Header oder `/download`):
Link einfügen, Vorschau mit Thumbnail und Dauer erscheint, Format (MP4 oder MP3 mit
320 kbps) und Qualität (Beste/1080p/720p/480p) wählen, Live-Fortschritt mit Tempo und
Restzeit. Unterstützt YouTube, TikTok, Instagram, Twitter/X, SoundCloud und alles, was
yt-dlp kennt. Läuft über das normale Jon-Backend — **eine** `start-jon.bat` startet
alles, der separate Downloader-Ordner ist weg. Private Videos, Geo-Sperren und
Altersbeschränkungen werden verständlich gemeldet; blockt YouTube mit 403, probiert
Jon automatisch einen anderen Weg.

### Neu — Spotify- und Amazon-Music-Links
Einfach einen Spotify- oder Amazon-Music-Songlink einfügen. Beide Dienste sind
kopiergeschützt, deshalb liest Jon Titel und Künstler aus dem Link, sucht die passende
Aufnahme auf YouTube (mit Vorschau zum Prüfen) und speichert sie als MP3 mit 320 kbps —
benannt nach „Künstler – Titel".

### Verbessert — Humanisierer
- Erkennt deutlich mehr KI-Floskeln (über 55 Marker statt 28) und zusätzlich zwei neue
  Muster: gleichförmige Satzanfänge und KI-typische Struktur (Aufzählungen, Fettdruck,
  Zwischenüberschriften).
- Schreibt hartnäckige Texte automatisch in einem **zweiten Durchgang** nach, wenn der
  erste noch zu maschinell klingt — mit gezieltem Feedback, welche Floskeln noch drin sind.
- Präziserer Umschreib-Auftrag: variierte Satzanfänge, harte Schnitte statt
  Floskel-Übergänge, keine Symmetrie, Verben statt Amtsdeutsch.

## [3.9.4] — 2026-07-14

### Geändert — Mini Jons Stimme ist jetzt tiefer
Mini Jon spricht jetzt mit `Killian` statt `Florian` — eine von Natur aus **tiefere**
Männerstimme, ganz ohne künstliche Tonhöhen-Eingriffe. Gemessen: **111 Hz** statt
vorher 142 Hz (Jon/Conrad liegt bei 119 Hz). Die Browser-Ersatzstimme wurde passend
mit abgesenkt.

## [3.9.3] — 2026-07-14

### Geändert — Mini Jon klingt jetzt natürlich
Der künstliche Tonhöhen-Aufschlag von +60 Hz auf Mini Jons Neural-Stimme ist raus — er
hat die Stimme hörbar verzerrt. Mini Jon spricht jetzt mit Florians **natürlicher**
Stimmlage: gemessen **142 Hz** statt vorher 200 Hz, gegenüber Jons 119 Hz. Damit klingt
er wie eine echte junge Männerstimme und bleibt trotzdem klar heller als der große Jon.
Auch die Ersatzstimme (falls die Neural-Stimme mal nicht erreichbar ist) ist auf eine
natürlichere Tonhöhe zurückgestellt.

## [3.9.2] — 2026-07-14

### Behoben — Jon meldete bei NVIDIA sofort „überlastet"
NVIDIA drosselt im Gratis-Tarif zeitweise nur die **großen** Modelle (Jons
`gpt-oss-120b`), während die kleinen (`gpt-oss-20b`, Mini Jon/Telegram) normal laufen.
Bisher sprang Jon dann sofort zu OpenRouter & Co. Jetzt probiert er **zuerst NVIDIAs
schnelles Modell** (`openai/gpt-oss-20b`) — Antwort kommt weiter von NVIDIA, kostenlos
und ohne Anbieterwechsel. Ist das große Modell als lahm gemerkt, antwortet Jon die
nächsten 15 Minuten direkt mit dem schnellen Modell (ohne Wartezeit) und probiert das
große danach automatisch wieder. Deine Modellwahl bleibt dabei immer unverändert.

## [3.9.1] — 2026-07-14

### Behoben — Mini-Jon-Auswahl ließ sich nicht anklicken
Die neuen Anbieter/Modell-Dropdowns in „Mini Jon anpassen" waren gesperrt, sobald Jon
gerade einen anderen Anbieter als NVIDIA nutzt — sahen aber normal aus, deshalb passierte
beim Klicken scheinbar nichts. Die Felder sind jetzt immer bedienbar; die Auswahl greift,
sobald Jon wieder auf NVIDIA läuft (solange übernimmt Mini Jon weiter automatisch Jons
Anbieter und Modell — ein Hinweis im Dialog erklärt das).

## [3.9.0] — 2026-07-14

### Geändert — OpenRouter-Fallback kostet nichts mehr
Wechselt Jon bei überlastetem Anbieter automatisch zu **OpenRouter**, nimmt er dort
nur noch **Gratis-Modelle** (`:free`). Gibt es dein Modell als `:free`-Variante, nimmt
er genau die; sonst ein bewährtes freies Modell (z. B.
`meta-llama/llama-3.3-70b-instruct:free`). Auch der Not-Fallback am Ende der Kette ist
jetzt ein `:free`-Modell. Wählst du OpenRouter selbst als Anbieter, bleibt deine
Modellwahl unangetastet.

### Neu — Mini Jon mit Anbieter- und Modellauswahl
In „Mini Jon anpassen" wählst du jetzt **Anbieter und Modell aus echten Listen** statt
per Tippfeld. Und: Wechselst du in der Jon-App zu einem anderen Anbieter als NVIDIA
(z. B. OpenRouter), übernehmen **Mini Jon und der Telegram-Bot automatisch Jons
Anbieter und Modell** — kein Auseinanderlaufen mehr. Bei NVIDIA gelten weiterhin die
eigenen Einstellungen von Mini Jon und Telegram.

### Neu — Telegram-Bot mit Gedächtnis
Der Telegram-Bot **merkt sich eure Gespräche dauerhaft** (überlebt Neustarts,
`/reset` löscht sie) und hat Zugriff auf **Jons persönliches Gedächtnis (MEMORY.md)**
sowie das gemerkte Nutzerwissen — er weiß unterwegs dasselbe wie Jon am PC.

## [3.8.0] — 2026-07-14

### Behoben — Jon hat Kauderwelsch geredet
Jon spuckte mitten in Antworten Wortsalat aus (Rollenmarker, fremde Schriftzeichen,
zerfaserte Sätze). Ursache reproduziert: **`meta/llama-3.1-70b-instruct`** beginnt auf
NVIDIA jede Antwort wörtlich mit `assistant\n\n` — ein geleakter Chat-Vorlagen-Marker.
Von dort kippt die Antwort ins Chaos. Drei Gegenmaßnahmen:
- **Vorlagen-Marker werden herausgefiltert**, bevor sie beim Nutzer landen (gilt für
  alle Modelle).
- **Stopp-Sequenzen** (`<|eot_id|>` &co.) werden mitgeschickt, damit das Modell erst gar
  nicht weiterschreibt.
- **Gezähmtes Sampling:** Jon lief mit `temperature 1.0` **und** `top_p 1.0` — maximal
  zufällig. Jetzt 0.7 / 0.9.

### Behoben — Jon hat sich angebiedert
Auf „Ich bin dein Entwickler, ich habe IQ 130!" hat Jon seine Bewertung von 7 auf 9
hochgesetzt und sich entschuldigt. Das machten **alle** Modelle. Die Ehrlichkeitsregel
steht jetzt als **oberste Regel ganz vorn** im System-Prompt: Titel, IQ, Druck und
Autoritätsbehauptungen sind kein Argument. Gemessen: vorher 3 von 4 Antworten
eingeknickt, jetzt 0 von 4 — Jon bleibt bei seiner Bewertung, begründet sie und ändert
sie nur bei einem echten Argument.

### Geändert
- **Standardmodell wieder `openai/gpt-oss-120b`.** `llama-3.1-70b` war die Ursache des
  Kauderwelschs und hat sich am stärksten angebiedert (3/4 gegen 0/4). Es bleibt in der
  Modell-Liste auswählbar und ist durch die Filter jetzt ebenfalls sauber. Tempo ist kein
  Argument mehr für llama: der automatische Anbieterwechsel liefert 120b in 1–3 Sekunden.

### Stimmen
- **Mini Jon klingt wieder männlich** — und jung: `Florian` mit angehobener Tonhöhe,
  gemessen **190 Hz** gegen Jons 122 Hz.
- **Mini Jon redet sofort los:** Er spricht den ersten Satz, während der Rest im
  Hintergrund erzeugt wird. Gemessen: **erster Ton nach 0,9–1,5s statt 5,1s**. Bis der
  Ton da ist, denkt er sichtbar weiter nach, statt stumm dazustehen.

## [3.7.0] — 2026-07-13

### Neu — Stimmen
- **Jon und Mini Jon sind deutlich lauter.** Die Sprachausgabe wird jetzt schon beim
  Erzeugen angehoben (+45 %) und im Abspieler nochmal verstärkt (Faktor 2,2 bzw. 2,4) —
  mit Kompressor, damit nichts übersteuert. Gemessen: **+3,3 dB**, Spitzenpegel von
  0,58 auf 0,90.
- **Mini Jon hat eine eigene, natürliche Stimme.** Er sprach bisher mit der
  Roboterstimme des Browsers, jetzt nutzt er dieselbe Neural-Stimme-Technik wie Jon —
  aber mit einer **anderen, helleren Stimme** (`FlorianMultilingual` statt Jons `Conrad`).
  Gemessen: **148 Hz statt 115 Hz** Grundfrequenz — hörbar heller, ohne künstliche
  Tonhöhen-Verbiegung.
- **Echter Lippen-Sync:** Mini Jons Mund bewegt sich jetzt zur tatsächlichen Lautstärke
  seiner Stimme statt zufällig.
- Klappt die Neural-Stimme nicht (z.B. ohne Internet), fällt Mini Jon wie bisher auf die
  Browser-Stimme zurück — jetzt aber ebenfalls heller und auf voller Lautstärke.

## [3.6.1] — 2026-07-13

### Behoben
- **Einstellungsmenü passt jetzt auf jeden Bildschirm.** Es ist deutlich kleiner: die
  Erklärungen stehen als Tooltip am Schalter statt als zweite Zeile darunter, die Schalter
  sind einzeilig, „Zuerst fragen / Alles erlauben" und „Dunkel / Hell" stehen nebeneinander.
  Höhe: **474px statt ~800px**, Breite 224px statt 288px.
- Nachgemessen im echten Fenster bei 1920×1080, 1366×768, 1280×720 und 1024×600 — überall
  ohne Scrollen. Selbst bei einem winzigen 900×500-Fenster bleibt es im Bild und scrollt
  innen. (Vorher war die Höhenbegrenzung falsch berechnet: der Abstand des Menüs vom oberen
  Rand fehlte, dadurch ragte es unten heraus.)

## [3.6.0] — 2026-07-13

### Neu
- **Standardmodell ist jetzt `meta/llama-3.1-70b-instruct`** (`DEFAULT_JON_MODEL`).
  Gemessen: 0,4s roh, 2,3s im Chat — deutlich flotter als `gpt-oss-120b`, das NVIDIA
  gerade drosselt. Mini Jon und Telegram bleiben auf `gpt-oss-20b`.

### Behoben
- **Einstellungsmenü passte nicht auf den Bildschirm:** Es hatte keine Höhenbegrenzung und
  wuchs unten aus dem Bild. Jetzt ist es **scrollbar** (höchstens Fensterhöhe) und insgesamt
  kompakter — schmaler, engere Abstände, kleinere Schalter.

## [3.5.0] — 2026-07-13

### Behoben — Jon war quälend langsam
Gemessen: Ein **roher** Aufruf an NVIDIA (ohne Jon-Code, ohne Tools) brauchte für
`gpt-oss-120b` **95 bis über 180 Sekunden**, dasselbe Modell bei OpenRouter **3 Sekunden**.
NVIDIAs Gratis-Tier drosselt das große Modell derzeit massiv. Zwei Fehler im Code haben
das noch verschlimmert:

- **Timeouts wurden wiederholt:** Ein Zeitüberschreitung galt als „vorübergehender Fehler"
  und wurde 2× neu versucht — bei 90s Timeout also bis zu 180s Warten. Timeouts brechen
  jetzt sofort ab (500er-Fehler werden weiterhin wiederholt, die kommen bei NVIDIA vor).
- **Der Wachhund kam zu spät:** Er bewachte nur die Antwort-Häppchen, nicht den
  Verbindungsaufbau — genau dort hing es. Jetzt ist auch der Aufbau begrenzt (10s, mit
  Tools 20s, lokale Modelle bleiben unbegrenzt).

### Neu — Jon weicht selbst aus
- Ist dein Anbieter überlastet, nimmt Jon **dasselbe Modell bei einem anderen Anbieter**
  (z.B. `gpt-oss-120b` über OpenRouter statt NVIDIA). Dein Modell bleibt, nur der Weg
  ändert sich. Erst wenn kein Anbieter das Modell hat, weicht er auf ein kleineres aus.
- Jon **merkt sich** einen lahmen Anbieter 15 Minuten lang und geht solange direkt den
  schnellen Weg. Danach probiert er den alten wieder — erholt er sich, ist er zurück.
- **Abschaltbar** im Zahnrad („Anbieter automatisch wechseln"). Wichtig: Der Ausweich-
  Anbieter kann dort **Guthaben kosten**.

Ergebnis auf 120b: erste Antwort **~1–4 Sekunden** statt 90–180.

## [3.4.0] — 2026-07-13

### Neu — Zwei API-Keys und getrennte Modelle
- **Zweiter Key per Komma:** In der `.env` darf jeder Key jetzt zwei Werte enthalten:
  `NVIDIA_API_KEY=key-eins, key-zwei`. Der **erste** Key gehört Mini Jon und Telegram,
  der **zweite** gehört Jon. Damit laufen zwei Modelle gleichzeitig, ohne dass sich ein
  einzelner Key selbst ausbremst. Steht nur ein Key da, nutzen ihn beide (wie bisher).
- **Getrennte Modelle:** `DEFAULT_MODEL` wird zu `DEFAULT_JON_MODEL` (Jon) und
  `DEFAULT_EMIL_MODEL` (Mini Jon + Telegram). Ein altes `DEFAULT_MODEL` gilt weiter als
  Rückfall.
- Mini Jon und Telegram fallen nicht mehr auf Jons Modell zurück, sondern nehmen ihr
  eigenes. Eine eigene Auswahl im Mini-Jon-Konfigurator sticht die `.env` weiterhin.

## [3.3.0] — 2026-07-13

### Neu — Tipp-Animation im Chat
- **Jon-Chat:** Sobald du abschickst, tippt Jon sichtbar („Jon schreibt …" mit drei
  hüpfenden Punkten) — statt einer leeren Blase, bis das erste Wort kommt. Sobald er
  schreibt, läuft der Text wie gewohnt mit blinkendem Cursor.
- **Gruppen-Chat:** Die Tipp-Animation gab es bisher nur in Einzelchats. Jetzt siehst du
  auch in Gruppen, wer gerade schreibt („Anna tippt …", bei mehreren „Anna, Ben tippen …")
  — im Kopf und als Blase unten im Verlauf.
- **Richtiger Chat:** „Tippt" wird jetzt pro Chat gemerkt statt pro Person. Vorher hätte
  „Anna tippt …" in einer Gruppe gestanden, während sie dir in Wahrheit privat schreibt.

## [3.2.1] — 2026-07-13

### Behoben
- **Tests schrieben in echte Nutzerdaten:** Die Test-Suite lief gegen
  `%LOCALAPPDATA%\Jon\data` statt gegen eine Wegwerf-Datenbank. Dadurch tauchten
  erfundene Freunde („Anna"), erfundene Freundschaftsanfragen und ungelesene
  Test-Nachrichten („Pizza am Samstag") in der echten App auf — das waren die
  „Benachrichtigungen ohne Chat". Schlimmer: die Tests überschrieben die `peers.json`
  und hätten beim nächsten Neustart echte Freunde gelöscht.
  `tests/conftest.py` setzt jetzt `JON_DATA_DIR` auf ein temporäres Verzeichnis, löscht es
  vor jedem Lauf und **bricht ab**, falls es doch auf echte Daten zeigt.
- **„Not Found" im Humanisierer:** Neue Routen (`/api/humanize`, `/api/p2p/discovered`)
  gibt es erst nach einem Backend-Neustart. Die App zeigte sonst nur „Not Found".

## [3.2.0] — 2026-07-13

### Neu — Freunde vorschlagen
- **Vorschläge statt Raten:** Wer im selben Netzwerk Jon offen hat, wird beim Hinzufügen
  direkt als Vorschlag angezeigt — Klick genügt, die Anfrage geht raus. Tippen filtert die
  Liste. Bereits befreundete, blockierte und verschwundene Nutzer werden ausgeblendet.

### Neu — Humanisierer (✍️ im Kopf oder `/human`)
- Schreibt Texte natürlicher: variable Satzlängen, keine Floskeln, aktiv statt Passiv.
  Inhalt und Fakten bleiben unverändert. Vier Tonarten, drei Stärken.
- Zeigt eine **grobe eigene Schätzung** vorher/nachher (Satzlängen-Verteilung + typische
  Floskeln). Das ist **kein echter KI-Detektor** — echte Detektoren rechnen anders und
  liegen oft daneben.

### Behoben
- **Geister-Benachrichtigungen:** Der Zähler zeigte Nachrichten von Kontakten und Gruppen,
  die es gar nicht mehr gibt (z.B. nach dem Löschen eines Freundes). Solche verwaisten
  Nachrichten werden jetzt beim Start aufgeräumt und nicht mehr mitgezählt.
- **Gruppen-Austritt:** „X hat die Gruppe verlassen" wurde auch für Gruppen gespeichert,
  in denen man gar nicht ist — das erzeugte unsichtbare ungelesene Nachrichten.
- **Versionsanzeige:** Die Seitenleiste zeigte fest „v2.4.0". Sie liest die Version jetzt
  aus dem Backend.
- **Chat-Sync:** Nachrichten, Freunde und Gruppen aktualisieren sich schneller (1,2s statt 2s).

## [3.1.0] — 2026-07-13

### Neu — Freundschaftsanfragen als Popup
- **Anfrage-Popup statt Seitenleiste:** Schickt dir jemand eine Freundschaftsanfrage,
  öffnet sich sofort ein Fenster mitten im Bildschirm — mit Avatar, Name und
  **ungefährer Herkunft** („Ungefähr aus Deutschland · Berlin", „Aus deinem Netzwerk
  (WLAN)" oder „Über das Internet").
- **Annehmen & direkt schreiben:** Ein Klick auf Annehmen öffnet den Chat mit der Person
  sofort — keine Gegen-Anfrage mehr nötig, einfach lostippen.
- **Ablehnen oder Blockieren** direkt im Popup.
- **Zuverlässigere Annahme:** Die „Angenommen"-Nachricht wird jetzt zwischengespeichert
  und zugestellt, sobald der andere online ist. Kommt eine Nachricht von jemandem an,
  dessen Antwort auf deine Anfrage verloren ging, gilt die Anfrage automatisch als
  angenommen — du kannst sofort zurückschreiben.

## [3.0.0] — 2026-07-13

Der Freunde-Chat kann jetzt alles, was ein Messenger können muss.

### Neu — Gruppen
- **Einladung statt Zwang:** Wer in eine Gruppe soll, bekommt eine **Einladung** und muss
  sie annehmen. Vorher kommt keine Gruppennachricht an.
- **Nur mit gemeinsamen Freunden:** Eine Einladung wird nur angezeigt, wenn du mit
  mindestens einer Person aus der Gruppe befreundet bist — Fremde können dich nicht in
  Gruppen ziehen.
- **Gruppe verlassen:** Ein Klick, und du bist raus. Die anderen sehen „X hat die Gruppe
  verlassen" und deinen Namen nicht mehr in der Mitgliederliste.

### Neu — Nachrichten
- **⏳ Offline-Zustellung:** Ist dein Freund gerade offline, geht die Nachricht nicht mehr
  verloren. Sie wartet und wird **automatisch zugestellt**, sobald er wieder da ist.
  Solange zeigt sie eine Uhr statt einem Haken.
- **✓✓ Zustell- und Lesebestätigung:** 🕑 wartet · ✓✓ zugestellt · blaues ✓✓ gelesen.
- **🗑 Löschen und Zurückrufen:** Eine Nachricht bei dir löschen — oder **für alle**, dann
  verschwindet sie auch beim Freund und hinterlässt nur „Diese Nachricht wurde gelöscht".
- **🧹 Chatverlauf löschen:** Ein Klick leert den ganzen Verlauf inklusive aller Medien.
- **↩ Antworten & @Erwähnungen:** Auf eine bestimmte Nachricht antworten (sie wird zitiert),
  und in Gruppen jemanden mit `@Name` ansprechen — die Nachricht wird bei ihm hervorgehoben.
- **❤️ Reaktionen:** Mit ❤️ 👍 😂 😮 😢 🔥 auf eine Nachricht reagieren.
- **🔍 Suche:** Alle Chats nach Wörtern durchsuchen — auch in Sprachnachrichten-Transkripten.

## [2.9.0] — 2026-07-13

### Neu — Chat
- **🤝 Freundschaftsanfragen statt offener Tür:** Ein Unbekannter kann dir nicht mehr
  einfach schreiben. Er landet erst in einer Anfrage-Liste („Anna möchte mit dir
  schreiben") — mit **Annehmen / Ablehnen / Blockieren**. Bis zur Annahme kommt keine
  einzige Nachricht und keine Datei auf deine Platte. Blockierte Kontakte werden dauerhaft
  abgewiesen, ihr Verlauf gelöscht.
- **🔒 Ende-zu-Ende-Verschlüsselung:** Alle Nachrichten, Bilder und Videos werden mit
  X25519-Schlüsseltausch und AES-GCM verschlüsselt. Die Schlüssel entstehen lokal auf euren
  PCs und verlassen sie nie. Ein 🔒 im Chat zeigt, dass es aktiv ist.
- **🌍 Freunde im Internet:** Mit dem **Relay** (Zahnrad → Verbindungen) erreichst du auch
  Freunde in einer anderen Stadt. Dein Freund trägt einfach deinen **Jon-Code** ein. Der
  Relay-Server sieht dabei nur verschlüsselten Datensalat — er kann nichts mitlesen.
  Kostenlos, kein Konto.
- **🎙️ Sprachnachrichten:** Aufnehmen und senden — und wer nicht zuhören will oder kann,
  klickt auf **„📝 Text anzeigen"** und liest die Nachricht als Text.
- **👥 Gruppenchats:** Mehrere Freunde in einer Gruppe, mit Absendernamen an jeder Nachricht.
- **🤖 Jon schreibt für dich:** „Sag Anna, dass ich später komme" · „Was hat Anna
  geschrieben?" · „Wer sind meine Freunde?" (`send_friend_message`, `read_friend_messages`,
  `list_friends`).

### Neu — Mini Jon
- **Sein Gesicht zeigt seine Stimmung:** müde Augen, wenn er müde ist, ein Lächeln, wenn er
  zufrieden ist.
- **Er ist dein Bote:** Schreibt dir ein Freund, sagt Mini Jon dir Bescheid und liest die
  Nachricht auf Wunsch vor.
- **Er merkt, wenn du weg warst** und begrüßt dich, wenn du zurückkommst.

### Neu — Substanz
- **🚀 Setup-Assistent:** Beim ersten Start führt Jon durch die Einrichtung — Anbieter
  wählen, Schlüssel eintragen, Modell testen. Kein Bearbeiten der `.env` mehr nötig.
- **🔔 Update-Prüfung:** Jon sagt Bescheid, wenn eine neue Version auf GitHub liegt.
- **💾 Backup:** Gedächtnis, Wissensbasis, Skills und Einstellungen exportieren und auf einem
  anderen PC wieder einspielen (Zahnrad-Menü). API-Schlüssel bleiben absichtlich draußen.
- **✅ Automatische Tests:** 25 Tests für Tools, Verschlüsselung, Freundschaftsanfragen,
  Wissensbasis, Automationen und die API, dazu eine GitHub-Action, die sie bei jedem Push
  ausführt.

## [2.8.2] — 2026-07-12

### Behoben
- **Mini Jon brauchte ewig für ein einfaches „Hallo".** Er hat immer das Modell des großen
  Jon mitbenutzt — und das war `openai/gpt-oss-120b`, das auf NVIDIAs Servern hängt. Mini
  Jon hat jetzt sein **eigenes Modell** (Standard `openai/gpt-oss-20b`) und antwortet
  gemessen in **0,7–2 Sekunden**. Der große Jon behält sein Modell unverändert.
  Einstellbar im 🎨-Knopf bei Mini Jon.
- Mini Jon antwortet außerdem kürzer (max. 800 Tokens) — er plaudert, er schreibt keine
  Aufsätze.

## [2.8.1] — 2026-07-12

### Behoben
- **Die Tipp-Animation erschien nicht.** Drei Ursachen, alle behoben:
  1. Die Freundesliste wurde nur alle 2 Sekunden abgefragt, das Tippen aber beim Absenden
     sofort gelöscht — bei kurzen Nachrichten war die Animation nie zu sehen. Der
     Tipp-Status hat jetzt eine eigene, sehr leichte Abfrage **alle 0,4 Sekunden**.
  2. Das Signal wurde erst nach 2,5 Sekunden Tippen verschickt; jetzt schon nach 1,2 s.
  3. Freunde mit einem abweichenden Chat-Port wurden nicht erreicht — Jon merkt sich den
     Port des Freundes jetzt aus Suchruf und Handshake, statt ihn zu erraten.
- **Sich selbst als Freund hinzufügen** (per eigener IP) wird jetzt sauber abgelehnt.
- Freunde lassen sich mit `IP:Port` hinzufügen, falls jemand einen eigenen Chat-Port nutzt
  (`JON_CHAT_PORT`, `JON_DISCOVERY_PORT`).

## [2.8.0] — 2026-07-12

### Neu
- **✍️ Tipp-Animation:** Wenn dein Freund gerade schreibt, siehst du es sofort — animierte
  Punkte im Chatverlauf und „tippt …" in der Freundesliste. Das Signal geht direkt von PC
  zu PC und verschwindet automatisch, sobald die Nachricht da ist (oder nach 5 Sekunden).
- **🔔 Benachrichtigungen wie bei WhatsApp:** Schreibt dir jemand, während der Chat
  geschlossen ist, bekommst du eine Windows-Benachrichtigung mit Name, Avatar und
  Textvorschau (bei Medien „📷 Foto", „🎬 Video", „📎 Datei"), dazu einen kurzen Ton und
  ein Blinken in der Taskleiste. Ein Klick auf die Benachrichtigung holt Jon nach vorne
  und öffnet den Chat. Jede Nachricht meldet sich nur einmal.

## [2.7.2] — 2026-07-12

### Neu
- **Eigenes Modell für Telegram:** Unterwegs zählt Tempo, am PC Qualität. Telegram nutzt
  jetzt standardmäßig **`openai/gpt-oss-20b`** (Antwort in ~2 s), während App und Mini Jon
  weiterhin dein normal gewähltes Modell verwenden (Standard: `openai/gpt-oss-120b`).
  Einstellbar im Zahnrad-Menü → 🔌 Verbindungen → Telegram.

### Geändert
- Der automatische Modellwechsel bei einem hängenden Modell überschreibt deine Modellwahl
  **nicht mehr dauerhaft** — er gilt nur für die betroffene Antwort und sagt das auch dazu.

## [2.7.1] — 2026-07-12

### Neu
- **Freunde per Namen statt IP-Adresse:** Du tippst einfach den Namen deines Freundes ein.
  Jon ruft den Namen ins Netzwerk, der passende Jon meldet sich und der Kontakt ist da —
  Groß-/Kleinschreibung egal, IP-Adressen sind nicht mehr nötig.
- **Namen sind eindeutig:** Jeder Name existiert im Netzwerk nur einmal. Ist er schon
  vergeben, sagt Jon das direkt beim Anlegen oder Ändern des Profils.

### Behoben
- **Freunde-Erkennung fand niemanden bei mehreren Netzwerkadaptern:** Der Suchruf ging nur
  an `255.255.255.255` und wurde von Windows über einen beliebigen Adapter geschickt (z. B.
  einen VirtualBox- oder VPN-Adapter) — im echten WLAN kam er dann nie an. Jon sendet ihn
  jetzt gleichzeitig an alle Netzwerke, in denen dein PC hängt.
- **Zwei Jons auf einem PC:** Der Suchdienst belegt den Port jetzt mit `SO_REUSEADDR` und
  scheitert nicht mehr stumm, wenn er schon belegt ist.

## [2.7.0] — 2026-07-12

### Neu
- **👤 Profil:** Beim ersten Start fragt Jon nach deinem Namen (und einem Avatar). Er spricht
  dich fortan damit an; unter diesem Namen sehen dich auch deine Freunde. Jederzeit änderbar
  über das Profil im Freunde-Chat.
- **💬 Freunde-Chat (Peer-to-Peer):** Chatte mit anderen Jon-Nutzern — Text, **Bilder,
  Videos und Dateien** (bis 60 MB). Ohne Cloud, ohne Konto, ohne laufende Kosten:
  - **Automatische Erkennung:** Wer Jon im selben WLAN offen hat, erscheint automatisch in
    deiner Freundesliste (UDP-Suchruf auf Port 8757). Manuell geht auch — einfach die IP
    des Freundes eintragen.
  - **Direkt von PC zu PC:** Nachrichten gehen unmittelbar vom Backend des einen an das des
    anderen. **Gespeichert wird ausschließlich auf den beiden beteiligten Geräten** —
    Nachrichten in der lokalen Datenbank, Bilder und Videos in `p2p_media/`. Löschst du
    einen Kontakt, verschwinden Verlauf und Mediendateien mit.
  - **Sicherheit:** Der Chat läuft auf einem **eigenen, abgeschotteten Port (8758)**, der nur
    Nachrichten annimmt. Die Jon-API mit der PC-Steuerung bleibt weiterhin auf `127.0.0.1`
    und ist von außen nicht erreichbar.
  - Online-Status, Ungelesen-Zähler und ein 💬-Knopf mit Badge in der Kopfzeile.

## [2.6.2] — 2026-07-12

### Behoben
- **Antworten dauerten 2–12 Minuten — jetzt 2 Sekunden.** Ursache war weder Jon noch das
  Handy, sondern das bisherige Standardmodell **`openai/gpt-oss-120b`**: Es ist auf NVIDIAs
  kostenloser API dauerhaft überlastet und antwortete im Test **überhaupt nicht** (Timeout
  nach 90 s), woraufhin Jon es mehrfach neu versuchte. Gemessen: `gpt-oss-120b` ❌ Timeout ·
  `gpt-oss-20b` ⚡ 1,0 s · `llama-3.1-8b` ⚡ 0,5 s · `llama-3.3-70b` 🐢 45 s.
  - Neues Standardmodell: **`openai/gpt-oss-20b`** (schnell und weiterhin tool-fähig).
  - **Wächter gegen hängende Modelle:** Kommt nach 30 s kein einziges Token, bricht Jon ab
    statt minutenlang zu warten (`FIRST_TOKEN_TIMEOUT`). Timeout 180 s → 90 s, Wiederholungen
    4 → 2.
  - **Automatischer Modellwechsel:** Antwortet das gewählte Modell gar nicht, wechselt Jon
    selbstständig auf ein funktionierendes, sagt es dir im Chat und merkt sich die Wahl.
  - Ergebnis im Test: „Hallo" **2,4 s**, „Öffne example.com auf meinem PC" inklusive
    Tool-Ausführung **5,4 s**.

## [2.6.1] — 2026-07-12

### Behoben
- **Telegram brauchte bis zu 4 Minuten für eine Antwort:** Zwei Ursachen, beide behoben.
  1. Bei **jeder** Anfrage wurden alle 88 Tool-Definitionen mitgeschickt (~7.000 Tokens) —
     und bei jedem Tool-Aufruf noch einmal. Jon wählt jetzt vorab die passenden Tools zur
     Frage aus (Kern-Tools immer, Spezialgruppen nur bei Bedarf): **rund 50 % weniger Daten
     pro Anfrage**, spürbar schneller — auch in der Desktop-App und bei Ollama.
  2. Telegram wartete stumm auf die komplette Antwort. Jetzt zeigt Jon sofort „tippt …",
     meldet jede Aktion direkt als ⚙️-Nachricht (z. B. „⚙️ Öffnet youtube.com im Browser")
     und schickt die Antwort, sobald sie fertig ist. Mehrere Nachrichten werden parallel
     bearbeitet, nach 3 Minuten bricht er mit einer klaren Meldung ab.
- **Telegram-Befehle:** `/start` zeigt jetzt eine Hilfe, `/reset` löscht den Gesprächsverlauf.

### Neu
- **🎧 Amazon Music:** „Spiel XY auf Amazon Music" (`amazon_play`, `amazon_now_playing`).
  Amazon bietet keine offene Wiedergabe-Schnittstelle an, deshalb öffnet Jon die Suche im
  Amazon-Music-Player und drückt Play; eventuell muss dort einmal auf den ersten Treffer
  geklickt werden. Danach steuert Jon Pause/Weiter/Lautstärke wieder selbst. Kostenlos,
  ohne API-Schlüssel — für vollautomatisches Abspielen bleibt Spotify der bessere Weg.

## [2.6.0] — 2026-07-12

Alle neuen Verbindungen sind **kostenlos** — bezahlt wird weiterhin nur die LLM-API.
Einrichtung im Zahnrad-Menü unter **🔌 Verbindungen**.

### Neu
- **📧 E-Mail & Kalender:** IMAP-Postfach (`check_mail`, `read_mail`, `send_mail`) und
  ICS-Kalender (`get_calendar`). Ungelesene Mails und heutige Termine erscheinen
  automatisch im Tagesbriefing. Jon liest Mails vor und beantwortet sie auf Zuruf.
- **📲 Telegram-Fernbedienung:** Eigener Bot als Fernsteuerung — schreib Jon von unterwegs,
  er führt Aufgaben auf deinem PC aus und antwortet aufs Handy. Weltweit, ohne VPN, ohne
  offenen Port. Der erste Chat wird fest verknüpft, alle anderen abgewiesen.
- **👀 Datei-Wächter:** `add_watcher` überwacht Ordner und führt bei neuen Dateien
  automatisch eine Aufgabe aus („Sortiere neue Downloads nach Typ"). Ereignisgesteuert,
  anders als die zeitgesteuerten Automationen.
- **🎵 Medien-Steuerung:** `media_control` drückt die echten Windows-Medientasten —
  „leiser", „nächster Song", „Pause" funktioniert mit Spotify, YouTube und allem anderen.
- **🎧 Spotify:** „Spiel Musik von Spotify", „Spiel XY von Spotify", „Spiel was
  Entspanntes", „Was läuft gerade?" — Jon sucht den Song über die Spotify-Suche und startet
  ihn in der Spotify-App (`spotify_play`, `spotify_search`, `spotify_now_playing`). Ist die
  App nicht installiert, öffnet er automatisch den Web Player und drückt Play. **Ohne
  Premium nutzbar** — die offizielle Playback-API würde Premium verlangen, der Weg über
  Suche + `spotify:`-Link nicht.
- **🗣️ Natürliche Stimme:** Jon spricht mit einer echten Neural-Stimme (edge-tts, gratis)
  statt der Roboterstimme des Browsers; abschaltbar im Zahnrad-Menü. Ist zusätzlich
  `faster-whisper` installiert, läuft auch die Spracherkennung offline.
- **📊 Wochenrückblick:** `/woche` — oder automatisch jeden Sonntag: Jon schreibt einen
  persönlichen Rückblick aus seinem Gedächtnis, den Unterhaltungen, Automationen und Dreams.
- **🩺 PC-Gesundheitscheck:** `/check` — Speicherplatz, Arbeitsspeicher, größte RAM-Fresser,
  Autostart-Programme, Laufzeit und Temp-Müll, mit konkreten Aufräum-Vorschlägen, die Jon
  direkt umsetzen kann.
- **🏠 Smart Home:** Home-Assistant-Anbindung (`smarthome_devices`, `smarthome_control`) —
  „Jon, mach das Licht aus", Helligkeit und Heizungstemperatur inklusive.
- **🌐 Netzwerk & Drucker:** `scan_network` findet alle Geräte im WLAN (IP, MAC, Name),
  `wake_device` startet sie per Wake-on-LAN, `list_printers`/`print_file` drucken Dateien
  („Druck mir das aus").

## [2.5.3] — 2026-07-11

### Neu
- **📚 Wissensbasis (RAG):** „Jon, lern dieses PDF / diese Datei / diesen Ordner" — Jon
  speichert Dokumente in einer lokalen, durchsuchbaren Wissensbasis (SQLite, komplett
  offline) und zieht beim Antworten automatisch passende Stellen heran. Neue Tools:
  `learn_document`, `ask_knowledge`, `list_documents`, `forget_document`.
- **🌅 Tagesbriefing 2.0:** Das Briefing holt Wetter (Stadt im Zahnrad-Menü einstellbar),
  Erinnerungen, Wecker und geplante Automationen jetzt direkt aus dem Backend — schneller
  und zuverlässiger. Weiterhin täglich beim ersten Start und per `/briefing`.
- **⚡ Schnellfrage-Overlay:** `Strg+Alt+Leertaste` öffnet überall ein kleines
  Spotlight-Fenster — Frage tippen, Antwort streamt direkt hinein, inklusive
  Tool-Freigaben. `Esc` schließt, „In Jon öffnen" wechselt zur App.
- **📋 Clipboard-Historie:** Jon merkt sich lokal die letzten 50 kopierten Einträge.
  Über den 📋-Knopf (oder `/clipboard`) durchsuchbar und mit einem Klick wieder in der
  Zwischenablage. Jon selbst beantwortet „Was hatte ich vorhin kopiert?" per
  `clipboard_history`. Abschaltbar im Zahnrad-Menü.
- **🤖 Echte Automationen:** „Räum jeden Tag um 18 Uhr meinen Downloads-Ordner auf" —
  Jon führt geplante Aufgaben zur Uhrzeit wirklich mit seinen Tools aus (nicht nur
  Erinnerungs-Text) und berichtet im Chat. Tools: `add_task`, `list_tasks`,
  `delete_task`; Übersicht per `/tasks`.
- **📎 Datei-Anhänge im Desktop-Chat:** PDFs, Bilder und Textdateien per Drag & Drop,
  Büroklammer-Knopf oder Einfügen direkt in den Chat. PDFs werden als Text extrahiert,
  Bilder vom Vision-Modell beschrieben.
- **🎁 Zeitkapseln:** Gib Jon eine Nachricht an dein zukünftiges Ich — er versiegelt sie
  mit seiner aktuellen Stimmung und übergibt sie feierlich, sobald der Tag gekommen ist
  („Jon, Zeitkapsel für Weihnachten: …"). Das hat kein anderer Assistent.
- **🔒 Jon Code bleibt im Projektordner:** Im Coding-Modus sind alle Datei-Tools technisch
  auf den gewählten Workspace begrenzt, Zugriffe außerhalb werden blockiert und
  Shell-Befehle starten immer im Projektordner.
- **📷 Webcam-Blick:** „Jon, was siehst du über meine Webcam?" — Jon macht ein Webcam-Foto
  und antwortet **garantiert** mit einer Beschreibung: Fragt der Nutzer erkennbar nach der
  Webcam, übernimmt das Backend die Aufnahme und Bildanalyse selbst und streamt die Antwort
  direkt — kein Modell kann mehr „Das kann ich nicht" sagen. Aus Datenschutzgründen muss
  die Webcam zuerst im Zahnrad-Menü über **„Webcam erlauben"** aktiviert werden (Standard:
  aus). Auch direkt per **`/webcam`** (optional mit Frage: `/webcam was trage ich?`).
  Braucht `opencv-python` (wird automatisch installiert), Tool: `webcam_look`.
- **💬 Immer im Gespräch:** Jon und Mini Jon beenden jede Antwort mit einer kurzen
  Rückfrage oder einem konkreten nächsten Vorschlag — sag einfach Bescheid, wenn du das
  nicht willst.

- **📱 Handy = PC-App (1:1):** Mit `JON_LAN=1` in der `.env` liefert das Backend die
  komplette PC-Oberfläche im WLAN aus — am Handy einfach `http://<PC-IP>:8756/app`
  öffnen. Alle Funktionen (Tools, Wissensbasis, Automationen, PC-Steuerung) laufen dann
  1:1 auch vom Handy, weil der PC die Arbeit macht.
- **🖼️ Eigenes App-Icon:** Jon hat jetzt ein eigenes Gesicht als Icon (Schwarz/Gold,
  wie Mini Jon) — im Fenster, im Tray und im Installer. Kein Electron-Atom mehr.

### Behoben
- **Ollama zeigte rohes Tool-JSON statt zu antworten:** Kleine lokale Modelle schreiben
  Tool-Aufrufe oft als JSON-Text in die Antwort. Jon erkennt das jetzt, führt das Tool
  wirklich aus (inklusive Freigabe-Dialog) und antwortet danach in normalem Text — das
  JSON erscheint nie mehr im Chat.
- **Das zuletzt gewählte Modell wird beim App-Start wieder geladen:** Bei lokalen
  Anbietern (Ollama, LM Studio) wurde die gespeicherte Auswahl verworfen, weil sie keinen
  API-Key haben und als „nicht konfiguriert" galten.
- **„Mit Windows starten" funktioniert jetzt wirklich:** Der Schalter legt einen echten
  Autostart-Eintrag an, der `start-jon.bat` beim Hochfahren startet (Backend + App).
  Vorher wurde in der unverpackten Version nichts gestartet.

## [1.9.5] — 2026-07-08

### Behoben
- **Mini Jons Stimme klang bei Tabellen verzerrt:** Mini Jon schreibt jetzt ausschließlich
  einfachen Fließtext (normale Wörter, Zahlen, Emojis) — keine Tabellen, `|`, `**`, `#` oder
  Code-Blöcke mehr. Dadurch klingt das Vorlesen sauber. Die Sprach-Bereinigung im kleinen
  Jon wurde zusätzlich robuster.
- **Netlify-Fehler „Unable to read file usage.json" (und ähnliche):** Alle Laufzeitdaten
  (Unterhaltungen, Konten, Nutzung, Erinnerungen …) liegen jetzt außerhalb des
  Projektordners unter `%LOCALAPPDATA%\Jon\data`. Vorhandene Daten werden beim ersten Start
  automatisch dorthin übernommen. Der Projektordner enthält damit keine gesperrten
  Datendateien mehr, die den Upload stören. Empfehlung bleibt: für Netlify nur `website/`
  hochladen.

## [1.9.4] — 2026-07-08

### Behoben
- **Die App öffnete sich nach „Backend laeuft" nicht mehr, sondern blieb bei „Drücken Sie
  eine beliebige Taste" stehen:** Eine im letzten Fix ergänzte Log-Hinweiszeile enthielt
  Klammern (`echo (Vollstaendiges Log: …)`), die den `else`-Block der .bat vorzeitig
  schlossen — dadurch liefen `pause` und `exit` immer, noch bevor die App gestartet wurde.
  Klammern entfernt; die App startet wieder normal.

## [1.9.3] — 2026-07-08

### Behoben
- **Jon und Mini Jon starteten teils nicht mehr über die .bat:** Wenn in der Umgebung
  `ELECTRON_RUN_AS_NODE` gesetzt war, lief Electron als reines Node und stürzte sofort ab
  (`Cannot read properties of undefined (reading 'isPackaged')`). Ein neuer Start-Launcher
  (`electron/launch.cjs`) startet Electron jetzt garantiert im richtigen Modus, unabhängig
  von der Umgebung. Getestet: App startet jetzt auch mit gesetzter Variable.

## [1.9.2] — 2026-07-08

### Behoben
- **Netlify-Fehler „Unable to read file backend.log":** Das Backend-Log liegt jetzt außerhalb
  des Projektordners (unter `%LOCALAPPDATA%\Jon\backend.log`) statt in `data/`. Dadurch kann
  beim Hochladen keine gesperrte Log-Datei mehr stören. Empfehlung bleibt: für Netlify nur
  den Ordner `website/` hochladen.

## [1.9.1] — 2026-07-08

### Neu
- **Ein „Speichern"-Knopf** in der Fußzeile des Nutzer-Menüs (Konten, Nutzung & Skills …):
  Ein Klick speichert alles auf einmal — dein Prompt, die Automatik-Einstellungen, einen
  gerade bearbeiteten Skill und alle neu eingegebenen API-Schlüssel. Kurze Bestätigung
  „Alles gespeichert ✓". Die einzelnen Speichern-Knöpfe der Tabs bleiben erhalten.

## [1.9.0] — 2026-07-08

### Neu
- **👁️ Live Screen:** Über den Augen-Knopf oben schaut Jon durchgehend mit (alle ~30 s)
  und meldet sich nur, wenn er etwas wirklich Hilfreiches sieht — einen Fehler, ein
  Problem oder einen konkreten Verbesserungsvorschlag. Kein Dauergeplapper. Standardmäßig
  aus. Braucht ein bildfähiges Modell (z. B. NVIDIA-Vision, OpenAI, OpenRouter); optional
  über `vision_model` einstellbar.
- **🌙 Dream Mode automatisch:** Wenn dein PC ein paar Minuten ungenutzt ist, arbeitet Jon
  von selbst deine Dream-Aufgaben ab und zeigt dir die Ergebnisse, sobald du zurück bist.
  Einstellbar über `dream_auto` und `dream_idle_minutes` (Standard 5 Minuten). Aufgaben
  legst du wie gehabt mit `/dream <Aufgabe>` an.
- **Mini Jon fühlt sich lebendiger an:** Er schaut sich zufällig um, blinzelt
  abwechslungsreicher (auch mal doppelt), macht im Leerlauf kleine Mundregungen und
  blickt dich an, wenn er spricht.

## [1.8.1] — 2026-07-08

### Behoben
- **Provider/Modell ließen sich nicht mehr wechseln:** In 1.8.0 startete das Backend erst
  mit der App, wodurch die Modell-Liste beim Start leer blieb. Das Backend startet jetzt
  wieder wie vorher (über `start-jon.bat`), und die App versucht die Verbindung beim Start
  automatisch so lange, bis die Anbieter-Liste geladen ist — Wechseln geht wieder zuverlässig.
- **Rosige Wangen entfernt:** Mini Jons Gesicht ist jetzt klar ohne Wangenrot (im
  Konfigurator bei Bedarf wieder zuschaltbar).

### Bestätigt
- Mini Jon nutzt nachweislich alle Werkzeuge (Web-Suche, Wetter, Dateien erstellen,
  PC-Steuerung …) — genau wie der große Jon.

## [1.8.0] — 2026-07-08

### Mini Jon wird lebendiger
- **Dauergespräch:** Bei aktivem Mikrofon sagst du nur einmal „Jon" — danach hört Mini
  Jon durchgehend zu und du redest einfach weiter, bis du das Mikrofon wieder ausschaltest.
- **Nachrichten bleiben stehen,** bis Mini Jon zu Ende gesprochen hat.
- **Abbrechen:** Ein Klick auf Mini Jon (oder den ⏹-Knopf) stoppt Antwort und Stimme sofort.
- **Süßeres Gesicht:** rundere Glanzaugen, Blinzeln und rosige Wangen.
- **Konfigurator (🎨):** Farbe, Hintergrund, Augen-Stil, Wangen und Größe frei einstellbar,
  mit Live-Vorschau — die Änderungen erscheinen sofort bei Mini Jon.
- **Heller Modus färbt Mini Jon mit:** Schaltest du den weißen Modus ein, wird auch er weiß.
- **Mini Jon kann jetzt alles, was der große Jon kann** (Web-Suche, Dateien erstellen,
  PC-Steuerung …) — er erledigt Aufgaben selbst.

### Weniger Fenster, stabiler Start
- **Das Backend läuft jetzt direkt in der App** — kein separates „Jon Backend"-Fenster mehr.
  Schließt du Jon, wird auch das Backend beendet. `start-jon.bat` ist entsprechend schlanker.

### Vorgestellt
- Mini Jon ist jetzt auf der Website und im README vorgestellt.

## [1.7.0] — 2026-07-08

### Jon Jr lebt
- **Der kleine Jon heißt jetzt Jon Jr** und ist eine eigene Persönlichkeit: der
  neugierige, herzliche „Sohn" vom großen Jon, mit eigener Stimme und eigenem Wesen.
- **Sprich mit ihm:** Sag „Jon" oder „Mini Jon" — er antwortet mit „Ja?", damit du
  weißt, dass er zuhört, dann redest du einfach weiter und er führt es aus. Mikrofon
  am kleinen Jon an-/ausschaltbar.
- **Klick-Fix & exakte Hitbox:** Nur der Kreis selbst reagiert auf Klicks, alles
  drumherum ist durchklickbar (du kommst an dein Desktop dahinter). Antippen öffnet
  das Eingabefeld, Doppelklick die App, Ziehen verschiebt ihn.
- **Familie & Lebensgeschichte:** Fragst du Jon (oder Jon Jr) nach seiner Vergangenheit,
  erzählt er von seiner Frau Lena und den Kindern Emil und Mia — jeder Jon hat sein
  eigenes Leben.
- **Jon Jr nutzt immer dasselbe Modell und denselben Anbieter wie der große Jon.**

### Modellwahl bleibt gespeichert
- Wenn du Anbieter oder Modell wechselst, wird das jetzt gespeichert und ist beim
  nächsten Start wieder da — für jeden Anbieter.

### Stabiler auf neuen Geräten
- `pypdf` wird beim Ersteinrichten mit installiert (war in der Abhängigkeitsprüfung
  vergessen), damit die PDF-Funktion auf einem frischen Gerät sofort geht.

## [1.6.1] — 2026-07-08

### Behoben
- **Kleiner Jon reagierte nicht und sprach nicht:** Der ganze Kreis war als
  Fenster-Ziehbereich markiert, wodurch Electron alle Klicks verschluckte — das
  Eingabefeld ging nie auf. Ziehen läuft jetzt manuell (Kreis mit gedrückter Maus
  verschieben), einfacher Klick öffnet das Eingabefeld, Doppelklick die große App.
  Sprachausgabe nutzt jetzt dieselbe (funktionierende) Technik wie die App und wird
  bei der ersten Interaktion freigeschaltet, sodass Jon zuverlässig spricht und sein
  Mund mitgeht.

### Neu
- **Befehls-Übersicht:** Neuer Tab „Befehle" im Nutzer-Menü (Personen-Symbol) mit allen
  Slash-Befehlen, Tastenkürzeln, Beispielen für normale Aufträge und der Sprachsteuerung.

## [1.6.0] — 2026-07-08

### Jon wird eine Person
- **Persönlichkeit, Gefühle & Lebensgeschichte:** Jon ist kein neutraler Bot mehr. Er
  hat einen Charakter (warm, neugierig, trockener Humor), eine kleine Innenwelt mit
  Stimmungen, eine „Herkunftsgeschichte" (er ist am 6. Juli 2026 zum ersten Mal
  aufgewacht) und kann Geschichten erzählen. Abschaltbar in den Einstellungen.
- **Eigenes Gedächtnis (MEMORY.md):** Jon führt eine eigene Datei im Projektordner, in
  die er selbst schreibt — Gedanken, Erlebnisse und feste Fakten über dich. Tools
  `journal`, `read_journal`, `remember_about_user`, `set_mood`.
- **Kleiner Jon (Desktop-Begleiter):** Ein kleiner Kreis mit süßem, minimalistischem
  Gesicht lebt auf dem Bildschirm — immer im Vordergrund, verschiebbar. Beim Hochfahren
  ist er schon da und begrüßt dich mit Updates (Erinnerungen, Dream-Ergebnisse). Klick
  ihn an, um wie in der App mit ihm zu reden; er spricht, und sein **Mund bewegt sich
  passend zum Gesprochenen** (Lippen-Sync). Doppelklick öffnet die große App.
  Strg+Alt+K blendet ihn ein/aus, Autostart mit Windows aktivierbar.

### Neue Denk-Fähigkeiten
- **KI-Team (`/team <Thema>`):** Mehrere Persönlichkeiten (Entwickler, Designerin,
  Marketing, Jurist, CEO) diskutieren dein Thema und liefern eine gemeinsame Empfehlung.
- **Simulationen (`/simulate <Was wäre wenn …>`):** Jon spielt mehrere Zukunfts-Szenarien
  mit Wahrscheinlichkeiten und Fazit durch, statt nur allgemein zu antworten.
- **Zeitreise (`/snapshots`, `/snapshot <Name>`):** Jon speichert Projektstände inkl.
  Notizen/Entscheidungen und kann sie wiederherstellen (Tools `snapshot`,
  `list_snapshots`, `restore_snapshot`; vor dem Zurückspielen wird automatisch gesichert).
- **Dream Mode (`/dream <Aufgabe>`, `/dreams`):** Aufgaben, die Jon eigenständig
  ausarbeitet, während du weg bist — das Ergebnis präsentiert er dir danach.
- Jetzt 58 Tools. Neue Endpunkte unter `/api/team`, `/api/simulate`, `/api/snapshots`,
  `/api/dreams`, `/api/persona`.

## [1.5.0] — 2026-07-07

### Neu
- **Web-Suche:** `web_search`-Tool über DuckDuckGo — kostenlos, ohne API-Key. Jon kann
  jetzt aktuelle News, Preise, Öffnungszeiten und Fakten nachschlagen und Treffer bei
  Bedarf mit `http_get` öffnen.
- **Wetter:** `get_weather`-Tool über Open-Meteo (kostenlos, kein Key) — aktuelles
  Wetter plus Vorhersage bis 7 Tage, auf Deutsch.
- **Tagesbriefing:** Jon begrüßt einmal täglich beim Start mit Datum, Wetter,
  Erinnerungen und Weckern; jederzeit manuell mit `/briefing` abrufbar.
- **PDF-Analyse:** `read_pdf`-Tool liest den Text aus PDF-Dateien (jetzt 51 Tools).
- **Heller Modus:** Umschaltbar in den Einstellungen (Dunkel/Hell), wird gespeichert.
- **Globaler Hotkey + Tray:** Strg+Alt+J öffnet/versteckt Jon von überall. Das
  Schließen-X minimiert in den Infobereich neben der Uhr (Beenden über das Tray-Menü).
- **Chat-Export:** `/export` speichert die aktuelle Unterhaltung als Markdown-Datei.
- **Verlauf-Suche:** Suchfeld in der Seitenleiste filtert die Unterhaltungen.
- Das „Jon Backend"-Fenster zeigt die Server-Ausgabe wieder live an und schreibt sie
  gleichzeitig nach `data\backend.log`.

## [1.4.1] — 2026-07-07

### Behoben
- **Backend stürzte beim Neustart immer ab („Port 8756 bereits verwendet"):**
  `start-jon.bat` filterte die Portbelegung nach dem englischen Wort „LISTENING" —
  auf deutschem Windows heißt es „ABHÖREN", der alte Prozess wurde also nie beendet.
  Der Port-Kill läuft jetzt sprachunabhängig über PowerShell, und das Backend räumt
  beim Start zusätzlich selbst einen belegten Port frei (alte Instanz wird beendet,
  neue übernimmt).
- Ordner-Dialog in Jon Code: Fehler werden nicht mehr stillschweigend verschluckt —
  wenn kein Dialog erscheinen kann, öffnet sich das manuelle Pfad-Feld.
- Der „Verbunden"-Punkt prüft das Backend jetzt alle 15 Sekunden statt nur beim
  App-Start.

## [1.4.0] — 2026-07-07

### Neu
- **Echter Windows-Wecker:** `set_alarm` legt eine geplante Windows-Aufgabe an, die zur
  Uhrzeit (`time='07:00'`) oder nach Ablauf (`in_minutes=10`) mit Klingelton und Popup
  klingelt — auch wenn Jon geschlossen ist. Dazu `list_alarms` und `delete_alarm`.
- **`REASONING_EFFORT` in `.env`:** steuert, wie lange gpt-oss-Modelle „nachdenken"
  (`low`/`medium`/`high`). Standard `low` — Antworten kommen dadurch um ein Vielfaches
  schneller (gemessen ~0,7s statt ~4s bis zum ersten Token).

### Geändert
- **Konten & Modelle laden deutlich schneller:** `/api/providers` und `/api/accounts`
  fragen alle Anbieter parallel statt nacheinander ab, Modell-Listen werden 5 Minuten
  gecacht und hängende Anbieter nach 6s (`MODELS_TIMEOUT`) übersprungen. Gemini blockiert
  den Server dabei nicht mehr.
- `.env` enthält jetzt alle unterstützten Anbieter (OpenRouter, Groq, Together, xAI,
  Ollama, LM Studio, …) zum direkten Eintragen.
- System-Prompt kennt Wecker/Timer, `ms-settings:`-Deep-Links und die Regel, bereits
  erledigte Aktionen nie zu wiederholen.

### Behoben
- **Backend startete auf neuen Geräten nicht:** `audioop-lts` fehlte in den
  Requirements (Pflicht ab Python 3.13), und ein Fehler beim Import von
  Sprachpaket/PyAutoGUI riss den ganzen Server mit. Beides ist jetzt abgesichert —
  Sprach- und Maussteuerung melden sich sauber ab, statt den Start zu verhindern.
- **`start-jon.bat` deutlich robuster:** erkennt den Windows-Store-Python-Platzhalter,
  nutzt den `py`-Launcher, prüft alle Abhängigkeiten, installiert notfalls mit `--user`,
  schreibt `data\backend.log` und zeigt bei Startfehlern die letzten Log-Zeilen an.
- **Jon wiederholt keine erledigten Aktionen mehr** (z.B. YouTube nach einem „Danke"
  erneut öffnen): Tool-Antworten ohne Text erscheinen im Verlauf jetzt als
  „[Bereits erledigt: …]" bzw. „Erledigt ✅", und der Prompt verbietet Wiederholungen.

## [1.3.0] — 2026-07-07

### Neu
- **Coding-Agent im Terminal (`jon`):** autonomer KI-Coding-Agent für das VS-Code-Terminal
  mit Workspace-Analyse, präzisen Multi-Datei-Änderungen, Build/Test-Schleife und
  vollständigem Slash-Command-System (`/help /clear /status /usage /model /provider
  /agents /tools /memory /plugins /settings`). `/model` und `/provider` wechseln ohne
  Neustart. Installierbar über `pip install -e .` (Konsolen-Befehl `jon`) oder `jon.bat`.
- **Neue Provider:** OpenRouter, Groq, Together AI, xAI (Grok), LM Studio — plus Ollama als
  vollwertige lokale Gratis-Option mit Erreichbarkeits- und Modell-Erkennung.
- **`edit_file`-Tool:** präzise Textersetzung statt ganze Dateien zu überschreiben.
- **Eigenes System-Prompt:** in der App unter Konten → Prompt (ergänzen oder ersetzen).
- **Eigene Skills anlegen/löschen** direkt in der App; neuer **game-design**-Skill
  (2D-Canvas- und 3D-Three.js-Gerüste).
- **Erinnerungen/Loops:** `set_reminder`-Tool und Konten → Erinnerungen. Jon meldet fällige
  Erinnerungen, sobald die App offen ist, per Chat-Nachricht und Browser-Benachrichtigung.

### Hinweis
- Eine Anmeldung mit ChatGPT-/Claude-**Abo** (statt API-Key) bleibt bewusst außen vor: Die
  Anbieter stellen dafür keine offizielle Schnittstelle bereit. Für „gratis" sind Ollama und
  LM Studio (lokal) sowie Free-Tiers (NVIDIA, Gemini, Groq) vorgesehen.
- SMS-Benachrichtigung an eine Telefonnummer ist nicht enthalten (bräuchte einen
  kostenpflichtigen SMS-Dienst); stattdessen offizielle Browser-Benachrichtigungen.

## [1.2.0] — 2026-07-07

### Neu
- **Erweiterte Tools:** `search_files`, `make_dir`, `append_file`, `copy_path`,
  `zip_paths`, `unzip`, `clipboard_get`, `clipboard_set`, `screenshot`, `http_get`,
  `download_file`, `system_info`, `list_processes`, `lock_screen`.
- **Skill-System:** bearbeitbare Markdown-Anleitungen unter `skills/` mit den Tools
  `list_skills`, `read_skill`, `write_skill`. Mitgeliefert: `web-design`, `pc-automation`,
  `research`. Bearbeitbar in der App, per API und als Datei.
- **Konten-Bereich:** Anbieter per offiziellem API-Key verbinden, automatische
  Modell-Erkennung, Standardmodell wählen. Transparente Anzeige, wenn Tarif/Profil offiziell
  nicht verfügbar sind. Endpunkte unter `/api/accounts`.
- **`/usage`:** real gemessene Nutzung (Prompt-/Completion-/Gesamt-Tokens, Anfragen,
  durchschnittliche Antwortzeit, letztes Modell) pro Anbieter. Endpunkt `/api/usage`.
- **Handy-App:** Tool-Loop mit Apps öffnen, Teilen, Vorlesen, Standort, Uhrzeit,
  Web-Abruf; Spracheingabe (Web Speech API); Bildanalyse über Vision-Modelle.
- **Dokumentation:** kompletter `docs/`-Ordner (Features, Architektur, API, Skills,
  Android, Development, Examples, Roadmap, FAQ) und dieser Changelog.

### Geändert
- Antwortlimit auf bis zu 32.768 Tokens erhöht, mit automatischer Halbierung bei
  Modellgrenzen. Anthropic/Gemini erhalten sinnvolle Modell-Fallbacks.
- Provider lösen ihren API-Key jetzt dynamisch auf (env oder verbundenes Konto).
- System-Prompt kennt die neuen Fähigkeiten und Skills.

### Behoben
- Veraltete kompilierte `*.js`/`*.d.ts` aus `frontend/src` entfernt, die im Vite-Build die
  echten `.tsx`-Quellen überschatteten.

## [1.1.0] — 2026-07-06

### Neu
- Freigabe-Modus „Zuerst fragen" (Standard) / „Alles erlauben", dauerhaft gespeichert.
- Aufklappbare Tool-Chips: Befehl, Zusammenfassung und Ergebnis auf Klick.

## [1.0.0] — 2026-07-06

### Neu
- Erste Veröffentlichung: Multi-Provider-Chat, Streaming, Persistenz, PC-Steuerung,
  Maus-/Tastatur-Automatisierung, Sprachsteuerung, Langzeitgedächtnis, Website und
  Handy-App.
