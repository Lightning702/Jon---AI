package at.felworks.jon.uhr

import android.os.Build
import com.google.android.gms.tasks.Task
import com.google.android.gms.tasks.TaskCompletionSource
import com.google.android.gms.wearable.WearableListenerService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

class UhrEmpfang : WearableListenerService() {
    override fun onRequest(nodeId: String, path: String, request: ByteArray): Task<ByteArray> {
        val quelle = TaskCompletionSource<ByteArray>()
        val kontext = applicationContext
        Jon.bereich.launch {
            val antwort = runCatching {
                val daten = runCatching { JSONObject(String(request, Charsets.UTF_8)) }.getOrDefault(JSONObject())
                when (path) {
                    "/jon/kopplung" -> {
                        val liste = daten.optJSONArray("adressen") ?: JSONArray()
                        val name = Jon.koppeln(kontext, daten.getString("code"), (0 until liste.length()).map { liste.getString(it) }, daten.optString("besitzer"))
                        Zustand.melden(kontext)
                        JSONObject().put("ok", true).put("jon", name).put("uhr", "${Build.MANUFACTURER.replaceFirstChar { it.uppercase() }} ${Build.MODEL}")
                    }
                    "/jon/auftrag" -> {
                        val ergebnis = withContext(Dispatchers.Main) { Aufgaben.ausfuehren(kontext, daten.optString("op"), daten.optJSONObject("daten") ?: JSONObject()) }
                        JSONObject().put("ok", true).put("daten", ergebnis)
                    }
                    "/jon/zustand" -> JSONObject().put("ok", true).put("daten", Jon.zustandDaten(kontext)).put("gekoppelt", Tresor(kontext).zugang() != null)
                    "/jon/entkoppeln" -> {
                        Tresor(kontext).loeschen()
                        Zustand.melden(kontext)
                        JSONObject().put("ok", true)
                    }
                    else -> error("Diese Anfrage kennt die Uhr nicht.")
                }
            }.getOrElse { JSONObject().put("ok", false).put("fehler", it.message ?: "Fehler auf der Uhr.") }
            quelle.setResult(antwort.toString().toByteArray(Charsets.UTF_8))
        }
        return quelle.task
    }
}

object Zustand {
    private val beobachter = mutableListOf<() -> Unit>()

    fun beobachten(aufruf: () -> Unit): () -> Unit {
        synchronized(beobachter) { beobachter += aufruf }
        return { synchronized(beobachter) { beobachter -= aufruf } }
    }

    fun melden(context: android.content.Context) {
        val liste = synchronized(beobachter) { beobachter.toList() }
        android.os.Handler(android.os.Looper.getMainLooper()).post { liste.forEach { it() } }
    }
}
