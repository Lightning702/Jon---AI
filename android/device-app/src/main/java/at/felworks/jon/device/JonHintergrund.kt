package at.felworks.jon.device

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import at.felworks.jon.JonApplication
import at.felworks.jon.domain.model.Draht
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

class JonHintergrund : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var schleife: Job? = null
    private var letzteSicherung = 0L

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val typ = when {
            Build.VERSION.SDK_INT >= 34 -> ServiceInfo.FOREGROUND_SERVICE_TYPE_REMOTE_MESSAGING
            Build.VERSION.SDK_INT >= 29 -> ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            else -> 0
        }
        val gestartet = runCatching { ServiceCompat.startForeground(this, 4901, Benachrichtigung.dienst(this), typ) }.isSuccess
        if (!gestartet) {
            stopSelf()
            return START_NOT_STICKY
        }
        if (schleife?.isActive != true) schleife = scope.launch { laufen() }
        return START_STICKY
    }

    private suspend fun laufen() {
        val behaelter = (application as JonApplication).behaelter
        while (scope.isActive) {
            if (behaelter.gekoppelt.value && behaelter.verbindung.lage.value.draht != Draht.AUS && Sicherung.faellig(this) && System.currentTimeMillis() - letzteSicherung > 3_600_000L) {
                letzteSicherung = System.currentTimeMillis()
                runCatching { Sicherung.hochladen(this, behaelter) }
            }
            if (behaelter.gekoppelt.value && behaelter.verbindung.lage.value.draht != Draht.AUS && !Sichtbarkeit.vorne) {
                runCatching {
                    val antwort = behaelter.verbindung.geraeteOperation(JSONObject().put("op", "call").put("method", "GET").put("path", "/api/p2p/notifications?channel=handy"), 20_000)
                    val liste = runCatching { JSONArray(antwort.optString("text", "[]")) }.getOrDefault(JSONArray())
                    for (i in 0 until liste.length()) {
                        val n = liste.optJSONObject(i) ?: continue
                        val gruppe = n.optString("group_name")
                        val titel = listOf(n.optString("avatar"), n.optString("sender_name").ifBlank { "Jon Chat" }).filter { it.isNotBlank() }.joinToString(" ") + if (gruppe.isNotBlank()) " · $gruppe" else ""
                        val text = n.optString("text").ifBlank {
                            when (n.optString("media_kind")) { "image" -> "📷 Foto"; "audio" -> "🎤 Sprachnachricht"; "video" -> "🎬 Video"; else -> "📎 Datei" }
                        }
                        Benachrichtigung.jonChat(this, titel, text, n.optString("peer_id") + n.optString("group_id"))
                    }
                }
            }
            delay(20_000)
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        private fun prefs(context: Context) = context.getSharedPreferences("jon-hintergrund", Context.MODE_PRIVATE)

        fun aktiv(context: Context): Boolean = prefs(context).getBoolean("an", true)

        fun setzen(context: Context, an: Boolean) {
            prefs(context).edit().putBoolean("an", an).commit()
            if (an) starten(context) else context.stopService(Intent(context, JonHintergrund::class.java))
        }

        fun starten(context: Context) {
            if (!aktiv(context)) return
            val gekoppelt = runCatching { (context.applicationContext as JonApplication).behaelter.gekoppelt.value }.getOrDefault(false)
            if (!gekoppelt) return
            runCatching { ContextCompat.startForegroundService(context, Intent(context, JonHintergrund::class.java)) }
        }
    }
}
