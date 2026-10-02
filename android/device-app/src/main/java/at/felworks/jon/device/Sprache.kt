package at.felworks.jon.device

import android.content.Context
import org.json.JSONObject
import java.util.Locale

object Sprache {
    private val erlaubt = setOf("auto", "de", "en")

    private fun prefs(context: Context) = context.getSharedPreferences("jon-profil", Context.MODE_PRIVATE)

    fun wahl(context: Context): String = prefs(context).getString("sprache", "auto")?.takeIf { it in erlaubt } ?: "auto"

    fun code(context: Context): String = when (wahl(context)) {
        "de" -> "de"
        "en" -> "en"
        else -> if (Locale.getDefault().language == "de") "de" else "en"
    }

    fun englisch(context: Context): Boolean = code(context) == "en"

    fun locale(context: Context): Locale = if (englisch(context)) Locale.US else Locale.GERMANY

    fun t(context: Context, deutsch: String, english: String): String = if (englisch(context)) english else deutsch

    fun stand(context: Context): JSONObject = JSONObject().put("wahl", wahl(context)).put("code", code(context))

    fun setzen(context: Context, wert: String): JSONObject {
        prefs(context).edit().putString("sprache", wert.takeIf { it in erlaubt } ?: "auto").commit()
        return stand(context)
    }
}
