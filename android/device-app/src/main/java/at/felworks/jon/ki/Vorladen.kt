package at.felworks.jon.ki

import android.app.ActivityManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

object Vorladen {
    private val bereich = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var aufraeumen: Job? = null
    @Volatile private var letzteNutzung = 0L

    private fun prefs(context: Context) = context.getSharedPreferences("jon-ki", Context.MODE_PRIVATE)

    fun genutzt(context: Context) {
        letzteNutzung = System.currentTimeMillis()
        prefs(context).edit().putLong("offline-zuletzt", letzteNutzung).apply()
    }

    private fun sinnvoll(context: Context): Boolean {
        val name = Katalog.standard(context) ?: return false
        if (LokaleKi.geladen == name) return false
        val eigenerWeg = Solo.an(context) && Solo.gewaehlt(context) == "handy"
        val kuerzlich = System.currentTimeMillis() - prefs(context).getLong("offline-zuletzt", 0L) < 3 * 86_400_000L
        val speicher = context.getSystemService(ActivityManager::class.java)?.let { am ->
            ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }.let { !it.lowMemory && it.availMem > 2_500_000_000L }
        } ?: false
        return (eigenerWeg || kuerzlich) && speicher
    }

    fun anstossen(context: Context) {
        val app = context.applicationContext
        if (!sinnvoll(app)) return
        val name = Katalog.standard(app) ?: return
        bereich.launch {
            LokaleKi.vorladen(app, name)
            aufraeumen?.cancel()
            aufraeumen = bereich.launch {
                val start = System.currentTimeMillis()
                delay(30 * 60_000L)
                if (letzteNutzung < start && LokaleKi.geladen == name) LokaleKi.entladen()
            }
        }
    }

    fun beobachten(context: Context) {
        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_USER_PRESENT)
            addAction(Intent.ACTION_POWER_CONNECTED)
        }
        runCatching {
            ContextCompat.registerReceiver(context.applicationContext, object : BroadcastReceiver() {
                override fun onReceive(context: Context, intent: Intent) = anstossen(context)
            }, filter, ContextCompat.RECEIVER_NOT_EXPORTED)
        }
    }
}
