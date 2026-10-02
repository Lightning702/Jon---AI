package at.felworks.jon.device

import android.content.Context
import android.content.Intent
import at.felworks.jon.MainActivity
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import org.json.JSONArray
import org.json.JSONObject

object Anzeige {
    private val _liste = MutableStateFlow<List<JSONObject>>(emptyList())
    val liste: StateFlow<List<JSONObject>> = _liste
    private val weckend = setOf("wecker", "timer", "suchen", "durchsage")

    fun zeigen(eintrag: JSONObject) {
        val id = eintrag.optString("id")
        _liste.update { alt -> alt.filter { it.optString("id") != id } + eintrag }
    }

    fun entfernen(id: String): JSONObject? {
        val weg = _liste.value.firstOrNull { it.optString("id") == id }
        _liste.update { alt -> alt.filter { it.optString("id") != id } }
        return weg
    }

    fun json(): JSONArray = JSONArray().apply { _liste.value.forEach { put(it) } }

    fun weckt(liste: List<JSONObject> = _liste.value): Boolean = liste.any { it.optString("art") in weckend }

    fun jonHolen(context: Context, wecken: Boolean = true) {
        runCatching {
            context.startActivity(
                Intent(context, MainActivity::class.java)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                    .putExtra("wecken", wecken)
            )
        }
    }
}
