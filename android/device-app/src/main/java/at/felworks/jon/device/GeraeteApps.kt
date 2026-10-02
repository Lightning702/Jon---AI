package at.felworks.jon.device

import android.app.ActivityOptions
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.media.MediaMetadata
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.Build
import android.provider.Settings
import android.util.Base64
import at.felworks.jon.connector.Hinweisdienst
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream

data class JonApp(val id: String, val paket: String, val name: String)

object GeraeteApps {
    val pakete = mapOf("amazon" to "com.amazon.mp3", "tiktok" to "com.zhiliaoapp.musically", "whatsapp" to "com.whatsapp", "vpn" to "com.tailscale.ipn")
    val standard = listOf(JonApp("whatsapp", "com.whatsapp", "WhatsApp"), JonApp("tiktok", "com.zhiliaoapp.musically", "TikTok"), JonApp("amazon", "com.amazon.mp3", "Amazon Music"))
    private val immerGesperrt = setOf(
        "com.android.settings", "com.samsung.android.app.settings", "com.google.android.packageinstaller", "com.android.packageinstaller",
        "com.samsung.android.packageinstaller", "com.android.shell", "com.google.android.apps.work.clouddpc"
    )

    private fun prefs(context: Context) = context.getSharedPreferences("jon-apps", Context.MODE_PRIVATE)

    fun liste(context: Context): List<JonApp> {
        val roh = prefs(context).getString("auswahl", null) ?: return standard
        return runCatching {
            val feld = JSONArray(roh)
            (0 until feld.length()).mapNotNull { i ->
                feld.optJSONObject(i)?.let { o ->
                    val paket = o.optString("paket")
                    if (paket.isBlank()) null else JonApp(o.optString("id").ifBlank { paket }, paket, o.optString("name").ifBlank { paket })
                }
            }
        }.getOrDefault(standard)
    }

    fun ids(context: Context): List<String> = liste(context).map { it.id }

    fun paket(context: Context, id: String): String? = liste(context).firstOrNull { it.id == id }?.paket ?: pakete[id]

    fun name(context: Context, id: String): String =
        liste(context).firstOrNull { it.id == id }?.name ?: standard.firstOrNull { it.id == id }?.name ?: id.substringAfterLast('.').replaceFirstChar { it.uppercase() }

    fun installiert(context: Context, id: String): Boolean {
        val ziel = paket(context, id) ?: return false
        return runCatching { context.packageManager.getPackageInfo(ziel, 0); true }.getOrDefault(false)
    }

    private fun normal(text: String) = text.lowercase().replace(Regex("[^a-z0-9äöüß]"), "")

    fun finden(context: Context, wunsch: String): JonApp? = finden(liste(context), wunsch)

    fun finden(apps: List<JonApp>, wunsch: String): JonApp? {
        val suche = normal(wunsch)
        if (suche.isBlank()) return null
        return apps.firstOrNull { it.id == wunsch || it.paket == wunsch }
            ?: apps.firstOrNull { normal(it.name) == suche || normal(it.id) == suche }
            ?: apps.firstOrNull { suche.length >= 4 && normal(it.name).startsWith(suche) }
    }

    fun versteckt(context: Context): Boolean = prefs(context).getBoolean("versteckt", false)

    fun verstecktSetzen(context: Context, an: Boolean): Boolean {
        prefs(context).edit().putBoolean("versteckt", an).commit()
        return an
    }

    fun stand(context: Context): JSONObject {
        val json = JSONObject()
        val feld = JSONArray()
        liste(context).forEach { app ->
            val da = installiert(context, app.id)
            json.put(app.id, da)
            feld.put(JSONObject().put("id", app.id).put("paket", app.paket).put("name", app.name).put("installiert", da))
        }
        return json.put("liste", feld).put("versteckt", versteckt(context))
    }

    fun ausgeschlossen(context: Context): Set<String> {
        val pm = context.packageManager
        val startseiten = runCatching { pm.queryIntentActivities(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME), 0).map { it.activityInfo.packageName } }.getOrDefault(emptyList())
        val einstellungen = runCatching { pm.queryIntentActivities(Intent(Settings.ACTION_SETTINGS), 0).map { it.activityInfo.packageName } }.getOrDefault(emptyList())
        return (startseiten + einstellungen + immerGesperrt + context.packageName + "android").toSet()
    }

    fun installierte(context: Context): JSONArray {
        val pm = context.packageManager
        val gesperrt = ausgeschlossen(context)
        val gewaehlt = liste(context).map { it.paket }.toSet()
        val treffer = pm.queryIntentActivities(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER), 0)
            .map { it.activityInfo.packageName to it.loadLabel(pm).toString() }
            .distinctBy { it.first }
            .filter { it.first !in gesperrt }
            .sortedBy { it.second.lowercase() }
        return JSONArray().apply {
            treffer.forEach { (paket, name) ->
                put(JSONObject().put("paket", paket).put("name", name).put("gewaehlt", paket in gewaehlt)
                    .put("laden", paket == "com.android.vending" || paket.contains("store", true) || paket.contains("market", true)))
            }
        }
    }

    fun symbol(context: Context, paket: String, groesse: Int = 96): String? = runCatching {
        val bild = context.packageManager.getApplicationIcon(paket)
        val bitmap = Bitmap.createBitmap(groesse, groesse, Bitmap.Config.ARGB_8888)
        bild.setBounds(0, 0, groesse, groesse)
        bild.draw(Canvas(bitmap))
        val puffer = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, puffer)
        bitmap.recycle()
        Base64.encodeToString(puffer.toByteArray(), Base64.NO_WRAP)
    }.getOrNull()

    fun symbole(context: Context, pakete: List<String>): JSONObject = JSONObject().apply {
        pakete.distinct().take(60).forEach { paket -> symbol(context, paket)?.let { put(paket, it) } }
    }

    fun auswahlSetzen(context: Context, gewuenscht: List<String>): JSONObject {
        val pm = context.packageManager
        val gesperrt = ausgeschlossen(context)
        val bisher = liste(context)
        val neu = gewuenscht.distinct().take(40).mapNotNull { paket ->
            if (paket in gesperrt) return@mapNotNull null
            val info = runCatching { pm.getApplicationInfo(paket, 0) }.getOrNull() ?: return@mapNotNull null
            if (pm.getLaunchIntentForPackage(paket) == null) return@mapNotNull null
            val id = bisher.firstOrNull { it.paket == paket }?.id ?: standard.firstOrNull { it.paket == paket }?.id ?: paket
            JonApp(id, paket, pm.getApplicationLabel(info).toString().ifBlank { paket })
        }
        val feld = JSONArray().apply { neu.forEach { put(JSONObject().put("id", it.id).put("paket", it.paket).put("name", it.name)) } }
        prefs(context).edit().putString("auswahl", feld.toString()).commit()
        runCatching { GeraeteModus(context).appsUebernehmen() }
        runCatching { Bildschirmzeit.pruefen(context) }
        return stand(context)
    }

    private fun starten(context: Context, intent: Intent) {
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        val optionen = ActivityOptions.makeBasic()
        if (Build.VERSION.SDK_INT >= 28 && GeraeteModus(context).aktiv) optionen.setLockTaskEnabled(true)
        context.startActivity(intent, optionen.toBundle())
    }

    fun oeffnen(context: Context, app: String): JSONObject {
        val ziel = finden(context, app) ?: error("Diese App ist nicht freigegeben.")
        val intent = context.packageManager.getLaunchIntentForPackage(ziel.paket) ?: error("${ziel.name} ist nicht installiert.")
        Bildschirmzeit.pruefeStart(context, ziel.id)
        starten(context, intent)
        Bildschirmzeit.gestartet(context, ziel.id)
        return JSONObject().put("geoeffnet", ziel.id).put("name", ziel.name)
    }

    fun teilen(context: Context, text: String): JSONObject {
        check(installiert(context, "whatsapp")) { "WhatsApp ist nicht installiert." }
        Bildschirmzeit.pruefeStart(context, "whatsapp")
        starten(context, Intent(Intent.ACTION_SEND).setPackage(pakete.getValue("whatsapp")).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text.take(60_000)))
        Bildschirmzeit.gestartet(context, "whatsapp")
        return JSONObject().put("geteilt", true)
    }

    fun musik(context: Context, aktion: String): JSONObject {
        if (aktion == "oeffnen") return oeffnen(context, "amazon")
        require(aktion in setOf("play", "pause", "next", "previous", "status")) { "Unbekannte Musikaktion." }
        check(Hinweisdienst.aktiv(context)) { "Medienzugriff ist noch nicht freigegeben." }
        val manager = context.getSystemService(MediaSessionManager::class.java)
        val controller = manager.getActiveSessions(ComponentName(context, Hinweisdienst::class.java))
            .firstOrNull { it.packageName == pakete.getValue("amazon") }
        if (controller == null) {
            if (aktion == "status") return JSONObject().put("spielt", false).put("titel", "").put("verfuegbar", false)
            error("Öffne Amazon Music einmal und wähle Musik aus.")
        }
        val status = controller.playbackState
        val benoetigt = when (aktion) {
            "play" -> PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PLAY_PAUSE
            "pause" -> PlaybackState.ACTION_PAUSE or PlaybackState.ACTION_PLAY_PAUSE
            "next" -> PlaybackState.ACTION_SKIP_TO_NEXT
            "previous" -> PlaybackState.ACTION_SKIP_TO_PREVIOUS
            else -> 0L
        }
        check(benoetigt == 0L || ((status?.actions ?: 0L) and benoetigt) != 0L) { "Amazon Music unterstützt das gerade nicht." }
        when (aktion) {
            "play" -> controller.transportControls.play()
            "pause" -> controller.transportControls.pause()
            "next" -> controller.transportControls.skipToNext()
            "previous" -> controller.transportControls.skipToPrevious()
        }
        val daten = controller.metadata
        return JSONObject().put("aktion", aktion).put("gesendet", aktion != "status").put("verfuegbar", true)
            .put("spielt", if (aktion == "play") true else if (aktion == "pause") false else status?.state == PlaybackState.STATE_PLAYING)
            .put("titel", daten?.getString(MediaMetadata.METADATA_KEY_TITLE).orEmpty())
            .put("kuenstler", daten?.getString(MediaMetadata.METADATA_KEY_ARTIST).orEmpty())
    }

    fun sprachAktion(text: String, apps: List<JonApp> = standard): Pair<String, String>? {
        val t = text.lowercase().trim().trimEnd('.', '!', '?')
        Regex("^(bitte )?(öffne|starte|öffnen|starten|open|start)( bitte)? (die |den |das )?(.+?)( app)?$").matchEntire(t)?.let { treffer ->
            val wunsch = treffer.groupValues[5]
            val app = finden(apps, wunsch) ?: when (normal(wunsch)) {
                "amazon", "amazonmusik" -> apps.firstOrNull { it.id == "amazon" }
                "tiktok" -> apps.firstOrNull { it.id == "tiktok" }
                else -> null
            }
            if (app != null) return app.id to "oeffnen"
        }
        return when (t) {
            "musik abspielen", "musik fortsetzen", "spiel musik", "spiele musik", "play music" -> "amazon" to "play"
            "musik pausieren", "pause", "musik pause", "musik stoppen", "pause music" -> "amazon" to "pause"
            "nächster titel", "nächstes lied", "weiter", "next song" -> "amazon" to "next"
            "vorheriger titel", "vorheriges lied", "previous song" -> "amazon" to "previous"
            else -> null
        }
    }
}
