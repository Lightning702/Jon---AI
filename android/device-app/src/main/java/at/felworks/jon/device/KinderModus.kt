package at.felworks.jon.device

import android.content.Context
import org.json.JSONObject

object KinderModus {
    private val gesperrt = Regex("(?i)porn|xxx|sex|nude|nackt|erotik|escort|onlyfans|hentai|casino|wetten|betting|gambling|poker|slot|drogen|weed|cannabis|vape|waffen|gore")

    private fun prefs(context: Context) = context.getSharedPreferences("jon-kinder", Context.MODE_PRIVATE)

    fun alter(context: Context): Int {
        val p = prefs(context)
        return if (p.getBoolean("an", false)) p.getInt("alter", 10).coerceIn(3, 17) else 0
    }

    fun stand(context: Context): JSONObject {
        val p = prefs(context)
        return JSONObject().put("an", p.getBoolean("an", false)).put("alter", p.getInt("alter", 10).coerceIn(3, 17))
    }

    fun setzen(context: Context, daten: JSONObject): JSONObject {
        val p = prefs(context)
        p.edit()
            .putBoolean("an", daten.optBoolean("an", p.getBoolean("an", false)))
            .putInt("alter", daten.optInt("alter", p.getInt("alter", 10)).coerceIn(3, 17))
            .commit()
        return stand(context)
    }

    fun kindgerecht(text: String): Boolean = !gesperrt.containsMatchIn(text)

    fun anfrage(context: Context, body: JSONObject): JSONObject {
        val jahre = alter(context)
        if (jahre > 0) body.put("kinder", jahre)
        if (Sprache.englisch(context)) body.put("sprache", "en")
        return body
    }

    fun prompt(alter: Int): String = buildString {
        append("KINDERMODUS: Du sprichst mit einem Kind, etwa $alter Jahre alt. ")
        append(
            when {
                alter <= 8 -> "Nutze sehr einfache Wörter und ganz kurze Sätze. "
                alter <= 12 -> "Nutze einfache Wörter und kurze Absätze. "
                else -> "Sprich wie mit einem Teenager: locker, ehrlich, ohne von oben herab. "
            }
        )
        append("Sei freundlich, geduldig und ermutigend. Keine Inhalte für Erwachsene, keine Gewaltdetails, keine Schimpfwörter, keine Gruselgeschichten, keine Diät- oder Körpertipps und keine Anleitungen für Gefährliches wie Feuer, Messer, Medikamente, Chemikalien oder Mutproben. ")
        append("Frag nie nach Adresse, Schule, Telefonnummer, Fotos oder Passwörtern und rate freundlich davon ab, so etwas online zu teilen. ")
        append("Wenn das Kind traurig ist, Angst hat, gemobbt wird oder von etwas Schlimmem erzählt: nimm es ernst, tröste es und ermutige es, gleich mit den Eltern oder einer Vertrauensperson zu reden. In Österreich hilft Rat auf Draht rund um die Uhr unter 147, in Deutschland die Nummer gegen Kummer unter 116 111. ")
        append("HAUSAUFGABEN: Gib nicht einfach die fertige Lösung. Erkläre Schritt für Schritt, gib Hinweise, stell kleine Rückfragen und lass das Kind selbst rechnen, lesen oder formulieren. Prüfe danach seine Antwort, erkläre Fehler freundlich und lobe echte Fortschritte. ")
        append("Nur wenn das Kind ausdrücklich seine eigene Lösung vergleichen will, zeig die richtige Lösung mit kurzer Erklärung. ")
        append("Bei Themen, die nichts für Kinder sind, sag freundlich, dass das eine Frage für die Eltern ist. Bilder, die du erstellst, müssen kindgerecht sein.")
    }
}
