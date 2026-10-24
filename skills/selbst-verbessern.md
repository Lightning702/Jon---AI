# Selbst verbessern

Anleitung, wie Jon ein Projekt – auch sich selbst – gründlich prüft, ehrlich bewertet und so
lange verbessert, bis nichts Wesentliches mehr fehlt. Nutze sie, wenn der Nutzer sagt
„verbessere dich selbst“, „mach alles fertig“, „probier alle Funktionen aus“ oder „was fehlt
noch?“. Am besten läuft das im Jon Harness (Werkzeug `harness_task`, modus code) oder im
Terminal mit `/verbessern` bzw. `/ziel`.

## Grundhaltung

- **Ehrlich bewerten.** Eine 7 ist eine 7. Schönreden hilft niemandem.
- **Erst messen, dann ändern.** Jede Bewertung stützt sich auf einen echten Versuch: Test,
  Aufruf, Klick, Messung der Zeit – nicht auf Vermutungen.
- **Ursachen statt Symptome.** Dauert etwas lange, findest du heraus, *wo* die Zeit
  verloren geht (Modell, Netzwerk, Freigabe, Vorbereitung), bevor du etwas änderst.
- **Nichts kaputt machen.** Tests laufen nie gegen echte Nutzerdaten, sondern mit eigenem
  Datenordner (`JON_DATA_DIR`) und auf einer Testinstanz (anderer Port).

## Ablauf in Runden

1. **Bestand aufnehmen.** Liste alle Hauptfunktionen auf (README, docs/FEATURES.md,
   Werkzeugliste, Menüs). Gruppiere sie: Chat, Dateien und Office, Präsentationen, Code,
   Bildschirm und PC-Steuerung, Telegram, Handy, Lernen, Spiele, Website, Terminal.
2. **Jede Funktion ausprobieren.** Für jede Gruppe ein echter Durchlauf mit typischer
   Eingabe. Notiere Dauer, Ergebnis und jeden Fehler.
3. **Bewerten (1–10)** mit einem Satz Begründung. Maßstab: 10 = funktioniert beim ersten
   Mal, schnell, schön, verständlich, robust bei Fehlern.
4. **Fragen stellen:** Was braucht der Nutzer, das es noch nicht gibt? Was kann Jon noch
   nicht gut? Was würde ein Profi anders machen? Wo könnte ein Freund des Nutzers
   scheitern (kein Schlüssel, kein Internet, anderes Betriebssystem)?
5. **Die drei wichtigsten Punkte umsetzen**, jeweils mit Test.
6. **Neu bewerten.** Zurück zu Schritt 2, bis alles mindestens 9 ist oder keine sinnvolle
   Verbesserung mehr übrig ist.
7. **Abschluss:** Versionsnummer erhöhen, Änderungsprotokoll schreiben, alle Tests laufen
   lassen, Bericht an den Nutzer mit Tabelle Funktion → vorher → nachher.

## Typische Schwachstellen, die sich lohnen

- Antwortzeit: Denkt das Modell bei einfachen Fragen zu lange nach? Ist ein schnelleres
  Modell für Kurzantworten eingestellt? Wird vorab unnötig viel geladen?
- Freigaben, die auf einem Kanal (z. B. Telegram) nie angezeigt werden und deshalb hängen.
- Fehlermeldungen, die der Nutzer nicht versteht („Fehler 500“ statt „Der Anbieter ist
  überlastet – ich versuche es mit einem anderen Modell“).
- Abgeschaltete Modelle oder Dienste in Standardeinstellungen.
- Funktionen, die nur mit API-Schlüssel gehen, obwohl es einen freien Weg gäbe.
- Persönliche Daten in Code, Tests oder Beispielen.
- Kalter Start: Die erste Anfrage nach dem Start ist oft viel langsamer als die zweite
  (Verbindung, Modelle laden, Prompt bauen). Miss beide getrennt und wärme beim Start vor.
- Riesige Anfragen: Prüfe, wie viele Zeichen System-Prompt und Werkzeugliste bei einer
  einfachen Frage wie „Hallo“ wirklich mitgehen.
- Bildschirmsteuerung: Ein Hintergrundprozess darf unter Windows nicht einfach den Fokus
  wechseln, und ein offenes Sicherheitsfenster dunkelt den Bildschirm ab und fängt jeden
  Klick ab. In Sicherheitsfenster (Firewall, Benutzerkontensteuerung, Anmeldung) klickt
  Jon nie selbst.
- Abkürzungen, die zu viel fangen: Ein Schnellweg wie „klick …“ darf nicht greifen, wenn
  im Satz ein Ziel steht.
- Testattrappen müssen dieselben Felder liefern wie das Original, sonst bewertest du
  Fehler, die es gar nicht gibt.
- Tests, die heimlich echte Ordner beschreiben: Prüfe nach einem Testlauf, ob in Jons
  echtem Ordner oder Datenordner neue Dateien entstanden sind.

## Bericht-Vorlage

| Funktion | vorher | nachher | Was geändert wurde |
| --- | --- | --- | --- |
| Telegram-Antworten | 4 | 9 | Freigaben als Knöpfe, schnelles Modell, Antwort erscheint live |
