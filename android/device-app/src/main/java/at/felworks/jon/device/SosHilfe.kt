package at.felworks.jon.device

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.net.Uri
import android.os.Build
import android.os.CancellationSignal
import android.telecom.TelecomManager
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONObject
import java.util.concurrent.Executors
import kotlin.coroutines.resume

object SosHilfe {
    private fun prefs(context: Context) = context.getSharedPreferences("jon-sos", Context.MODE_PRIVATE)

    fun einstellungen(context: Context): JSONObject {
        val p = prefs(context)
        return JSONObject().put("standort", p.getBoolean("standort", false)).put("anruf", p.getBoolean("anruf", false))
            .put("nummer", p.getString("nummer", "").orEmpty()).put("name", p.getString("name", "").orEmpty())
            .put("standort_erlaubt", standortErlaubt(context)).put("anruf_erlaubt", anrufErlaubt(context))
            .put("telefon", telefon(context))
    }

    fun setzen(context: Context, daten: JSONObject): JSONObject {
        val nummer = daten.optString("nummer", prefs(context).getString("nummer", "").orEmpty()).replace(Regex("[^0-9+*#]"), "").take(24)
        prefs(context).edit()
            .putBoolean("standort", daten.optBoolean("standort", prefs(context).getBoolean("standort", false)))
            .putBoolean("anruf", daten.optBoolean("anruf", prefs(context).getBoolean("anruf", false)) && nummer.length >= 3)
            .putString("nummer", nummer)
            .putString("name", daten.optString("name", prefs(context).getString("name", "").orEmpty()).take(40))
            .commit()
        runCatching { GeraeteModus(context).appsUebernehmen() }
        return einstellungen(context)
    }

    fun waehlerPaket(context: Context): String? {
        if (!prefs(context).getBoolean("anruf", false)) return null
        return runCatching { context.getSystemService(TelecomManager::class.java)?.defaultDialerPackage }.getOrNull()
    }

    fun standortErlaubt(context: Context): Boolean =
        context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            context.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    fun telefon(context: Context): Boolean = context.packageManager.hasSystemFeature(if (Build.VERSION.SDK_INT >= 33) PackageManager.FEATURE_TELEPHONY_CALLING else PackageManager.FEATURE_TELEPHONY)

    fun anrufErlaubt(context: Context): Boolean = context.checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED

    @SuppressLint("MissingPermission")
    suspend fun standort(context: Context): Location? {
        if (!prefs(context).getBoolean("standort", false) || !standortErlaubt(context)) return null
        val lm = context.getSystemService(LocationManager::class.java) ?: return null
        val anbieter = (listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER) + if (Build.VERSION.SDK_INT >= 31) listOf(LocationManager.FUSED_PROVIDER) else emptyList()).filter { runCatching { lm.isProviderEnabled(it) }.getOrDefault(false) }
        val letzte = anbieter.mapNotNull { runCatching { lm.getLastKnownLocation(it) }.getOrNull() }.maxByOrNull { it.time }
        if (Build.VERSION.SDK_INT < 30 || anbieter.isEmpty()) return letzte
        val frisch = withTimeoutOrNull(12_000) {
            suspendCancellableCoroutine<Location?> { weiter ->
                val abbruch = CancellationSignal()
                weiter.invokeOnCancellation { abbruch.cancel() }
                val quelle = if (LocationManager.GPS_PROVIDER in anbieter) LocationManager.GPS_PROVIDER else anbieter.first()
                runCatching { lm.getCurrentLocation(quelle, abbruch, Executors.newSingleThreadExecutor()) { ort -> if (weiter.isActive) weiter.resume(ort) } }
                    .onFailure { if (weiter.isActive) weiter.resume(null) }
            }
        }
        return frisch ?: letzte
    }

    fun anrufen(context: Context): Boolean {
        val p = prefs(context)
        val nummer = p.getString("nummer", "").orEmpty()
        if (!p.getBoolean("anruf", false) || nummer.length < 3) return false
        val direkt = anrufErlaubt(context) && telefon(context)
        val intent = Intent(if (direkt) Intent.ACTION_CALL else Intent.ACTION_DIAL, Uri.parse("tel:" + Uri.encode(nummer))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return runCatching { context.startActivity(intent); true }.getOrDefault(false)
    }
}
