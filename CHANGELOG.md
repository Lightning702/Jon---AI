# Changelog

Alle nennenswerten Änderungen an Jon.

## [4.34.8] — 2026-08-28

### 🔧 Werkzeuge und Einstellungen gehen wieder auf

Die Handy-Anpassung aus 4.34.7 hatte die Kopfzeile seitlich scrollbar gemacht. Ein
scrollender Kasten schneidet aber alles ab, was aus ihm herausragt — und damit auch die
Klappmenüs hinter 🧰 Werkzeuge, ⚙️ Einstellungen und der Modellauswahl. Sie öffneten
sich zwar, blieben aber unsichtbar in einer 28 Pixel hohen Zeile stecken.

- Die Kopfzeile schneidet nichts mehr ab: Statt zu scrollen, schrumpfen Anbieter- und
  Modellauswahl auf schmalen Bildschirmen mit und kürzen ihren Text.
- Geprüft bei 375 und 894 Pixel Breite: Werkzeugmenü, Einstellungen und die Panels
  dahinter (z. B. Kalender) öffnen wieder und passen vollständig auf den Bildschirm.

### 🔌 Verbindungen öffnen wieder

„Einstellungen → 🔌 Verbindungen …" tat manchmal einfach nichts. Der Knopf holte erst die
Einstellungen vom Backend und öffnete das Fenster danach — war das Backend gerade nicht
erreichbar, brach der Aufruf still ab und es passierte gar nichts.

- Das Fenster geht jetzt sofort auf, das Menü schließt sich sofort mit.
- Ist das Backend nicht erreichbar, öffnet es mit den Standardwerten, statt zu
  verschwinden. Das gilt für alle Stellen, die die Einstellungen laden.

### 🖥️ Start über start-jon.bat lässt kein Backend zurück

Startete man Jon über `start-jon.bat` und die App verabschiedete sich, lief das Backend
allein weiter — der nächste Start traf dann auf einen belegten Port. Und war Port 5173
noch von einem alten Entwicklungsserver besetzt, beendete sich die App sofort wieder,
weil Vite den Port fest braucht.

- Die bat räumt jetzt vor dem Start auch Port 5173 ab, aber nur, wenn dort wirklich ein
  `node` oder `electron` liegt.
- Endet die App — ob normal oder durch einen Absturz —, stoppt die bat das Backend
  hinterher: erst über den Shutdown-Endpunkt, dann gezielt über den Port, und nur eigene
  Python-Prozesse.
- Beendet sich die App mit einem Fehler, sagt die bat das mit Code und Pfad zum
  Backend-Log, statt einfach zu verschwinden.
- Die App selbst versucht im Entwicklungsmodus erneut zu laden, wenn der Vite-Server
  beim ersten Versuch noch nicht steht, und lädt sich nach einem Absturz der Oberfläche
  selbst neu.

## [4.34.7] — 2026-08-28

### 📱 Jon am Handy — die volle Oberfläche über den Raspberry Pi

Läuft Jon auf dem Pi, rufst du ihn im WLAN unter `http://<pi>:8756/app` auf. Diese
Oberfläche war bisher für Maus und großen Bildschirm gebaut. Jetzt lässt sie sich mit dem
Daumen bedienen.

- **Unterhaltungen als Schublade:** Auf schmalen Bildschirmen liegt die Seitenleiste
  aus dem Weg und fährt über ☰ herein, mit abdunkelndem Hintergrund. Ein Tipp auf eine
  Unterhaltung schließt sie wieder. Am PC ist alles unverändert.
- **Kopfzeile passt sich an:** Modellauswahl und Werkzeugleiste schrumpfen, scrollen
  seitlich und verlieren auf dem Handy nur ihre Beschriftungen — nichts wird mehr
  abgeschnitten, nichts schiebt die Seite in die Breite.
- **Kein Zoom-Gehüpfe mehr:** Eingabefelder haben auf Touchgeräten 16px, damit Safari
  und Chrome beim Antippen nicht mehr hineinzoomen. Knöpfe und Eingabezeile sind auf
  44 Pixel Höhe gewachsen.
- **Volle Höhe, echte Ränder:** Die App rechnet mit der dynamischen Fensterhöhe
  (`100dvh`) und respektiert die sichere Fläche unten, sodass die Eingabezeile nicht mehr
  hinter der Browserleiste oder dem Homebalken verschwindet.
- **Nachrichten und Karten** nutzen auf dem Handy fast die ganze Breite.
- **Zum Startbildschirm hinzufügen** funktioniert sauber: eigene Farbe für die
  Statusleiste, Vollbild-Modus und Titel.
- **Backend-Adresse:** Wird Jon über einen anderen Namen oder Port erreicht (Reverse
  Proxy, Tailscale, Port 80), spricht die Oberfläche jetzt denselben Ursprung an, statt
  stur `127.0.0.1:8756` zu versuchen.

## [4.34.6] — 2026-08-28

### 🗺️ Jon Maps versteht die Filter

Jon bedient die Kartenfilter jetzt selbst. „Starte eine Route von meinem Standort zum
nächsten Supermarkt" genügt — er sucht den nächstgelegenen Treffer, plant die Route und
zeigt die anderen Läden gleich daneben.

- Ziel und Zwischenstopps einer Route dürfen ein Filter (`supermarkt`, `apotheke`,
  `tankstelle` …) oder ein Laden- und Markenname sein: „zum Interspar in meiner Nähe".
- „nächster", „in meiner Nähe", „um mich herum" werden verstanden und aus der Suche
  herausgerechnet, statt als Ortsname im Geocoder zu landen.
- Neue Filter: **Bäckereien**, **Drogerien** und **Post & Paket** — zusammen 22 Stück.
  Marken wie Interspar, Billa, Hofer, dm, Shell oder McDonald's kennt Jon direkt und
  sucht sie in der passenden Kategorie.
- Findet er in 2,5 km nichts, weitet er auf 10 und 25 km aus, statt aufzugeben.
- In der Kartenkarte im Chat stehen die Alternativen als Chips: ein Klick rechnet die
  Route sofort dorthin um — Karte, Dauer, Entfernung und Text ziehen mit. „Groß öffnen"
  übernimmt die neue Route und schaltet den passenden Filter in Jon Maps scharf.
- Overpass läuft über drei Server: fällt einer aus, übernimmt der nächste.

### ✈️ Jon und Mini Jon unterwegs

Was Jon am PC kann, kann er jetzt auch über Telegram — und Mini Jon zum ersten Mal
überhaupt: Er hatte dort bisher gar keine Werkzeuge.

- Standort teilen (📎 → Standort), und „hier" ist wirklich dort, wo du bist. Live-Standorte
  werden dabei schonend übernommen, nicht bei jedem Zucken.
- Zu jeder Karte kommt ein **Kartenpin** zum Antippen, zu jeder Route zusätzlich ein
  Routenlink fürs Handy.
- **/lernen &lt;Thema&gt;** startet eine echte Tiefenrecherche am PC, **/lernstatus**,
  **/lernstop** und **/lernweiter** steuern sie. Sobald sie fertig ist, meldet sich Jon
  von selbst mit Zusammenfassung, Quellen und Dateien — auch wenn du die Recherche
  einfach im Gespräch angestoßen hast.
- In Gruppen antworten beide weiterhin nur auf @Erwähnung, dort aber mit einem bewusst
  kleinen Werkzeugkasten: Karten, Routen, Websuche, Wetter und Deep Learning. Kein
  Zugriff auf PC, Mails, Zwischenablage oder Freunde-Chats — den vollen Satz hat nur der
  Chat, der mit deinem PC verbunden ist.

### 🗑️ Jon deinstallieren

Im Zahnrad-Menü ganz unten: **Jon deinstallieren**. Der Dialog zeigt zuerst genau, was
verschwinden würde — Ordner, Dateizahl und Größe — bevor irgendetwas passiert.

- Gelöscht werden Jons Datenordner (Unterhaltungen, Gedächtnis, Einstellungen,
  Wissensbasis, Tresor, Kalender, Freunde, Schlüssel) und die `.env` mit den API-Schlüsseln.
- Der Autostart-Eintrag wird entfernt.
- Auf Wunsch startet danach der Windows-Deinstallierer und entfernt das Programm.
- Läuft Jon aus dem Quellordner, bleibt dieser stehen — der Dialog sagt das ausdrücklich.
- Der Knopf bleibt gesperrt, bis `JON LOESCHEN` eingetippt wurde. Systempfade wie das
  Benutzerverzeichnis werden grundsätzlich abgelehnt, auch wenn sie eingetragen würden.

## [4.34.5] — 2026-08-23

### 📍 Freunde auf der Karte

Jon Maps zeigt jetzt, wo deine Freunde sind — über Jons vorhandene, verschlüsselte
Freundesverbindung, ohne fremden Server.

- **Standort teilen ist standardmäßig aus.** Unter ▦ Ebenen → „Freunde auf der Karte"
  schaltest du ihn ein, entweder für alle Freunde oder für einzelne. Dort steht auch, wer
  dich gerade sehen kann, und ein Schalter nimmt es sofort wieder zurück.
- Freunde erscheinen als Marker mit ihrem Avatar. Frische Standorte leuchten blau, ältere
  werden blass und grau, damit du nie einen alten Punkt für den aktuellen hältst. Nach
  30 Minuten ohne Nachricht verschwinden sie ganz.
- Ein Klick auf einen Freund öffnet seine Karte: Entfernung, Alter der Meldung,
  Genauigkeit, dazu Route hin, Umsehen und Nachricht schreiben.
- Blockierst oder entfernst du jemanden, wird sein Standort sofort mitgelöscht.

### 🎯 Standort auf 100 statt 150 Meter

Jon fragt den Windows-Standortdienst jetzt mit hoher Genauigkeit an, nimmt mehrere
Messungen und behält die beste. Auf Geräten mit GPS greift damit auch das GPS. Auf einem
Desktop ohne GPS bleibt die WLAN-Ortung die physikalische Grenze — für metergenau setzt
du deinen Standort weiter mit einem Klick auf die Kartenmitte.

### 🕯️ ECHO: die Verstorbenen haben ein Modell

Bisher war der Verstorbene, den man in die Leichenhalle bringt, ein unsichtbarer Punkt auf
der Trage. Jetzt liegt dort wirklich jemand: eine Gestalt unter einem Leinentuch, mit
Kopf, Haar, dem Tuch über Brust, Armen und Beinen und einem Zettel am Fuß. Er erscheint,
wenn der Auftrag beginnt, und verschwindet, sobald du die Trage schiebst.

### 👀 Multiplayer: Freunde schauen wieder dorthin, wo sie hinsehen

In ECHO und AETHERIA drehte sich der Kopf entfernter Spieler immer zu **dir** statt in
ihre eigene Blickrichtung — die Blickneigung wurde zwar übertragen, aber nie benutzt.
Jetzt zeigt der Kopf genau dorthin, wo der Freund wirklich hinschaut, auch nach oben und
unten. (In der Blockwelt war es bereits richtig.)

### 🏝️ Harmonische Inseln: ein Ziel, das weitergeht

- **Der Spielstand wurde nie gespeichert.** Gespeichert wurden nur Fortschritt, Ort und
  Saat — Leuchtturmstufe und Herzen las das Spiel beim Start zwar, geschrieben hat sie
  aber niemand. Nach jedem Beenden fing man von vorne an. Das war der eigentliche Grund,
  warum sich das Spiel ziellos anfühlte. Jetzt bleibt alles erhalten.
- **Nach dem Leuchtturm ist nicht Schluss.** Bisher hörte das Sammeln auf, sobald das
  Licht brannte. Jetzt hält dieses Licht den Nebel zurück: Was du weiter zum Turm
  bringst, drängt ihn Stück für Stück ab — und mit jedem Stück zieht **ein neuer Bewohner
  zu**, manchmal mit Haustier. Die Anzeige zeigt, wie viele Bewohner schon da sind und
  wie weit es bis zum nächsten Zuzug ist. Jeder Zuzug braucht etwas mehr als der letzte.

### 🙂 Mini Jon und seine Tiere bekommen Wangen

Die 3D-Modelle von Mini Jon, Katze und Hund haben jetzt weiche rosa Wangen, wenn du
„Wangen" einschaltest — vorher gab es die nur in der flachen 2D-Ansicht. Der Schalter
wirkt sofort in der Vorschau und auf dem Desktop.

## [4.34.4] — 2026-08-23

### 🗺️ Jon Maps — eine eigene Karten- und Navigationsplattform

Jon hat jetzt seine eigene Karte. Kein eingebettetes fremdes Kartenfenster, sondern eine
Oberfläche, die zu Jon gehört: Liquid Glass über einer Karte, die den ganzen Bildschirm
einnimmt. Zu öffnen über 🧰 Werkzeuge → Jon Maps oder mit `/maps`.

- **Liquid Glass in Hell und Dunkel.** Die Panels sind echtes Glas: 30–46 px
  Hintergrundunschärfe, ein Lichtreflex, der beim Überfahren wandert, ein Rahmen aus
  Farbverlauf statt einer Linie, feine innere Kanten, sehr weiche Schatten und eine
  Rauschtextur, damit es Material bleibt und nicht Milchglas wird. Die Karte bewegt sich
  sichtbar hinter den Flächen. Umschalten jederzeit oben rechts, der Modus wird gemerkt.
- **Die Karte selbst.** Zoomen, schieben, drehen, neigen, 2D/3D-Schalter, 3D-Gebäude mit
  echten Höhen aus OpenStreetMap, echtes 3D-Gelände aus Höhendaten, Satellitenbilder,
  Fahrradnetz, ÖPNV-Netz und Fußwege als eigene Ebenen.
- **Globus.** Weit genug herausgezoomt wird die Karte zur Kugel und beim Hineinzoomen
  wieder flach — fließend, ohne Bruch. Auch von Hand schaltbar.
- **Suche** nach Städten, Adressen, Straßen, Restaurants, Hotels, Bahnhöfen, Flughäfen,
  Tankstellen, Parks und Sehenswürdigkeiten, dazu Schnellfilter für die Umgebung.
- **Echte Routen** für 🚶 Fuß, 🚗 Auto, 🚲 Fahrrad und 🚌 Bus & Bahn — mit Dauer,
  Entfernung, Alternativrouten, Zwischenstopps und Abbiegeanweisungen.
- **Dein Standort, auf den Meter statt auf die Stadt.** Jon holt den echten
  Windows-Standortdienst (auf ~150 m genau, ohne Schlüssel, ohne Cloud) und merkt sich
  das Ergebnis dauerhaft — auch für Fragen im Chat wie „Was gibt es hier in der Nähe?".
  Vorher wurde nur die IP geschätzt, die je nach Anbieter im falschen Bundesland oder
  sogar im falschen Land landet. Klappt der Standortdienst nicht, setzt du deinen
  Standort unter ▦ Ebenen mit einem Klick auf die Kartenmitte.
- **Erde-Ansicht** 🌎 — ein Knopf schaltet Satellitenbild, echtes 3D-Gelände und
  3D-Gebäude zusammen ein und neigt die Kamera. Über Luftbildern bekommen die Gebäude
  helle Fassaden und neutrales Licht, damit sie plastisch wirken statt als schwarze
  Klötze.
- **Street Exploration.** Auf einen Punkt klicken und auf Straßenebene wechseln: echte
  Straßenfotos, umsehen per Ziehen, vor und zurück entlang der Straße mit W und S.
- **Jon World Explorer.** Die Welt frei erkunden als 🚶 Mensch auf Augenhöhe, 🚗 Auto auf
  Fahrzeughöhe oder ✈️ Flugzeug mit freier Flughöhe. Eine berechnete Route lässt sich
  abfahren.
- **Maps im Chat.** Fragen wie „Wie lange brauche ich zu Fuß zum Bahnhof?" oder „Finde mir
  ein Restaurant in der Nähe" beantwortet Jon mit dem neuen Tool `maps` — die interaktive
  Karte erscheint direkt im Chat, mit Dauer, Entfernung und Alternativen.

### 🧠 Jon Deep Learning — Jon arbeitet sich selbst in ein Thema ein

„Jon, lerne alles über Quantenmechanik. Du hast zwei Stunden." Ab jetzt macht er das
wirklich. Zu öffnen über 🧰 Werkzeuge → Deep Learning oder mit `/lerne`.

- **Eigenständige Recherche** in Stufen: Thema analysieren, Unterthemen bilden, Plan
  aufstellen, suchen, Quellen öffnen und lesen, Inhalte bewerten, Quellen vergleichen,
  Widersprüche erkennen und gegenprüfen, Wissen herausziehen, speichern, Skill bauen,
  Wissen indexieren.
- **Zeitbudget.** Jon teilt die Zeit selbst auf die Unterthemen auf und wechselt weiter,
  sobald eins fertig ist. Nennt man die Zeit im Satz („du hast zwei Stunden"), erkennt er
  sie.
- **Live im Chat**: Fortschrittsbalken, verbleibende Zeit, aktuelles Unterthema und ein
  laufendes Protokoll, das zeigt, welche Seite gerade geöffnet, gelesen, verglichen oder
  gespeichert wird.
- **Wissensordner.** Das Ergebnis landet als Markdown unter `skills/<thema>/` mit
  README.md, einer Datei je Unterthema, sources.md und skill.md. Skills dürfen jetzt
  Ordner sein, und Jon liest einzelne Wissensdateien mit dem neuen Tool
  `read_skill_file`.
- **Pause, Fortsetzen, Abbrechen** jederzeit. Der Fortschritt wird laufend gespeichert;
  nach einem Neustart lässt sich eine unterbrochene Recherche weiterführen.
- **Verlauf** aller Recherchen mit Dauer, Quellenzahl, Dateien und Skill.
- **Sicherer Webzugriff.** Der Recherche-Agent liest nur: kein Login, kein Kauf, keine
  Formulare, keine ausführbaren Dateien, keine Adressen im lokalen Netz.

### Dazu

- Alle Kartendienste sind **kostenlos und ohne Schlüssel**: OpenFreeMap, Nominatim,
  Overpass, OSRM, Valhalla, Transitous, KartaView, CyclOSM, ÖPNV-Karte und offene
  Höhen- und Satellitenkacheln. Jede Ebene ist in der `.env` austauschbar.
- Rad- und Fußwege laufen über Valhalla, weil der öffentliche OSRM-Demoserver nur das
  Autoprofil kennt und sonst stillschweigend die Autoroute zurückgegeben hätte.
- Karte und Deep-Learning-Ansicht werden erst geladen, wenn man sie öffnet — der Start
  von Jon bleibt dadurch gleich schnell.

## [4.34.3] — 2026-08-11

### ⬇️ Downloader: ganze Amazon-Music-Playlists

Bisher ging pro Amazon-Music-Link genau ein Song. Jetzt nimmt der Downloader auch
Playlist- und Album-Links und lädt alles auf einmal.

- Einen Playlist-, Album- oder geteilten Amazon-Music-Link einfügen — Jon liest die
  komplette Trackliste mit Titel, Künstler und Länge und zeigt sie vor dem Laden an.
- **Alle Songs als ZIP**: Jon sucht zu jedem Titel die passende Aufnahme, macht MP3s
  daraus (320 kbps, drei Songs gleichzeitig) und packt sie durchnummeriert in eine
  ZIP-Datei, benannt nach der Playlist.
- Der Fortschritt zeigt „x von y Songs" und den Titel, der gerade läuft.
- Songs, zu denen es keine Aufnahme gibt, überspringt Jon und listet sie am Ende auf,
  statt den ganzen Download abzubrechen.
- Amazon Music bleibt kopiergeschützt — Jon lädt nichts von Amazon, sondern benutzt die
  öffentliche Trackliste als Einkaufszettel und holt die Aufnahmen wie bisher von YouTube.
- Nebenbei behoben: Geteilte Links auf einen einzelnen Song (`…/albums/…?trackAsin=…`)
  landeten beim Album statt beim Song, und der Künstlername fehlte oft. Beides kommt
  jetzt sauber aus den Song-Daten.

## [4.34.2] — 2026-08-10

### ⬇️ Downloader: gekaufte YouTube-Filme

„This video requires payment to watch" kam auch dann, wenn man den Film längst gekauft
hatte — der Downloader war schlicht nicht eingeloggt und sah nur die Bezahlschranke.

- Neuer Abschnitt **YouTube-Login** im Downloader. Jon liest die Cookies entweder direkt
  aus deinem Browser (Firefox, Brave, Edge, Chrome, Chromium, Opera, Vivaldi, Safari) oder
  aus einer exportierten `cookies.txt`, die du einmal hinterlegst.
- Scheitert ein Download an Bezahlung, Mitgliedschaft, Altersfreigabe oder der
  Bot-Abfrage, probiert Jon die hinterlegten Logins automatisch durch, statt sofort
  aufzugeben.
- Der Fehlertext sagt jetzt, was zu tun ist, und unterscheidet „noch kein Login
  hinterlegt" von „Login abgelaufen oder falsches Konto".
- Der Login-Bereich klappt von selbst auf, wenn ein Video ihn braucht.
- Cookies bleiben lokal in `<Daten>/downloader/cookies.txt` — nichts wird hochgeladen.

## [4.34.1] — 2026-08-10

### 👥 Koop in den neuen Spielen

Die Harmonischen Inseln und die Blockwelt spielt ihr jetzt zu zweit — über denselben
Freundschaftscode wie ECHO, AETHERIA und die alte Browser-Blockwelt.

- **K** öffnet die Koop-Anzeige: einer erstellt ein Spiel, der andere tippt den
  sechsstelligen Code ein. Wer beitritt, meldet sich selbst bereit; der Gastgeber startet
  mit Enter.
- Ihr seht euch gegenseitig laufen, sauber zwischen den Servertakten geglättet.
- In der Blockwelt bekommt der Gast die Welt des Gastgebers (gleiche Saat), und jeder
  gesetzte oder abgebaute Block erscheint auch beim anderen.
- Auf den Harmonischen Inseln zählt jede Lieferung für beide, und geschenkte Herzen
  zählen zusammen.
- Der Netzcode (`spiele/felwerk/src/fw/Koop.*`) liegt in der gemeinsamen Engine, spricht
  dasselbe JSON-Protokoll über TCP 8759 und wird von beiden Spielen geteilt.

### 🏝️ Die Harmonischen Inseln haben ein Ziel

Vorher konnte man sammeln und abgeben, aber nichts sagte einem wofür. Jetzt schon:

- Der Leuchtturm nennt seinen **Auftrag**: „braucht 3 × Korn", mit Fortschrittsbalken.
  Sechs Stufen, jede mit eigenem Wunsch — das schickt dich abwechselnd zur Farm, zum Berg
  und in die Werkstatt. Das Gewünschte zählt doppelt, alles andere einfach.
- Über dem Kopf mancher Bewohner schwebt ein **Wunsch**. Hast du das Passende dabei,
  schenkst du es mit **F** und bekommst ein **Herz**.
- Ist der Turm fertig, kommen alle Bewohner an der Werft zusammen, es steigen Lichter auf,
  und ein Abspann zählt die verschenkten Herzen. Weiterspielen geht trotzdem.

### 🎮 Steuerung

- **Blockwelt**: A und D waren vertauscht — der Rechts-Vektor zeigte nach links.
- **Harmonische Inseln**: W lief nach hinten (aus der Vorversion), jetzt läuft W nach vorn.

## [4.34.0] — 2026-08-10

### 🧱 Die Blockwelt hat keinen Rand mehr

Die Voxel-Sandbox ist wieder so weit wie im Browser — nur eben als eigenes Programm.

- **Endlose Welt**: Felder von 16 × 16 Blöcken entstehen, während du läufst, und werden
  hinter dir wieder freigegeben. Im Speicher liegen immer nur ein paar hundert Felder,
  egal wie weit du gehst.
- **Landschaften**: Aus drei Lagen Perlin-Rauschen wachsen Ebene, Wald, Wüste mit Kakteen,
  Schneeland und Gebirge, dazu Seen, Strände und Wälder. Die Anzeige nennt Landschaft und
  Position.
- **Echte Texturen**: 20 Kacheln werden beim Start Bildpunkt für Bildpunkt gemalt —
  Grasnarbe über Erde, Jahresringe im Stamm, Fugen im Ziegel, die weiße Binde am TNT.
  Keine einzige Bilddatei liegt bei.
- **16 Blocksorten** in der Leiste, mit 1–9 und dem Mausrad wählbar.
- **TNT und Enderperle**: Ein Klick auf TNT zündet die Lunte, die Explosion reißt ein Loch
  und steckt benachbartes TNT an. Die Enderperle fliegt im Bogen und versetzt dich dorthin,
  wo sie landet.
- Gespeichert wird nur, was du geändert hast — die Datei bleibt klein.

### 🏝️ Harmonische Inseln: W läuft nach vorn

In der isometrischen Ansicht liefen W und S verkehrt herum, weil die Blickrichtung von der
Kamera zum Ziel gerechnet wurde statt umgekehrt. Jetzt geht W nach vorn und S zurück.

## [4.33.9] — 2026-08-09

### 🏝️ Harmonische Inseln — ein neues Spiel zum Runterkommen

Ein schwebendes Archipel in der Abendsonne, in echter isometrischer Schrägsicht, als
eigenes Programm neben ECHO, AETHERIA und STARFALL.

- Vier Inseln, durch Holzbrücken verbunden: die Herzinsel mit Markt, runder Werkstatt und
  Gildenhalle, dazu Farm, Steinmutter und Werft.
- Korn, Stein und Bretter sammeln und zum unfertigen Leuchtturm bringen — er wächst in
  sechs Stufen, bis sein Licht brennt.
- Die Bewohner leben ihr eigenes Leben: sie wandern über die Brücken, tragen selbst
  Bretter zur Baustelle, haben Haustiere dabei und jubeln mit, wenn der Turm wächst.
- Alpakas, Schafe und Capybaras auf der Weide, Blätter im Wind, Gischt an den Ufern, ein
  Regenbogen über dem Berg und weiche Schatten unter allem.
- In C++ ohne Engine geschrieben; Gelände, Häuser, Figuren und Klänge entstehen zur
  Laufzeit. Läuft mit rund 150 Bildern je Sekunde auf einer Intel-UHD-620.

### 🧱 Blockwelt läuft jetzt als eigenes Spiel

Die Voxel-Sandbox startet nicht mehr im Browser, sondern wie ECHO als eigenes Fenster aus
dem Spiele-Tab.

- Neu in C++ geschrieben: Landschaft mit Hügeln, Stränden, Seen, Wäldern und Höhlen,
  weiche Kantenverschattung, Tag- und Nachtwechsel mit Sternen.
- Abbauen, setzen, graben, schwimmen, fliegen — und **Mini Jon schwebt mit**: Auf `T`
  baut er dir Haus, Turm, Brücke, Baum oder Leuchtfeuer, Block für Block zum Zuschauen.
- Änderungen werden gespeichert und beim nächsten Start wieder eingesetzt.

### 🌸 Cozy — ein dritter Modus in Weiß und Rosa

Neben Hell und Dunkel gibt es jetzt **Cozy**: zartes Rosa auf Weiß, für Jon und für Mini
Jon. Der Goldton der ganzen Oberfläche hängt jetzt an einer einzigen Stelle, deshalb
färbt sich alles mit — Knöpfe, Ränder, Verläufe, Bildlaufleisten.

### 👀 Mini Jon und sein Haustier sehen endlich aus wie gedacht

In den 3D-Modellen wurden Teile in falscher Reihenfolge verkettet — Ohren, Augen, Nase
und Beine rutschten dabei ins Innere des Körpers, übrig blieb eine glatte Kugel. Jetzt
sitzt alles am richtigen Platz:

- Katze und Hund haben Ohren mit Innenohr, Augen mit Iris und Lichtpunkt, Schnauze,
  Beine mit Pfoten und einen Schweif, der sich bewegt.
- Mini Jon hat glänzende Augen und ein Lächeln aus dem Goldton.
- Neue Beleuchtung mit Haupt-, Fülllicht und Fellschimmer.

### 🖊️ Kleinigkeiten

- Haustierauswahl umgezogen: sie steht jetzt bei „Mini Jon anpassen" zwischen Farbe,
  Augen und Größe, nicht mehr im Einstellungsmenü.
- Heller und Cozy-Modus sind etwas abgetönt — auf Weiß in Weiß war zu wenig zu erkennen.
- Lange Texte brechen sauber um: im Spiele-Tab werden Beschreibungen gekürzt („mehr
  lesen" klappt sie auf), und in den Haftnotizen läuft kein Wort mehr aus dem Zettel.

## [4.33.8] — 2026-08-08

### ☎️ Jon anrufen — und von überall telefonieren

Bisher rief nur Jon an. Jetzt geht es in beide Richtungen, und zwar von überall.

- **Jon anrufen**: In der SIP-App einfach den eigenen Benutzernamen wählen. Jon hebt ab,
  begrüßt dich und redet mit dir — mit demselben Zugriff wie im Chat. Der Begrüßungssatz
  ist über `phone_greeting` frei wählbar, und wer das nicht will, schaltet eingehende
  Anrufe mit `phone_accept_incoming` ab. Ohne gültiges SIP-Passwort nimmt Jon nichts an.
- **Von unterwegs, mit mobilen Daten**: Die Serveradresse steht jetzt auf
  **Automatisch** — Jon nennt jedem Anrufer die Adresse, über die dieser ihn tatsächlich
  erreicht hat. Zu Hause die WLAN-Adresse, unterwegs die Tailscale-Adresse. Beim
  Verlassen des Hauses muss nichts umgestellt werden. Die Anleitung für Tailscale steht
  in `docs/TELEFON.md`; der SIP-Port gehört weiterhin **nicht** in den Router.

### 🔇 Jon sagt jetzt, wenn er nichts hört

Kam beim Anruf kein Ton an, wartete Jon stumm. Jetzt sagt er es nach sechs Sekunden ins
Telefon, und der Anrufeintrag nennt den Grund statt pauschal „Gespräch beendet" —
meistens fehlt die Firewallregel für die Sprachpakete.

### 🔌 SIP kommt nach einem Neustart wieder hoch

Hielt nach dem Schließen der App noch der alte Prozess den Port, blieb die
Telefonfunktion stumm und wirkte wie vergessen. Die Sockets binden jetzt mit
`SO_REUSEADDR`, und schlägt es trotzdem fehl, nennt die Meldung den Prozess, dem der Port
gehört.

Dazu: SIP läuft zusätzlich über **TCP** — manche SIP-Apps sprechen kein UDP und meldeten
sonst nur „IOError". Jeder Anmeldeversuch wird mit Quelle, Transport und Grund
protokolliert und im Einrichtungs-Tab angezeigt.

## [4.33.7] — 2026-08-08

### 📞 Jon ruft dich auf dem Handy an

Sag „Jon, ruf mich in 15 Minuten an" — und 15 Minuten später klingelt dein Handy. Nicht
eine Benachrichtigung, sondern ein **echter eingehender Anruf** mit Annehmen und
Ablehnen. Du hebst ab, Jon sagt „Hey Felix!", und ihr redet.

**Ohne Anbieter, ohne Kosten.** Kein Twilio, kein Vonage, keine Telefonie-API. Jon ist
selbst die Telefonanlage: ein SIP-Registrar und ein SIP-Endpunkt direkt im Backend, dazu
ein eigener RTP-Sprachkanal. Dein Handy meldet sich mit einer kostenlosen SIP-App
(Linphone) bei Jon an, alles läuft über dein eigenes Netz.

- **Natürliche Zeitangaben**: „jetzt", „in 20 Minuten", „heute um 18 Uhr", „morgen um 9",
  „nächsten Montag um 17 Uhr" — und für Wiederkehrendes „jeden Montag um 18 Uhr".
  Zeitpunkte werden mit Zeitzone gespeichert, Sommer- und Winterzeit sind abgedeckt.
- **Echtes Gespräch**: Jon hört durchgehend zu, merkt an einer mitlaufenden
  Sprecherkennung, wann du fertig gesprochen hast, und antwortet satzweise — der erste
  Ton kommt, bevor der ganze Satz fertig berechnet ist.
- **Unterbrechen geht**: Sagst du „warte" oder „stopp", während Jon redet, bricht er
  mitten im Wort ab und hört zu.
- **Telefonstimme statt Chatbot**: Am Telefon gilt ein eigener Systemprompt — kurze
  gesprochene Sätze, kein Markdown, keine Aufzählungen, keine Emojis.
- **Neue Werkzeuge**: `call_user`, `schedule_call`, `list_scheduled_calls`,
  `cancel_call`, `update_call`. „Welche Anrufe sind geplant?", „Lösch den um 18 Uhr",
  „Verschieb ihn auf 19 Uhr" funktionieren im Chat.
- **Eigener Bereich** unter Werkzeuge → 📞 Telefonanrufe: Ampel für SIP, Handy und
  Bereitschaft, Einrichtungsassistent mit den fertigen Zugangsdaten, geplante Anrufe zum
  Bearbeiten, Testanruf-Knopf und Gesprächsverlauf.

**Alles lokal**: Spracherkennung mit faster-whisper auf deinem Rechner, Sprachausgabe mit
Jons gewohnter Stimme, und das Sprachmodell ist das, was du in Jon eingestellt hast —
auch Ollama. Audio wird nur im Arbeitsspeicher verarbeitet und danach verworfen; ein
Gesprächsprotokoll entsteht nur, wenn du es einschaltest.

**Sicherheit**: Das SIP-Passwort erzeugt Jon zufällig, angemeldet wird per Digest, und
Jon nimmt selbst keine eingehenden Anrufe an. Für unterwegs gehört der Port nicht ins
Internet, sondern in ein VPN — die Anleitung für Tailscale steht in `docs/TELEFON.md`.

Warum kein Asterisk, obwohl es dafür gemacht ist: Asterisk gibt es für Windows nicht. Es
bräuchte WSL2 oder Docker, und deren NAT-Netz macht gerade die dynamischen RTP-Ports
unzuverlässig. Der eingebaute Stack startet einfach mit `start-jon.bat` mit.

35 neue Tests, 286 insgesamt.

## [4.33.6] — 2026-08-07

### 🕳️ STARFALL rechnet die Scheibe jetzt relativistisch

Die Schwarzloch-Simulation zeigt nicht mehr eine hübsche Näherung, sondern das, was
Astrophysiker rechnen. Fünf Änderungen bringen das Bild näher an das Beobachtbare:

- Das Strahlungsprofil der Akkretionsscheibe folgt dem relativistischen Fluss nach
  **Page und Thorne (1974)** statt der newtonschen Näherung. Der Fluss verschwindet
  exakt an der ISCO und fällt weit außen mit `r⁻³`. Für Schwarzschild liegt das
  Maximum bei 8,39 r_g statt bei 8,17 r_g; mit Spin wandert die Scheibe nach innen
  und wird heißer.
- **Chandrasekhar-Randverdunklung** für streuungsdominierte Scheibenatmosphären.
- **Endliche Schichtdicke**: die optische Tiefe folgt der tatsächlichen Weglänge durch
  die Schicht, dazu Kantenaufhellung am Innenrand.
- **Differentielle Scherung** im Turbulenzmuster — Strukturen werden zu Spiralfäden
  ausgezogen, statt rund zu bleiben.
- **Zeitliche Akkumulation**: Steht die Kamera still, friert die Simulationszeit ein
  und das Bild baut sich in voller Auflösung über bis zu 192 Halton-versetzte
  Abtastungen auf. Vorher lief der Raymarch dauerhaft in 28 bis 70 Prozent Auflösung
  — genau das hat den Photonenring verwaschen.

Die angezeigten Kennzahlen kommen aus demselben Page-Thorne-Profil wie das Bild,
damit Anzeige und Darstellung nicht auseinanderlaufen.

### 📦 STARFALL ist im Windows-Paket dabei

Setup und portable ZIP nehmen den STARFALL-Ordner jetzt mit — wer Jon installiert, hat
alle vier Titel der FelWorks Game Collection sofort unter Werkzeuge → Spiele. Saves,
Einstellungen und die Logdatei bleiben dabei außen vor.

### 🎬 Werbespot direkt im Browser

Neuer Ordner `motion/`: ein 20-Sekunden-Spot für Jon im Hochformat 1080 × 1920 bei
60 FPS, der komplett zur Laufzeit entsteht — jedes Pixel aus WebGL-Shadern, jeder Ton
aus Oszillatoren, keine einzige Bild- oder Videodatei als Vorlage. `index.html`
öffnen, **MP4 exportieren** drücken, fertige Datei hochladen. Kein After Effects,
kein ffmpeg.

### ⬇️ Website: eigener Abschnitt zum Downloader

Die Website erklärt jetzt, was der eingebaute Downloader kann: Vorabprüfung mit Titel,
Kanal, Dauer und Vorschaubild, vier Qualitätsstufen oder MP3, Fortschritt in Klartext
— und der Hinweis, dass alles lokal auf dem eigenen PC läuft.

## [4.33.0] — 2026-08-03

### 🤝 „KI teilen" ist jetzt verständlich

Das Freigabe-Fenster war eine Wand aus Fachbegriffen. Jetzt fragt es zuerst das
Einfachste: **Gebe ich meine KI frei — oder nutze ich die von jemandem?** Danach kommen
nummerierte Schritte statt Optionen.

- Ganz oben steht in einem Satz, was Teilen überhaupt bedeutet: Ein Freund schickt seine
  Fragen an **deine** KI, braucht selbst keinen Schlüssel und sieht von deinem PC nichts
  außer den Antworten.
- Aus „Sichtbarkeit: privat / eingeladen / öffentlich" wurde die Frage **Wer darf
  mitschreiben?** mit den Antworten *Jeder mit meinem Code*, *Nur wen ich einlade* und
  *Gerade niemand* — jede mit einem Satz Erklärung.
- Der Code steht groß da, mit **Code kopieren** und **Link kopieren** und dem Hinweis,
  wann man was braucht (gleiches WLAN oder nicht).
- Aus „Verbundene Benutzer" wurde **Wer gerade verbunden ist** mit Klartext:
  *schreibt gerade*, *verbunden*, *gerade offline* — und **rauswerfen** statt „entfernen".
- Läuft Ollama gar nicht, sagt das Fenster das sofort, statt dich raten zu lassen.
- Name, Beschreibung und „neuer Code" sind unter **Details** eingeklappt.

Der Knopf sitzt jetzt im **Freunde-Chat** links unter deinem Jon-Code — dort, wo man
sowieso ist, wenn man etwas mit Freunden teilen will. Aus der Chat-Kopfzeile ist er raus.

### 🪪 Jon-Code neben jedem Namen

In der Freundesliste steht unter jedem Namen sein **Jon-Code**, und im Chat-Kopf des
offenen Gesprächs ebenso. Ein Klick kopiert ihn — praktisch, wenn du einen Freund an
jemand anderen weiterreichen willst.

### 🎮 ECHO: Sprung nach vorn mit Q

**Q** teleportiert dich **3 Meter in Blickrichtung**, danach **10 Sekunden Abklingzeit**.
Der Sprung prüft vorher per Strahl, ob der Weg frei ist, hält vor Wänden an, setzt dich
sauber auf den Boden und bricht ab, wenn am Ziel kein Platz ist („Kein Platz zum
Springen"). Während die Abklingzeit läuft, zeigt Jon die Restsekunden an.

### 🧭 Mitspieler schauen in die richtige Richtung

In der **Blockwelt** saß die Gesichtstextur auf der falschen Seite des Kopfes: Die
Spielfiguren blickten exakt entgegengesetzt zu ihrer Laufrichtung, weil das Gesicht auf
der **+Z**-Seite lag, die Blickrichtung im Spiel aber **−Z** ist. Gesicht und Kopfneigung
sitzen jetzt richtig — auch bei Jon selbst. ECHO und AETHERIA waren bereits korrekt
(dort zeigt das Modell mit Nase und Augenbrauen nach −Z).

## [4.32.9] — 2026-08-02

### 🧊 Echte 3D-Modelle für Mini Jon, Katze und Hund

Aus der Schattierung von 3.38.0 sind jetzt richtige 3D-Modelle geworden. Neu ist
`frontend/electron/pet3d.js`: ein eigener **WebGL-Renderer ohne jede Fremdbibliothek** —
nichts wird nachgeladen, alles läuft offline im Mini-Jon-Fenster.

- **Echte Geometrie** statt Zeichnung: Kugeln, Ellipsoide, Kegel und ein Torus werden zur
  Laufzeit erzeugt, mit Normalen pro Vertex.
- **Echte Beleuchtung**: gerichtetes Licht, Ambient, Blinn-Phong-Glanzlicht und ein
  Rim-Light, alles pro Pixel im Fragment-Shader. Tiefentest an, damit sich Teile richtig
  verdecken.
- **Mini Jon** ist eine Kugel in deiner Gesichtsfarbe mit goldenem Ring, zwei Augen und
  einem Mund, der sich beim Sprechen wirklich öffnet — Lippensynchronität und Blinzeln
  steuern jetzt das 3D-Modell.
- **Die Katze** hat Körper, Kopf, zwei Ohren mit rosa Innenseite, Schnauze, Nase,
  Schnurrhaare und einen geschwungenen Schwanz. **Der Hund** hat Körper, Kopf, Schnauze,
  feuchte Nase, Schlappohren und Rute. Beide drehen sich sanft, wippen und schlafen
  sichtbar ein; die Laufrichtung dreht das Modell mit.
- **Fällt WebGL aus**, schaltet Jon automatisch auf die plastische CSS-Darstellung von
  3.38.0 zurück statt gar nichts zu zeigen.

### Der Schalter sitzt jetzt dort, wo er hingehört

Der 3D-Schalter ist aus dem Zahnrad-Menü **in „Mini Jon anpassen"** umgezogen — direkt
neben Farbe, Augen und Größe. Dort gibt es auch eine **Live-Vorschau in 3D** mit
Umschalter zwischen Mini Jon, Katze und Hund; Farbwechsel sind sofort am Modell zu sehen.

Nachgemessen im Browser: Mini Jon füllt 68 % der Fläche mit 822 verschiedenen
Farbwerten, Katze und Hund liegen bei 346 bzw. 783 — das ist echte Schattierung auf
gekrümmten Flächen, keine Flächenfüllung. Ausschalten stellt exakt die alte flache
Darstellung wieder her.

## [3.38.0] — 2026-08-02

### 🧊 3D-Modus für Mini Jon, Katze und Hund

Ein Schalter im Zahnrad-Menü unter **Mini Jon & Haustier** — und alle drei bekommen Tiefe:

- **Mini Jon** wird zur Kugel statt zur Scheibe: ein Glanzlicht oben links, Abschattung
  unten rechts, dazu eine sanfte Drehung um die eigene Achse (`rotateY`/`rotateX` mit
  Perspektive) und ein mitwandernder Bodenschatten.
- **Katze und Hund** bekommen plastische Verläufe für Körper, Kopf und Ohren, Glanzlichter
  in den Augen, eine feuchte Nase, einen weichen Bodenschatten und dieselbe leichte
  Drehung. Ihre Laufrichtung bleibt dabei erhalten.
- Der Schatten überlebt jetzt auch das Schlafen: `setPetSleep` arbeitet mit einer
  CSS-Klasse statt einem Inline-Filter, der den Schatten vorher überschrieben hätte.
- Aus bleibt aus: Ohne den Schalter sieht alles exakt so aus wie bisher.

### 🤝 Ollama teilen direkt aus dem Chat

- Neuer Knopf **🤝 Ollama teilen** in der Chat-Kopfzeile. Er öffnet Freigabe und
  Verbindungsaufbau in einem Fenster — Server freigeben, Code kopieren oder den Code eines
  anderen eintragen.
- **Neuer Eintrag in der Anbieterauswahl**: Sobald dir jemand seinen Server freigegeben
  hat, steht dort **„Ollama von &lt;Name&gt;"** — nur dann, sonst nicht.
- Wählst du ihn, ist **das Modell fest vorgegeben**: Es ist genau das, was der Besitzer
  teilt. Statt der Modell-Auswahl steht ein Schloss mit dem Modellnamen; ändern kann man
  es nicht. Wechselt der Besitzer sein Modell, zieht die Anzeige beim nächsten
  Aktualisieren nach.

### 🛑 Der Knopf neben dem X beendet jetzt wirklich alles

Der Pfeil-nach-unten in der Titelleiste hat Jon bisher nur ausgeblendet — Backend und
Konsolenfenster liefen weiter. Jetzt stoppt er **alles**: Jon-Fenster, Mini Jon, das
Backend und das zugehörige Konsolenfenster (`start-jon.bat`, `jon-backend.exe`,
`app.main`). Wer Jon weiter im Hintergrund laufen lassen will, nimmt den Eintrag
**Fenster ausblenden (Jon läuft weiter)** im Infobereich.

Die komplette Suite bleibt grün (247 → 251).

## [3.37.2] — 2026-08-02

### 🤝 Ollama-Server über den Jon-Chat freigeben

Wer die stärkere Grafikkarte hat, kann seinen Ollama-Server jetzt für andere Jon-Nutzer
freigeben. Sie chatten darüber, als wäre es ihr eigenes Modell — ohne Zugriff auf
irgendetwas anderes auf dem fremden PC.

- **Neuer Bereich „Serverfreigabe"** in den Ollama-Einstellungen: an/aus, Freigabename,
  Beschreibung, Sichtbarkeit (**Privat**, **Nur Eingeladene**, **Öffentlich**),
  Freigabecode und Einladungslink zum Kopieren, jederzeit abschaltbar.
- **Verbinden per Code oder Link**: `AB39KD12` genügt im Heimnetz — Jon sucht den Server
  per Broadcast (UDP 8762). Über Tailscale oder von außerhalb nimmt man
  `AB39KD12@100.101.102.103:8758` bzw. `jon://ollama/…`.
- **Automatisch in der KI-Auswahl**: Modelle eines verbundenen Servers erscheinen unter
  dem Anbieter `ollama` als eigene Gruppe „Freigabe <Code>". Chatverlauf, Streaming und
  sämtliche Ollama-Einstellungen (Temperatur, Top P, Top K, Max Tokens, Context Length,
  Keep Alive, Seed, System Prompt, Timeout) gelten unverändert weiter.
- **Verwaltung für den Besitzer**: verbundene Benutzer mit Adresse, Verbindungsstatus
  (aktiv/verbunden/offline), genutztem Modell, Anzahl Sitzungen und Anfragen sowie
  Zeitpunkt der letzten Aktivität. Einzelne Benutzer entfernen oder allen den Zugriff
  entziehen — beides wirkt sofort, auch mitten in einer laufenden Antwort.
- **Einladungen** gelten für genau einen Benutzer und verfallen nach der ersten Nutzung.
  **Neuen Code erzeugen** macht den alten augenblicklich ungültig.

### Sicherheit

- **Kein offener Zugriff.** Beim Beitritt bekommt jeder Gast ein eigenes Zugriffstoken
  (256 Bit, `secrets.token_urlsafe`). Ohne gültiges Token antwortet jeder
  `/share/api/*`-Endpunkt mit **401** — auch bei öffentlicher Sichtbarkeit.
- Tokens liegen **nur als SHA-256-Hash** in `data/ollama_share.json` und werden
  zeitkonstant verglichen (`hmac.compare_digest`).
- Die Freigabe hängt am LAN-Chat-Port **8758**, **nicht** an Jons Steuer-API
  (127.0.0.1:8756). Freigegeben ist ausschließlich das Antworten des Modells — Chats,
  Dateien, Werkzeuge und PC-Steuerung des Besitzers bleiben unerreichbar. Die Werkzeuge
  eines Gastes laufen weiterhin auf seinem eigenen Rechner.
- Fehlversuche werden pro Adresse gebremst (10 pro Minute).
- Anfragen von Gästen werden gefiltert: Sampling-Werte (Temperatur, Top P, Top K, Seed,
  Stop) gelten, aber **Context Length** und **Max Tokens** deckelt der Gastgeber auf seine
  eigenen Einstellungen, und sein Keep Alive bleibt gültig — niemand kann den Speicher des
  Gastgebers mit `num_ctx: 1000000` sprengen.
- Freigabe aus = alle Tokens sofort ungültig; laufende Streams brechen ab.

### Dokumentation

Neues Kapitel „Server für andere freigeben" in [docs/OLLAMA.md](docs/OLLAMA.md) und auf
[getjon.info](https://getjon.info/ollama.html), dazu README (de/en), FEATURES, API, FAQ
und EXAMPLES.

30 neue Tests decken Sichtbarkeiten, Einladungen, Beitritt, Tokenprüfung, Widerruf,
Rate-Limit, Netzwerksuche, die Gastgeber-Endpunkte und den Chat über einen fremden Server
ab; die komplette Suite bleibt grün (217 → 247). Zusätzlich end-to-end gegen einen echten
Ollama-Server geprüft: Gastgeber freigeben, Gast verbinden, Antwort streamen, Zugriff
widerrufen — der Gast bekommt danach sofort eine klare Meldung.

## [3.37.0] — 2026-08-02

### 🦙 Ollama komplett eingebaut

Ollama war bisher nur ein Eintrag in der Anbieterliste mit fester Adresse aus der `.env`.
Jetzt hat es einen eigenen Bereich in den Einstellungen, einen sichtbaren Serverstatus und
alle Regler, die Ollama wirklich kennt — und es darf auf einem ganz anderen Rechner laufen.

- **Neuer Einstellungsbereich „Ollama"** im Zahnrad-Menü mit Statuszeile
  (Online/Offline · Antwortzeit · Modellanzahl) und dem Fenster **Server & Modelle …**.
  Es gibt **keinen** neuen Anbieter und keine zweite Anbieterseite: Die Anbieterliste ist
  unverändert, nur der vorhandene `ollama`-Eintrag kann jetzt mehr.
- **Offizielle Ollama-API** (`/api/chat`, `/api/tags`, `/api/version`) statt der
  OpenAI-kompatiblen Hilfsschnittstelle. Das war nötig, weil `/v1` **Top K**,
  **Context Length** (`num_ctx`) und **Keep Alive** stillschweigend verwirft — nachgemessen
  über `/api/ps`. Über die native API greifen sie wirklich.
- **Server frei wählbar:** Server-URL, Host/IP, Port und http/https sind einzeln
  einstellbar und halten sich gegenseitig synchron. Darunter schlägt Jon die Adressen
  dieses PCs zum Anklicken vor — **localhost**, **Heimnetz (LAN)** und **Tailscale**
  (erkannt am Bereich 100.64.0.0/10). Damit läuft das Modell auf dem Rechner mit der
  starken Grafikkarte, während Jon auf dem Laptop sitzt.
- **Serverstatus jederzeit:** Zustand, Antwortzeit in Millisekunden, Ollama-Version,
  gewähltes Modell, Anzahl installierter Modelle und Zeitpunkt der letzten erfolgreichen
  Verbindung. Aktualisiert sich alle 15 Sekunden, **Verbindung testen** fragt sofort nach.
- **Modelle** automatisch laden, neu laden und auswählen — direkt aus `/api/tags`. Die
  Modellwahl im Ollama-Fenster und die oben im Chat bleiben synchron.
- **Alle Antwort-Einstellungen:** Temperatur, Top P, Top K, Max Tokens (`-1` = ohne Limit),
  Context Length, Keep Alive, Seed, System Prompt, Streaming an/aus, Timeout und
  automatische Wiederverbindung. Alles landet in `data/ollama.json` und wird beim Start
  geladen.
- **Fehler statt Absturz:** „Keine Verbindung zu Ollama unter …", „Das Modell X ist auf dem
  Server nicht installiert (ollama pull X)", „Ollama hat zu lange gebraucht", „passt nicht
  in den Speicher" — jeweils mit dem konkreten nächsten Schritt. Falsche Eingaben (Port 0,
  Host mit Leerzeichen, Temperatur 5) werden mit Klartext abgelehnt und ändern die
  gespeicherte Konfiguration nicht.
- **Automatische Wiederverbindung:** Bricht die Verbindung vor der ersten Antwort weg,
  versucht Jon es bis zu dreimal mit wachsendem Abstand.
- **Modelle ohne Werkzeuge** (z. B. `gemma3:270m`) antworten trotzdem: Meldet der Server
  `does not support tools`, wiederholt Jon die Anfrage automatisch ohne Werkzeuge.
- **Ausschalten heißt ausschalten:** Steht der Schalter auf aus, verschwindet Ollama aus
  der Anbieterliste und aus dem Konten-Bereich, statt weiter „verbunden" zu behaupten.
- Neue Endpunkte: `GET/PUT /api/ollama/config`, `POST /api/ollama/reset`,
  `GET /api/ollama/status`, `POST /api/ollama/test`, `GET /api/ollama/models`,
  `GET /api/ollama/hosts`.
- Neue Dokumentation **[docs/OLLAMA.md](docs/OLLAMA.md)**: Was ist Ollama, Voraussetzungen,
  Installation, Einrichtung, Server/Port/Host, LAN, Tailscale, Verbindung testen, Modelle
  installieren und wechseln, Fehlerbehebung, FAQ, Sicherheit und Tipps. Dazu die
  Ollama-Seite auf [getjon.info](https://getjon.info).

38 neue Tests decken Konfiguration, Validierung, Status, Modell-Liste, Chat-Optionen,
Werkzeug-Runden, Streaming an/aus, Reconnect und alle Fehlerfälle ab; die komplette Suite
bleibt grün (211 → 217). Zusätzlich gegen einen echten Ollama-Server (0.32.5) gegengeprüft: `num_ctx`
und `keep_alive` kommen dort nachweislich an.

## [3.36.3] — 2026-07-30

### Fix — Koop ging nur auf demselben Gerät

Der Freundschaftscode existierte immer nur in dem Jon, das die Lobby angelegt hat. Tippte
man ihn am zweiten Rechner ein, fragte dieses Jon **sich selbst** — und antwortete
„Code nicht gefunden". Funktioniert hat nur die lange Einladung `CODE@adresse:8760`, und
selbst deren Adresse war oft falsch: Jon nahm einfach den ersten Eintrag von
`socket.gethostname()`, und das war auf diesem Rechner die VPN-Adresse (`10.2.0.2`) statt
der echten WLAN-Adresse. Laptop gegen PC war damit praktisch unspielbar.

- **Lobby-Suche im Netzwerk** (neu `coop_lan_service.py`): Jeder Jon horcht auf
  **UDP 8761**. Kennt das Jon des Gastes den Code nicht, fragt es per Broadcast „wer hat
  `AB39KD`?" — der Gastgeber antwortet mit Adresse, Ports und Lobby-Infos. Gesucht wird
  auf allen Netzwerkkarten (255.255.255.255 **und** die Broadcast-Adresse jedes Subnetzes),
  damit ein aktives VPN die Suche nicht verschluckt.
- **`redirect` im Koop-Protokoll**: Statt eines Fehlers schickt der Server jetzt
  `{"t":"redirect","host":…,"tcp_port":…,"ws_port":…}`. Browser (`blockwelt.html`) und
  C++-Spiele (`CoopSession`) verbinden sich daraufhin neu zum Gastgeber — maximal drei
  Weiterleitungen, danach eine ehrliche Fehlermeldung.
- **Richtige LAN-Adresse in der Einladung**: Die Adapter kommen über
  `GetAdaptersAddresses`. Sortiert wird nach Gateway, DHCP, Adaptertyp und Name —
  VPN-, Hyper-V-, VirtualBox-, WSL- und Docker-Adapter landen hinten. In der Antwort an
  einen Sucher nennt der Gastgeber gezielt die Adresse der Netzwerkkarte, die in dessen
  Subnetz liegt. Aus `10.2.0.2` wird so `10.0.0.253`.
- **Windows-Firewall**: `GET /api/mp/network` sagt, ob die Koop-Regeln fehlen; in der
  Lobby erscheint dann **Netzwerk freigeben** (`POST /api/mp/firewall`). Das legt nach
  einer Windows-Rückfrage genau zwei Regeln an — TCP 8759/8760 und UDP 8761.
- **Blockwelt**: Im Beitreten-Fenster listet **Netzwerk durchsuchen** alle offenen Spiele
  im Heimnetz mit Gastgeber, Spielerzahl und Adresse zum Anklicken (`GET /api/mp/scan`).
  Die Lobby zeigt die Einladung so an, wie der Server sie kennt.
- **ECHO/AETHERIA**: Der Code allein genügt jetzt auch hier. Ein Beitritt setzt Adresse
  und Port vorher auf das lokale Jon zurück, damit nach einem Fremdspiel kein alter
  Gastgeber hängen bleibt; die angezeigte Einladung kommt vom Server (`invite_tcp`).

Verifiziert mit zwei getrennten Jon-Instanzen (eigene Datenordner, eigene Ports): Der
Gast kennt den Code nicht, findet die Lobby über die Netzwerksuche, wird weitergeleitet
und steht danach mit dem Gastgeber in derselben Lobby — einmal als ECHO-Client über TCP,
einmal als Browser über WebSocket.

### Spiele 1.1.0
`ECHO_VERSION` steht jetzt auf **1.1.0**, passend zur Sammlung in `jon-spiele.json`.

## [3.35.0] — 2026-07-30

### Fix — der Beenden-Knopf ließ das Backend doch weiterlaufen

3.34.0 hat nur den Prozess beendet, den die App **selbst** gestartet hatte. Lief das
Backend aus `start-jon.bat`, aus dem Autostart oder aus einer vorherigen Sitzung, kannte
Electron dessen PID nicht — und `jon-backend.exe` blieb im Task-Manager stehen. Im
Entwicklungsmodus (`npm run dev`) startet die App gar kein Backend, dort hat das
Aufräumen deshalb nie gegriffen: die Portsuche hing an `app.isPackaged`.

- Neu `POST /api/system/shutdown`: das Backend beendet sich selbst sauber, egal wer es
  gestartet hat. `quitJon()` fragt zuerst höflich (max. 2 s) und greift erst dann hart
  durch. Neu `GET /api/system/whoami` (PID + Version) zum Nachprüfen.
- Das Aufräumen der Ports 8756/8758/8759/8760 läuft jetzt **immer**, nicht nur in der
  Installer-Version — und tötet nur Prozesse, die auch wirklich `jon-backend`, `python`,
  `pythonw` oder `py` heißen, statt blind alles auf dem Port.

Verifiziert: sauberes Herunterfahren beendet den Prozess in 0,5 s mit Code 0; ein
absichtlich fremd gestartetes Backend ohne `JON_PARENT_PID` ist nach dem Aufräumen
ebenfalls in 0,5 s weg.

### Neu — Update über die .exe funktioniert wirklich

`/update` prüfte zwar auf neue Versionen, brach in der Installer-Version aber mit
„Bitte lade die neueste Version manuell herunter" ab — ein Update über die App gab es
schlicht nicht. Jetzt:

- `update_service.py` kennt die Installationsart (`exe` / `git` / `manual`) und liest im
  EXE-Modus das GitHub-Release samt `Jon-Setup.exe` (Adresse, Größe, Release-Text).
- **Maßgeblich ist, was installierbar ist**: angeboten wird die Version des fertigen
  Releases, nicht die Versionsnummer aus dem Quellcode. Ist auf `main` schon eine höhere
  Version angekündigt, für die es noch kein Installationsprogramm gibt, sagt Jon das —
  und bietet kein Update an, das dann doch dieselbe Version installieren würde.
- `download_installer()` lädt mit Fortschrittsanzeige nach `DATA_DIR/updates/` und
  **prüft, was ankommt**: nur `https`, Mindestgröße, Größe wie im Release angekündigt,
  und die Datei muss mit `MZ` beginnen (eine HTML-Fehlerseite wird also nicht als
  Programm gestartet). Halbe Downloads landen in `.part` und werden bei jedem Fehler
  weggeräumt; alte Installer verschwinden nach dem nächsten erfolgreichen Download.
- Der Ablauf endet mit `INSTALLER <pfad>`; die App fragt einmal nach, startet das
  Installationsprogramm losgelöst und beendet Jon danach, damit die Dateien nicht mehr
  gesperrt sind. Der Installer bringt Jon anschließend selbst zurück
  (`runAfterFinish`). Electron nimmt dafür nur Pfade der Form
  `X:\...\Jon-Setup*.exe` an — kein beliebiges Programm.
- Chats, Konten und Einstellungen liegen unter `DATA_DIR` und werden nicht angefasst.

Für Quellcode-Installationen bleibt alles wie gehabt (`git pull` + bedingtes
`pip`/`npm`), das wird jetzt nur noch bewusst über `install_mode()` ausgewählt.

### Kleinigkeiten
- Herausgeber überall FelWorks; `win.publisherName` ist bei electron-builder 25
  veraltet und liegt jetzt unter `win.signtoolOptions.publisherName`.
- 10 neue Tests in `test_update.py` (Installationsart, Release-Auswahl, kein Downgrade,
  Download-Prüfungen, Fortschritt, Aufräumen, kompletter Ablauf bis `INSTALLER`).
  Gesamt **172 Tests grün**.

## [3.34.0] — 2026-07-30

### Fix — Multiplayer: „man kann sich nicht verbinden"

Der Koop aus 3.33.0 funktionierte nur in Sonderfällen. Vier echte Ursachen, alle
gefunden und behoben:

- **Der Server war für Mitspieler gar nicht erreichbar.** Uvicorn lauschte auf
  `127.0.0.1`, solange nicht `JON_LAN=1` in der `.env` stand — und diese Datei gab es
  gar nicht. Ein Freund am zweiten PC lief also immer ins Leere, obwohl das Menü die
  LAN-IP versprach. Jetzt hat der Koop einen **eigenen Port 8760 auf `0.0.0.0`**
  (`create_coop_app()` in `multiplayer_routes.py`, gestartet als `_coop_web_server()` —
  nach dem Muster des P2P-Chats, inkl. „Port belegt"-Abfangen). Dieser Port liefert
  ausschließlich `/api/mp/*` und `/blockwelt`; Chat, Dateien, Konten und PC-Steuerung
  bleiben auf 8756 und damit lokal. `JON_LAN` braucht man für Koop nicht mehr.
  Ein Gast ohne eigenes Jon kann sogar direkt `http://<adresse>:8760/blockwelt` öffnen.
- **ECHO/AETHERIA schickten den Handshake nur einmal pro Programmstart.**
  `CoopSession::update()` hing an einem `everSent`-Flag, das nie zurückgesetzt wurde.
  Der erste Versuch klappte; jeder weitere — nach einem Tippfehler im Code, nach
  „Lobby verlassen", nach einem Serverfehler — verband die Leitung, sagte aber nie
  „hallo" und blieb für immer auf **VERBINDE** stehen. Ersetzt durch `handshakeSent`,
  das `beginConnect()` bei jedem Verbindungsaufbau löscht.
- **Der Fehlerbildschirm war eine Sackgasse.** `ZURUECK ZUM MENUE` setzte nur die
  Ansicht zurück, die Sitzung blieb im Zustand `COOP_ERROR` — und `update()` sprang
  sofort wieder in den Fehlerbildschirm. Jetzt räumt `ACT_RETRY` die Sitzung sauber auf.
- **Abgelehnte Verbindungen wurden nicht erkannt.** `NetClient` prüfte beim
  nicht-blockierenden `connect()` nur `writefds`, nie `exceptfds` oder `SO_ERROR` — ein
  geschlossener Port lief 6 s pro Adresse in den Timeout, bei IPv6+IPv4 also 12 s
  scheinbares Hängen. Jetzt sofortige Erkennung mit klarer Meldung
  („Kein Jon-Server auf host:port" statt „Verbindung abgelehnt").

Dazu aufgeräumt:

- Der Handshake meldet **jeden** Fehlgrund an den Client (`resume`, `create`, `join`,
  `handshake`) statt nur beim Beitreten; die WebSocket-Route schickt keine doppelte
  Fehlermeldung mehr.
- Die Blockwelt schließt den alten Socket, bevor sie einen neuen öffnet, und ignoriert
  Ereignisse veralteter Verbindungen — vorher konnte das `onclose` eines toten Sockets
  die frische Verbindung wieder auf „verloren" setzen.
- Die Lobby zeigt jetzt **zwei** Felder: den Code für denselben PC und die
  **Einladung mit Adresse** (`AB39KD@192.168.1.20:8760`) für andere PCs, beide mit
  Kopierknopf. Adresse und Port holt die Seite aus `/api/mp/info`
  (neu: `ws_port`, `invite_host`).
- Das Koop-Menü in ECHO verarbeitet den Team-Chat auch während der 0,22-s-Eingabesperre
  nach dem Öffnen; die Sperre blockiert nur noch Tasten und Klicks, nicht die
  Serverantworten.
- `jon-backend.spec` nimmt `websockets` vollständig mit, damit der WebSocket-Koop auch
  in der gepackten `jon-backend.exe` läuft.

Verifiziert: zwei Browser-Kontexte über die echte Netzwerkadresse (10.2.0.2) bis
`phase=playing` inkl. Ping und Team-Chat, ohne JS-Fehler; ECHO verbindet sich nach einem
absichtlich fehlgeschlagenen ersten Versuch im selben Prozess und taucht im Roster des
Gastgebers auf.

### Neu — Jon beenden stoppt auch das Backend

Das X der App versteckte das Fenster nur; `jon-backend.exe` lief unbemerkt weiter.

- **X beendet Jon jetzt wirklich** (`quitJon()`): Backend stoppen, Fenster schließen,
  Tray-Symbol entfernen. Wer Jon nur wegklicken will, hat dafür einen neuen Knopf
  in der Titelleiste (⌄, „In den Hintergrund") und den Tray-Eintrag
  „Im Hintergrund weiterlaufen" — Strg+Alt+J holt ihn zurück.
- **`stopBackend()`** killt den Prozessbaum und räumt danach übrig gebliebene Listener
  auf 8756/8758/8759/8760 ab, damit kein Backend einer vorherigen Sitzung stehen bleibt.
- **Parent-Watchdog im Backend**: Electron gibt seine PID als `JON_PARENT_PID` mit;
  `_parent_watchdog()` prüft alle 2 s, ob die App noch lebt, und fährt das Backend
  sonst selbst herunter. Damit bleibt auch nach einem Absturz der App nichts hängen.

### Fix — ECHO: Aufzugtür führte vor eine Wand

Die Aufzugkabine steht im hinteren Teil des Schachtraums und öffnet nach vorn. Die
Eingangstür vom Flur landet aber je nach Grundriss irgendwo an der Raumwand — ein
kopfloser Durchlauf über 40 Seeds zeigt: **168 von 328 Aufzugtüren (51 %)** öffneten
auf die Stahlwand der Kabine statt auf ihren Eingang.

Wer jetzt eine Aufzugtür öffnet, **steigt direkt in die Kabine ein** (`Game::enterCab()`):
Tür auf, Spieler in die Kabine, Blick zur Kabinentür, Ding — und das Etagenpanel
(1 – 4) hat 6 s Zeit, bevor der Aufzug von selbst losfährt. Neu dafür:
`World::cabInRoom()` und `World::cabForDoor()`.

### Tests & Werkzeuge
- 4 neue Tests in `test_multiplayer.py`: Koop-Port liefert Lobby und Spielseite und
  eben **nicht** den Rest der API; die drei Ports sind verschieden; jeder Handshake-
  Fehler nennt seinen Grund; ein zweiter Versuch auf derselben Leitung klappt.
  Gesamt **162 Tests grün**.
- `ECHO.exe -nettest <adresse> [CODE]` prüft jetzt zwei Versuche hintereinander
  (erst absichtlich auf einen geschlossenen Port, dann richtig) und fällt damit auf
  genau den behobenen Handshake-Fehler herein, falls er zurückkommt.
- `ECHO.exe -seeds N` zählt Aufzugtüren, Kabinen und blockierte Zugänge.

## [3.33.0] — 2026-07-30

### Neu — Online-Multiplayer für alle drei Spiele
- **Serverautoritativer Koop-Server im Jon-Backend**
  (`backend/app/services/multiplayer_service.py`): Lobbys mit 6-stelligem
  Freundschaftscode (Alphabet ohne `O/0/I/1`), 20-Hz-Tick, delta-komprimierte
  Snapshots, zuverlässige Event-Liste mit Cursor-Ack, Heartbeat/Ping, Paketverlust-
  Schätzung, Reconnect-Fenster von 150 s und Persistenz nach
  `DATA_DIR/multiplayer/<CODE>.json` — eine Sitzung übersteht einen Backend-Neustart.
- **Zwei Transporte, ein Protokoll**: WebSocket `/api/mp/ws` für die Blockwelt im
  Browser, roher TCP-Port **8759** (4-Byte-Längenpräfix + JSON) für ECHO und AETHERIA.
  REST daneben: `/api/mp/create`, `/api/mp/join`, `/api/mp/lobby/{code}`,
  `/api/mp/status`, `/api/mp/info`.
- **Server hat die Autorität**: Bewegung wird gegen ein Spielprofil geprüft
  (Höchstgeschwindigkeit, Fallgeschwindigkeit, Weltgrenzen) — unmögliche Sprünge werden
  mit `correct` zurückgesetzt, nach 40 Verstößen fliegt der Client. Blöcke, Türen,
  Hebel, Schalter, Rätsel, Items, NPCs, Quests, Lichter, Timer und Checkpoints landen
  nur über geprüfte `act`-Nachrichten im Weltzustand (Reichweite, Whitelist,
  Token-Bucket-Ratenbegrenzung). Inventare bleiben privat, geteilt wird nur der
  Weltzustand.
- **Gleichzeitiger Start**: Host drückt Start → alle laden → jeder meldet
  `scene ready` → der Server gibt `spawn` frei. Niemand läuft allein los.
  Szenenwechsel und Wiedereinstieg laufen über dieselbe Barriere; wer mitten im Spiel
  wieder reinkommt, spawnt sofort an seiner letzten Position.

### Neu — Blockwelt: Koop im Browser
- **Online-Menü** (Knopf im Startbildschirm oder `O`): Spiel erstellen, Spiel
  beitreten, Lobby mit Code, Spielerliste, Ready, Start, Ping, freie Plätze.
  Beitreten akzeptiert `AB39KD` und `AB39KD@host:8756`.
- **Eigenes 3D-Modell pro Spieler**: acht Paletten × vier Kopfbedeckungen, Gesicht als
  Pixel-Textur, Namensschild mit Ping-Punkt. Animationen für Idle, Laufen, Rennen,
  Ducken, Springen, Fallen, Schwimmen, Abbauen und Platzieren — interpoliert mit 110 ms
  Puffer, Extrapolation bis 280 ms, kein Teleportieren.
- **Gemeinsame Welt**: Blockänderungen, TNT-Zündung, Explosionen, Enderperlen,
  Team-Chat (`Z`) und Jons Bauaufträge werden synchronisiert. Jon ist
  host-autoritativ — Gäste schicken ihm ihre Wünsche, er baut, alle sehen es.
  Der Weltgenerator ist jetzt seedbar, beide Spieler bekommen dieselbe Landschaft.
- **Neu: Ducken mit Strg** (langsamer, tiefere Kameraposition) — auch synchronisiert.
- **Emotes mit `B`** (Winken, Nicken, Zeigen, Jubeln, Kopfschütteln): der Mitspieler sieht
  die Bewegung am Avatar, nicht nur einen Text.
- **Eigenes Icon**, im Code gezeichnet: isometrischer Grasblock mit Jons Goldkristall.
  Als Favicon und Apple-Touch-Icon in `blockwelt.html` (Canvas) und als PNG über
  `scripts/blockwelt_icon.py` für Website und PWA.

### Neu — ECHO & AETHERIA: Koop im Spiel
- **Netzwerk-Schicht in C++** unter `ECHO/src/net/`: eigener JSON-Parser/Writer
  (`Json.*`), WinSock-Client mit eigenem Thread und Längenpräfix-Frames
  (`NetClient.*`), Sitzungslogik mit Snapshot-Interpolation, Weltzustand, Reconnect
  und Backoff (`CoopSession.*`) sowie die Lobby-Oberfläche (`CoopUI.*`).
  `build.bat` linkt jetzt `ws2_32.lib`.
- **Menüpunkt „ONLINE KOOP"** in ECHO (Haupt- und Pausemenü) und
  **„ONLINE SPIELEN"** in AETHERIA: Code erstellen oder eintippen, Namenswahl,
  Spielerliste mit Ping, Bereit/Start, Lobby schließen. Im Spiel zeigt eine Ecke
  oben rechts alle Mitspieler mit Ping; bei Abbruch blinkt ein Reconnect-Banner.
- **Mitspieler sichtbar**: Remote-Spieler nutzen das vorhandene Menschen-Rig mit
  eigenem Typ pro Slot, Pose je Animationszustand und Blick zum Zuhörer.
- **Synchronisiert**: ECHO überträgt Türen, Lichtschalter, Items und Checkpoints;
  AETHERIA Ernten, Dorfbesuche, Quests, Kampftreffer und den Tag-Nacht-Zyklus
  (Host gibt die Zeit vor). Fortschritt wird alle 45–60 s als Checkpoint gesichert.
- **Diagnose**: `bin/ECHO.exe -nettest 127.0.0.1:8759 [CODE]` verbindet sich headless,
  legt eine Lobby an bzw. tritt bei und schreibt das Ergebnis in `echo.log`.

### Neu — ECHO: Jumpscares mit eigenen Modellen
- **Neues Kreaturen-Rig** (`ECHO/src/world/Horror.*`): 19 Teile, überlanger Schädel mit
  tiefen Augenhöhlen, aufgerissener Kiefer mit Zähnen, freiliegender Rippenbogen,
  überlange Arme mit Krallenhänden, vier Archetypen (`GAUNT`, `CRAWLER`, `BANDAGED`,
  `LONGARM`) und Animationsmodi Starren, Zucken, Zuschlagen, Kriechen, Schreien, Hängen.
- **Garantiert mindestens ein Schreck pro Flur** (`ECHO/src/ai/Jumpscare.cpp`): jeder
  Korridor wird genau einmal benutzt, dann gemerkt. Sechs Auslöser — Rennen aus der
  Tiefe des Flurs, Auftauchen im Rücken beim Umdrehen, Herausbrechen aus einer Seitentür,
  Fall von der Decke, Kriechen über den Boden, Lauern an der Wandkante.
- **Und es wird laut**: fünf neue synthetisierte Klänge (`SFX_SCREAM`, `SFX_SCREECH`,
  `SFX_SLAM_HIT`, `SFX_BREATH_CLOSE`, `SFX_BONE_CRACK`) — verzerrter Schrei mit
  Formantfiltern, Bass-Drop mit Metallnachhall, nasses Atmen direkt am Ohr. Dazu
  Licht aus im ganzen Raum, Taschenlampen-Ausfall, harter Kamerawackler, Blickzwang zur
  Kreatur, roter Blitz und Tinnitus-Ton.

### Neu — ECHO: Wegweiser mit H
- **`H` öffnet und schließt** den direkten Weg zum Ziel (`ECHO/src/game/Guide.*`):
  Breitensuche über den Raum-Graph zum Kampagnenziel, sonst zum nächsten Aufzug oder
  Treppenhaus. Der Pfad wird als Markerkette durch die Türen gezeichnet, der nächste
  Abschnitt hervorgehoben, Treppen gelb, Aufzüge grün. Oben mittig Ziel, Restdistanz
  und Zahl der Abschnitte; ohne offenen Weg sagt er das auch.

### Behoben
- **Emote, Blickrichtung, Animations-Layer und Trefferpunkte gingen sofort wieder verloren**:
  der Server hat sie bei jedem Bewegungspaket auf den Standardwert zurückgesetzt, weil das
  Paket diese Felder nicht mitschickt. Jetzt werden nur Felder überschrieben, die im Paket
  wirklich enthalten sind — mit Wertegrenzen pro Feld.
- **Backend starb, wenn Port 8758 belegt war**: uvicorn beendet sich bei einem fehlgeschlagenen
  Bind mit `sys.exit(3)`, und `SystemExit` ist keine `Exception` — das `except Exception`
  im P2P-Chat-Server hat es also nicht gefangen und der ganze Prozess starb beim Start.
  Trat auf, sobald eine zweite Jon-Instanz lief. Jetzt fangen Chat- und Koop-Server
  `SystemExit` mit, melden den belegten Port und lassen nur den einen Dienst aus.

### Geändert
- FelWorks Game Collection auf **1.1.0**, `ECHO/jon-spiele.json` beschreibt Koop,
  Jumpscares und die H-Taste.
- Website: neuer Abschnitt **„Zusammen spielen"** mit Ablauf, Lobby-Vorschau und sechs
  Kacheln zur Technik, Koop-Link in der Navigation, aktualisierte Spielkarten und das
  neue Blockwelt-Icon.
- 157 Tests grün (28 neue in `backend/tests/test_multiplayer.py`), darunter ein Test, der
  die Multiplayer-Routen gegen die echte `create_app()` prüft.

## [3.32.0] — 2026-07-28

### Neu — Jon macht PowerPoints
- **`create_pptx`** baut eine fertige `.pptx` (16:9) mit neun Layouts: `title`,
  `bullets`, `cards`, `stat`, `two_columns`, `image`, `quote`, `timeline`, `closing` —
  je mit Sprechernotizen, Karten, nummerierten Kreisen, großen Kennzahlen und
  automatischer Schriftgrößen-Anpassung bei langen Titeln.
- **Elf Farbwelten** (`midnight`, `ocean`, `forest`, `sage`, `teal`, `coral`,
  `terracotta`, `berry`, `cherry`, `charcoal`, `gold`) mit abgestimmten Werten für
  Fläche, Text, Akzent und gedämpften Text.
- **Neuer Skill `powerpoint`**: Aufbau einer Präsentation, Layout-Tabelle, Themenwahl,
  Regeln (max. 5 Punkte pro Folie, Layouts abwechseln, dunkle Anker-Folien) und
  Checkliste. Jon liest ihn vor dem Bauen und hält sich daran.
- **`read_pptx`** liest vorhandene Präsentationen samt Notizen — zum Zusammenfassen oder
  Weiterbauen.
- Fehlt die Titelfolie, wird sie ergänzt; fehlt ein Bild, bleibt die Folie heil.
  Abhängigkeit `python-pptx` liegt der Installer-Version bei.

### Geändert — Jon Code bleibt im Ordner und schreibt direkt in die Datei
- **Nur der geöffnete Projektordner**: zusätzlich zur bestehenden Pfad-Sperre werden jetzt
  auch Shell-Ausbrüche (`cd ..`, `pushd`, `Set-Location C:\…`, `cd ~`) blockiert, bevor
  der Befehl läuft. Im Code-Modus bekommt Jon außerdem nur noch die 23 Projekt-Werkzeuge
  (Dateien, Suche, Shell, Git, Web) — Mail, Musik, Smarthome, Kalender & Co. fallen weg.
- **Genannte Dateien**: „schreib mir in index.html …" — Jon sucht die Datei im Projekt,
  bekommt Pfad und Inhalt in den Kontext und ändert genau sie. Mehrere Treffer werden
  benannt, fehlende Dateien legt er an.
- **Geöffnete Datei als Kontext**: Pfad und Inhalt der im Editor offenen Datei gehen mit;
  „hier", „da" und „in der Datei" beziehen sich darauf. Ungespeicherte Änderungen werden
  vor dem Senden automatisch gespeichert, ein Chip im Chat zeigt die aktive Datei.
- **Projektbaum statt Ordnerliste**: der System-Prompt enthält jetzt zwei Ebenen des
  Projekts (ohne `node_modules`, `dist`, `.venv` …), damit Jon Dateien direkt findet.
- **Bessere Coding-Prompts**: Code kommt in die Datei statt in den Chat, keine Rückfrage
  vor dem Schreiben, keine Kommentare im Code (außer gewünscht), Stil und Konventionen des
  Projekts werden übernommen.
- **Design-Vorgabe (Liquid Glass)**: für alles Sichtbare gibt Jon sich jetzt Mühe —
  halbtransparente Flächen mit `backdrop-filter`, Tiefe im Hintergrund, Design-Tokens,
  fluide Typografie, Hover-/Fokus-Zustände, Hell und Dunkel, Kontrast ≥ 4.5:1,
  `prefers-reduced-motion`, keine externen CDNs. Hat das Projekt schon ein Design, fügt er
  sich dort ein.

## [3.31.0] — 2026-07-28

### Neu — Spiele in Jon (FelWorks Game Collection)
- **Werkzeuge → Spiele**: neuer Abschnitt im Werkzeuge-Menü plus Übersichtsfenster mit
  einer Karte je Spiel — Vorschaubild, Titel, Genre, Beschreibung, Steuerung, Version,
  Herausgeber, Baudatum und Status (bereit · läuft · wird gebaut · Fehler). Gestartet
  wird ausschließlich per Klick auf **Starten**; beim Start von Jon öffnet sich kein
  Spielfenster.
- **ECHO** (Psychological Horror) und **AETHERIA** (Fantasy-Open-World-RPG) laufen als
  eigener Prozess in einem eigenen Fenster, die **Blockwelt** öffnet sich in einem neuen
  Tab. Jon bleibt in allen Fällen offen und bedienbar.
- Neue Endpoints `GET /api/games`, `POST /api/games/{id}/start|stop|build` und
  `GET /api/games/{id}/vorschau`; laufende Spiele werden mitverfolgt und lassen sich aus
  der Karte heraus wieder beenden.
- **Erweiterbar ohne Code-Änderung**: `arcade_service` sucht neben Jon (und in `games/`)
  nach Ordnern mit einer `jon-spiele.json` — Titel, Icon, Vorschaubild, Exe,
  Startparameter und optionales Bau-Skript stehen dort drin.
- **Fehlerbehandlung**: fehlende Spieldatei, sofortiger Absturz, fehlende Build-Tools
  oder ein blockiertes Browser-Fenster ergeben eine verständliche Meldung in der Karte
  statt eines Absturzes. Ist ein Spiel noch nicht kompiliert, baut der **Bauen**-Knopf es
  im Hintergrund.
- `start-jon.bat` bleibt der einzige Einstiegspunkt und startet mit dem Backend auch den
  Spiele-Dienst; es meldet beim Start, welche Spiele bereit sind.
- Installer und ZIP liefern die Spiele mit (`resources/ECHO`), die Website stellt sie mit
  Screenshots vor.

### Geändert
- Herausgeber der Downloads ist jetzt **FelWorks** (NSIS-Installer, `Jon.exe` und
  `jon-backend.exe`).
- Der Menüpunkt „Blockwelt-Spiel" ist von „Spaß & mehr" in den neuen Abschnitt „Spiele"
  umgezogen; `/spiel` öffnet sie weiterhin direkt.

## [3.30.1] — 2026-07-23

### Behoben — Downloads werden seltener fälschlich als schädlich gemeldet
- Die Warnungen kamen von SmartScreen/Virenscanner-Heuristiken, die bei neuen,
  unsignierten Programmen anschlagen — nicht von echter Schadsoftware. Dagegen getan:
  `jon-backend.exe` trägt jetzt vollständige Datei-Metadaten (Produkt, Version,
  Herausgeber, Open-Source-Hinweis), läuft als normales Konsolenprogramm statt als
  „unsichtbare" Fenster-Anwendung (ein bekannter Heuristik-Auslöser; die App versteckt
  die Konsole selbst) und der Installer nennt einen echten Herausgeber. Neue Downloads
  als Release v3.30.1, das alte Release ist entfernt.
- Die Download-Seite erklärt jetzt ehrlich, warum die SmartScreen-Meldung erscheinen
  kann und wie man sie bestätigt (Weitere Informationen → Trotzdem ausführen).
- Ganz verschwinden kann die Erst-Warnung nur mit einem kostenpflichtigen
  Code-Signing-Zertifikat oder wachsender Download-Reputation.

## [3.30.0] — 2026-07-22

### Neu — Fertige Downloads: Jon-Setup.exe und portable ZIP
- Jon gibt es jetzt fertig gebaut zum Herunterladen — **Jon-Setup.exe** (Installer mit
  Startmenü- und Desktop-Verknüpfung) und **Jon-Windows.zip** (portabel: entpacken,
  `Jon.exe` starten). Beide enthalten die Jon App, Mini Jon und das komplette Backend,
  das automatisch mitstartet. API-Einstellungen trägst du direkt in der App ein
  (Zahnrad → Konten) — sie werden lokal gespeichert, keine `.env` nötig.
- Die Downloads liegen als GitHub-Release (zu groß fürs Repo); die Website verlinkt auf
  `releases/latest/download/…` und zeigt damit immer die neueste Version. Auf der
  Download-Seite wählst du frei zwischen .exe und .zip, der Quellcode bleibt daneben.
- Gebaut wird beides mit `python scripts/build_installer.py` (ersetzt
  `build-installer.bat`). `jon.bat` ist ebenfalls entfernt — die CLI startet mit
  `python -m app.cli` im backend-Ordner. `start-jon.bat` und `autostart-jon.bat`
  bleiben (Entwickler-Start + Autostart-Funktion).

### Neu — /goal-Modus in Jon Code
- In Jon Code startest du mit **`/goal Zielbeschreibung`** den Ziel-Modus: Jon sieht
  sich das Projekt an, zerlegt dein Ziel in 2-8 Schritte, arbeitet sie nacheinander ab
  und zeigt den Fortschritt als Checkliste (⚪ offen, ▶️ läuft, ✅ fertig, ❌ Fehler).
- Ist das Ziel zu unklar, stellt Jon genau eine Rückfrage — deine Antwort unten im Chat
  genügt, dann plant er weiter. Schlägt ein Schritt fehl, analysiert Jon den Fehler und
  versucht es einmal erneut; danach bricht er sauber ab. Am Ende gibt es immer einen
  Abschlussbericht: was erledigt wurde, was offen blieb, was du prüfen solltest.
- Über den Stopp-Knopf im Ziel-Panel brichst du jederzeit ab.

### Neu — Über-mich-Seite auf der Website
- Die Website hat jetzt eine „Über mich"-Sektion über Felix und das Jon-Projekt.

## [3.29.0] — 2026-07-22

### Behoben — Mini Jon mit eigenem Anbieter + Ollama ohne Tool-Fehler
- Mini Jon (und Telegram) können jetzt einen **eigenen Anbieter** nutzen, auch wenn Jon
  selbst auf einem anderen läuft: Wählst du in „Mini Jon anpassen" z. B. **nvidia**,
  gilt deine Auswahl immer — die Folge-Regel („übernimmt Jons Anbieter") greift nur
  noch, wenn kein eigener Anbieter gewählt ist. Damit läuft Mini Jon mit NVIDIA,
  während Jon Ollama nutzt.
- **Ollama-Fehler behoben**: Modelle ohne Tool-Unterstützung (z. B. `gemma3:270m`)
  brachen mit `400 — does not support tools` ab. Jon wiederholt die Anfrage jetzt
  automatisch ohne Tools und merkt sich das Modell, sodass künftige Anfragen direkt
  ohne Tools laufen. Das Modell antwortet dann ganz normal (kann nur keine
  PC-Werkzeuge aufrufen).

## [3.28.0] — 2026-07-21

### Entfernt — kein eigener Veröffentlichungsdienst mehr
- Die selbstgebaute Netlify-Anbindung (Veröffentlichen-Seite `/veroeffentlichen`, das
  Werkzeug „Website hochladen", `netlify_service.py`, die `/api/netlify/*`-Routen,
  `scripts/netlify_paket.py`) ist komplett entfernt. Die Website wird wieder ganz normal
  bei Netlify veröffentlicht.
- **So geht's** (einmal einrichten, dann automatisch): Bei Netlify „Add new site →
  Import an existing project → GitHub" wählen und das Repo `Jon---AI` verbinden. Das
  Root-`netlify.toml` (`publish = "website"`) sorgt dafür, dass Netlify nur den
  `website/`-Ordner veröffentlicht und den Rest (`node_modules`, `backend/dist`)
  ignoriert. Jeder `git push` deployt dann automatisch — kein „Access Denied" mehr.
- Manuell geht weiterhin: nur den **`website/`-Ordner** (nicht den ganzen Jon-Ordner)
  auf `app.netlify.com/drop` ziehen.

## [3.27.0] — 2026-07-21

### Geändert — Jon-Ordner per Drag&Drop veröffentlichen (Werkzeug-Fenster entfernt)
- Das Werkzeug-Fenster „Website hochladen" aus 3.26.0 ist wieder entfernt. Stattdessen
  gibt es die Seite **`http://127.0.0.1:8756/veroeffentlichen`** (öffnet auch mit
  `/website` im Chat): Dort ziehst du den **kompletten Jon-Ordner** auf die Fläche —
  Jon nimmt die Dateien direkt von der Festplatte, baut jon.zip frisch und schickt nur
  die Website (~1 MB) zu Netlify. Live in Sekunden, mit Link.
- Zum „Access Denied" bei netlify.com: Beim Ziehen des ganzen Ordners lädt der Browser
  dort über 1 GB hoch (node_modules, backend/dist); nach vielen Minuten läuft Netlifys
  Upload-Freigabe ab und Netlify blockt mit „Access Denied". Das lässt sich auf
  netlify.com nicht abstellen — die Veröffentlichen-Seite umgeht es, weil nur die
  Website selbst hochgeladen wird. Ein frischer Deploy darüber ersetzt auch einen
  hängengebliebenen kaputten Deploy.

## [3.26.0] — 2026-07-21

### Neu — Website hochladen direkt in der App (Drag&Drop des Jon-Ordners)
- Neues Werkzeug **🧰 Werkzeuge → 🌐 Website hochladen** (auch `/website`, `/netlify`,
  `/hochladen`): Zieh einfach deinen kompletten Jon-Ordner auf die Fläche (oder klick) —
  Jon baut `website/jon.zip` frisch und lädt nur den Website-Inhalt (~1 MB) über die
  Netlify-API hoch. Fertig in Sekunden, mit Live-Link zur Website.
- Einmalige Einrichtung: Netlify Personal Access Token einfügen
  (app.netlify.com/user/applications) und Website aus der Liste wählen. Der Token wird
  nur lokal gespeichert.
- `netlify-hochladen.bat` ist wieder entfernt — kein Skript mehr nötig, alles läuft in
  der App. (`scripts/netlify_paket.py` bleibt als Alternative ohne App.)
- Hintergrund: Drag&Drop des ganzen Ordners auf netlify.com lud über 1 GB
  (`backend/dist`, `node_modules`) durch den Browser — deshalb 15 Minuten und Abbruch.

## [3.25.0] — 2026-07-21

### Neu — Netlify-Upload in Sekunden statt 15 Minuten
- Neues Skript `netlify-hochladen.bat` (nutzt `scripts/netlify_paket.py`): baut
  `website/jon.zip` frisch, packt den kompletten Website-Inhalt in eine kleine
  `netlify-upload.zip` (wenige MB) und öffnet Explorer + Netlify. Die Zip einfach auf
  die Deploy-Fläche ziehen — Netlify entpackt sie automatisch, fertig in Sekunden.
- Hintergrund: Beim Hochladen des ganzen Jon-Ordners gingen über 1 GB mit
  (`backend/dist`, `node_modules`) — deshalb dauerte der Upload 15 Minuten und brach ab.

### Neu — 10 weitere Träume für Mini Jon, alle mit passender Visualisierung
- Seifenblasen-Meer, Sternen-Express, leuchtende Quallen, Glücksklee-Garten,
  Himmel in Regenbogenfarben anmalen, Schneemann im Sommer, Wettrennen gegen Minka
  und Rocky, Sternschnuppen mit dem Kescher fangen, Mond-Kekse backen und ein
  Glühwürmchen-Orchester dirigieren — Mini Jon träumt jetzt aus 20 Träumen.

## [3.24.0] — 2026-07-21

### Neu — Mini Jons Träume werden visualisiert
- Während Mini Jon schläft, zeigt die Traum-Blase jetzt zu jedem Traum eine **kleine
  animierte Szene** (Canvas) über dem Traumtext: goldene Wolken mit fliegendem Emil,
  „so groß wie Papa Jon", springende Schäfchen mit Binär-Zähler, ein Kakao-Meer mit
  Marshmallows, der Blockwelt-Pokal mit Konfetti, hüpfende Pixel-Schäfchen, Surfen auf
  der Regenbogen-Datenwelle, ein leuchtendes Erinnerungs-Sternbild, ein Schloss aus
  goldenen Bausteinen, das sich Stein für Stein baut, und eine Abenteuer-Rakete.
- Die Animation läuft nur, solange er wirklich schläft und der Traum sichtbar ist,
  und stoppt beim Aufwachen sofort.

## [3.23.0] — 2026-07-21

### Neu — Mini Jon schläft mit Schlafmaske und träumt
- Wenn Mini Jon schläft (z. B. weil du länger als 5 Minuten weg bist oder per
  Telegram `/schlafen`), setzt er sich jetzt eine **Schlafmaske** auf — dunkel mit
  Goldrand, kleinem Mond und Sternchen.
- In der Sprechblase, wo sonst seine Antworten stehen, wird währenddessen sein
  **Traum** angezeigt (💭, wechselt alle paar Sekunden) — in einem eigenen,
  verträumten Blau-Stil.
- Die **Zzz** schweben jetzt direkt an seinem Kopf statt weit daneben.
- Ist der PC länger als 5 Minuten unbenutzt (AFK), schläft Mini Jon automatisch ein
  und wacht auf, sobald du zurück bist oder ihn ansprichst.

## [3.22.1] — 2026-07-21

### Behoben — Privater Browser jetzt auch auf dem Raspberry Pi
- Der private Browser lief backendseitig schon auf dem Pi (die Seite `/privat` und der
  Proxy `/api/private/proxy` werden direkt vom Backend ausgeliefert), aber `pi-update.sh`
  hat die Web-App nach dem `git pull` **nie neu gebaut** — dadurch erschienen neue
  Frontend-Funktionen (wie der „Privater Browser"-Knopf unter Werkzeuge) auf dem Pi nicht.
  `pi-update.sh` baut die Web-App jetzt neu; schlägt der Bau fehl (oft zu wenig RAM), wird
  die vorige Oberfläche automatisch wiederhergestellt statt zerstört.
- Beide Pi-Skripte zeigen jetzt die direkte Adresse des privaten Browsers an
  (`http://<IP>:8756/privat`). Diese Seite braucht **keinen** Web-App-Build und funktioniert
  auf dem Pi auch dann, wenn der React-Bau nicht durchläuft.

## [3.22.0] — 2026-07-21

### Geändert — Privater Browser öffnet jetzt in der App
- Der private Browser öffnet unter **🧰 Werkzeuge → 🕶️ Privater Browser** jetzt als
  eingebettetes Fenster **in der App** (Modal) statt in einem separaten Fenster/Tab —
  überall gleich, auch auf dem Raspberry Pi und in der Web-App. Ein Knopf „↗ Eigenes
  Fenster" öffnet ihn in der Desktop-App weiterhin als eigenes Fenster.
- `/privat`, `Strg+Alt+P` und das Tray-Menü öffnen ebenfalls diese In-App-Ansicht.
- **Mini Jon** öffnet den privaten Browser jetzt zuverlässig in der App: Ein Zuruf wie
  „privat", „inkognito", „öffne den privaten Browser" oder „privat surfen" holt Jon in
  den Vordergrund und öffnet den Browser direkt im Fenster. Die Browser-Seite kennt
  einen `embed`-Modus, der ihre eigene Titelleiste ausblendet, damit sie sauber in die
  App passt.

## [3.21.0] — 2026-07-21

### Neu — Privater Browser auch auf dem Pi & über Mini Jon
- **Web-/Pi-Version**: Der private Browser läuft jetzt auch ohne Electron. Das Backend
  liefert unter `/privat` eine eigenständige Browser-Seite (Tabs, Adress-/Suchleiste,
  DuckDuckGo, In-Memory — nichts wird gespeichert). Läuft Jon auf dem Raspberry Pi oder
  wird die Web-App im Browser geöffnet, startet über „Privater Browser"/`/privat` diese
  Seite in einem neuen Tab; in der Electron-App weiterhin das native Fenster.
- **Seiten-Proxy** (`/api/private/proxy`): Seiten werden über Jon geladen, damit sie sich
  im In-App-Browser überhaupt öffnen (X-Frame-Options/CSP-Frame-Sperren werden dabei
  umgangen, ein `<base>` und ein kleines Navigations-Skript werden eingefügt, sodass
  Links und Suchformulare im privaten Browser bleiben). Der Proxy speichert nichts, setzt
  `Cache-Control: no-store` und `Referrer-Policy: no-referrer` und blockt interne Adressen
  (Loopback, Link-Local, Cloud-Metadaten) gegen SSRF.
- **Mini Jon** öffnet den privaten Browser: Sag der Desktop-Figur z. B. „öffne den
  privaten Browser" oder „privat surfen", und Emil startet ihn für dich.

## [3.20.3] — 2026-07-21

### Neu — Privater Browser
Komplett privater Browser direkt in der Jon-App (Werkzeuge → 🕶️ Privater Browser,
`/privat` oder Strg+Alt+P, auch im Tray): eigenes Fenster im Jon-Design mit Tabs,
Adress-/Suchleiste und Mausrad-/Tastatur-Shortcuts (Strg+T/W/L/R, Strg+Tab). Alles läuft
in einer reinen In-Memory-Session — kein Verlauf, keine Cookies, kein Cache, keine
Logins landen auf der Festplatte; beim Schließen (und per 🧹 „Spuren löschen") wird
zusätzlich alles sofort gewischt. Suchen laufen standardmäßig über DuckDuckGo,
Berechtigungsanfragen (Kamera, Standort …) werden in diesem Fenster automatisch
abgelehnt, Popups öffnen als Tab statt als neues Fenster. Kein Konto, keine Anmeldung,
nichts verlässt den PC.

## [3.19.0] — 2026-07-21

### Neu — Telegram-Gruppen & schlafender Mini Jon
- **Gruppen-Chats mit mehreren Bots**: Jon und Mini Jon (eigener Bot-Token unter
  Verbindungen) lesen in Telegram-Gruppen alle Nachrichten mit und verstehen so den
  Gesprächskontext, antworten aber nur, wenn sie jemand mit ihrem `@Benutzernamen`
  erwähnt. Ein gemeinsamer Gruppen-Verlauf sorgt dafür, dass beliebig viele Bots in
  derselben Gruppe harmonieren — jeder kennt auch die Antworten der anderen. Neue
  Architektur `telegram_group_service.py` (GroupBot-Basisklasse, weitere Bots =
  Unterklasse). In Gruppen sind PC-Tools bewusst aus. Wichtig: bei @BotFather pro Bot
  `/setprivacy` → Disable, sonst liefert Telegram den Bots nur Erwähnungen und Befehle.
- **Mini Jon schläft**: neuer Status `wach`/`schläft` (`GET/POST /api/mini-jon/status`,
  Telegram `/schlafen` und `/aufwachen`). Schläft Emil, antwortet er in Telegram nicht
  mehr, sondern schickt eine generierte Schlaf-Animation (GIF im Jon-Design: geschlossene
  Augen, schwebende Zzz, ruhiges Atmen). Die Desktop-Figur schläft sichtbar mit:
  geschlossene Augen, gedimmtes Gesicht, Zzz und Atem-Animation; Blinzeln, Umschauen,
  Stimmungs- und Wellness-Impulse pausieren. Eine Nachricht an ihn weckt ihn auf.

## [3.18.1] — 2026-07-19

### Geändert — LAN-Pairing entfernt
Das Geräte-Pairing (6-stelliger Code bei `JON_LAN=1`) ist komplett entfernt. Wie früher
ist Jon mit `JON_LAN=1` einfach im eigenen WLAN für Handy und Smartwatch erreichbar, ohne
Kopplung — besonders praktisch auf dem Raspberry Pi ohne Bildschirm. Papierkorb und
Aktionsprotokoll bleiben unverändert erhalten.

## [3.18.0] — 2026-07-19

### Neu — fünf weitere Ideen
- **Standort-Erinnerungen über Telegram** — benannte Orte per geteiltem Standort merken
  („Ort speichern: Supermarkt") und Geo-Erinnerungen anlegen („Erinnere mich an Milch,
  wenn ich beim Supermarkt bin"). Während ein Live-Standort läuft, meldet sich Jon, wenn
  du am Ort bist.
- **Zwischenablage-Aktionen** — die Clipboard-Historie erkennt URLs, E-Mails, Telefon,
  IBAN, Adressen und Code und bietet passende Aktionen (öffnen, Maps, anrufen, merken,
  erklären lassen …).
- **Fokus-Statistik** — Jon erfasst lokal, in welchen Apps du wie lange bist; `/fokus`
  zeigt die letzten 7 Tage als Balkendiagramm, fließt in den Wochenrückblick ein.
  Standardmäßig aus, alles bleibt auf dem PC.
- **Pomodoro-Coach** — Mini Jon zeigt ein Timer-Badge, wird in Pausen fröhlich und gibt
  Bewegungstipps.
- **Meeting-Mitschrift** — `/meeting` nimmt System-Ton und Mikrofon (bevorzugt Fifine)
  gleichzeitig auf, transkribiert live und erstellt beim Stopp eine Zusammenfassung mit
  To-dos, die in den Kalender wandern.

## [3.17.0] — 2026-07-19

### Neu — fünf frische Ideen
- **Mini Jon tanzt zur Musik** — läuft Spotify oder Amazon Music, wippt Mini Jon im Takt,
  zeigt Notensymbole und färbt sich in einer Song-Farbe; stoppt die Musik, wird er sofort
  wieder normal (`/api/music/now`).
- **Trink- & Steh-Erinnerungen** — Mini Jon meldet sich alle 90 Minuten sanft (Wasser,
  aufstehen, durchatmen). Abschaltbar im Zahnrad-Menü.
- **Lange Telegram-Sprachnachrichten** — ab 200 Zeichen fasst Jon sie in Stichpunkten
  zusammen und trägt genannte Termine automatisch in den Kalender ein.
- **Vorlese-Modus** — markierten Text mit **Strg+Alt+V** an Mini Jon geben, er liest ihn
  mit seiner Stimme vor.
- **Automatische Datei-Ablage** — neue Downloads wandern regelbasiert in Unterordner
  (Bilder, Dokumente, Musik, Rechnungen, Screenshots …), alles per Papierkorb
  wiederherstellbar. Standardmäßig aus, Toggle im Zahnrad-Menü.

### Verbessert
- **Sprachwechsel** greift jetzt wirklich live (Deutsch/English) und ist auf mehr
  Oberflächen-Bereiche ausgeweitet.
- README mit Banner-Bild von Jon und Mini Jon, englische README ebenso.

## [3.16.0] — 2026-07-19

### Neu — Sieben große Funktionsblöcke

**Vertrauen: Papierkorb, Aktionsprotokoll, LAN-Pairing.** Löschen, Überschreiben und
Verschieben von Dateien sichern das Original vorher in `data/trash` (30 Tage). `/undo`
stellt die letzte Dateiaktion wieder her, `/papierkorb` (Alias `/trash`) listet den Inhalt.
Jeder Tool-Aufruf wird mit Quelle (App, Mini Jon, Telegram, Automation, Watcher) in einer
SQLite-Tabelle protokolliert; `/log` zeigt die letzten Aktionen mit Filter, das
Tagesbriefing fasst zusammen, was Jon in Abwesenheit getan hat. Bei `JON_LAN=1` muss sich
jedes neue Gerät per 6-stelligem Code koppeln, bevor es Zugriff bekommt; gekoppelte Geräte
sind im Zahnrad-Menü verwaltbar.

**Sprach-Erlebnis.** Wake-Word „Jon" läuft offline über openWakeWord im Backend, mit
automatischem Fallback auf die bisherige Erkennung. Barge-in: sprichst du, während Jon
redet, stoppt er sofort. Empfindlichkeit im Zahnrad-Menü einstellbar. Gilt für Jon und
Mini Jon.

**Browser-Automatisierung.** Neue Tool-Gruppe `browser_goto/click/fill/read/screenshot/
back/close` steuert ein sichtbares Chromium-Fenster (Playwright). Jon liest Seiten Schritt
für Schritt, klickt per Selektor oder sichtbarem Text und meldet Fehler verständlich.

**Jon-Kalender.** Eigener lokaler Kalender (📅-Knopf) mit Monats-/Wochenansicht. Jon trägt
Termine per Zuruf ein („Trag Freitag 15 Uhr Zahnarzt ein"), warnt bei Konflikten, zeigt
Automationen, Erinnerungen und den ICS-Kalender farblich integriert. `/kalender` zeigt 7
Tage; Termine mit Uhrzeit melden sich im Chat und als Benachrichtigung.

**Echtes Auto-Update.** `/update` sichert `data/`, holt per git die neue Version,
installiert nur Geändertes nach und startet neu (auf dem Pi via `systemctl restart jon`).

**Englisch & Deutsch.** Sprachumschalter im Zahnrad-Menü stellt Oberfläche und Jons
Antworten auf Englisch um. Neue `README.en.md`.

**Windows-Installer.** `build-installer.bat` bündelt das Backend mit PyInstaller zu einer
eigenständigen `jon-backend.exe` und paketiert per NSIS eine `Jon-Setup.exe` — kein Python,
kein Node, kein Terminal nötig. Ersetzt `installer-bauen.bat`.

### Auch dabei
- Telegram: Fotos werden per Vision-Modell analysiert; einfache Maus-/Tastaturbefehle
  („klick", „schreibe …", „drücke enter") lösen sofort das echte Tool aus.

## [3.15.1] — 2026-07-16

### Behoben — Web-App-Build scheiterte auf dem Raspberry Pi
`postcss.config.js` nutzte ESM-Syntax (`export default`) in einer CommonJS-Datei. Neuere
Node-Versionen am PC erkennen das automatisch, Node 18 auf dem Pi bricht mit
`SyntaxError: Unexpected token 'export'` ab. Die Datei heißt jetzt
`postcss.config.mjs` und ist damit auf jeder Node-Version eindeutig ESM.

## [3.15.0] — 2026-07-16

### Neu — Always-on-Jon auf dem Raspberry Pi
Das Backend läuft jetzt auf Wunsch auf einem **Raspberry Pi (ab Pi 4)** und ist damit für
Handy-PWA und Smartwatch **rund um die Uhr** erreichbar, auch wenn der PC aus ist. Ein
Befehl genügt: `bash pi-installieren.sh` installiert die Abhängigkeiten (neue schlanke
`backend/requirements-pi.txt` ohne PC-Steuerungs-Bibliotheken), setzt `JON_LAN=true`, baut
die Web-App für `http://<Pi-IP>:8756/app` und richtet einen **systemd-Dienst** ein, der
beim Hochfahren automatisch startet und bei Abstürzen neu startet. Der PC-Start über
`start-jon.bat` funktioniert unverändert weiter. Neue `.gitattributes` sorgt dafür, dass
Shell-Skripte mit Linux-Zeilenenden ausgeliefert werden.

## [3.14.3] — 2026-07-16

### Behoben — Mini Jon hatte kein Gesicht mehr
Bei den Stimmungen **nachdenklich/müde** (z. B. nach mehr als 20 Stunden ohne Kontakt)
und bei der Augen-Einstellung **„Verschlafen“** werden Augen und Mund als waagerechte
Linien gezeichnet. Der goldene Farbverlauf konnte auf solche Linien ohne Höhe nicht
angewendet werden — der Browser zeichnete sie dann **gar nicht**, und Mini Jon war nur
noch ein leerer Kreis. Der Farbverlauf nutzt jetzt feste Koordinaten
(`gradientUnits="userSpaceOnUse"`), damit hat Mini Jon in jeder Stimmung ein Gesicht.

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
