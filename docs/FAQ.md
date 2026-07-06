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

**Wie bringe ich Jon etwas bei?**
Bearbeite einen Skill (Konten → Skills) oder sag es ihm — mit `remember` merkt er sich
Fakten dauerhaft.
