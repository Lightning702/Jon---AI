package at.felworks.jon.device

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Looper
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONObject
import java.util.concurrent.Executors
import kotlin.coroutines.resume

object Ortung {
    private val ausfuehrer = Executors.newSingleThreadExecutor()
    @Volatile private var letzter: Location? = null
    private var hoerer: LocationListener? = null

    private fun prefs(context: Context) = context.getSharedPreferences("jon-ortung", Context.MODE_PRIVATE)

    fun teilen(context: Context): Boolean = prefs(context).getBoolean("teilen", false)

    fun teilenSetzen(context: Context, an: Boolean) {
        prefs(context).edit().putBoolean("teilen", an).apply()
        if (an) beobachten(context) else beenden(context)
    }

    fun erlaubt(context: Context): Boolean =
        context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            context.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    fun hintergrund(context: Context): Boolean =
        Build.VERSION.SDK_INT < 29 || context.checkSelfPermission(Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED

    private fun verwaltung(context: Context): LocationManager? = context.getSystemService(LocationManager::class.java)

    private fun anbieter(lm: LocationManager): List<String> {
        val alle = runCatching { lm.getProviders(true) }.getOrDefault(emptyList())
        return listOf("fused", LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER, LocationManager.PASSIVE_PROVIDER).filter { it in alle }
    }

    private fun besser(neu: Location?, alt: Location?): Location? {
        if (neu == null) return alt
        if (alt == null) return neu
        val juenger = neu.time - alt.time
        if (juenger > 120_000) return neu
        if (juenger < -120_000) return alt
        return if (neu.accuracy <= alt.accuracy + 15) neu else alt
    }

    @SuppressLint("MissingPermission")
    fun zuletzt(context: Context): Location? {
        if (!erlaubt(context)) return letzter
        val lm = verwaltung(context) ?: return letzter
        var bester = letzter
        for (name in anbieter(lm)) bester = besser(runCatching { lm.getLastKnownLocation(name) }.getOrNull(), bester)
        return bester
    }

    fun json(ort: Location): JSONObject = JSONObject()
        .put("lat", ort.latitude)
        .put("lon", ort.longitude)
        .put("genau", ort.accuracy.toDouble())
        .put("zeit", ort.time)
        .apply {
            if (ort.hasSpeed()) put("tempo", ort.speed.toDouble())
            if (ort.hasBearing()) put("richtung", ort.bearing.toDouble())
            if (ort.hasAltitude()) put("hoehe", ort.altitude)
        }

    @SuppressLint("MissingPermission")
    suspend fun jetzt(context: Context, wartezeit: Long = 20_000): Location? {
        if (!erlaubt(context)) return null
        val lm = verwaltung(context) ?: return zuletzt(context)
        val namen = anbieter(lm).filter { it != LocationManager.PASSIVE_PROVIDER }
        if (namen.isEmpty()) return zuletzt(context)
        val frisch = withTimeoutOrNull(wartezeit) {
            suspendCancellableCoroutine<Location?> { fortsetzung ->
                val fertig = java.util.concurrent.atomic.AtomicBoolean(false)
                val listener = object : LocationListener {
                    override fun onLocationChanged(location: Location) {
                        if (!fertig.compareAndSet(false, true)) return
                        runCatching { lm.removeUpdates(this) }
                        if (fortsetzung.isActive) fortsetzung.resume(location)
                    }
                    override fun onProviderDisabled(provider: String) {}
                    override fun onProviderEnabled(provider: String) {}
                }
                if (Build.VERSION.SDK_INT >= 30) {
                    for (name in namen) {
                        runCatching {
                            lm.getCurrentLocation(name, null, ausfuehrer) { ort -> if (ort != null) listener.onLocationChanged(ort) }
                        }
                    }
                } else {
                    for (name in namen) runCatching { lm.requestLocationUpdates(name, 0L, 0f, listener, Looper.getMainLooper()) }
                }
                fortsetzung.invokeOnCancellation { runCatching { lm.removeUpdates(listener) } }
            }
        }
        if (frisch != null) letzter = besser(frisch, letzter)
        return frisch ?: zuletzt(context)
    }

    @SuppressLint("MissingPermission")
    @Synchronized
    fun beobachten(context: Context) {
        if (hoerer != null || !teilen(context) || !erlaubt(context)) return
        val lm = verwaltung(context.applicationContext) ?: return
        val listener = LocationListener { ort -> letzter = besser(ort, letzter) }
        val namen = anbieter(lm)
        if (namen.isEmpty()) return
        for (name in namen) {
            val takt = if (name == LocationManager.GPS_PROVIDER) 180_000L else 60_000L
            runCatching { lm.requestLocationUpdates(name, takt, 30f, listener, Looper.getMainLooper()) }
        }
        hoerer = listener
    }

    @Synchronized
    fun beenden(context: Context) {
        val listener = hoerer ?: return
        runCatching { verwaltung(context.applicationContext)?.removeUpdates(listener) }
        hoerer = null
    }
}
