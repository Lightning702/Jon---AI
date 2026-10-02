# MiniJon auf dem Handy

Stand: 2. Oktober 2026, Android-Version 1.6.0 (Code 10).

## Starten

1. Die aktualisierte Jon-App öffnen.
2. Direkt auf der Startseite unter der oberen Leiste **MiniJon öffnen** antippen. Alternativ oben links **Menü**, dann **MiniJon**.
3. **MiniJon auf dem Bildschirm zeigen** antippen.
4. In Android **Über anderen Apps anzeigen** für Jon erlauben und zur App zurückkehren.

MiniJon bleibt danach auch außerhalb des Kiosk-Modus über anderen Apps sichtbar. Ziehen verschiebt ihn, Antippen öffnet den Chat. **Klein** klappt den Chat wieder zu. **Ausblenden** in der dauerhaften Benachrichtigung oder auf der MiniJon-Seite beendet den Begleiter. Beim Sperren verschwindet die Figur; die Animation pausiert. Nach einer erzwungenen Beendigung durch Android die Jon-App erneut öffnen.

Die Overlay-Freigabe ist eine Android-Systementscheidung. Sie wird nicht automatisch oder über ADB erteilt. Manche geschützten Apps unterdrücken fremde Overlays. Der Begleiter liest dadurch nicht automatisch den Inhalt anderer Handy-Apps.

Im Kiosk wird MiniJon als Teil des sichtbaren Jon-Fensters angezeigt. Dadurch kann die Android-Sperre für fremde Overlay-Fenster bestehen bleiben. Beim Verlassen des Kiosks wechselt MiniJon zurück zum schwebenden Fenster. Während im Kiosk eine andere zugelassene App geöffnet ist, bleibt MiniJon verborgen und erscheint bei der Rückkehr zu Jon wieder. Ein laufendes Gespräch bleibt während dieses Wechsels erhalten.

## Verbindung und Erinnerungen

Der mobile MiniJon nutzt dieselbe verschlüsselte Verbindung zum PC/Pi wie die vorhandene Jon-App. Es gibt keine zweite Kopplung. Gesprächskontext des schwebenden Chats wird nach verbundenem Server getrennt gespeichert. MiniJon verwendet die Persona `junior`; Werkzeuge benötigen ihre bestehenden Freigaben.

Für das neue Alltagsgedächtnis muss auf dem verbundenen Pi auch das aktualisierte Backend laufen. Das Handy-Update allein installiert kein Pi-Update.

Beispiel: Am Freitag, 02.10.2026, **Am Sonntag gibt es Schnitzel zu Mittag** sagen. Jon speichert den 04.10.2026 und die Mahlzeit. Am Sonntag beantwortet **Was gibt es heute zu Mittag?** die Frage auch nach einem Backend-Neustart. Diese eindeutigen Essenspläne werden ohne Modellaufruf gespeichert und abgefragt. Vermutungen, Fragen, verneinte Angaben und zitierte Beispiele werden nicht automatisch als Zusage gespeichert. Andere Erinnerungen verwenden weiterhin Jons vorhandene Gedächtniswerkzeuge.

Auf der MiniJon-Seite stehen die datierten Essenspläne mit Datum und Löschknopf. Sie liegen auf dem jeweils verbundenen Backend in `alltagsgedaechtnis.json`. PC und Handy teilen sie, wenn beide denselben Server verwenden. Zwei unabhängige Backend-Installationen synchronisieren sie nicht automatisch.

## Quellcode und Build

Der Android-Quellcode liegt jetzt auch im Jon-Repository unter `android/`. Das bestehende Android-Studio-Projekt unter `C:\Users\felix\AndroidStudioProjects\Jon` wurde ebenfalls aktualisiert. Eine Sicherung seiner zuvor bearbeiteten Dateien liegt lokal unter `design/android-backup-20261002/`.

```powershell
./scripts/build-android.ps1
```

Der Build benötigt die Android-SDK-/JDK-Umgebung, Node und die vorhandene Signierungskonfiguration. Er baut die mobile React-Oberfläche, übernimmt denselben WebGL-Roboter wie auf dem Desktop, führt Android-Unit-Tests aus und erzeugt APK und Prüfsummen. Mit `-PlayBundle` entsteht zusätzlich das Play-Bundle unter `artifacts/minijon-1.6.0/`. Zugangsschlüssel und lokale Geräte-Einstellungen sind nicht Bestandteil des Repositorys.

## Prüfung

- Signierter Release-Build mit Android-Lint und vorhandenen Android-Unit-Tests erfolgreich.
- Android-Version 1.5.1 wurde zuvor auf dem Testgerät installiert und nachgeprüft. Der Build von 1.6.0 wurde signiert und alle 15 Android-Unit-Tests bestehen; die Installation von 1.6.0 ist bei wieder angeschlossenem Gerät möglich.
- Direkter Startknopf, Seitenmenü, MiniJon-Seite, Aufgabenauftritte und Chat im Browser mit Beispieldaten geprüft.
- Dauerhaftes Sonntagsgedächtnis, Datumwechsel, Überschreiben derselben Mahlzeit, Löschen und fehlende Erinnerungen automatisch geprüft.
- Die native Overlay-Freigabe war bei der letzten Geräteprüfung erteilt. Dauerbetrieb, Tastaturverhalten und Akkuverbrauch sind noch nicht durch einen längeren Test am physischen Handy bestätigt.

Android-Dokumentation: [Overlay-Einstellung](https://developer.android.com/reference/android/provider/Settings#ACTION_MANAGE_OVERLAY_PERMISSION), [Foreground-Service-Typen](https://developer.android.com/develop/background-work/services/fgs/service-types), [Kiosk und Overlay-Sperren](https://developer.android.com/work/dpc/dedicated-devices/lock-task-mode).
