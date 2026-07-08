# Changelog

Alle nennenswerten Änderungen an Jon.

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
