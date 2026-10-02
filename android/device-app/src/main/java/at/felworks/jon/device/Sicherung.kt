package at.felworks.jon.device

import android.app.Activity
import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.util.Base64
import at.felworks.jon.core.AppBehaelter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipOutputStream

object Sicherung {
    private val einstellungen = listOf(
        "jon-apps", "jon-bildschirmzeit", "jon-gedaechtnis", "jon-ki", "jon-profil", "jon-schritte",
        "jon-solo", "jon-sos", "jon-uhren", "jon-freigabe", "jon-hintergrund", "jon-kinder"
    )
    private val dateien = listOf("chats", "fitness.json", "arbeit")
    private const val GRENZE = 90_000_000L
    private const val TEIL = 384 * 1024

    private fun prefs(context: Context) = context.getSharedPreferences("jon-sicherung", Context.MODE_PRIVATE)

    fun stand(context: Context): JSONObject = JSONObject().put("zuletzt", prefs(context).getLong("zuletzt", 0L))
        .put("automatisch", prefs(context).getBoolean("automatisch", true))

    fun automatischSetzen(context: Context, an: Boolean): JSONObject {
        prefs(context).edit().putBoolean("automatisch", an).commit()
        return stand(context)
    }

    fun faellig(context: Context): Boolean = prefs(context).getBoolean("automatisch", true) &&
        System.currentTimeMillis() - prefs(context).getLong("zuletzt", 0L) > 22 * 3_600_000L

    private fun eintrag(zip: ZipOutputStream, datei: File, name: String) {
        zip.putNextEntry(ZipEntry(name))
        datei.inputStream().use { it.copyTo(zip) }
        zip.closeEntry()
    }

    fun erstellen(context: Context): File = run {
        val ziel = File(context.cacheDir, "jon-sicherung.zip").apply { delete() }
        val basis = context.dataDir
        var summe = 0L
        ZipOutputStream(ziel.outputStream().buffered()).use { zip ->
            val version = runCatching { context.packageManager.getPackageInfo(context.packageName, 0).versionName }.getOrNull().orEmpty()
            zip.putNextEntry(ZipEntry("jon-sicherung.json"))
            zip.write(JSONObject().put("version", version).put("zeit", System.currentTimeMillis()).put("geraet", "${Build.MANUFACTURER} ${Build.MODEL}").toString().toByteArray())
            zip.closeEntry()
            einstellungen.forEach { name -> File(basis, "shared_prefs/$name.xml").takeIf { it.isFile }?.let { eintrag(zip, it, "prefs/$name.xml") } }
            dateien.forEach { name ->
                val quelle = File(context.filesDir, name)
                quelle.walkTopDown().filter { it.isFile }.sortedBy { it.length() }.forEach { datei ->
                    if (summe + datei.length() <= GRENZE) {
                        eintrag(zip, datei, "dateien/" + datei.relativeTo(context.filesDir).path.replace('\\', '/'))
                        summe += datei.length()
                    }
                }
            }
        }
        ziel
    }

    fun einspielen(context: Context, zip: File) {
        ZipFile(zip).use { archiv ->
            check(archiv.getEntry("jon-sicherung.json") != null) { "Das ist keine Jon-Sicherung." }
            val basis = context.dataDir.canonicalFile
            val eintraege = archiv.entries().toList().filter { !it.isDirectory }
            for (e in eintraege) {
                val ziel = when {
                    e.name.startsWith("prefs/") -> {
                        val name = e.name.removePrefix("prefs/").removeSuffix(".xml")
                        if (name !in einstellungen) continue
                        File(basis, "shared_prefs/$name.xml")
                    }
                    e.name.startsWith("dateien/") -> File(context.filesDir, e.name.removePrefix("dateien/"))
                    else -> continue
                }.canonicalFile
                check(ziel.path.startsWith(basis.path + File.separator)) { "Die Sicherung enthält ungültige Pfade." }
                ziel.parentFile?.mkdirs()
                archiv.getInputStream(e).use { eingabe -> ziel.outputStream().use { eingabe.copyTo(it) } }
            }
        }
    }

    suspend fun hochladen(context: Context, behaelter: AppBehaelter, fortschritt: (String) -> Unit = {}): JSONObject = withContext(Dispatchers.IO) {
        check(behaelter.gekoppelt.value) { "Jon ist mit keinem PC oder Pi verbunden." }
        fortschritt("Packe deine Daten …")
        val datei = erstellen(context)
        try {
            val marke = behaelter.verbindung.objekt("POST", "/api/handy/sicherung/start", JSONObject().put("groesse", datei.length())).let { antwort ->
                antwort.optString("marke").ifBlank { error(antwort.optString("detail", "Die Sicherung wurde abgelehnt.")) }
            }
            var gesendet = 0L
            datei.inputStream().use { strom ->
                val puffer = ByteArray(TEIL)
                while (true) {
                    val gelesen = strom.read(puffer)
                    if (gelesen < 0) break
                    val antwort = behaelter.verbindung.objekt("POST", "/api/handy/sicherung/teil", JSONObject().put("marke", marke).put("data", Base64.encodeToString(puffer, 0, gelesen, Base64.NO_WRAP)))
                    check(antwort.has("empfangen")) { antwort.optString("detail", "Übertragung abgebrochen.") }
                    gesendet += gelesen
                    fortschritt("Sende ${gesendet * 100 / datei.length().coerceAtLeast(1)} %")
                }
            }
            val ende = behaelter.verbindung.objekt("POST", "/api/handy/sicherung/ende", JSONObject().put("marke", marke))
            check(ende.has("name")) { ende.optString("detail", "Die Sicherung ist fehlgeschlagen.") }
            prefs(context).edit().putLong("zuletzt", System.currentTimeMillis()).commit()
            ende
        } finally {
            datei.delete()
        }
    }

    suspend fun liste(behaelter: AppBehaelter): JSONArray = withContext(Dispatchers.IO) {
        if (!behaelter.gekoppelt.value) return@withContext JSONArray()
        behaelter.verbindung.objekt("GET", "/api/handy/sicherung/liste").optJSONArray("sicherungen") ?: JSONArray()
    }

    suspend fun vomRechnerEinspielen(activity: Activity, behaelter: AppBehaelter, name: String, fortschritt: (String) -> Unit) {
        val ziel = File(activity.cacheDir, "jon-wiederherstellen.zip").apply { delete() }
        withContext(Dispatchers.IO) {
            var offset = 0L
            ziel.outputStream().use { aus ->
                while (true) {
                    val teil = behaelter.verbindung.objekt("GET", "/api/handy/sicherung/datei?name=${Uri.encode(name)}&offset=$offset")
                    check(teil.has("data")) { teil.optString("detail", "Download abgebrochen.") }
                    aus.write(Base64.decode(teil.getString("data"), Base64.DEFAULT))
                    val weiter = teil.optLong("offset", offset)
                    val groesse = teil.optLong("size", 0L)
                    fortschritt("Lade ${if (groesse > 0) weiter * 100 / groesse else 100} %")
                    if (weiter >= groesse || weiter <= offset) break
                    offset = weiter
                }
            }
            fortschritt("Spiele die Sicherung ein …")
            einspielen(activity, ziel)
            ziel.delete()
        }
        withContext(Dispatchers.Main) { Zuruecksetzen.neustarten(activity) }
    }

    fun alsDatei(context: Context): JSONObject {
        val datei = erstellen(context)
        try {
            val name = "Jon-Sicherung-${LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd-HHmm"))}.zip"
            if (Build.VERSION.SDK_INT >= 29) {
                val werte = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, name)
                    put(MediaStore.Downloads.MIME_TYPE, "application/zip")
                    put(MediaStore.Downloads.RELATIVE_PATH, "Download/Jon")
                }
                val resolver = context.contentResolver
                val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, werte) ?: error("Speichern fehlgeschlagen.")
                resolver.openOutputStream(uri)?.use { aus -> datei.inputStream().use { it.copyTo(aus) } } ?: error("Speichern fehlgeschlagen.")
            } else datei.copyTo(File(context.getExternalFilesDir(null), name), true)
            prefs(context).edit().putLong("zuletzt", System.currentTimeMillis()).commit()
            return JSONObject().put("saved", name)
        } finally {
            datei.delete()
        }
    }

    suspend fun ausDateiEinspielen(activity: Activity, uri: Uri) {
        val ziel = File(activity.cacheDir, "jon-wiederherstellen.zip").apply { delete() }
        withContext(Dispatchers.IO) {
            activity.contentResolver.openInputStream(uri)?.use { eingabe -> ziel.outputStream().use { eingabe.copyTo(it) } } ?: error("Die Datei lässt sich nicht öffnen.")
            einspielen(activity, ziel)
            ziel.delete()
        }
        withContext(Dispatchers.Main) { Zuruecksetzen.neustarten(activity) }
    }
}
