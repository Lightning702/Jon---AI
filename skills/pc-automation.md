# PC-Automatisierung

Anleitung für zuverlässige Maus-/Tastatur-Steuerung und App-Bedienung. Bearbeitbar.

## Regeln

1. Rufe zuerst `get_screen_info` auf, um Auflösung und Mausposition zu kennen.
2. Koordinaten als Bruchteile 0–1 (bezogen auf den Hauptmonitor) sind robuster als feste
   Pixel. Mitte = x 0.5, y 0.5.
3. Nach dem Öffnen einer App oder Seite immer `wait` (2–4 s), bei Apps zusätzlich
   `focus_window`, bevor du klickst oder tippst.
4. Bevorzuge Tastatur (`keyboard_hotkey`, `keyboard_type`) statt blindem Klicken.
5. Prüfe Zwischenschritte mit `screenshot` oder `list_windows`, wenn unsicher.

## Rezepte

**YouTube-Suche + erstes Video:** `open_url` mit
`https://www.youtube.com/results?search_query=BEGRIFF` (Leerzeichen = +), `wait 4`,
`mouse_click` bei x 0.25 y 0.35.

**Datei schnell finden:** `search_files` mit Wurzelordner und Muster (`*.pdf`).

**Text in App einfügen:** `clipboard_set` mit dem Text, `focus_window`, dann
`keyboard_hotkey ["ctrl","v"]` — sicherer als Tippen bei Sonderzeichen.
