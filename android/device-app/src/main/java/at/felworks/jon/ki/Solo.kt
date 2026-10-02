package at.felworks.jon.ki

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.provider.MediaStore
import android.util.Base64
import at.felworks.jon.security.Tresor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import okhttp3.Call
import okhttp3.Headers
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

data class Anbieter(val id: String, val name: String, val basis: String, val bevorzugt: List<String>, val bildModell: String?, val seite: String, val sprache: String? = null)

private fun JSONObject.textOder(name: String): String = if (isNull(name)) "" else optString(name)

object Solo {
    val anbieter = listOf(
        Anbieter("openai", "OpenAI", "https://api.openai.com/v1", listOf("gpt-5.6-mini", "gpt-5.5-mini", "gpt-5.1-mini", "gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini"), "gpt-image-1", "platform.openai.com/api-keys", "gpt-4o-mini-transcribe"),
        Anbieter("anthropic", "Anthropic Claude", "https://api.anthropic.com/v1", listOf("claude-sonnet-5", "claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-5-5"), null, "console.anthropic.com/settings/keys"),
        Anbieter("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", listOf("gemini-3.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"), "imagen-4.0-generate-001", "aistudio.google.com/apikey"),
        Anbieter("nvidia", "NVIDIA", "https://integrate.api.nvidia.com/v1", listOf("meta/llama-4-maverick-17b-128e-instruct", "qwen/qwen3-235b-a22b", "mistralai/mistral-medium-3-instruct"), null, "build.nvidia.com"),
        Anbieter("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", listOf("openrouter/auto"), null, "openrouter.ai/keys"),
        Anbieter("groq", "Groq", "https://api.groq.com/openai/v1", listOf("llama-3.3-70b-versatile", "openai/gpt-oss-120b"), null, "console.groq.com/keys", "whisper-large-v3-turbo"),
        Anbieter("mistral", "Mistral", "https://api.mistral.ai/v1", listOf("mistral-medium-latest", "mistral-small-latest", "mistral-large-latest"), null, "console.mistral.ai/api-keys"),
        Anbieter("deepseek", "DeepSeek", "https://api.deepseek.com/v1", listOf("deepseek-chat", "deepseek-reasoner"), null, "platform.deepseek.com/api_keys"),
        Anbieter("xai", "xAI Grok", "https://api.x.ai/v1", listOf("grok-4", "grok-3-mini"), "grok-2-image", "console.x.ai"),
        Anbieter("eigener", "Eigener Server", "", emptyList(), null, ""),
    )
    private val json = "application/json; charset=utf-8".toMediaType()
    private val klient = OkHttpClient.Builder().connectTimeout(20, TimeUnit.SECONDS).readTimeout(240, TimeUnit.SECONDS).build()
    @Volatile private var laufend: Call? = null
    @Volatile private var abgebrochen = false

    private fun prefs(context: Context) = context.getSharedPreferences("jon-solo", Context.MODE_PRIVATE)

    fun an(context: Context): Boolean = prefs(context).getBoolean("an", false)

    fun gewaehlt(context: Context): String = prefs(context).getString("anbieter", "") ?: ""

    fun eintrag(id: String): Anbieter? = anbieter.firstOrNull { it.id == id }

    private fun basis(context: Context, a: Anbieter): String =
        (if (a.id == "eigener") prefs(context).getString("basis-eigener", "") ?: "" else a.basis).trimEnd('/')

    private fun schluessel(context: Context, id: String): String? = Tresor(context).geheimnisLesen("solo-$id")?.takeIf { it.isNotBlank() }

    fun bereit(context: Context): Boolean {
        val id = gewaehlt(context)
        if (id == "handy") return Katalog.standard(context) != null
        val a = eintrag(id) ?: return false
        return (a.id == "eigener" && basis(context, a).isNotBlank()) || schluessel(context, id) != null
    }

    fun modell(context: Context, id: String = gewaehlt(context)): String =
        prefs(context).getString("modell-$id", null)?.takeIf { it.isNotBlank() } ?: eintrag(id)?.bevorzugt?.firstOrNull().orEmpty()

    fun kannBilder(context: Context): Boolean = eintrag(gewaehlt(context))?.bildModell != null && schluessel(context, gewaehlt(context)) != null

    fun stand(context: Context): JSONObject {
        val liste = JSONArray()
        anbieter.forEach { a ->
            liste.put(JSONObject().put("id", a.id).put("name", a.name).put("seite", a.seite).put("verbunden", schluessel(context, a.id) != null || (a.id == "eigener" && basis(context, a).isNotBlank()))
                .put("modell", modell(context, a.id)).put("bilder", a.bildModell != null).put("basis", if (a.id == "eigener") basis(context, a) else a.basis))
        }
        return JSONObject().put("an", an(context)).put("anbieter", gewaehlt(context)).put("modell", modell(context))
            .put("bereit", bereit(context)).put("liste", liste).put("lokal", Katalog.standard(context) ?: JSONObject.NULL)
    }

    fun setzen(context: Context, daten: JSONObject): JSONObject {
        val e = prefs(context).edit()
        if (daten.has("anbieter")) {
            val id = daten.getString("anbieter")
            require(id == "handy" || eintrag(id) != null) { "Diesen Anbieter kennt Jon nicht." }
            e.putString("anbieter", id)
        }
        if (daten.has("modell")) e.putString("modell-${daten.optString("fuer", gewaehlt(context).ifBlank { daten.optString("anbieter") })}", daten.optString("modell").trim().take(120))
        if (daten.has("basis")) {
            val basis = daten.optString("basis").trim().trimEnd('/')
            require(basis.isEmpty() || basis.matches(Regex("https?://[^\\s]+"))) { "Die Adresse muss mit http:// oder https:// beginnen." }
            e.putString("basis-eigener", basis)
        }
        e.commit()
        if (daten.has("an")) {
            val soll = daten.optBoolean("an")
            if (soll) check(bereit(context)) { "Wähle zuerst einen Anbieter und hinterlege deinen API-Schlüssel." }
            prefs(context).edit().putBoolean("an", soll).commit()
        }
        return stand(context)
    }

    fun schluesselSetzen(context: Context, id: String, wert: String): JSONObject {
        require(eintrag(id) != null) { "Diesen Anbieter kennt Jon nicht." }
        val sauber = wert.trim()
        if (sauber.isEmpty()) Tresor(context).geheimnisLoeschen("solo-$id")
        else {
            require(sauber.length in 8..400 && !sauber.contains(Regex("\\s"))) { "Der Schlüssel sieht nicht richtig aus." }
            Tresor(context).geheimnisSpeichern("solo-$id", sauber)
        }
        return stand(context)
    }

    private fun kopf(context: Context, a: Anbieter): Headers {
        val b = Headers.Builder().add("Content-Type", "application/json")
        schluessel(context, a.id)?.let { b.add("Authorization", "Bearer $it") }
        if (a.id == "anthropic") schluessel(context, a.id)?.let { b.add("x-api-key", it).add("anthropic-version", "2023-06-01") }
        if (a.id == "openrouter") b.add("HTTP-Referer", "https://getjon.info").add("X-Title", "Jon")
        return b.build()
    }

    private fun fehlerText(code: Int, koerper: String): String {
        val meldung = runCatching { JSONObject(koerper).let { it.optJSONObject("error")?.optString("message") ?: it.optString("message") ?: it.optString("detail") } }.getOrNull()?.takeIf { it.isNotBlank() }
        return when (code) {
            401, 403 -> "Der API-Schlüssel wird abgelehnt. Prüfe ihn unter Einstellungen → Auf Jon verzichten."
            404 -> "Das Modell gibt es beim Anbieter nicht: ${meldung ?: "unbekannt"}"
            429 -> "Zu viele Anfragen oder kein Guthaben beim Anbieter. ${meldung.orEmpty()}".trim()
            else -> "Der Anbieter meldet Fehler $code: ${meldung ?: koerper.take(200)}"
        }
    }

    suspend fun modelle(context: Context, id: String): JSONArray = withContext(Dispatchers.IO) {
        val a = eintrag(id) ?: error("Unbekannter Anbieter.")
        val basis = basis(context, a)
        require(basis.isNotBlank()) { "Trage zuerst die Adresse deines Servers ein." }
        val ergebnis = runCatching {
            klient.newCall(Request.Builder().url("$basis/models").headers(kopf(context, a)).get().build()).execute().use { antwort ->
                val koerper = antwort.body.string()
                check(antwort.isSuccessful) { fehlerText(antwort.code, koerper) }
                val daten = JSONObject(koerper).optJSONArray("data") ?: JSONObject(koerper).optJSONArray("models") ?: JSONArray()
                (0 until daten.length()).mapNotNull { i -> daten.optJSONObject(i)?.let { it.textOder("id").ifBlank { it.textOder("name") }.removePrefix("models/") } }
                    .filter { m -> m.isNotBlank() && listOf("embed", "whisper", "tts", "dall-e", "moderation", "transcribe", "realtime", "audio", "search", "image", "imagen", "rerank", "guard").none { m.contains(it, true) } }
                    .distinct().sorted()
            }
        }
        val liste = ergebnis.getOrElse { fehler -> if (a.bevorzugt.isNotEmpty() && fehler !is IllegalStateException) a.bevorzugt else throw fehler }
        val sortiert = a.bevorzugt.filter { it in liste } + liste.filterNot { it in a.bevorzugt }
        if (prefs(context).getString("modell-$id", null).isNullOrBlank() && sortiert.isNotEmpty()) prefs(context).edit().putString("modell-$id", sortiert.first()).apply()
        JSONArray(sortiert)
    }

    fun stoppen() {
        abgebrochen = true
        runCatching { laufend?.cancel() }
    }

    private class Aufruf(var id: String = "", var name: String = "", val args: StringBuilder = StringBuilder())

    fun antworten(context: Context, system: String, verlauf: List<Pair<String, String>>, text: String, bilder: List<ByteArray>, arbeit: Boolean): Flow<JSONObject> = channelFlow {
        val id = gewaehlt(context)
        val a = eintrag(id) ?: error("Wähle unter Einstellungen → Auf Jon verzichten einen KI-Anbieter.")
        val basis = basis(context, a)
        check(basis.isNotBlank()) { "Für deinen eigenen Server fehlt die Adresse." }
        check(a.id == "eigener" || schluessel(context, a.id) != null) { "Für ${a.name} fehlt noch der API-Schlüssel." }
        val modell = modell(context, id).ifBlank { error("Wähle zuerst ein Modell für ${a.name}.") }
        send(JSONObject().put("type", "meta").put("provider", "solo-${a.id}").put("model", modell))
        abgebrochen = false
        val nachrichten = JSONArray().put(JSONObject().put("role", "system").put("content", system))
        verlauf.takeLast(40).forEach { (rolle, inhalt) -> nachrichten.put(JSONObject().put("role", if (rolle == "user") "user" else "assistant").put("content", inhalt.take(24_000))) }
        if (bilder.isNotEmpty()) {
            val inhalt = JSONArray().put(JSONObject().put("type", "text").put("text", text))
            bilder.take(8).forEach { inhalt.put(JSONObject().put("type", "image_url").put("image_url", JSONObject().put("url", "data:image/jpeg;base64," + Base64.encodeToString(it, Base64.NO_WRAP)))) }
            nachrichten.put(JSONObject().put("role", "user").put("content", inhalt))
        } else nachrichten.put(JSONObject().put("role", "user").put("content", text))
        val defs = Werkzeuge.liste(context, arbeit, kannBilder(context))
        val werkzeuge = Werkzeuge.openAi(defs)
        var runden = 0
        var ohneWerkzeuge = false
        while (!abgebrochen) {
            runden++
            val inhalt = StringBuilder()
            val aufrufe = sortedMapOf<Int, Aufruf>()
            val koerper = JSONObject().put("model", modell).put("messages", nachrichten).put("stream", true)
            if (!ohneWerkzeuge && werkzeuge.length() > 0 && runden <= 10) koerper.put("tools", werkzeuge).put("tool_choice", "auto")
            val call = klient.newCall(Request.Builder().url("$basis/chat/completions").headers(kopf(context, a)).header("Accept", "text/event-stream").post(koerper.toString().toRequestBody(json)).build())
            laufend = call
            val fehler = withContext(Dispatchers.IO) {
                runCatching {
                    call.execute().use { antwort ->
                        if (!antwort.isSuccessful) {
                            val roh = antwort.body.string()
                            if (antwort.code == 400 && !ohneWerkzeuge && roh.contains("tool", true)) return@use "ohne-werkzeuge"
                            error(fehlerText(antwort.code, roh))
                        }
                        val quelle = antwort.body.source()
                        while (!abgebrochen) {
                            val zeile = quelle.readUtf8Line() ?: break
                            if (!zeile.startsWith("data:")) continue
                            val daten = zeile.substring(5).trim()
                            if (daten == "[DONE]") break
                            val stueck = runCatching { JSONObject(daten) }.getOrNull() ?: continue
                            stueck.optJSONObject("error")?.let { error(it.optString("message", "Der Anbieter meldet einen Fehler.")) }
                            val delta = stueck.optJSONArray("choices")?.optJSONObject(0)?.optJSONObject("delta") ?: continue
                            val gedanke = delta.textOder("reasoning_content").ifEmpty { delta.textOder("reasoning") }
                            if (gedanke.isNotEmpty()) send(JSONObject().put("type", "reasoning").put("delta", gedanke))
                            val teil = delta.textOder("content")
                            if (teil.isNotEmpty()) {
                                inhalt.append(teil)
                                send(JSONObject().put("type", "content").put("delta", teil))
                            }
                            delta.optJSONArray("tool_calls")?.let { liste ->
                                for (i in 0 until liste.length()) {
                                    val tc = liste.optJSONObject(i) ?: continue
                                    val aufruf = aufrufe.getOrPut(tc.optInt("index", i)) { Aufruf() }
                                    tc.textOder("id").takeIf { it.isNotBlank() }?.let { aufruf.id = it }
                                    tc.optJSONObject("function")?.let { f ->
                                        f.textOder("name").takeIf { it.isNotBlank() }?.let { aufruf.name = it }
                                        aufruf.args.append(f.textOder("arguments"))
                                    }
                                }
                            }
                        }
                        ""
                    }
                }
            }
            laufend = null
            if (abgebrochen) break
            val ergebnis = fehler.getOrElse { throw IllegalStateException(if (it is java.io.IOException && abgebrochen) "Abgebrochen" else it.message ?: "Verbindung zum Anbieter unterbrochen.") }
            if (ergebnis == "ohne-werkzeuge") {
                ohneWerkzeuge = true
                continue
            }
            val gueltig = aufrufe.values.filter { it.name.isNotBlank() }
            if (gueltig.isEmpty()) break
            val rufe = JSONArray()
            gueltig.forEachIndexed { i, aufruf ->
                if (aufruf.id.isBlank()) aufruf.id = "call_${runden}_$i"
                rufe.put(JSONObject().put("id", aufruf.id).put("type", "function").put("function", JSONObject().put("name", aufruf.name).put("arguments", aufruf.args.toString().ifBlank { "{}" })))
            }
            nachrichten.put(JSONObject().put("role", "assistant").put("content", if (inhalt.isEmpty()) JSONObject.NULL else inhalt.toString()).put("tool_calls", rufe))
            for (aufruf in gueltig) {
                val args = runCatching { JSONObject(aufruf.args.toString().ifBlank { "{}" }) }.getOrDefault(JSONObject())
                val def = defs.firstOrNull { it.name == aufruf.name }
                send(if (def != null) Werkzeuge.laeuft(def, args) else JSONObject().put("type", "tool").put("name", aufruf.name).put("status", "running").put("summary", aufruf.name))
                val ergebnisWerkzeug = if (def == null) JSONObject().put("fehler", "Dieses Werkzeug gibt es nicht.") else Werkzeuge.ausfuehren(context, aufruf.name, args)
                send(Werkzeuge.fertig(aufruf.name, ergebnisWerkzeug))
                val fuerModell = JSONObject(ergebnisWerkzeug.toString()).apply { remove("karte") }.toString()
                nachrichten.put(JSONObject().put("role", "tool").put("tool_call_id", aufruf.id).put("name", aufruf.name).put("content", fuerModell.take(14_000)))
            }
            if (runden > 12) {
                send(JSONObject().put("type", "content").put("delta", "\n\nIch habe sehr viele Schritte gebraucht und höre hier auf."))
                break
            }
        }
    }.flowOn(Dispatchers.IO)

    suspend fun bildErstellen(context: Context, beschreibung: String): JSONObject = withContext(Dispatchers.IO) {
        require(beschreibung.isNotBlank()) { "Was soll auf dem Bild sein?" }
        val a = eintrag(gewaehlt(context))?.takeIf { it.bildModell != null } ?: error("Bilder kann Jon ohne PC nur mit OpenAI, Gemini oder xAI erstellen.")
        val koerper = JSONObject().put("model", a.bildModell).put("prompt", beschreibung.take(3800)).put("n", 1)
        if (a.id == "openai") koerper.put("size", "1024x1024")
        if (a.id != "openai") koerper.put("response_format", "b64_json")
        val daten = klient.newCall(Request.Builder().url("${basis(context, a)}/images/generations").headers(kopf(context, a)).post(koerper.toString().toRequestBody(json)).build()).execute().use { antwort ->
            val roh = antwort.body.string()
            check(antwort.isSuccessful) { fehlerText(antwort.code, roh) }
            val erstes = JSONObject(roh).optJSONArray("data")?.optJSONObject(0) ?: error("Der Anbieter hat kein Bild geliefert.")
            val b64 = erstes.textOder("b64_json")
            if (b64.isNotBlank()) Base64.decode(b64, Base64.DEFAULT)
            else klient.newCall(Request.Builder().url(erstes.getString("url")).build()).execute().use { it.body.bytes() }
        }
        val name = "bild-${System.currentTimeMillis()}.png"
        val datei = Arbeitsraum.datei(context, "bilder/$name")
        datei.parentFile?.mkdirs()
        datei.writeBytes(daten)
        if (Build.VERSION.SDK_INT >= 29) runCatching {
            val werte = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, "Jon-$name")
                put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/Jon")
            }
            context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, werte)?.let { uri -> context.contentResolver.openOutputStream(uri)?.use { it.write(daten) } }
        }
        JSONObject().put("ok", true).put("pfad", "bilder/$name")
            .put("karte", JSONObject().put("kind", "handy-bild").put("data", JSONObject().put("pfad", "bilder/$name").put("prompt", beschreibung.take(300))))
    }

    suspend fun transkribieren(context: Context, wav: ByteArray): String? = withContext(Dispatchers.IO) {
        val a = eintrag(gewaehlt(context)) ?: return@withContext null
        val modell = a.sprache ?: return@withContext null
        if (schluessel(context, a.id) == null) return@withContext null
        runCatching {
            val koerper = MultipartBody.Builder().setType(MultipartBody.FORM)
                .addFormDataPart("model", modell).addFormDataPart("language", at.felworks.jon.device.Sprache.code(context))
                .addFormDataPart("file", "sprache.wav", wav.toRequestBody("audio/wav".toMediaType())).build()
            klient.newCall(Request.Builder().url("${basis(context, a)}/audio/transcriptions").headers(kopf(context, a).newBuilder().removeAll("Content-Type").build()).post(koerper).build()).execute().use { antwort ->
                if (!antwort.isSuccessful) null else JSONObject(antwort.body.string()).optString("text").trim().ifBlank { null }
            }
        }.getOrNull()
    }

    suspend fun sprechen(context: Context, text: String): File? = withContext(Dispatchers.IO) {
        val a = eintrag(gewaehlt(context))?.takeIf { it.id == "openai" } ?: return@withContext null
        if (schluessel(context, a.id) == null) return@withContext null
        runCatching {
            val koerper = JSONObject().put("model", "gpt-4o-mini-tts").put("voice", "alloy").put("input", text.take(3000)).put("response_format", "mp3")
            klient.newCall(Request.Builder().url("${basis(context, a)}/audio/speech").headers(kopf(context, a)).post(koerper.toString().toRequestBody(json)).build()).execute().use { antwort ->
                if (!antwort.isSuccessful) null else File.createTempFile("jon-stimme", ".mp3", context.cacheDir).apply { writeBytes(antwort.body.bytes()) }
            }
        }.getOrNull()
    }
}
