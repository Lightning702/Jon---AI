package at.felworks.jon.ki

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

object Gedaechtnis {
    private fun prefs(context: Context) = context.getSharedPreferences("jon-gedaechtnis", Context.MODE_PRIVATE)

    fun fakten(context: Context): List<String> {
        val roh = runCatching { JSONArray(prefs(context).getString("fakten", "[]")) }.getOrDefault(JSONArray())
        return (0 until roh.length()).map { roh.optString(it) }.filter { it.isNotBlank() }
    }

    @Synchronized
    fun merken(context: Context, fakt: String): JSONObject {
        val sauber = fakt.trim().replace(Regex("\\s+"), " ").take(300)
        require(sauber.isNotEmpty()) { "Was soll ich mir merken?" }
        val liste = fakten(context).filterNot { it.equals(sauber, true) }.toMutableList()
        liste += sauber
        prefs(context).edit().putString("fakten", JSONArray(liste.takeLast(120)).toString()).apply()
        return JSONObject().put("gemerkt", sauber).put("anzahl", liste.size.coerceAtMost(120))
    }

    fun vergessen(context: Context, index: Int): JSONArray {
        val liste = fakten(context).toMutableList()
        if (index in liste.indices) liste.removeAt(index)
        prefs(context).edit().putString("fakten", JSONArray(liste).toString()).apply()
        return JSONArray(liste)
    }

    private fun ordner(context: Context) = File(context.filesDir, "chats").apply { mkdirs() }

    private fun sicher(id: String): String {
        require(id.matches(Regex("lokal-[A-Za-z0-9_-]{4,60}"))) { "Ungültige Chat-Kennung." }
        return id
    }

    fun chats(context: Context): JSONArray {
        val liste = ordner(context).listFiles { d -> d.name.endsWith(".json") }.orEmpty()
            .mapNotNull { runCatching { JSONObject(it.readText()) }.getOrNull() }
            .sortedByDescending { it.optLong("updated") }
        return JSONArray().apply {
            liste.forEach { c ->
                put(JSONObject().put("id", c.optString("id")).put("title", c.optString("title")).put("updated_at", c.optString("updated_at"))
                    .put("updated", c.optLong("updated")).put("provider", c.optString("provider")).put("model", c.optString("model"))
                    .put("mode", c.optString("mode")).put("lokal", true))
            }
        }
    }

    fun chat(context: Context, id: String): JSONObject {
        val datei = File(ordner(context), sicher(id) + ".json")
        check(datei.isFile) { "Diesen Chat gibt es nicht mehr." }
        return JSONObject(datei.readText())
    }

    @Synchronized
    fun speichern(context: Context, chat: JSONObject): JSONObject {
        val id = sicher(chat.optString("id"))
        val text = chat.toString()
        require(text.length < 4_000_000) { "Der Chat ist zu lang zum Speichern." }
        val jetzt = System.currentTimeMillis()
        chat.put("updated", jetzt).put("updated_at", java.time.Instant.ofEpochMilli(jetzt).toString())
        val ziel = File(ordner(context), "$id.json")
        val temp = File(ordner(context), "$id.neu")
        temp.writeText(chat.toString())
        temp.renameTo(ziel)
        val alle = ordner(context).listFiles { d -> d.name.endsWith(".json") }.orEmpty().sortedByDescending { it.lastModified() }
        alle.drop(300).forEach { it.delete() }
        return JSONObject().put("id", id).put("updated_at", chat.optString("updated_at"))
    }

    fun loeschen(context: Context, id: String): Boolean = File(ordner(context), sicher(id) + ".json").delete()
}
