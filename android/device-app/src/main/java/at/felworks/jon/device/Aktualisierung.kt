package at.felworks.jon.device

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Base64
import at.felworks.jon.BuildConfig
import at.felworks.jon.core.AppBehaelter
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

object Aktualisierung {
    private fun prefs(context: Context) = context.getSharedPreferences("jon-update", Context.MODE_PRIVATE)

    fun eigeneVersion(context: Context): Pair<String, Long> {
        val info = context.packageManager.getPackageInfo(context.packageName, 0)
        val code = if (Build.VERSION.SDK_INT >= 28) info.longVersionCode else @Suppress("DEPRECATION") info.versionCode.toLong()
        return info.versionName.orEmpty() to code
    }

    suspend fun pruefen(context: Context, behaelter: AppBehaelter): JSONObject {
        val (name, code) = eigeneVersion(context)
        val stand = JSONObject().put("version", name).put("code", code).put("moeglich", BuildConfig.SELBST_UPDATE)
            .put("fehler", prefs(context).getString("fehler", "").orEmpty())
        if (!BuildConfig.SELBST_UPDATE) return stand.put("hinweis", "Diese Version aktualisiert sich über Google Play.")
        if (!behaelter.gekoppelt.value) return stand.put("hinweis", "Verbinde Jon mit deinem PC oder Pi, dann kommen Updates von dort.")
        val info = behaelter.verbindung.objekt("GET", "/api/handy/app")
        val verfuegbar = info.optBoolean("verfuegbar")
        return stand.put("verfuegbar", verfuegbar).put("neu", verfuegbar && info.optLong("code") > code)
            .put("neue_version", info.optString("version")).put("groesse", info.optLong("groesse"))
    }

    suspend fun installieren(context: Context, behaelter: AppBehaelter, fortschritt: (String) -> Unit): JSONObject {
        check(BuildConfig.SELBST_UPDATE) { "Diese Version aktualisiert sich über Google Play." }
        check(behaelter.gekoppelt.value) { "Jon ist mit keinem PC oder Pi verbunden." }
        val info = behaelter.verbindung.objekt("GET", "/api/handy/app")
        check(info.optBoolean("verfuegbar")) { "Auf deinem PC oder Pi liegt keine App zum Aktualisieren." }
        check(info.optLong("code") > eigeneVersion(context).second) { "Jon ist schon auf dem neuesten Stand." }
        if (!GeraeteModus(context).eigentuemer && !context.packageManager.canRequestPackageInstalls()) {
            context.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${context.packageName}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            error("Erlaube Jon einmal, Apps zu installieren, und tippe dann nochmal auf Aktualisieren.")
        }
        val groesse = info.optLong("groesse")
        val datei = File(context.cacheDir, "jon-update.apk")
        datei.delete()
        var offset = 0L
        datei.outputStream().use { aus ->
            while (offset < groesse) {
                val teil = behaelter.verbindung.objekt("GET", "/api/handy/app/teil?offset=$offset")
                check(teil.has("data")) { teil.optString("detail", "Download abgebrochen.") }
                val weiter = teil.optLong("offset", offset)
                check(weiter > offset) { "Download abgebrochen." }
                aus.write(Base64.decode(teil.getString("data"), Base64.DEFAULT))
                offset = weiter
                fortschritt("Lade ${offset * 100 / groesse.coerceAtLeast(1)} %")
            }
        }
        fortschritt("Prüfe die App …")
        if (pruefsumme(datei) != info.optString("sha256")) {
            datei.delete()
            error("Die geladene App ist beschädigt. Bitte nochmal versuchen.")
        }
        fortschritt("Installiere …")
        prefs(context).edit().remove("fehler").putBoolean("neustart", true).commit()
        installierenDatei(context, datei)
        return JSONObject().put("gestartet", true)
    }

    private fun pruefsumme(datei: File): String {
        val summe = MessageDigest.getInstance("SHA-256")
        datei.inputStream().use { strom ->
            val puffer = ByteArray(1 shl 16)
            while (true) {
                val gelesen = strom.read(puffer)
                if (gelesen < 0) break
                summe.update(puffer, 0, gelesen)
            }
        }
        return summe.digest().joinToString("") { "%02x".format(it) }
    }

    private fun installierenDatei(context: Context, datei: File) {
        val installer = context.packageManager.packageInstaller
        val parameter = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL).apply {
            setAppPackageName(context.packageName)
            if (Build.VERSION.SDK_INT >= 31) setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED)
        }
        val sitzungId = installer.createSession(parameter)
        installer.openSession(sitzungId).use { sitzung ->
            sitzung.openWrite("jon.apk", 0, datei.length()).use { aus ->
                datei.inputStream().use { it.copyTo(aus) }
                sitzung.fsync(aus)
            }
            val absicht = Intent(context, UpdateEmpfaenger::class.java).setAction("at.felworks.jon.update")
            val rueckmeldung = PendingIntent.getBroadcast(context, 4812, absicht, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE)
            sitzung.commit(rueckmeldung.intentSender)
        }
    }

    fun fehlerMerken(context: Context, text: String) {
        prefs(context).edit().putString("fehler", text).putBoolean("neustart", false).commit()
    }

    fun neustartFaellig(context: Context): Boolean {
        val faellig = prefs(context).getBoolean("neustart", false)
        if (faellig) prefs(context).edit().putBoolean("neustart", false).commit()
        return faellig
    }
}

class UpdateEmpfaenger : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                val bestaetigen = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                else @Suppress("DEPRECATION") intent.getParcelableExtra(Intent.EXTRA_INTENT)
                bestaetigen?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)?.let { runCatching { context.startActivity(it) } }
            }
            PackageInstaller.STATUS_SUCCESS -> Unit
            else -> Aktualisierung.fehlerMerken(context, intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: "Die Installation ist fehlgeschlagen.")
        }
    }
}
