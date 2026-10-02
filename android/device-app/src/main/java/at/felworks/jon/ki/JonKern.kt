package at.felworks.jon.ki

import android.content.Context
import android.util.Base64
import kotlinx.coroutines.flow.Flow
import org.json.JSONObject
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

enum class Weg { PI, SOLO, LOKAL }

object JonKern {
    fun weg(context: Context, gekoppelt: Boolean, verbunden: Boolean): Weg = when {
        Solo.an(context) && Solo.gewaehlt(context) == "handy" && Katalog.standard(context) != null -> Weg.LOKAL
        Solo.an(context) && Solo.bereit(context) -> Weg.SOLO
        gekoppelt && verbunden -> Weg.PI
        Katalog.standard(context) != null -> Weg.LOKAL
        Solo.bereit(context) -> Weg.SOLO
        else -> Weg.PI
    }

    fun name(context: Context): String = context.getSharedPreferences("jon-profil", Context.MODE_PRIVATE).getString("name", "")?.trim().orEmpty()

    fun nameSetzen(context: Context, name: String) {
        context.getSharedPreferences("jon-profil", Context.MODE_PRIVATE).edit().putString("name", name.trim().take(40)).apply()
    }

    fun system(context: Context, arbeit: Boolean, nutzer: String, bilder: Boolean, stimme: Boolean = false): String {
        val englisch = at.felworks.jon.device.Sprache.englisch(context)
        val jetzt = LocalDateTime.now().format(DateTimeFormatter.ofPattern("EEEE, d. MMMM yyyy, HH:mm", if (englisch) Locale.US else Locale.GERMAN))
        val wer = nutzer.ifBlank { name(context) }
        val fakten = Gedaechtnis.fakten(context)
        return buildString {
            append("Du bist Jon, ein freundlicher und hilfsbereiter KI-Assistent von FelWorks. Du läufst direkt auf dem Handy")
            if (wer.isNotBlank()) append(" von $wer")
            append(". Heute ist $jetzt Uhr.\n")
            append("Antworte auf Deutsch, klar und natürlich. Duze den Nutzer.")
            append(if (stimme) " Deine Antwort wird vorgelesen: sprich in kurzen, gut hörbaren Sätzen ohne Aufzählungszeichen, Tabellen oder Code.\n" else " Nutze Markdown, wenn es hilft.\n")
            val apps = at.felworks.jon.device.GeraeteApps.liste(context).joinToString { it.name }
            append("Du hast Werkzeuge auf diesem Handy: Wecker und Timer stellen, ")
            val versteckt = at.felworks.jon.device.GeraeteApps.versteckt(context)
            append(if (apps.isNotBlank() && !versteckt) "freigegebene Apps öffnen ($apps), " else "")
            append("Musik steuern, Wetter, Websuche, Webseiten lesen, ein Fitness-Tagebuch mit Schritten und Trainings, die Bildschirmzeit ansehen, dir Dinge merken und den Handy-Status abfragen")
            if (bilder) append(" sowie Bilder erstellen")
            append(". Nutze sie, wenn sie helfen, und erfinde nie ihre Ergebnisse. Andere Apps kannst du nicht öffnen. Wenn etwas nicht geht, sag es ehrlich.\n")
            if (arbeit) {
                append("Du bist im Work-Modus und erledigst Aufgaben gründlich und vollständig wie ein Profi. Zerlege große Aufgaben in Schritte und arbeite sie ab. ")
                append("Dateien schreibst du mit datei_schreiben in deinen Arbeitsordner. Websites baust du als websites/<kurzer-name>/index.html mit style.css und script.js: modern, schön, responsiv fürs Handy, ohne Build-Werkzeuge. ")
                append("Programme schreibst du vollständig und lauffähig. Nenne am Ende kurz, welche Dateien du angelegt hast und wie man sie öffnet.\n")
            } else {
                append("Du bist im Chat-Modus: hilf schnell bei Fragen, Texten und kleinen Aufgaben. Für große Projekte, Websites oder Programme empfiehlst du den Work-Modus.\n")
            }
            if (fakten.isNotEmpty()) {
                append("Das weißt du über den Nutzer:\n")
                fakten.takeLast(60).forEach { append("- ").append(it).append('\n') }
            }
            if (versteckt) append("Die freigegebenen Apps sind versteckt: Zähl nie auf, welche Apps es gibt, und sag bei der Frage danach, dass Jon hier keine anderen Apps anbietet. Öffne eine App nur, wenn sie ausdrücklich beim Namen genannt wird.\n")
            val kind = at.felworks.jon.device.KinderModus.alter(context)
            if (kind > 0) append(at.felworks.jon.device.KinderModus.prompt(kind)).append('\n')
            if (englisch) append("IMPORTANT: The user has selected English. Answer entirely in English, including all explanations, unless you are explicitly asked to use another language.\n")
        }
    }

    fun antworten(context: Context, anfrage: JSONObject): Flow<JSONObject> {
        val liste = anfrage.optJSONArray("verlauf")
        val verlauf = mutableListOf<Pair<String, String>>()
        if (liste != null) for (i in 0 until liste.length()) {
            val m = liste.optJSONObject(i) ?: continue
            val rolle = m.optString("role")
            val inhalt = m.optString("content")
            if ((rolle == "user" || rolle == "assistant") && inhalt.isNotBlank()) verlauf += rolle to inhalt
        }
        val text = anfrage.optString("text").trim()
        require(text.isNotEmpty()) { "Die Nachricht ist leer." }
        val roheBilder = mutableListOf<String>()
        anfrage.optString("bild").takeIf { it.isNotBlank() }?.let { roheBilder += it }
        anfrage.optJSONArray("bilder")?.let { a -> for (i in 0 until a.length()) a.optString(i).takeIf { it.isNotBlank() }?.let { roheBilder += it } }
        val bilder = roheBilder.take(8).mapNotNull { runCatching { Base64.decode(it, Base64.DEFAULT) }.getOrNull() }
        val arbeit = anfrage.optString("modus") == "coding"
        val nutzer = anfrage.optString("name")
        val stimme = anfrage.optBoolean("stimme")
        val motor = anfrage.optString("motor").ifBlank { if (Solo.gewaehlt(context) == "handy") "lokal" else "solo" }
        return if (motor == "lokal") {
            val modell = anfrage.optString("modell").takeIf { name -> name.isNotBlank() && Katalog.modell(context, name)?.let { Katalog.vorhanden(context, it) } == true } ?: Katalog.standard(context)
                ?: error("Lade zuerst ein Offline-Modell herunter (Einstellungen → Offline-KI).")
            LokaleKi.antworten(context, modell, system(context, arbeit, nutzer, false, stimme), verlauf, text, bilder, arbeit)
        } else Solo.antworten(context, system(context, arbeit, nutzer, Solo.kannBilder(context), stimme), verlauf, text, bilder, arbeit)
    }

    fun stoppen() {
        LokaleKi.stoppen()
        Solo.stoppen()
    }
}
