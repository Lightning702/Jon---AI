# FAQ

**Kostet Jon etwas?**
Jon selbst ist kostenlos und quelloffen. Du brauchst einen API-Key eines Anbieters; viele
haben ein Gratis-Kontingent (z. B. NVIDIA NIM).

**Wo kommen meine API-Keys hin?**
In die lokale `.env` oder in den Konten-Speicher unter `data/` (beides git-ignoriert). Bei
der Handy-App bleibt der Key im `localStorage` deines Geräts. Keys landen nie im Code oder
auf GitHub.

**Kann ich mich mit meinem ChatGPT-Plus- oder Claude-Pro-Abo anmelden?**
Nicht mit dem Abo selbst. OpenAI und Anthropic bieten für Drittanbieter offiziell **keinen**
Login an, der die Abo-Tokens nutzt. Jon nutzt den offiziellen API-Zugang (eigener Key).
Sobald es eine offizielle Konto-Verknüpfung gibt, ist die Architektur darauf vorbereitet.

**Warum zeigt der Konten-Bereich keinen Tarif oder kein Profilbild?**
Weil die offiziellen APIs diese Informationen nicht bereitstellen. Jon zeigt dann ehrlich
„Über die offizielle API nicht verfügbar" statt etwas zu erfinden.

**Warum fragt Jon vor jeder Aktion?**
Der Standardmodus ist „Zuerst fragen". Im Zahnrad-Menü kannst du auf „Alles erlauben"
umstellen; die Wahl wird gespeichert.

**Kann Jon wirklich meinen PC steuern?**
Ja — PowerShell/CMD, Dateien, Programme, Maus/Tastatur und mehr. Deshalb der Freigabe-Modus.
Aktionen laufen mit deinen Benutzerrechten.

**Antwortet die KI langsam?**
Große Modelle im Gratis-Tier sind gedrosselt. `openai/gpt-oss-120b` ist ein guter
Kompromiss; kleinere Modelle sind schneller. Modell im Kopf der App wechselbar.

**Die KI schreibt nicht mal einfachen Code / bricht ab?**
Das Antwortlimit liegt jetzt bei bis zu 32.768 Tokens und passt sich Modellgrenzen an.
Falls ein Modell entkoppelt ist (404), ein anderes wählen.

**Warum blockiert ein Provider die Handy-App?**
CORS. NVIDIA läuft über einen Proxy; OpenAI/Gemini/GLM/DeepSeek/Qwen/Mistral gehen direkt.

**Geht Jon auch ganz ohne API-Key und ohne Cloud?**
Ja, mit Ollama. Ollama installieren, ein Modell laden (`ollama pull llama3.2`), im
Zahnrad-Menü unter **Ollama** einschalten — fertig. Kostenlos, privat, offline.
Komplette Anleitung: [OLLAMA.md](OLLAMA.md).

**Kann Ollama auf einem anderen PC laufen?**
Ja. Auf dem Ollama-Rechner `OLLAMA_HOST=0.0.0.0` setzen, Port 11434 in der Firewall
freigeben und in Jon Host und Port eintragen. Über Tailscale klappt das auch über das
Internet, ohne Portfreigabe im Router.

**Kann ich meinen Ollama-Server für Freunde freigeben?**
Ja, seit 3.37.2. Im Ollama-Fenster unter **Serverfreigabe** einschalten und den
Freigabecode weitergeben. Sie chatten dann über deine Grafikkarte, bekommen aber keinerlei
Zugriff auf deinen PC — nur das Antworten des Modells ist freigegeben. Jede Anfrage braucht
ein persönliches Zugriffstoken, und ein Widerruf wirkt sofort.

**Sieht der Besitzer eines freigegebenen Servers meine Chats?**
Er sieht, was jeder Modellbetreiber sieht: dass angefragt wird, mit welchem Modell und wann.
Die Inhalte laufen durch seinen Ollama-Server — schick also nichts Vertrauliches über einen
fremden Server.

**Warum ruft mein Ollama-Modell keine Werkzeuge auf?**
Nicht jedes lokale Modell kann das. Jon erkennt die Meldung `does not support tools` und
antwortet automatisch ohne Werkzeuge weiter. Modelle wie `llama3.1`, `llama3.3` oder
`qwen2.5` beherrschen Werkzeuge.

**Wie bringe ich Jon etwas bei?**
Bearbeite einen Skill (Konten → Skills) oder sag es ihm — mit `remember` merkt er sich
Fakten dauerhaft.
