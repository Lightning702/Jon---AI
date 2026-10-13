package at.felworks.jon.uhr

import android.content.Context
import android.os.BatteryManager
import android.os.Build
import com.google.android.gms.tasks.Tasks
import com.google.android.gms.wearable.Node
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

object Jon {
    val bereich = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val http = OkHttpClient.Builder()
        .followRedirects(false)
        .connectTimeout(3, TimeUnit.SECONDS)
        .readTimeout(190, TimeUnit.SECONDS)
        .build()
    private val json = "application/json; charset=utf-8".toMediaType()

    suspend fun handys(context: Context): List<Node> = withContext(Dispatchers.IO) {
        runCatching { Tasks.await(Wearable.getNodeClient(context).connectedNodes, 6, TimeUnit.SECONDS) }
            .getOrDefault(emptyList())
            .sortedByDescending { it.isNearby }
    }

    suspend fun anHandy(context: Context, knoten: Node, pfad: String, daten: JSONObject, sekunden: Long): JSONObject = withContext(Dispatchers.IO) {
        val roh = Tasks.await(Wearable.getMessageClient(context).sendRequest(knoten.id, pfad, daten.toString().toByteArray(Charsets.UTF_8)), sekunden, TimeUnit.SECONDS)
        JSONObject(String(roh ?: ByteArray(0), Charsets.UTF_8).ifBlank { "{}" })
    }

    private suspend fun roh(context: Context, umschlag: JSONObject, adressen: List<String>, wartezeit: Long): JSONObject {
        var letzter: Exception? = null
        for (knoten in handys(context)) {
            try {
                val antwort = anHandy(context, knoten, "/jon/gate", JSONObject().put("umschlag", umschlag).put("warten", wartezeit), wartezeit / 1000 + 10)
                if (antwort.has("c")) return antwort
                letzter = IOException(antwort.optString("fehler", "Das Handy konnte Jon nicht erreichen."))
                if (antwort.optInt("code") == 403) throw letzter
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                letzter = e
                if (e is IOException && e.message?.contains("Code") == true) throw e
            }
        }
        for (basis in adressen.filter { it.isNotBlank() }.take(4)) {
            try {
                return withContext(Dispatchers.IO) {
                    val ruf = Request.Builder().url("${basis.trimEnd('/')}/api/handy/gate").post(umschlag.toString().toRequestBody(json)).build()
                    http.newBuilder().readTimeout(wartezeit, TimeUnit.MILLISECONDS).build().newCall(ruf).execute().use { antwort ->
                        val text = antwort.body.string()
                        if (!antwort.isSuccessful) throw IOException(runCatching { JSONObject(text).optString("detail") }.getOrNull()?.ifBlank { null } ?: "Fehler ${antwort.code}")
                        JSONObject(text)
                    }
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                letzter = e
            }
        }
        throw letzter ?: IOException("Kein Handy in der Nähe und Jon ist nicht direkt erreichbar.")
    }

    private suspend fun ruf(context: Context, anfrage: JSONObject, art: String, id: String, schluessel: ByteArray, adressen: List<String>, wartezeit: Long): JSONObject {
        val rid = Krypto.kennung(12)
        anfrage.put("rid", rid)
        val antwort = roh(context, Krypto.umschlag(anfrage, art, id, schluessel), adressen, wartezeit)
        val inhalt = Krypto.oeffnen(schluessel, art, id, antwort)
        check(inhalt.optString("rid") == rid) { "Die Antwort gehört nicht zu dieser Frage." }
        check(inhalt.optBoolean("ok")) { inhalt.optString("fehler", "Jon hat die Anfrage abgelehnt.") }
        return inhalt
    }

    suspend fun senden(context: Context, anfrage: JSONObject, wartezeit: Long = 60_000): JSONObject {
        val zugang = Tresor(context).zugang() ?: error("Die Uhr ist noch nicht mit Jon verbunden.")
        return ruf(context, anfrage, "dev", zugang.geraet, zugang.schluessel, zugang.adressen, wartezeit)
    }

    suspend fun api(context: Context, methode: String, pfad: String, rumpf: JSONObject? = null, wartezeit: Long = 190_000): JSONObject {
        val antwort = senden(context, JSONObject().put("op", "call").put("method", methode).put("path", pfad).put("body", rumpf ?: JSONObject.NULL), wartezeit)
        return JSONObject(antwort.optString("text", "{}").ifBlank { "{}" })
    }

    suspend fun fragen(context: Context, text: String, verlauf: List<Pair<String, String>>, gespraech: String): JSONObject {
        val liste = JSONArray()
        verlauf.takeLast(8).forEach { (rolle, inhalt) -> liste.put(JSONObject().put("role", rolle).put("content", inhalt)) }
        val antwort = api(context, "POST", "/api/oekosystem/frage", JSONObject().put("text", text).put("verlauf", liste).put("gespraech", gespraech).put("persona", "junior"))
        if (antwort.optString("antwort").isBlank()) error(antwort.optString("fehler").ifBlank { "Jon hat nichts geantwortet." })
        bereich.launch { runCatching { zustand(context) } }
        return antwort
    }

    fun akku(context: Context): Int = context.getSystemService(BatteryManager::class.java)?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) ?: -1

    fun laedt(context: Context): Boolean = context.getSystemService(BatteryManager::class.java)?.isCharging == true

    fun zustandDaten(context: Context): JSONObject = JSONObject()
        .put("name", "${Build.MANUFACTURER.replaceFirstChar { it.uppercase() }} ${Build.MODEL}")
        .put("akku", akku(context))
        .put("laedt", laedt(context))
        .put("modell", Build.MODEL)
        .put("android", "Wear OS · Android ${Build.VERSION.RELEASE}")
        .put("sdk", Build.VERSION.SDK_INT)
        .put("version", runCatching { context.packageManager.getPackageInfo(context.packageName, 0).versionName }.getOrNull().orEmpty())

    suspend fun zustand(context: Context): JSONObject {
        val zugang = Tresor(context).zugang()
        return senden(
            context,
            JSONObject().put("op", "zustand").put("zustand", zustandDaten(context))
                .put("faehigkeiten", JSONArray(listOf("status", "durchsage", "klingeln")))
                .put("typ", "uhr").put("besitzer", zugang?.besitzer.orEmpty()),
            20_000,
        )
    }

    suspend fun koppeln(context: Context, code: String, adressen: List<String>, besitzer: String): String {
        val sauber = Krypto.codeSaeubern(code)
        require(sauber.length == 12) { "Der Code braucht 12 Zeichen." }
        val schluessel = Krypto.codeSchluessel(sauber)
        val thema = Krypto.codeThema(sauber)
        val name = "${Build.MANUFACTURER.replaceFirstChar { it.uppercase() }} ${Build.MODEL}"
        suspend fun schritt(op: String): JSONObject = ruf(
            context,
            JSONObject().put("op", op).put("name", name).put("plattform", "Wear OS · Android ${Build.VERSION.RELEASE} · Jon Uhr").put("typ", "uhr").put("besitzer", besitzer),
            "pair", thema, schluessel, adressen, 15_000,
        )
        schritt("pair")
        repeat(80) {
            val stand = schritt("pair-status")
            if (stand.has("schluessel")) {
                val pc = stand.optJSONObject("pc") ?: JSONObject()
                val neue = stand.optJSONArray("adressen") ?: JSONArray()
                val alle = (adressen + (0 until neue.length()).map { neue.getString(it) }).filter { it.isNotBlank() && !it.contains("127.0.0.1") }.distinct()
                Tresor(context).speichern(Zugang(stand.getString("geraet"), Krypto.unb64(stand.getString("schluessel")), pc.optString("id"), pc.optString("name"), alle, besitzer))
                runCatching { zustand(context) }
                return pc.optString("name").ifBlank { "Jon" }
            }
            delay(1500)
        }
        error("Die Kopplung wurde nicht bestätigt.")
    }

    suspend fun ueberHandyKoppeln(context: Context): String {
        val knoten = handys(context).firstOrNull() ?: error("Kein Handy verbunden. Öffne Jon auf deinem Handy und versuch es nochmal.")
        val antwort = anHandy(context, knoten, "/jon/kopplung-anfrage", JSONObject(), 40)
        check(antwort.optBoolean("ok")) { antwort.optString("fehler", "Das Handy konnte keinen Code holen.") }
        val liste = antwort.optJSONArray("adressen") ?: JSONArray()
        return koppeln(context, antwort.getString("code"), (0 until liste.length()).map { liste.getString(it) }, antwort.optString("besitzer"))
    }

    suspend fun handyKlingeln(context: Context): String {
        for (knoten in handys(context)) {
            val ok = runCatching { anHandy(context, knoten, "/jon/klingeln", JSONObject().put("sekunden", 30), 12).optBoolean("ok") }.getOrDefault(false)
            if (ok) return "Dein Handy klingelt."
        }
        api(context, "POST", "/api/oekosystem/klingeln", JSONObject().put("sekunden", 30), 60_000)
        return "Dein Handy klingelt."
    }
}
