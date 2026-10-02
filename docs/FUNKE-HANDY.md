# Funke – dein Begleiter auf dem Handy

Stand: 2. Oktober 2026, Jon 4.58.0, Android-App Jon Gerät 1.7.0 (Code 11).

Funke ersetzt MiniJon auf dem Handy. Er ist ein kleiner, leuchtender Funke mit Gesicht und acht Stimmungen: ruhig, hört zu, denkt nach, arbeitet, spricht, freut sich, schläft und Fehler. Anders als MiniJon arbeitet Funke mit **Jons vollem Modell und allen Werkzeugen** und übernimmt Aufgaben vollständig, statt nur Tipps zu geben.

## Starten

1. Die Jon-App öffnen.
2. Auf der Startseite **Funke öffnen** antippen. Alternativ **Menü → Funke**.
3. Funke antippen, eine Schnellaktion wählen oder einfach schreiben bzw. diktieren.

## Was Funke kann

- **Schnellaktionen:** Timer, Erinnern, Mein Tag, Lernen, Fachteam und Wetter mit einem Tipp.
- **Alles, was Jon kann:** Wecker, Erinnerungen, Kalender, Recherche, Karten, Dateien, Präsentationen, Websites und mehr. Freigabepflichtige Aktionen fragt Funke vorher mit „Darf ich das?“.
- **Fachteam:** Bei komplexen Fragen holt Funke Jons Fachteam dazu. Die Fachagenten erscheinen als animierte Live-Karte im Gespräch – mit Verteilen, Arbeiten, Gegenprüfung und Ergebnis.
- **Harness:** Coding-Aufträge im gewählten Projekt erscheinen ebenfalls live mit Plan, Freigaben und Änderungen.
- **Gedächtnis:** Datierte Alltagsdinge („Am Sonntag gibt es Schnitzel“) bleiben auf deinem Jon gespeichert und lassen sich auf der Funke-Seite löschen.
- **Gesprächsverlauf:** Das Gespräch bleibt auf dem Gerät erhalten, bis du **Gespräch leeren** antippst.

## Funke über allen Apps

Der Schalter **Funke über allen Apps** blendet Funke als schwebende Figur über anderen Apps ein. Android fragt einmal nach **Über anderen Apps anzeigen**. Ziehen verschiebt Funke, Antippen öffnet den kleinen Chat. Während er arbeitet, leuchtet er orange und lässt Funken kreisen; danach freut er sich kurz. Beim Sperren verschwindet die Figur, die Animation pausiert.

Im Kiosk wird Funke als Teil des Jon-Fensters angezeigt, wie bisher MiniJon. Die Overlay-Freigabe ist eine Android-Systementscheidung und wird nicht automatisch erteilt.

## Technik

- Persona `funke` im Backend (`backend/app/services/personality.py`), Modell-Slot `jon`. Ältere Backends ohne diese Persona werden erkannt; Funke antwortet dann mit Jons Standard-Persönlichkeit.
- Die Figur ist ein eigenständiges Canvas-Skript (`frontend/mobile/funke.js`). Dieselbe Datei läuft in der App und im Overlay (`android/device-app/src/main/assets/mini-jon/funke.js`). `scripts/build-android.ps1` kopiert sie beim Build.
- Reduzierte Bewegung wird respektiert; verborgene Fenster pausieren das Rendering.
- MiniJon bleibt auf dem Desktop unverändert erhalten.

## Build

```powershell
./scripts/build-android.ps1
```

Der Build benötigt Android-SDK, JDK, Node und die vorhandene Signierungskonfiguration. Für das Fachteam, die Funke-Persona und die Live-Karten muss auf dem verbundenen PC oder Pi Jon 4.58.0 laufen.

## Prüfung

- Funke-Seite, Schnellaktionen, Fachteam-Live-Karte, Freigaben und Overlay-Figur im Browser mit simulierter Gerätebrücke geprüft.
- Backend-Tests für Persona, Modell-Slot und Fachteam-Karten bestehen.
- Der Android-Build selbst und ein Test auf einem physischen Handy stehen für 1.7.0 noch aus.
