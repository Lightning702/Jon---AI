package at.felworks.jon

import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.SystemBarStyle
import androidx.activity.addCallback
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.lifecycleScope
import at.felworks.jon.device.Anzeige
import at.felworks.jon.device.Bildschirmzeit
import at.felworks.jon.device.GeraeteModus
import at.felworks.jon.device.SprachDienst
import at.felworks.jon.device.Uhren
import at.felworks.jon.ui.GeraeteApp
import at.felworks.jon.ui.JonWebBruecke
import at.felworks.jon.ui.SiteWunsch
import android.net.Uri
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import org.json.JSONObject
import kotlin.coroutines.resume

data class KameraWunsch(val ziel: String, val ergebnis: CompletableDeferred<JSONObject?>)

class MainActivity : androidx.fragment.app.FragmentActivity() {
    val home = MutableStateFlow(0)
    val qrWunsch = MutableStateFlow<CompletableDeferred<String?>?>(null)
    val kameraWunsch = MutableStateFlow<KameraWunsch?>(null)
    val siteWunsch = MutableStateFlow<SiteWunsch?>(null)
    private var dateiRueckruf: ((Uri?) -> Unit)? = null
    private val dateiWahl = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        dateiRueckruf?.invoke(uri)
        dateiRueckruf = null
    }
    var bruecke: JonWebBruecke? = null
    val geteilt = MutableStateFlow<JSONObject?>(null)
    val oeffnenWunsch = MutableStateFlow<String?>(null)
    private var sprechenWunsch = false
    val teilDateien = java.util.concurrent.ConcurrentHashMap<String, Triple<java.io.File, String, String>>()
    private var rechteRueckruf: ((Map<String, Boolean>) -> Unit)? = null
    private val rechte = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { ergebnis ->
        rechteRueckruf?.invoke(ergebnis)
        rechteRueckruf = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge(SystemBarStyle.dark(Color.TRANSPARENT), SystemBarStyle.dark(Color.TRANSPARENT))
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= 28) window.attributes = window.attributes.apply { layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES }
        window.setBackgroundDrawableResource(android.R.color.black)
        GeraeteModus(this).vollbild(this)
        if (intent?.getBooleanExtra("wecken", false) == true) wachZeigen(true)
        intent?.let { teilenAnnehmen(it); seiteAnnehmen(it) }
        onBackPressedDispatcher.addCallback(this) { bruecke?.zurueck() }
        lifecycleScope.launch { Anzeige.liste.collect { wachZeigen(Anzeige.weckt(it)) } }
        lifecycleScope.launch(Dispatchers.IO) { runCatching { Uhren.allePlanen(applicationContext) } }
        setContent { GeraeteApp(this, (application as JonApplication).behaelter) }
    }

    private fun wachZeigen(an: Boolean) {
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(an)
            setTurnScreenOn(an)
        } else {
            @Suppress("DEPRECATION")
            val flags = WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
            if (an) window.addFlags(flags) else window.clearFlags(flags)
        }
        if (an) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }

    suspend fun rechteAnfragen(liste: Array<String>): Map<String, Boolean> = suspendCancellableCoroutine { weiter ->
        runOnUiThread {
            rechteRueckruf?.invoke(emptyMap())
            rechteRueckruf = { if (weiter.isActive) weiter.resume(it) }
            rechte.launch(liste)
        }
    }

    suspend fun qrScannen(): String? {
        val auftrag = CompletableDeferred<String?>()
        qrWunsch.value?.complete(null)
        qrWunsch.value = auftrag
        return try { auftrag.await() } finally { if (qrWunsch.value === auftrag) qrWunsch.value = null }
    }

    suspend fun kameraOeffnen(ziel: String): JSONObject? {
        val wunsch = KameraWunsch(ziel, CompletableDeferred())
        kameraWunsch.value?.ergebnis?.complete(null)
        kameraWunsch.value = wunsch
        return try { wunsch.ergebnis.await() } finally { if (kameraWunsch.value === wunsch) kameraWunsch.value = null }
    }

    suspend fun dateiWaehlen(typen: Array<String>): Uri? = suspendCancellableCoroutine { weiter ->
        runOnUiThread {
            dateiRueckruf?.invoke(null)
            dateiRueckruf = { if (weiter.isActive) weiter.resume(it) }
            runCatching { dateiWahl.launch(typen) }.onFailure { dateiRueckruf = null; if (weiter.isActive) weiter.resume(null) }
        }
    }

    suspend fun siteOeffnen(quelle: String, pfad: String, titel: String) {
        val wunsch = SiteWunsch(quelle, pfad, titel, CompletableDeferred())
        siteWunsch.value?.fertig?.complete(Unit)
        siteWunsch.value = wunsch
        try { wunsch.fertig.await() } finally { if (siteWunsch.value === wunsch) siteWunsch.value = null }
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) GeraeteModus(this).vollbild(this)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent.getBooleanExtra("wecken", false)) wachZeigen(true)
        if (intent.hasCategory(Intent.CATEGORY_HOME)) home.value++
        teilenAnnehmen(intent)
        seiteAnnehmen(intent)
    }

    private fun seiteAnnehmen(absicht: Intent) {
        if (absicht.getBooleanExtra("sprechen", false)) {
            absicht.removeExtra("sprechen")
            sprechenWunsch = true
        }
        val seite = absicht.getStringExtra("oeffnen") ?: return
        absicht.removeExtra("oeffnen")
        oeffnenWunsch.value = seite
    }

    private fun teilenAnnehmen(absicht: Intent) {
        if (absicht.action != Intent.ACTION_SEND && absicht.action != Intent.ACTION_SEND_MULTIPLE) return
        val text = listOfNotNull(absicht.getStringExtra(Intent.EXTRA_SUBJECT), absicht.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString())
            .map { it.trim() }.filter { it.isNotBlank() }.distinct().joinToString("\n").take(20_000)
        val quellen: List<Uri> = if (absicht.action == Intent.ACTION_SEND_MULTIPLE) {
            (if (Build.VERSION.SDK_INT >= 33) absicht.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java)
            else @Suppress("DEPRECATION") absicht.getParcelableArrayListExtra(Intent.EXTRA_STREAM)).orEmpty()
        } else listOfNotNull(if (Build.VERSION.SDK_INT >= 33) absicht.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java) else @Suppress("DEPRECATION") absicht.getParcelableExtra(Intent.EXTRA_STREAM))
        setIntent(Intent(this, MainActivity::class.java))
        if (text.isBlank() && quellen.isEmpty()) return
        lifecycleScope.launch(Dispatchers.IO) {
            val dateien = org.json.JSONArray()
            teilDateien.values.forEach { it.first.delete() }
            teilDateien.clear()
            quellen.take(10).forEach { uri ->
                runCatching { at.felworks.jon.ki.MedienAnalyse.kopieren(this@MainActivity, uri) }.getOrNull()?.let { (datei, name, mime) ->
                    val marke = java.util.UUID.randomUUID().toString()
                    teilDateien[marke] = Triple(datei, name, mime)
                    dateien.put(JSONObject().put("marke", marke).put("name", name).put("mime", mime).put("groesse", datei.length()))
                }
            }
            geteilt.value = JSONObject().put("text", text).put("dateien", dateien).put("zeit", System.currentTimeMillis())
        }
    }

    override fun onResume() {
        super.onResume()
        runCatching { at.felworks.jon.device.MiniJonDienst.resume(this) }
        at.felworks.jon.device.Sichtbarkeit.vorne = true
        runCatching { at.felworks.jon.ki.Vorladen.anstossen(this) }
        runCatching { at.felworks.jon.device.JonHintergrund.starten(this) }
        val modus = GeraeteModus(this)
        runCatching { modus.anwenden(this) }
        if (sprechenWunsch) {
            sprechenWunsch = false
            if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED) runCatching { SprachDienst.starten(this, true, false) }
        }
        bruecke?.aufgewacht()
        lifecycleScope.launch(Dispatchers.IO) {
            runCatching { Bildschirmzeit.zurueck(applicationContext) }
            runCatching { at.felworks.jon.device.Schritte.aktualisieren(applicationContext); at.felworks.jon.device.Schritte.planen(applicationContext) }
        }
    }

    override fun onPause() {
        super.onPause()
        runCatching { at.felworks.jon.device.MiniJonDienst.detach(this) }
        at.felworks.jon.device.Sichtbarkeit.vorne = false
        runCatching { at.felworks.jon.device.JonWidget.aktualisieren(this) }
    }

    override fun onStop() {
        super.onStop()
        if (!isChangingConfigurations && SprachDienst.zustand.value.offen) SprachDienst.schliessen(this)
    }
}
