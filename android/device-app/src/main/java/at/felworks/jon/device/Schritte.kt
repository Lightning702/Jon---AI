package at.felworks.jon.device

import android.Manifest
import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONObject
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import kotlin.coroutines.resume

class SchrittWaechter : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val ende = goAsync()
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch {
            try {
                runCatching { Schritte.aktualisieren(context) }
                runCatching { Schritte.planen(context) }
            } finally { ende.finish() }
        }
    }
}

object Schritte {
    private fun prefs(context: Context) = context.getSharedPreferences("jon-schritte", Context.MODE_PRIVATE)

    fun erlaubt(context: Context): Boolean = Build.VERSION.SDK_INT < 29 || context.checkSelfPermission(Manifest.permission.ACTIVITY_RECOGNITION) == PackageManager.PERMISSION_GRANTED

    fun verfuegbar(context: Context): Boolean = context.getSystemService(SensorManager::class.java)?.getDefaultSensor(Sensor.TYPE_STEP_COUNTER) != null

    private suspend fun zaehler(context: Context): Float? = withTimeoutOrNull(4000) {
        suspendCancellableCoroutine { weiter ->
            val sensoren = context.getSystemService(SensorManager::class.java)
            val sensor = sensoren?.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)
            if (sensoren == null || sensor == null) {
                weiter.resume(null)
                return@suspendCancellableCoroutine
            }
            val hoerer = object : SensorEventListener {
                override fun onSensorChanged(ereignis: SensorEvent) {
                    sensoren.unregisterListener(this)
                    if (weiter.isActive) weiter.resume(ereignis.values.firstOrNull())
                }

                override fun onAccuracyChanged(sensor: Sensor?, genauigkeit: Int) {}
            }
            sensoren.registerListener(hoerer, sensor, SensorManager.SENSOR_DELAY_NORMAL)
            weiter.invokeOnCancellation { sensoren.unregisterListener(hoerer) }
        }
    }

    private fun verlauf(context: Context): JSONObject = runCatching { JSONObject(prefs(context).getString("verlauf", "{}") ?: "{}") }.getOrDefault(JSONObject())

    @Synchronized
    fun verbuchen(context: Context, wert: Float) {
        val p = prefs(context)
        val heute = LocalDate.now().toString()
        val tag = p.getString("tag", heute) ?: heute
        val letzter = p.getFloat("letzter", -1f)
        var anzahl = if (tag == heute) p.getInt("heute", 0) else 0
        val verlauf = verlauf(context)
        if (tag != heute) verlauf.put(tag, p.getInt("heute", 0))
        if (letzter >= 0f) {
            val plus = if (wert >= letzter) wert - letzter else wert
            anzahl += plus.toInt().coerceIn(0, 60_000)
        }
        verlauf.put(heute, anzahl)
        val grenze = LocalDate.now().minusDays(120).toString()
        verlauf.keys().asSequence().toList().filter { it < grenze }.forEach { verlauf.remove(it) }
        p.edit().putString("tag", heute).putFloat("letzter", wert).putInt("heute", anzahl).putString("verlauf", verlauf.toString()).commit()
    }

    suspend fun aktualisieren(context: Context): Int {
        if (!erlaubt(context)) return heute(context)
        zaehler(context)?.let { verbuchen(context, it) }
        runCatching { JonWidget.aktualisieren(context) }
        return heute(context)
    }

    fun heute(context: Context): Int {
        val p = prefs(context)
        return if (p.getString("tag", "") == LocalDate.now().toString()) p.getInt("heute", 0) else 0
    }

    fun tage(context: Context, anzahl: Int = 30): JSONObject {
        val verlauf = verlauf(context)
        val ergebnis = JSONObject()
        for (versatz in (anzahl - 1) downTo 0) {
            val tag = LocalDate.now().minusDays(versatz.toLong()).toString()
            ergebnis.put(tag, verlauf.optInt(tag, 0))
        }
        ergebnis.put(LocalDate.now().toString(), heute(context))
        return ergebnis
    }

    fun stand(context: Context): JSONObject = JSONObject()
        .put("heute", heute(context)).put("tage", tage(context, 30))
        .put("erlaubt", erlaubt(context)).put("verfuegbar", verfuegbar(context))
        .put("ziel", prefs(context).getInt("ziel", 8000))

    fun zielSetzen(context: Context, ziel: Int) {
        prefs(context).edit().putInt("ziel", ziel.coerceIn(500, 100_000)).apply()
    }

    fun planen(context: Context) {
        val am = context.getSystemService(AlarmManager::class.java)
        val zeit = LocalDate.now().atTime(LocalTime.of(23, 59, 30)).let { if (it.isBefore(java.time.LocalDateTime.now())) it.plusDays(1) else it }
        val ms = zeit.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
        val pi = PendingIntent.getBroadcast(context, 4740, Intent(context, SchrittWaechter::class.java).setAction("at.felworks.jon.schritte"), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        if (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()) am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, ms, pi)
        else am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, ms, pi)
    }
}
