package at.felworks.jon.ki

import android.app.ActivityManager
import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.StatFs
import at.felworks.jon.security.Tresor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

data class KiModell(
    val name: String,
    val titel: String,
    val beschreibung: String,
    val modelId: String,
    val datei: String,
    val commit: String,
    val groesse: Long,
    val ram: Int,
    val bild: Boolean,
    val audio: Boolean,
    val werkzeuge: Boolean,
    val geschuetzt: Boolean,
    val topK: Int,
    val topP: Double,
    val temperatur: Double,
    val maxTokens: Int,
    val gpu: Boolean,
) {
    val adresse: String get() = "https://huggingface.co/$modelId/resolve/$commit/$datei?download=true"

    companion object {
        fun lesen(json: JSONObject): KiModell? = runCatching {
            KiModell(
                name = json.getString("name"),
                titel = json.optString("titel").ifBlank { json.getString("name") },
                beschreibung = json.optString("beschreibung"),
                modelId = json.getString("modelId"),
                datei = json.getString("datei").also { require(it.matches(Regex("[A-Za-z0-9._-]+\\.litertlm"))) },
                commit = json.getString("commit").also { require(it.matches(Regex("[A-Za-z0-9._-]+"))) },
                groesse = json.getLong("groesse"),
                ram = json.optInt("ram", 6),
                bild = json.optBoolean("bild"),
                audio = json.optBoolean("audio"),
                werkzeuge = json.optBoolean("werkzeuge"),
                geschuetzt = json.optBoolean("geschuetzt"),
                topK = json.optInt("topK", 40).coerceAtLeast(1),
                topP = json.optDouble("topP", 0.95).coerceIn(0.0, 1.0),
                temperatur = json.optDouble("temperatur", 0.8).coerceAtLeast(0.0),
                maxTokens = json.optInt("maxTokens", 2048).coerceIn(256, 32_000),
                gpu = json.optBoolean("gpu", true),
            )
        }.getOrNull()
    }
}

object Katalog {
    private val klient = OkHttpClient.Builder().followRedirects(false).connectTimeout(15, TimeUnit.SECONDS).readTimeout(30, TimeUnit.SECONDS).build()
    private val netz = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(30, TimeUnit.SECONDS).build()

    private fun prefs(context: Context) = context.getSharedPreferences("jon-ki", Context.MODE_PRIVATE)

    private fun lesenAus(text: String): List<KiModell> {
        val liste = JSONObject(text).optJSONArray("modelle") ?: JSONArray()
        return (0 until liste.length()).mapNotNull { KiModell.lesen(liste.getJSONObject(it)) }
    }

    fun modelle(context: Context): List<KiModell> {
        val eigene = File(context.filesDir, "ki-modelle.json")
        if (eigene.isFile) runCatching { lesenAus(eigene.readText()) }.getOrNull()?.takeIf { it.isNotEmpty() }?.let { return it }
        return context.assets.open("ki-modelle.json").bufferedReader().use { lesenAus(it.readText()) }
    }

    fun modell(context: Context, name: String): KiModell? = modelle(context).firstOrNull { it.name == name }

    fun ordner(context: Context): File = (context.getExternalFilesDir("modelle") ?: File(context.filesDir, "modelle")).apply { mkdirs() }

    fun datei(context: Context, m: KiModell): File = File(ordner(context), m.datei)

    fun vorhanden(context: Context, m: KiModell): Boolean {
        val datei = datei(context, m)
        return datei.isFile && datei.length() >= m.groesse * 99 / 100
    }

    fun installierte(context: Context): List<KiModell> = modelle(context).filter { vorhanden(context, it) }

    fun arbeitsspeicherGb(context: Context): Double {
        val info = ActivityManager.MemoryInfo()
        context.getSystemService(ActivityManager::class.java).getMemoryInfo(info)
        return info.totalMem / 1_073_741_824.0
    }

    fun passt(context: Context, m: KiModell): String {
        val ram = arbeitsspeicherGb(context)
        return when {
            ram >= m.ram * 0.88 -> "passt"
            ram >= m.ram * 0.7 -> "knapp"
            else -> "zu-gross"
        }
    }

    fun tokenVorhanden(context: Context): Boolean = Tresor(context).geheimnisVorhanden("huggingface")

    fun tokenSetzen(context: Context, token: String) {
        val sauber = token.trim()
        if (sauber.isEmpty()) Tresor(context).geheimnisLoeschen("huggingface")
        else {
            require(sauber.matches(Regex("hf_[A-Za-z0-9]{20,}"))) { "Ein Hugging-Face-Schlüssel beginnt mit hf_." }
            Tresor(context).geheimnisSpeichern("huggingface", sauber)
        }
    }

    private fun dm(context: Context) = context.getSystemService(DownloadManager::class.java)

    private fun ladeZustand(context: Context, m: KiModell): JSONObject? {
        val id = prefs(context).getLong("download-${m.name}", -1L)
        if (id < 0) return null
        dm(context).query(DownloadManager.Query().setFilterById(id))?.use { zeiger ->
            if (!zeiger.moveToFirst()) return null
            val status = zeiger.getInt(zeiger.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS))
            val geladen = zeiger.getLong(zeiger.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR))
            val gesamt = zeiger.getLong(zeiger.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES)).takeIf { it > 0 } ?: m.groesse
            val grund = zeiger.getInt(zeiger.getColumnIndexOrThrow(DownloadManager.COLUMN_REASON))
            val text = when (status) {
                DownloadManager.STATUS_SUCCESSFUL -> "fertig"
                DownloadManager.STATUS_FAILED -> "fehler"
                DownloadManager.STATUS_PAUSED -> "pausiert"
                else -> "laedt"
            }
            return JSONObject().put("status", text).put("geladen", geladen).put("gesamt", gesamt).put("grund", grund)
        }
        return null
    }

    private fun abschliessen(context: Context, m: KiModell) {
        val teil = File(ordner(context), m.datei + ".teil")
        val ziel = datei(context, m)
        if (teil.isFile && teil.length() >= m.groesse * 99 / 100) {
            ziel.delete()
            teil.renameTo(ziel)
        }
        prefs(context).edit().remove("download-${m.name}").apply()
        if (sparsam(context) && vorhanden(context, m)) {
            prefs(context).edit().putString("standard", m.name).apply()
            andereLoeschen(context, m.name)
        }
    }

    fun sparsam(context: Context): Boolean = prefs(context).getBoolean("sparsam", true)

    fun sparsamSetzen(context: Context, an: Boolean): JSONObject {
        prefs(context).edit().putBoolean("sparsam", an).apply()
        if (an) aufraeumen(context)
        return stand(context)
    }

    fun belegt(context: Context): Long = ordner(context).listFiles()?.filter { it.isFile }?.sumOf { it.length() } ?: 0L

    private fun andereLoeschen(context: Context, behalten: String?) {
        for (anderes in installierte(context)) {
            if (anderes.name == behalten) continue
            if (LokaleKi.geladen == anderes.name) LokaleKi.entladen()
            datei(context, anderes).delete()
        }
    }

    fun aufraeumen(context: Context): JSONObject {
        andereLoeschen(context, standard(context))
        return stand(context)
    }

    fun einmalAufraeumen(context: Context) {
        val p = prefs(context)
        if (p.getBoolean("aufgeraeumt", false)) return
        p.edit().putBoolean("aufgeraeumt", true).apply()
        if (sparsam(context) && installierte(context).size > 1) runCatching { andereLoeschen(context, standard(context)) }
    }

    fun stand(context: Context): JSONObject {
        val ram = arbeitsspeicherGb(context)
        val frei = runCatching { StatFs(ordner(context).absolutePath).availableBytes }.getOrDefault(0L)
        val liste = JSONArray()
        for (m in modelle(context)) {
            var zustand = ladeZustand(context, m)
            if (zustand?.optString("status") == "fertig") {
                abschliessen(context, m)
                zustand = null
            }
            val status = when {
                vorhanden(context, m) -> "fertig"
                zustand != null -> zustand.optString("status")
                else -> "fehlt"
            }
            liste.put(
                JSONObject().put("name", m.name).put("titel", m.titel).put("beschreibung", m.beschreibung)
                    .put("groesse", m.groesse).put("ram", m.ram).put("passt", passt(context, m))
                    .put("bild", m.bild).put("audio", m.audio).put("werkzeuge", m.werkzeuge).put("geschuetzt", m.geschuetzt)
                    .put("status", status)
                    .put("geladen", zustand?.optLong("geladen") ?: if (status == "fertig") m.groesse else 0L)
                    .put("gesamt", zustand?.optLong("gesamt") ?: m.groesse)
                    .put("fehler", if (zustand?.optString("status") == "fehler") fehlertext(zustand.optInt("grund")) else "")
            )
        }
        return JSONObject().put("modelle", liste).put("ram", Math.round(ram * 10) / 10.0).put("frei", frei)
            .put("belegt", belegt(context)).put("sparsam", sparsam(context))
            .put("token", tokenVorhanden(context)).put("standard", standard(context) ?: JSONObject.NULL)
            .put("mobil", prefs(context).getBoolean("mobil", false))
            .put("ki", LokaleKi.zustand.value)
    }

    private fun fehlertext(grund: Int): String = when (grund) {
        DownloadManager.ERROR_INSUFFICIENT_SPACE -> "Zu wenig Speicher frei."
        DownloadManager.ERROR_HTTP_DATA_ERROR, DownloadManager.ERROR_CANNOT_RESUME -> "Die Verbindung ist abgebrochen. Bitte neu starten."
        401, 403 -> "Kein Zugriff. Akzeptiere die Lizenz auf huggingface.co und prüfe deinen Schlüssel."
        404 -> "Das Modell gibt es unter dieser Adresse nicht mehr. Aktualisiere die Liste."
        else -> "Download fehlgeschlagen ($grund)."
    }

    fun standard(context: Context): String? = prefs(context).getString("standard", null)?.takeIf { name -> modell(context, name)?.let { vorhanden(context, it) } == true }
        ?: installierte(context).firstOrNull()?.name

    fun standardSetzen(context: Context, name: String) {
        val m = modell(context, name) ?: error("Unbekanntes Modell.")
        check(vorhanden(context, m)) { "${m.titel} ist noch nicht heruntergeladen." }
        prefs(context).edit().putString("standard", name).apply()
    }

    fun mobilSetzen(context: Context, an: Boolean) {
        prefs(context).edit().putBoolean("mobil", an).apply()
    }

    private suspend fun signierteAdresse(context: Context, m: KiModell): String = withContext(Dispatchers.IO) {
        val token = Tresor(context).geheimnisLesen("huggingface") ?: error("Für ${m.titel} brauchst du einen kostenlosen Hugging-Face-Schlüssel (Einstellungen → Offline-KI).")
        var adresse = m.adresse
        repeat(4) {
            val antwort = klient.newCall(Request.Builder().url(adresse).head().header("Authorization", "Bearer $token").build()).execute()
            antwort.use {
                when {
                    it.code in 300..399 -> {
                        val ziel = it.header("Location") ?: error("Hugging Face hat keine Download-Adresse geliefert.")
                        val neu = it.request.url.resolve(ziel)?.toString() ?: ziel
                        if (!neu.contains("huggingface.co")) return@withContext neu
                        adresse = neu
                    }
                    it.code == 401 || it.code == 403 -> error("Kein Zugriff auf ${m.titel}. Öffne huggingface.co/${m.modelId}, akzeptiere die Lizenz und prüfe deinen Schlüssel.")
                    it.isSuccessful -> return@withContext adresse
                    else -> error("Hugging Face antwortet mit Fehler ${it.code}.")
                }
            }
        }
        adresse
    }

    suspend fun herunterladen(context: Context, name: String): JSONObject {
        val m = modell(context, name) ?: error("Unbekanntes Modell.")
        if (vorhanden(context, m)) return stand(context)
        ladeZustand(context, m)?.let { if (it.optString("status") in setOf("laedt", "pausiert")) return stand(context) }
        val frei = StatFs(ordner(context).absolutePath).availableBytes
        check(frei > m.groesse + 300_000_000L) { "Für ${m.titel} brauchst du ${m.groesse / 1_000_000_000.0} GB freien Speicher." }
        val adresse = if (m.geschuetzt) signierteAdresse(context, m) else m.adresse
        File(ordner(context), m.datei + ".teil").delete()
        val anfrage = DownloadManager.Request(Uri.parse(adresse))
            .setTitle("Jon · ${m.titel}")
            .setDescription("KI-Modell für Jon offline")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE)
            .setDestinationInExternalFilesDir(context, "modelle", m.datei + ".teil")
            .setAllowedOverMetered(prefs(context).getBoolean("mobil", false))
            .setAllowedOverRoaming(false)
        val id = dm(context).enqueue(anfrage)
        prefs(context).edit().putLong("download-${m.name}", id).apply()
        return stand(context)
    }

    fun abbrechen(context: Context, name: String): JSONObject {
        val m = modell(context, name) ?: error("Unbekanntes Modell.")
        val id = prefs(context).getLong("download-${m.name}", -1L)
        if (id >= 0) dm(context).remove(id)
        prefs(context).edit().remove("download-${m.name}").apply()
        File(ordner(context), m.datei + ".teil").delete()
        return stand(context)
    }

    fun loeschen(context: Context, name: String): JSONObject {
        val m = modell(context, name) ?: error("Unbekanntes Modell.")
        if (LokaleKi.geladen == m.name) LokaleKi.entladen()
        abbrechen(context, name)
        datei(context, m).delete()
        return stand(context)
    }

    suspend fun aktualisieren(context: Context): JSONObject = withContext(Dispatchers.IO) {
        val verzeichnis = netz.newCall(Request.Builder().url("https://api.github.com/repos/google-ai-edge/gallery/contents/model_allowlists").header("Accept", "application/vnd.github+json").build()).execute().use {
            check(it.isSuccessful) { "Die Modellliste ist gerade nicht erreichbar." }
            JSONArray(it.body.string())
        }
        val neueste = (0 until verzeichnis.length()).map { verzeichnis.getJSONObject(it).optString("name") }
            .mapNotNull { name -> Regex("^(\\d+)_(\\d+)_(\\d+)\\.json$").matchEntire(name)?.let { m -> Triple(m.groupValues[1].toInt(), m.groupValues[2].toInt(), m.groupValues[3].toInt()) to name } }
            .maxWithOrNull(compareBy({ it.first.first }, { it.first.second }, { it.first.third }))?.second ?: error("Keine Modellliste gefunden.")
        val roh = netz.newCall(Request.Builder().url("https://raw.githubusercontent.com/google-ai-edge/gallery/main/model_allowlists/$neueste").build()).execute().use {
            check(it.isSuccessful) { "Die Modellliste ist gerade nicht erreichbar." }
            JSONObject(it.body.string())
        }
        val bekannt = modelle(context).associateBy { it.name }
        val neu = JSONArray()
        val liste = roh.optJSONArray("models") ?: JSONArray()
        for (i in 0 until liste.length()) {
            val m = liste.getJSONObject(i)
            val datei = m.optString("modelFile")
            val aufgaben = m.optJSONArray("taskTypes")?.let { a -> (0 until a.length()).map { a.optString(it) } }.orEmpty()
            if (!datei.endsWith(".litertlm") || "llm_chat" !in aufgaben) continue
            val alt = bekannt[m.optString("name")]
            val cfg = m.optJSONObject("defaultConfig") ?: JSONObject()
            neu.put(
                JSONObject().put("name", m.optString("name")).put("titel", alt?.titel ?: m.optString("name").replace('-', ' '))
                    .put("beschreibung", alt?.beschreibung ?: "Neues Modell aus der Google AI Edge Gallery.")
                    .put("modelId", m.optString("modelId")).put("datei", datei).put("commit", m.optString("commitHash"))
                    .put("groesse", m.optLong("sizeInBytes")).put("ram", m.optInt("minDeviceMemoryInGb", 6))
                    .put("bild", m.optBoolean("llmSupportImage")).put("audio", m.optBoolean("llmSupportAudio"))
                    .put("werkzeuge", "llm_agent_chat" in aufgaben).put("geschuetzt", alt?.geschuetzt ?: m.optString("modelId").startsWith("google/"))
                    .put("topK", cfg.optInt("topK", 40)).put("topP", cfg.optDouble("topP", 0.95)).put("temperatur", cfg.optDouble("temperature", 0.8))
                    .put("maxTokens", cfg.optInt("maxTokens", 2048)).put("gpu", cfg.optString("accelerators").contains("gpu"))
            )
        }
        check(neu.length() > 0) { "Die neue Liste enthält keine passenden Modelle." }
        File(context.filesDir, "ki-modelle.json").writeText(JSONObject().put("version", neueste.removeSuffix(".json")).put("modelle", neu).toString())
        stand(context)
    }
}
