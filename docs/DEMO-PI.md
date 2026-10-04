# Jon auf der Website ausprobieren

Stand: 4. Oktober 2026, Jon 4.59.1.

Unter `getjon.info/testen/` können Besucher Jon direkt im Browser ausprobieren:
- mit Jon und MiniJon schreiben
- Orte finden und Routen berechnen (Jon Maps)
- eine kurze Aufnahme transkribieren

Die Demo läuft auf deinem Pi und kann nichts auf einem Computer steuern.

## Sicherheit

- Eigener Prozess `python -m app.demo` mit eigenem Benutzerdienst `jon-demo` (`systemctl --user`). Er lauscht nur auf `127.0.0.1:8790`.
- Der Prozess kennt nur die Demo-Routen: `/demo/status`, `/demo/chat`, `/demo/orte`, `/demo/route` und `/demo/transkript`. Normale Jon-Routen wie `/api/settings` oder `/api/chat` gibt es dort nicht.
- Der Chat ruft das Modell ohne Werkzeuge auf. Er nutzt eigene Persona-Texte und nimmt weder Jons Gedächtnis noch deine Persona oder Dateien mit. Nichts wird gespeichert.
- Erlaubt sind höchstens 12 Nachrichten mit je 1500 Zeichen und nur die Rollen „user“ und „assistant“.
- Pro Besucher sind 20 Anfragen in zehn Minuten erlaubt, insgesamt 600 pro Tag. Anpassbar über `JON_DEMO_PRO_IP` und `JON_DEMO_PRO_TAG`.
- CORS lässt nur `getjon.info` und `getjon.netlify.app` zu (`JON_DEMO_ORIGINS`).
- Das Modell ist das, was am Pi eingestellt ist. `JON_DEMO_PROVIDER` und `JON_DEMO_MODEL` setzen ein eigenes. Die Kosten trägt der hinterlegte API-Key.

## Einrichten

Die IP `10.0.0.63` liegt in deinem Heimnetz. Deshalb läuft die Einrichtung auf dem Pi selbst:

```text
ssh FelWorks@10.0.0.63
cd ~/Jon---AI          (oder wo Jon auf dem Pi liegt)
git pull               (oder Pi-Update in der Jon-App)
bash scripts/demo-pi-einrichten.sh
```

Das Skript richtet den Dienst ein, installiert bei Bedarf Tailscale und gibt die Demo über Tailscale Funnel unter dem Pfad `/demo` frei. Andere Pfade deines Funnels, etwa `/` für ein anderes Projekt oder `/codes` für den Codeserver, bleiben unverändert. Das ergibt eine feste HTTPS-Adresse ohne Portfreigabe am Router. Zum Schluss nennt es die Adresse, zum Beispiel `https://felworks-pi.tail1234.ts.net`. Trag sie in Netlify als `JON_DEMO_URL` ein und veröffentliche neu. Funnel muss in der Tailscale-Verwaltung einmal erlaubt werden; das Skript zeigt dafür einen Link an.

Stoppen: `tailscale funnel --set-path /demo off && systemctl --user disable --now jon-demo`

## Prüfung

Getestet sind:
- 4 Python-Tests:
  - Der Chat-Stream läuft ohne Werkzeuge und mit eigener Persona.
  - Normale Routen gibt es nicht, und fremde Seiten bekommen kein CORS.
  - Ungültige Eingaben werden abgelehnt, die Ratenbegrenzung greift.
  - Maps und Transkript funktionieren.
- Im Browser lief die Testseite gegen einen lokalen Demo-Server mit Testmodell.

Nicht getestet: der echte Pi, Tailscale Funnel und die Spracherkennung auf dem Pi.
