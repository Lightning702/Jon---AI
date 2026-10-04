package at.felworks.jon.data.repository

import android.content.Context
import at.felworks.jon.data.remote.JonVerbindung
import at.felworks.jon.domain.model.ChatNachricht
import at.felworks.jon.domain.model.Rolle
import at.felworks.jon.domain.repository.ChatStueck
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.catch
import org.json.JSONArray
import org.json.JSONObject

class GeraeteChat(context: Context, private val verbindung: JonVerbindung) {
    private val app = context.applicationContext
    private val prefs = context.getSharedPreferences("jon-chat", Context.MODE_PRIVATE)
    private val nachrichten = MutableStateFlow(runCatching {
        val liste = JSONArray(prefs.getString("verlauf", "[]"))
        (0 until liste.length()).map { n -> liste.getJSONObject(n).let { ChatNachricht(it.getString("id"), Rolle.valueOf(it.getString("rolle")), it.getString("text"), it.getLong("zeit")) } }
    }.getOrDefault(emptyList()))

    private val kontextPrefs = context.getSharedPreferences("jon-kontext", Context.MODE_PRIVATE)
    private val _aenderung = MutableStateFlow(0)
    val aenderung: StateFlow<Int> = _aenderung
    var aktuell = kontextPrefs.getString("id", "").orEmpty()
        private set

    fun kontext(id: String, provider: String, model: String, mode: String, workspace: String) {
        if (aktuell != id) nachrichten.value = emptyList()
        aktuell = id
        kontextPrefs.edit().putString("id", id).putString("provider", provider).putString("model", model).putString("mode", mode).putString("workspace", workspace).apply()
    }

    suspend fun historie(): List<ChatNachricht> {
        if (aktuell.isBlank()) return emptyList()
        val array = verbindung.objekt("GET", "/api/conversations/$aktuell").optJSONArray("messages") ?: JSONArray()
        return (0 until array.length()).map { array.getJSONObject(it).let { m -> ChatNachricht(m.optString("id"), if (m.optString("role") == "user") Rolle.NUTZER else Rolle.JON, m.optString("content"), 0L) } }
    }

    fun verlauf(unterhaltung: String): StateFlow<List<ChatNachricht>> = nachrichten

    @Synchronized fun merken(unterhaltung: String, nachricht: ChatNachricht) {
        nachrichten.value = (nachrichten.value.filterNot { it.id == nachricht.id } + nachricht).takeLast(100)
        val liste = JSONArray()
        nachrichten.value.forEach { liste.put(JSONObject().put("id", it.id).put("rolle", it.rolle.name).put("text", it.text).put("zeit", it.zeit)) }
        prefs.edit().putString("verlauf", liste.toString()).apply()
        _aenderung.value++
    }

    fun leeren() { nachrichten.value = emptyList(); prefs.edit().remove("verlauf").apply() }

    fun zuruecksetzen() {
        aktuell = ""
        kontextPrefs.edit().clear().apply()
        leeren()
        _aenderung.value++
    }

    suspend fun freigeben(id: String, erlaubt: Boolean) {
        verbindung.objekt("POST", "/api/chat/approve", JSONObject().put("id", id).put("approved", erlaubt))
    }

    fun fragen(unterhaltung: String, verlauf: List<ChatNachricht>) = flow<ChatStueck> {
        val messages = JSONArray()
        verlauf.filter { it.rolle != Rolle.SYSTEM }.takeLast(24).forEach {
            messages.put(JSONObject().put("role", if (it.rolle == Rolle.NUTZER) "user" else "assistant").put("content", it.text))
        }
        val body = JSONObject().put("messages", messages).put("persist", true).put("source", "handy").put("tool_mode", "ask")
        if (aktuell.isNotBlank()) body.put("conversation_id", aktuell)
        for (key in listOf("provider", "model", "mode", "workspace")) kontextPrefs.getString(key, "").orEmpty().takeIf { it.isNotBlank() }?.let { body.put(key, it) }
        verbindung.strom("/api/chat", at.felworks.jon.device.KinderModus.anfrage(app, body)).collect { e ->
            when (e.optString("type")) {
                "meta" -> {
                    e.optString("conversation_id").takeIf { it.isNotBlank() }?.let { aktuell = it; kontextPrefs.edit().putString("id", it).apply() }
                }
                "content" -> emit(ChatStueck.Text(e.optString("delta")))
                "error" -> emit(ChatStueck.Fehler(e.optString("message")))
                "tool" -> emit(ChatStueck.Werkzeug(e.optString("summary", "Jon arbeitet …"), e.optString("approval_id").ifEmpty { null }))
                "done" -> emit(ChatStueck.Ende)
            }
        }
    }.catch { e -> if (e is CancellationException) throw e else emit(ChatStueck.Fehler(e.message ?: "Pi nicht erreichbar.")) }
}
