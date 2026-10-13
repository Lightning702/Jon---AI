package at.felworks.jon.uhrbruecke

import android.content.Context
import at.felworks.jon.JonApplication
import at.felworks.jon.core.AppBehaelter
import at.felworks.jon.device.KlingelDienst
import com.google.android.gms.tasks.Task
import com.google.android.gms.tasks.TaskCompletionSource
import com.google.android.gms.tasks.Tasks
import com.google.android.gms.wearable.Node
import com.google.android.gms.wearable.Wearable
import com.google.android.gms.wearable.WearableListenerService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object Uhrbruecke {
    val bereich = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    suspend fun uhren(context: Context): List<Node> = withContext(Dispatchers.IO) {
        runCatching { Tasks.await(Wearable.getNodeClient(context).connectedNodes, 6, TimeUnit.SECONDS) }.getOrDefault(emptyList())
    }

    private suspend fun anfrage(context: Context, knoten: Node, pfad: String, daten: JSONObject, sekunden: Long): JSONObject = withContext(Dispatchers.IO) {
        val roh = Tasks.await(Wearable.getMessageClient(context).sendRequest(knoten.id, pfad, daten.toString().toByteArray(Charsets.UTF_8)), sekunden, TimeUnit.SECONDS)
        JSONObject(String(roh ?: ByteArray(0), Charsets.UTF_8).ifBlank { "{}" })
    }

    suspend fun stand(context: Context): JSONObject {
        val liste = JSONArray()
        for (knoten in uhren(context)) {
            val antwort = runCatching { anfrage(context, knoten, "/jon/zustand", JSONObject(), 8) }.getOrNull()
            liste.put(
                JSONObject().put("id", knoten.id).put("name", knoten.displayName).put("nah", knoten.isNearby)
                    .put("app", antwort != null).put("gekoppelt", antwort?.optBoolean("gekoppelt") == true)
                    .put("akku", antwort?.optJSONObject("daten")?.optInt("akku", -1) ?: -1),
            )
        }
        return JSONObject().put("uhren", liste)
    }

    suspend fun kopplungsdaten(behaelter: AppBehaelter): JSONObject {
        val daten = behaelter.verbindung.objekt("POST", "/api/oekosystem/uhr-koppeln", JSONObject())
        check(daten.optBoolean("ok")) { daten.optString("detail").ifBlank { "Jon hat keinen Kopplungscode für die Uhr erzeugt." } }
        val adressen = JSONArray()
        behaelter.verbindung.aktuell?.alleAdressen?.forEach { adressen.put(it) }
        val neue = daten.optJSONArray("adressen") ?: JSONArray()
        for (i in 0 until neue.length()) adressen.put(neue.getString(i))
        return JSONObject().put("ok", true).put("code", daten.getString("code")).put("adressen", adressen)
            .put("besitzer", daten.optString("besitzer")).put("pc", daten.optJSONObject("pc") ?: JSONObject())
    }

    suspend fun koppeln(context: Context, behaelter: AppBehaelter): JSONObject {
        val ziele = uhren(context)
        check(ziele.isNotEmpty()) { "Keine Uhr verbunden. Ist die Uhr mit diesem Handy gekoppelt und Jon auf der Uhr installiert?" }
        var fehler = "Die Uhr hat nicht geantwortet. Ist Jon auf der Uhr installiert?"
        for (knoten in ziele.sortedByDescending { it.isNearby }) {
            val antwort = runCatching { anfrage(context, knoten, "/jon/kopplung", kopplungsdaten(behaelter), 90) }
                .getOrElse { fehler = it.message ?: fehler; null } ?: continue
            if (antwort.optBoolean("ok")) return JSONObject().put("uhr", antwort.optString("uhr").ifBlank { knoten.displayName }).put("jon", antwort.optString("jon"))
            fehler = antwort.optString("fehler", fehler)
        }
        error(fehler)
    }

    suspend fun anUhr(context: Context, op: String, daten: JSONObject): JSONObject {
        val ziele = uhren(context)
        check(ziele.isNotEmpty()) { "Die Uhr ist gerade nicht mit dem Handy verbunden." }
        var fehler = "Die Uhr hat nicht reagiert."
        for (knoten in ziele.sortedByDescending { it.isNearby }) {
            val antwort = runCatching { anfrage(context, knoten, "/jon/auftrag", JSONObject().put("op", op).put("daten", daten), 25) }
                .getOrElse { fehler = it.message ?: fehler; null } ?: continue
            if (antwort.optBoolean("ok")) return antwort.optJSONObject("daten") ?: JSONObject()
            fehler = antwort.optString("fehler", fehler)
        }
        error(fehler)
    }
}

class UhrDienst : WearableListenerService() {
    override fun onRequest(nodeId: String, path: String, request: ByteArray): Task<ByteArray> {
        val quelle = TaskCompletionSource<ByteArray>()
        val kontext = applicationContext
        val behaelter = (application as JonApplication).behaelter
        Uhrbruecke.bereich.launch {
            val antwort = runCatching {
                val daten = runCatching { JSONObject(String(request, Charsets.UTF_8)) }.getOrDefault(JSONObject())
                when (path) {
                    "/jon/gate" -> {
                        val umschlag = daten.optJSONObject("umschlag") ?: error("Leere Anfrage von der Uhr.")
                        check(behaelter.gekoppelt.value) { "Das Handy ist nicht mit Jon verbunden." }
                        JSONObject(behaelter.verbindung.weiterleiten(umschlag, daten.optLong("warten", 120_000).coerceIn(5_000, 200_000)))
                    }
                    "/jon/kopplung-anfrage" -> {
                        check(behaelter.gekoppelt.value) { "Das Handy ist noch nicht mit Jon verbunden." }
                        Uhrbruecke.kopplungsdaten(behaelter)
                    }
                    "/jon/klingeln" -> {
                        withContext(Dispatchers.Main) { KlingelDienst.starten(kontext, "suchen", "Deine Uhr sucht dich", daten.optInt("sekunden", 30).coerceIn(5, 120)) }
                        JSONObject().put("ok", true)
                    }
                    else -> error("Diese Anfrage kennt das Handy nicht.")
                }
            }.getOrElse { JSONObject().put("ok", false).put("fehler", it.message ?: "Fehler auf dem Handy.") }
            quelle.setResult(antwort.toString().toByteArray(Charsets.UTF_8))
        }
        return quelle.task
    }
}
