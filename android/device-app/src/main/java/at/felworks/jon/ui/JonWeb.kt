package at.felworks.jon.ui

import android.Manifest
import android.content.BroadcastReceiver
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.BatteryManager
import android.os.Build
import android.provider.MediaStore
import android.provider.Settings
import android.util.Base64
import android.view.HapticFeedbackConstants
import android.view.ViewGroup
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.core.view.doOnLayout
import at.felworks.jon.MainActivity
import at.felworks.jon.connector.Hinweisdienst
import at.felworks.jon.connector.Verbinderrechte
import at.felworks.jon.core.AppBehaelter
import at.felworks.jon.data.remote.Krypto
import at.felworks.jon.device.Anzeige
import at.felworks.jon.device.Basisfunktionen
import at.felworks.jon.device.Bildschirmzeit
import at.felworks.jon.device.Fotos
import at.felworks.jon.device.GeraeteApps
import at.felworks.jon.device.GeraeteModus
import at.felworks.jon.device.KlingelDienst
import at.felworks.jon.device.SosHilfe
import at.felworks.jon.device.SprachDienst
import at.felworks.jon.device.Uhren
import at.felworks.jon.device.Schritte
import at.felworks.jon.device.Zeitregeln
import at.felworks.jon.ki.Arbeitsraum
import at.felworks.jon.ki.FitnessLokal
import at.felworks.jon.ki.Gedaechtnis
import at.felworks.jon.ki.JonKern
import at.felworks.jon.ki.Katalog
import at.felworks.jon.ki.LokaleKi
import at.felworks.jon.ki.MedienAnalyse
import at.felworks.jon.ki.Podcast
import at.felworks.jon.ki.Solo
import at.felworks.jon.domain.model.Draht
import at.felworks.jon.pairing.PiKopplung
import at.felworks.jon.pairing.QrNutzlast
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.File
import java.util.concurrent.ConcurrentHashMap

private val KARTENSERVER = setOf("tiles.openfreemap.org", "server.arcgisonline.com")

class JonWebBruecke(private val activity: MainActivity, private val behaelter: AppBehaelter) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val jobs = ConcurrentHashMap<String, Job>()
    private val transfers = ConcurrentHashMap<String, File>()
    var web: WebView? = null
    @Volatile private var bereit = false
    private var akku = JSONObject()
    private val akkuEmpfaenger = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
            val skala = intent.getIntExtra(BatteryManager.EXTRA_SCALE, 100)
            val status = intent.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
            if (level < 0) return
            akku = JSONObject().put("level", level * 100 / skala.coerceAtLeast(1)).put("charging", status == BatteryManager.BATTERY_STATUS_CHARGING || status == BatteryManager.BATTERY_STATUS_FULL)
            ereignis("battery", akku)
        }
    }

    init {
        ContextCompat.registerReceiver(activity, akkuEmpfaenger, IntentFilter(Intent.ACTION_BATTERY_CHANGED), ContextCompat.RECEIVER_NOT_EXPORTED)
        scope.launch { behaelter.verbindung.lage.collect { ereignis("connection", status()) } }
        scope.launch { behaelter.gekoppelt.collect { ereignis("connection", status()) } }
        scope.launch { behaelter.wechsel.collect { ereignis("server-gewechselt", it); ereignis("connection", status()) } }
        scope.launch {
            at.felworks.jon.device.AdminSchutz.frist.collectLatest { bis ->
                while (isActive) {
                    val rest = bis - android.os.SystemClock.elapsedRealtime()
                    ereignis("admin", JSONObject().put("frei", rest > 0).put("rest_ms", rest.coerceAtLeast(0L)))
                    if (rest <= 0) break
                    delay(rest + 250)
                }
            }
        }
        scope.launch { SprachDienst.zustand.collect { ereignis("voice", it.json()) } }
        scope.launch { behaelter.chat.aenderung.collect { if (it > 0) ereignis("chatChanged", JSONObject().put("conversation_id", behaelter.chat.aktuell)) } }
        scope.launch { Anzeige.liste.collect { ereignis("anzeige", JSONObject().put("liste", Anzeige.json())) } }
        scope.launch { activity.geteilt.collect { wert -> if (wert != null) ereignis("teilen", wert) } }
        scope.launch { activity.oeffnenWunsch.collect { seite -> if (seite != null) { ereignis("oeffnen", JSONObject().put("seite", seite)); activity.oeffnenWunsch.value = null } } }
        scope.launch {
            while (isActive) {
                delay(20_000)
                if (behaelter.gekoppelt.value && behaelter.verbindung.lage.value.draht == Draht.AUS) runCatching { behaelter.verbindung.pruefen() }
            }
        }
    }

    fun status(): JSONObject {
        val s = behaelter.verbindung.lage.value
        val m = GeraeteModus(activity)
        return JSONObject().put("connected", s.draht != Draht.AUS).put("paired", behaelter.gekoppelt.value).put("name", s.pcName)
            .put("kiosk", m.aktiv).put("owner", m.eigentuemer).put("locked", m.gesperrt)
            .put("server", behaelter.tresor.zugaenge().size).put("server_id", behaelter.aktiveId())
            .put("klemmt", m.reparaturNoetig())
            .put("apps_versteckt", GeraeteApps.versteckt(activity))
    }

    private fun liefern(objekt: JSONObject) {
        val text = objekt.toString()
        activity.runOnUiThread { if (bereit) web?.evaluateJavascript("window.jonReceive($text);", null) }
    }

    fun ereignis(art: String, daten: JSONObject) { liefern(JSONObject().put("event", art).put("data", daten)) }
    fun zurueck() = ereignis("back", JSONObject())
    fun home() = ereignis("home", JSONObject())
    fun einsaetze(oben: Float, unten: Float) = ereignis("insets", JSONObject().put("top", oben.toDouble()).put("bottom", unten.toDouble()))
    fun aufgewacht() {
        ereignis("connection", status())
        ereignis("anzeige", JSONObject().put("liste", Anzeige.json()))
        if (akku.length() > 0) ereignis("battery", akku)
        activity.geteilt.value?.let { ereignis("teilen", it) }
        if (behaelter.gekoppelt.value) scope.launch { runCatching { behaelter.verbindung.pruefen() } }
    }

    private fun dekodieren(text: String): ByteArray = Base64.decode(text.replace('-', '+').replace('_', '/'), Base64.DEFAULT)

    private fun adminNoetig() {
        val schutz = GeraeteModus(activity).schutz
        check(!schutz.eingerichtet || schutz.frei) { "Admin-PIN erforderlich." }
    }

    private suspend fun erlauben(vararg rechte: String): Boolean {
        val fehlend = rechte.filter { !Verbinderrechte.erteilt(activity, it) }
        if (fehlend.isEmpty()) return true
        val ergebnis = activity.rechteAnfragen(fehlend.toTypedArray())
        return fehlend.all { ergebnis[it] == true || Verbinderrechte.erteilt(activity, it) }
    }

    private fun rechteFuer(name: String): Array<String> = when (name) {
        "mikrofon" -> arrayOf(Manifest.permission.RECORD_AUDIO)
        "kamera" -> arrayOf(Manifest.permission.CAMERA)
        "benachrichtigungen" -> if (Build.VERSION.SDK_INT >= 33) arrayOf(Manifest.permission.POST_NOTIFICATIONS) else emptyArray()
        "standort" -> if (Build.VERSION.SDK_INT >= 33) arrayOf(Manifest.permission.NEARBY_WIFI_DEVICES) else arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        "bluetooth" -> if (Build.VERSION.SDK_INT >= 31) arrayOf(Manifest.permission.BLUETOOTH_CONNECT) else emptyArray()
        "bewegung" -> if (Build.VERSION.SDK_INT >= 29) arrayOf(Manifest.permission.ACTIVITY_RECOGNITION) else emptyArray()
        "ort" -> arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
        "anruf" -> arrayOf(Manifest.permission.CALL_PHONE)
        else -> error("Unbekannte Berechtigung.")
    }

    private fun geraet(): JSONObject {
        val m = GeraeteModus(activity)
        val b = Basisfunktionen(activity)
        val lage = behaelter.verbindung.lage.value
        val netz = activity.getSystemService(ConnectivityManager::class.java)
        val vpn = runCatching { netz.getNetworkCapabilities(netz.activeNetwork)?.hasTransport(NetworkCapabilities.TRANSPORT_VPN) == true }.getOrDefault(false)
        val helligkeit = if (m.eigentuemer) b.helligkeit else ((activity.window.attributes.screenBrightness.takeIf { it >= 0 } ?: (b.helligkeit / 255f)) * 255).toInt()
        return JSONObject()
            .put("wlan", runCatching { b.wlan }.getOrDefault(false))
            .put("bluetooth", runCatching { b.bluetooth }.getOrDefault(false))
            .put("lautstaerke", b.lautstaerke).put("maximal", b.maximal).put("helligkeit", helligkeit.coerceIn(10, 255))
            .put("unterbrechen", m.unterbrechen)
            .put("eigentuemer", m.eigentuemer).put("kiosk", m.aktiv).put("gesperrt", m.gesperrt)
            .put("admin", adminStand())
            .put("rechte", JSONObject()
                .put("mikrofon", Verbinderrechte.erteilt(activity, Manifest.permission.RECORD_AUDIO))
                .put("kamera", Verbinderrechte.erteilt(activity, Manifest.permission.CAMERA))
                .put("benachrichtigungen", Build.VERSION.SDK_INT < 33 || Verbinderrechte.erteilt(activity, Manifest.permission.POST_NOTIFICATIONS))
                .put("medien", Hinweisdienst.aktiv(activity)))
            .put("vpn", vpn).put("tailscale", GeraeteApps.installiert(activity, "vpn")).put("nutzungszugriff", Bildschirmzeit.zugriff(activity))
            .put("apps", GeraeteApps.stand(activity))
            .put("modell", "${Build.MANUFACTURER.replaceFirstChar { it.uppercase() }} ${Build.MODEL}")
            .put("android", "Android ${Build.VERSION.RELEASE} · API ${Build.VERSION.SDK_INT}")
            .put("version", runCatching { activity.packageManager.getPackageInfo(activity.packageName, 0).versionName }.getOrNull().orEmpty())
            .put("akku", akku.optInt("level", -1)).put("laedt", akku.optBoolean("charging"))
            .put("pi", JSONObject().put("name", lage.pcName).put("adresse", lage.adresse).put("verbunden", lage.draht != Draht.AUS).put("gekoppelt", behaelter.gekoppelt.value))
    }

    private fun adminStand(): JSONObject {
        val s = GeraeteModus(activity).schutz
        return JSONObject().put("eingerichtet", s.eingerichtet).put("frei", s.frei).put("bestaetigt", s.bestaetigt)
            .put("fingerabdruck", at.felworks.jon.device.Fingerabdruck.an(activity)).put("finger_moeglich", at.felworks.jon.device.Fingerabdruck.moeglich(activity))
    }

    private suspend fun setzen(name: String, wert: Any?): JSONObject {
        val m = GeraeteModus(activity)
        val b = Basisfunktionen(activity)
        when (name) {
            "wlan" -> { adminNoetig(); b.wlanSetzen(wert == true) }
            "bluetooth" -> { adminNoetig(); check(erlauben(*rechteFuer("bluetooth"))) { "Bluetooth-Berechtigung fehlt." }; b.bluetoothSetzen(wert == true) }
            "lautstaerke" -> b.lautstaerkeSetzen((wert as? Number)?.toInt() ?: 0)
            "helligkeit" -> {
                val stufe = ((wert as? Number)?.toInt() ?: 128).coerceIn(10, 255)
                if (m.eigentuemer) b.helligkeitSetzen(stufe)
                else withContext(Dispatchers.Main) { activity.window.attributes = activity.window.attributes.apply { screenBrightness = stufe / 255f } }
            }
            "unterbrechen" -> m.unterbrechen = wert == true
            else -> error("Unbekannte Einstellung.")
        }
        return geraet()
    }

    @JavascriptInterface
    fun post(raw: String) {
        if (raw.length > 6_000_000) return
        val r = runCatching { JSONObject(raw) }.getOrNull() ?: return
        val id = r.optString("id").take(100)
        if (id.isBlank()) return
        val op = r.optString("op")
        if (op == "cancel") { jobs.remove(r.optString("target"))?.cancel(); return }
        if (op == "haptic") { fuehlen(r.optString("kind")); return }
        val job = scope.launch(start = CoroutineStart.LAZY) {
            try {
                val result: Any = when (op) {
                    "ready" -> { bereit = true; activity.runOnUiThread { aufgewacht() }; status() }
                    "api" -> {
                        val pfad = r.getString("path")
                        check(pfad.startsWith("/api/") && !pfad.contains("\\") && !pfad.contains("..")) { "Ungültiger API-Pfad." }
                        if (pfad == "/api/agents/runs" && r.optString("method", "GET") == "POST") {
                            r.optJSONObject("body")?.let { at.felworks.jon.device.KinderModus.anfrage(activity, it) }
                        }
                        behaelter.verbindung.geraeteOperation(JSONObject().put("op", "call").put("method", r.optString("method", "GET")).put("path", pfad).put("body", r.opt("body")).put("binary", r.optBoolean("binary")), 240_000)
                    }
                    "stream" -> {
                        val inhalt = StringBuilder()
                        behaelter.verbindung.strom("/api/chat", at.felworks.jon.device.KinderModus.anfrage(activity, r.getJSONObject("body"))).collect { teil ->
                            if (teil.optString("type") == "content") inhalt.append(teil.optString("delta"))
                            liefern(JSONObject().put("id", id).put("chunk", teil))
                        }
                        if (!at.felworks.jon.device.Sichtbarkeit.vorne) at.felworks.jon.device.Benachrichtigung.antwortFertig(activity, inhalt.toString())
                        JSONObject()
                    }
                    "minijon-status" -> at.felworks.jon.device.MiniJonDienst.status(activity)
                    "minijon-enable" -> withContext(Dispatchers.Main) { at.felworks.jon.device.MiniJonDienst.enable(activity, r.optBoolean("enabled")) }
                    "context" -> {
                        behaelter.chat.kontext(r.optString("conversation_id"), r.optString("provider"), r.optString("model"), r.optString("mode", "chat"), r.optString("workspace"))
                        JSONObject()
                    }
                    "voice" -> {
                        check(erlauben(Manifest.permission.RECORD_AUDIO)) { "Erlaube das Mikrofon, um mit Jon zu sprechen." }
                        withContext(Dispatchers.Main) { SprachDienst.starten(activity, true, r.optString("mode") == "dictate") }
                        JSONObject()
                    }
                    "voice-finish" -> { withContext(Dispatchers.Main) { SprachDienst.befehl(activity, "fertig") }; JSONObject() }
                    "voice-cancel" -> { withContext(Dispatchers.Main) { SprachDienst.schliessen(activity) }; JSONObject() }
                    "voice-interrupt" -> { withContext(Dispatchers.Main) { SprachDienst.befehl(activity, "unterbrechen") }; JSONObject() }
                    "voice-mute" -> { val stumm = r.optBoolean("muted"); withContext(Dispatchers.Main) { SprachDienst.befehl(activity, "stumm") { putExtra("stumm", stumm) } }; JSONObject() }
                    "voice-state" -> SprachDienst.zustand.value.json()
                    "speak" -> { withContext(Dispatchers.Main) { SprachDienst.vorlesen(activity, r.getString("text")) }; JSONObject() }
                    "app" -> withContext(Dispatchers.Main) { GeraeteApps.oeffnen(activity, r.getString("app")) }
                    "apps" -> GeraeteApps.stand(activity)
                    "apps-installiert" -> JSONObject().put("apps", GeraeteApps.installierte(activity))
                    "apps-symbole" -> {
                        val liste = r.optJSONArray("pakete") ?: org.json.JSONArray()
                        GeraeteApps.symbole(activity, (0 until liste.length()).map { liste.optString(it) }.filter { it.isNotBlank() })
                    }
                    "apps-setzen" -> {
                        adminNoetig()
                        val liste = r.optJSONArray("pakete") ?: org.json.JSONArray()
                        GeraeteApps.auswahlSetzen(activity, (0 until liste.length()).map { liste.optString(it) }.filter { it.isNotBlank() })
                    }
                    "music" -> withContext(Dispatchers.Main) { GeraeteApps.musik(activity, r.optString("aktion", "status")) }
                    "share" -> withContext(Dispatchers.Main) {
                        if (r.optString("ziel") == "whatsapp") GeraeteApps.teilen(activity, r.getString("text"))
                        else { kopieren(r.getString("text")); JSONObject() }
                    }
                    "copy" -> { withContext(Dispatchers.Main) { kopieren(r.getString("text")) }; JSONObject() }
                    "device" -> geraet()
                    "set" -> setzen(r.getString("name"), r.opt("value"))
                    "wifi-scan" -> {
                        adminNoetig()
                        check(erlauben(*rechteFuer("standort"))) { "Erlaube „Geräte in der Nähe“, damit Jon WLAN-Netze findet." }
                        val b = Basisfunktionen(activity)
                        runCatching { b.suchen() }
                        delay(1800)
                        JSONObject().put("netze", org.json.JSONArray(runCatching { b.netze() }.getOrDefault(emptyList())))
                    }
                    "wifi-connect" -> { adminNoetig(); Basisfunktionen(activity).verbinden(r.getString("ssid"), r.optString("passwort"), r.optString("art", "wpa2")); JSONObject() }
                    "permission" -> {
                        val rechte = rechteFuer(r.getString("name"))
                        JSONObject().put("granted", rechte.isEmpty() || erlauben(*rechte))
                    }
                    "admin" -> admin(r)
                    "neustarten" -> { adminNoetig(); GeraeteModus(activity).neustarten(); JSONObject() }
                    "kiosk" -> withContext(Dispatchers.Main) {
                        val m = GeraeteModus(activity)
                        when (r.getString("aktion")) {
                            "an" -> m.einschalten(activity, behaelter.gekoppelt.value && behaelter.verbindung.lage.value.draht != Draht.AUS)
                            "aus" -> m.verlassen(activity)
                            "entfernen" -> m.entfernen(activity)
                            else -> error("Unbekannte Aktion.")
                        }
                        ereignis("connection", status())
                        geraet()
                    }
                    "system" -> withContext(Dispatchers.Main) { system(r.getString("ziel")); JSONObject() }
                    "pair" -> koppeln(r)
                    "unpair" -> {
                        behaelter.entkoppeln()
                        if (!behaelter.gekoppelt.value) runCatching { activity.stopService(Intent(activity, at.felworks.jon.device.JonHintergrund::class.java)) }
                        JSONObject()
                    }
                    "server" -> JSONObject().put("liste", behaelter.server()).put("automatisch", behaelter.automatisch())
                    "server-pruefen" -> JSONObject().put("liste", behaelter.serverPruefen()).put("automatisch", behaelter.automatisch())
                    "server-wechseln" -> {
                        adminNoetig()
                        behaelter.wechseln(r.getString("id"))
                        runCatching { behaelter.verbindung.pruefen() }
                        JSONObject().put("liste", behaelter.server())
                    }
                    "server-entfernen" -> {
                        behaelter.entfernen(r.getString("id"))
                        if (!behaelter.gekoppelt.value) runCatching { activity.stopService(Intent(activity, at.felworks.jon.device.JonHintergrund::class.java)) }
                        JSONObject().put("liste", behaelter.server())
                    }
                    "server-automatisch" -> {
                        adminNoetig()
                        behaelter.automatischSetzen(r.optBoolean("an", true))
                        JSONObject().put("automatisch", behaelter.automatisch())
                    }
                    "apps-versteckt" -> {
                        if (r.has("an")) { adminNoetig(); GeraeteApps.verstecktSetzen(activity, r.optBoolean("an")) }
                        ereignis("connection", status())
                        JSONObject().put("versteckt", GeraeteApps.versteckt(activity))
                    }
                    "teilen-erledigt" -> { activity.geteilt.value = null; JSONObject() }
                    "teilen-datei" -> {
                        val (datei, name, mime) = activity.teilDateien.remove(r.getString("marke")) ?: error("Die geteilte Datei ist nicht mehr da. Bitte nochmal teilen.")
                        val weg = JonKern.weg(activity, behaelter.gekoppelt.value, behaelter.verbindung.lage.value.draht != Draht.AUS)
                        val ziel = r.optString("ziel").ifBlank { if (weg == at.felworks.jon.ki.Weg.PI) "pi" else "handy" }
                        MedienAnalyse.auswerten(activity, behaelter, datei, name, mime, ziel, weg) { text -> liefern(JSONObject().put("id", id).put("chunk", JSONObject().put("fortschritt", text))) }
                    }
                    "sicherung" -> JSONObject().put("stand", at.felworks.jon.device.Sicherung.stand(activity))
                        .put("liste", runCatching { at.felworks.jon.device.Sicherung.liste(behaelter) }.getOrDefault(org.json.JSONArray()))
                    "sicherung-jetzt" -> at.felworks.jon.device.Sicherung.hochladen(activity, behaelter) { text -> liefern(JSONObject().put("id", id).put("chunk", JSONObject().put("fortschritt", text))) }
                    "sicherung-automatisch" -> at.felworks.jon.device.Sicherung.automatischSetzen(activity, r.optBoolean("an"))
                    "sicherung-datei" -> at.felworks.jon.device.Sicherung.alsDatei(activity)
                    "sicherung-einspielen" -> {
                        adminNoetig()
                        at.felworks.jon.device.Sicherung.vomRechnerEinspielen(activity, behaelter, r.getString("name")) { text -> liefern(JSONObject().put("id", id).put("chunk", JSONObject().put("fortschritt", text))) }
                        JSONObject()
                    }
                    "sicherung-aus-datei" -> {
                        adminNoetig()
                        val uri = activity.dateiWaehlen(arrayOf("application/zip", "application/octet-stream")) ?: error("Abgebrochen")
                        at.felworks.jon.device.Sicherung.ausDateiEinspielen(activity, uri)
                        JSONObject()
                    }
                    "update-pruefen" -> at.felworks.jon.device.Aktualisierung.pruefen(activity, behaelter)
                    "update-installieren" -> at.felworks.jon.device.Aktualisierung.installieren(activity, behaelter) { text -> liefern(JSONObject().put("id", id).put("chunk", JSONObject().put("fortschritt", text))) }
                    "alle-daten-loeschen" -> {
                        adminNoetig()
                        at.felworks.jon.device.Zuruecksetzen.allesLoeschen(activity, behaelter, r.optBoolean("medien"))
                        JSONObject()
                    }
                    "back-unhandled" -> withContext(Dispatchers.Main) {
                        val m = GeraeteModus(activity)
                        val frei = !m.aktiv && !m.gesperrt
                        if (frei) activity.moveTaskToBack(true)
                        JSONObject().put("geschlossen", frei)
                    }
                    "beenden" -> withContext(Dispatchers.Main) {
                        val m = GeraeteModus(activity)
                        check(!m.aktiv && !m.gesperrt) { "Im Kiosk bleibt Jon offen. Verlasse zuerst den Kiosk." }
                        SprachDienst.stoppen(activity)
                        activity.finishAndRemoveTask()
                        JSONObject()
                    }
                    "darstellung" -> withContext(Dispatchers.Main) {
                        val hell = r.optBoolean("hell")
                        WindowCompat.getInsetsController(activity.window, activity.window.decorView).apply {
                            isAppearanceLightNavigationBars = hell
                            isAppearanceLightStatusBars = hell
                        }
                        JSONObject()
                    }
                    "zeit" -> Bildschirmzeit.stand(activity)
                    "zeit-setzen" -> { adminNoetig(); Bildschirmzeit.setzen(activity, r.optJSONObject("regeln") ?: JSONObject()) }
                    "fokus" -> Bildschirmzeit.fokus(activity, r.optInt("minuten", 25))
                    "zeit-anfragen" -> {
                        check(behaelter.gekoppelt.value) { "Jon ist mit keinem Rechner verbunden. Frag bitte direkt nach." }
                        val app = r.getString("app")
                        check(app in GeraeteApps.ids(activity)) { "Diese App kennt Jon nicht." }
                        check(Bildschirmzeit.anfrage(activity) == null) { "Deine letzte Anfrage läuft noch." }
                        val minuten = r.optInt("minuten", 30).coerceIn(5, 120)
                        val antwort = behaelter.melden("zeitanfrage", JSONObject().put("app", app).put("name", GeraeteApps.name(activity, app))
                            .put("minuten", minuten).put("text", r.optString("text").trim().take(200)))
                        check(antwort.optBoolean("ok", true)) { antwort.optString("fehler").ifBlank { "Die Anfrage kam nicht an." } }
                        Bildschirmzeit.anfrageMerken(activity, app, minuten, antwort.optString("id").ifBlank { Krypto.kennung(6) })
                        Bildschirmzeit.stand(activity)
                    }
                    "uhren" -> Uhren.stand(activity)
                    "wecker-setzen" -> Uhren.weckerSetzen(activity, r.optJSONObject("wecker") ?: JSONObject())
                    "wecker-loeschen" -> Uhren.weckerLoeschen(activity, r.getString("wecker"))
                    "timer-starten" -> Uhren.timerStarten(activity, r.optInt("sekunden"), r.optString("name"))
                    "timer-abbrechen" -> Uhren.timerAbbrechen(activity, r.optString("timer").ifBlank { null })
                    "klingeln-stopp" -> { KlingelDienst.stoppen(); Anzeige.entfernen("klingeln"); JSONObject() }
                    "schlummern" -> { KlingelDienst.schlummern(activity); JSONObject() }
                    "anzeige-schliessen" -> {
                        val weg = Anzeige.entfernen(r.getString("anzeige"))
                        if (weg?.optString("art") == "durchsage" && r.optBoolean("gelesen") && behaelter.gekoppelt.value) {
                            scope.launch { runCatching { behaelter.melden("gelesen", JSONObject().put("kennung", weg.optString("kennung")).put("text", weg.optString("text").take(200))) } }
                        }
                        JSONObject()
                    }
                    "kamera" -> {
                        check(erlauben(Manifest.permission.CAMERA)) { "Erlaube die Kamera, um Fotos zu machen." }
                        activity.kameraOeffnen(if (r.optString("ziel") == "chat") "chat" else "galerie") ?: error("Abgebrochen")
                    }
                    "ki-katalog" -> Katalog.stand(activity)
                    "ki-laden" -> Katalog.herunterladen(activity, r.getString("name"))
                    "ki-aufraeumen" -> { adminNoetig(); Katalog.aufraeumen(activity) }
                    "ki-sparsam" -> { adminNoetig(); Katalog.sparsamSetzen(activity, r.optBoolean("an", true)) }
                    "sprachmodell" -> {
                        if (r.optBoolean("laden")) at.felworks.jon.device.VoskModell.anstossen(activity)
                        at.felworks.jon.device.VoskModell.stand(activity)
                    }
                    "ki-abbrechen" -> Katalog.abbrechen(activity, r.getString("name"))
                    "ki-loeschen" -> { adminNoetig(); Katalog.loeschen(activity, r.getString("name")) }
                    "ki-standard" -> {
                        val name = r.getString("name")
                        Katalog.standardSetzen(activity, name)
                        scope.launch { LokaleKi.vorladen(activity, name) }
                        Katalog.stand(activity)
                    }
                    "ki-token" -> { adminNoetig(); Katalog.tokenSetzen(activity, r.optString("token")); Katalog.stand(activity) }
                    "ki-aktualisieren" -> Katalog.aktualisieren(activity)
                    "ki-mobil" -> { Katalog.mobilSetzen(activity, r.optBoolean("an")); Katalog.stand(activity) }
                    "ki-stream" -> {
                        if (r.optString("motor") == "lokal" || r.optString("modell").isNotBlank()) at.felworks.jon.ki.Vorladen.genutzt(activity)
                        val inhalt = StringBuilder()
                        JonKern.antworten(activity, r).collect { teil ->
                            if (teil.optString("type") == "content") inhalt.append(teil.optString("delta"))
                            liefern(JSONObject().put("id", id).put("chunk", teil))
                        }
                        if (!at.felworks.jon.device.Sichtbarkeit.vorne) at.felworks.jon.device.Benachrichtigung.antwortFertig(activity, inhalt.toString())
                        JSONObject()
                    }
                    "hintergrund" -> {
                        if (r.has("an")) at.felworks.jon.device.JonHintergrund.setzen(activity, r.optBoolean("an"))
                        JSONObject().put("an", at.felworks.jon.device.JonHintergrund.aktiv(activity)).put("benachrichtigungen", at.felworks.jon.device.Benachrichtigung.erlaubt(activity))
                    }
                    "ki-stopp" -> { JonKern.stoppen(); JSONObject() }
                    "ki-entladen" -> { LokaleKi.entladen(); JSONObject() }
                    "solo" -> Solo.stand(activity)
                    "solo-setzen" -> { adminNoetig(); Solo.setzen(activity, r.optJSONObject("daten") ?: JSONObject()) }
                    "solo-schluessel" -> { adminNoetig(); Solo.schluesselSetzen(activity, r.getString("anbieter"), r.optString("schluessel")) }
                    "solo-modelle" -> JSONObject().put("modelle", Solo.modelle(activity, r.getString("anbieter")))
                    "weg" -> JSONObject().put("weg", JonKern.weg(activity, behaelter.gekoppelt.value, behaelter.verbindung.lage.value.draht != Draht.AUS).name.lowercase())
                        .put("solo", Solo.stand(activity)).put("lokal", Katalog.standard(activity) ?: JSONObject.NULL)
                    "profil" -> JSONObject().put("name", JonKern.name(activity))
                    "profil-setzen" -> { JonKern.nameSetzen(activity, r.optString("name")); JSONObject().put("name", JonKern.name(activity)) }
                    "freigabe" -> {
                        val prefs = activity.getSharedPreferences("jon-freigabe", android.content.Context.MODE_PRIVATE)
                        if (r.has("modus")) {
                            adminNoetig()
                            val modus = r.getString("modus")
                            require(modus in setOf("ask", "allow", "alles")) { "Unbekannte Freigabe." }
                            prefs.edit().putString("modus", modus).apply()
                        }
                        JSONObject().put("modus", prefs.getString("modus", "ask"))
                    }
                    "lokal-chats" -> JSONObject().put("chats", Gedaechtnis.chats(activity))
                    "lokal-chat" -> Gedaechtnis.chat(activity, r.getString("chat"))
                    "lokal-chat-speichern" -> Gedaechtnis.speichern(activity, r.getJSONObject("chat"))
                    "lokal-chat-loeschen" -> JSONObject().put("geloescht", Gedaechtnis.loeschen(activity, r.getString("chat")))
                    "gedaechtnis" -> JSONObject().put("fakten", org.json.JSONArray(Gedaechtnis.fakten(activity)))
                    "gedaechtnis-merken" -> Gedaechtnis.merken(activity, r.getString("fakt"))
                    "gedaechtnis-vergessen" -> JSONObject().put("fakten", Gedaechtnis.vergessen(activity, r.optInt("index", -1)))
                    "arbeit-liste" -> Arbeitsraum.liste(activity, r.optString("ordner"))
                    "arbeit-lesen" -> Arbeitsraum.lesen(activity, r.getString("pfad"))
                    "arbeit-datei" -> Arbeitsraum.inhaltBase64(activity, r.getString("pfad"))
                    "arbeit-export" -> Arbeitsraum.exportieren(activity, r.getString("pfad"))
                    "arbeit-loeschen" -> JSONObject().put("geloescht", Arbeitsraum.loeschen(activity, r.getString("pfad")))
                    "arbeit-zum-pi" -> {
                        check(behaelter.gekoppelt.value && behaelter.verbindung.lage.value.draht != Draht.AUS) { "Der Pi ist gerade nicht erreichbar." }
                        val datei = Arbeitsraum.datei(activity, r.getString("pfad"))
                        check(datei.isFile) { "Nur einzelne Dateien können auf den Pi." }
                        JSONObject().put("pfad", MedienAnalyse.piHochladen(behaelter, datei, datei.name, Arbeitsraum.mime(datei.name)) { text -> liefern(JSONObject().put("id", id).put("chunk", JSONObject().put("fortschritt", text))) })
                    }
                    "site" -> { activity.siteOeffnen(r.optString("quelle", "pi"), r.getString("pfad"), r.optString("titel")); JSONObject() }
                    "datei-waehlen" -> {
                        val liste = r.optJSONArray("typen")
                        val typen = if (liste != null && liste.length() > 0) Array(liste.length()) { liste.getString(it) } else arrayOf("*/*")
                        val uri = activity.dateiWaehlen(typen) ?: error("Abgebrochen")
                        val weg = JonKern.weg(activity, behaelter.gekoppelt.value, behaelter.verbindung.lage.value.draht != Draht.AUS)
                        val ziel = r.optString("ziel").ifBlank { if (weg == at.felworks.jon.ki.Weg.PI) "pi" else "handy" }
                        MedienAnalyse.verarbeiten(activity, behaelter, uri, ziel, weg) { text -> liefern(JSONObject().put("id", id).put("chunk", JSONObject().put("fortschritt", text))) }
                    }
                    "schritte" -> { Schritte.aktualisieren(activity); runCatching { Schritte.planen(activity) }; Schritte.stand(activity) }
                    "fitness" -> { Schritte.aktualisieren(activity); FitnessLokal.uebersicht(activity) }
                    "fitness-eintragen" -> FitnessLokal.eintragen(activity, r.optJSONObject("training") ?: JSONObject())
                    "fitness-loeschen" -> JSONObject().put("geloescht", FitnessLokal.loeschen(activity, r.getString("training")))
                    "fitness-ziele" -> FitnessLokal.zieleSetzen(activity, r.optInt("schritte", 0).takeIf { it > 0 }, r.optInt("wochen", 0).takeIf { it > 0 })
                    "uhr-befehl" -> Zeitregeln.uhrbefehl(r.optString("text"))?.let { JSONObject().put("antwort", Uhren.sprachbefehl(activity, it)) } ?: JSONObject()
                    "podcast" -> Podcast.erstellen(activity, r.optJSONObject("daten") ?: JSONObject())
                    "fotos" -> JSONObject().put("fotos", Fotos.liste(activity))
                    "foto" -> Fotos.laden(activity, r.getLong("foto"))
                    "foto-loeschen" -> JSONObject().put("geloescht", Fotos.loeschen(activity, r.getLong("foto")))
                    "sos" -> {
                        val m = GeraeteModus(activity)
                        val angerufen = withContext(Dispatchers.Main) { SosHilfe.anrufen(activity) }
                        val ort = runCatching { SosHilfe.standort(activity) }.getOrNull()
                        val daten = JSONObject().put("akku", akku.optInt("level", -1)).put("laedt", akku.optBoolean("charging"))
                            .put("kiosk", m.aktiv).put("modell", "${Build.MANUFACTURER} ${Build.MODEL}").put("zeit", System.currentTimeMillis())
                            .put("text", r.optString("text").take(300))
                        ort?.let { daten.put("lat", it.latitude).put("lon", it.longitude).put("genau", it.accuracy.toInt()) }
                        val versand = if (behaelter.gekoppelt.value) runCatching { behaelter.melden("sos", daten) }
                        else Result.failure(IllegalStateException("Jon ist mit keinem Rechner verbunden. Ruf direkt über WhatsApp an."))
                        if (versand.isFailure && !angerufen) throw versand.exceptionOrNull()!!
                        JSONObject().put("gesendet", versand.isSuccess).put("angerufen", angerufen).put("standort", ort != null)
                    }
                    "sprache" -> {
                        val neu = r.optString("setzen")
                        if (neu.isNotBlank()) at.felworks.jon.device.Sprache.setzen(activity, neu) else at.felworks.jon.device.Sprache.stand(activity)
                    }
                    "kinder" -> {
                        val neu = r.optJSONObject("setzen")
                        if (neu != null) { adminNoetig(); at.felworks.jon.device.KinderModus.setzen(activity, neu) } else at.felworks.jon.device.KinderModus.stand(activity)
                    }
                    "sos-einstellungen" -> {
                        val neu = r.optJSONObject("setzen")
                        if (neu != null) { adminNoetig(); SosHilfe.setzen(activity, neu) } else SosHilfe.einstellungen(activity)
                    }
                    "save-start" -> {
                        check(transfers.size < 3) { "Es laufen bereits Dateiübertragungen." }
                        val token = Krypto.kennung(12)
                        transfers[token] = File.createTempFile("jon-download-", ".tmp", activity.cacheDir)
                        JSONObject().put("transfer", token)
                    }
                    "save-chunk" -> {
                        val file = transfers[r.getString("transfer")] ?: error("Übertragung abgelaufen.")
                        val bytes = dekodieren(r.getString("data"))
                        check(bytes.size <= 400_000 && file.length() + bytes.size <= 32_000_000) { "Datei zu groß." }
                        file.appendBytes(bytes)
                        JSONObject()
                    }
                    "save-end" -> {
                        val file = transfers.remove(r.getString("transfer")) ?: error("Übertragung abgelaufen.")
                        try { speichern(r.getString("name"), r.optString("mime"), file.readBytes()) } finally { file.delete() }
                    }
                    "save-abort" -> { transfers.remove(r.getString("transfer"))?.delete(); JSONObject() }
                    "save" -> speichern(r.getString("name"), r.optString("mime", "application/octet-stream"), dekodieren(r.getString("data")))
                    else -> error("Unbekannte Aktion.")
                }
                liefern(JSONObject().put("id", id).put("result", result))
            } catch (e: CancellationException) { liefern(JSONObject().put("id", id).put("error", "Abgebrochen")) }
            catch (e: Exception) { liefern(JSONObject().put("id", id).put("error", e.message ?: "Das hat nicht funktioniert.")) }
            finally { jobs.remove(id) }
        }
        jobs[id] = job
        job.start()
    }

    private suspend fun admin(r: JSONObject): JSONObject {
        val schutz = GeraeteModus(activity).schutz
        return when (r.getString("aktion")) {
            "status" -> adminStand()
            "entsperren" -> {
                val ok = runCatching { schutz.pruefen(r.optString("pin")) }
                JSONObject().put("ok", ok.getOrDefault(false)).put("fehler", ok.exceptionOrNull()?.message ?: if (ok.getOrDefault(false)) "" else "Falsche PIN.")
            }
            "recovery" -> {
                val ok = runCatching { schutz.pruefen(r.optString("code"), true) }
                JSONObject().put("ok", ok.getOrDefault(false)).put("fehler", ok.exceptionOrNull()?.message ?: if (ok.getOrDefault(false)) "" else "Recovery-Code stimmt nicht.")
            }
            "einrichten" -> JSONObject().put("code", schutz.einrichten(r.getString("pin")))
            "bestaetigen" -> { schutz.recoveryBestaetigen(); adminStand() }
            "sperren" -> { schutz.sperren(); adminStand() }
            "finger" -> {
                val ok = runCatching { withContext(Dispatchers.Main) { at.felworks.jon.device.Fingerabdruck.entsperren(activity) } }
                if (ok.getOrDefault(false)) schutz.fingerFrei()
                JSONObject().put("ok", ok.getOrDefault(false)).put("fehler", ok.exceptionOrNull()?.message ?: if (ok.getOrDefault(false)) "" else "Abgebrochen.")
            }
            "finger-an" -> {
                adminNoetig()
                val ok = withContext(Dispatchers.Main) { at.felworks.jon.device.Fingerabdruck.einschalten(activity) }
                adminStand().put("ok", ok)
            }
            "finger-aus" -> { adminNoetig(); at.felworks.jon.device.Fingerabdruck.ausschalten(activity); adminStand() }
            else -> error("Unbekannte Aktion.")
        }
    }

    private fun system(ziel: String) {
        adminNoetig()
        val m = GeraeteModus(activity)
        check(!m.gesperrt) { "Verlasse zuerst den Kiosk, um Android-Einstellungen zu öffnen." }
        val intent = when (ziel) {
            "medien" -> Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
            "tailscale" -> activity.packageManager.getLaunchIntentForPackage(GeraeteApps.pakete.getValue("vpn")) ?: error("Tailscale ist nicht installiert.")
            "bluetooth" -> Intent(Settings.ACTION_BLUETOOTH_SETTINGS)
            "wlan" -> Intent(Settings.ACTION_WIFI_SETTINGS)
            "einstellungen" -> Intent(Settings.ACTION_SETTINGS)
            "nutzung" -> Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply { if (Build.VERSION.SDK_INT >= 29) data = Uri.parse("package:${activity.packageName}") }
            else -> error("Unbekanntes Ziel.")
        }
        runCatching { activity.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }.onFailure {
            if (ziel == "nutzung") activity.startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) else throw it
        }
    }

    private suspend fun koppeln(r: JSONObject): JSONObject {
        adminNoetig()
        check(!GeraeteModus(activity).gesperrt) { "Im aktiven Kiosk kann der Pi nicht gewechselt werden." }
        val qr = if (r.optString("art") == "qr") {
            check(erlauben(Manifest.permission.CAMERA)) { "Erlaube die Kamera, um den QR-Code zu scannen." }
            val roh = activity.qrScannen() ?: error("Scan abgebrochen.")
            QrNutzlast.lesen(roh) ?: error("Das ist kein Jon-Kopplungscode.")
        } else {
            val url = PiKopplung.adressePruefen(r.getString("adresse"))
            QrNutzlast.lesen(JSONObject().put("t", "jon-pair").put("n", "Dein Pi").put("c", r.getString("code")).put("u", url).put("direct_only", true).toString()) ?: error("Der Code braucht 12 Zeichen.")
        }
        val zugang = PiKopplung.verbinden(qr) { ereignis("pairing", JSONObject().put("text", it)) }
        behaelter.koppeln(zugang)
        runCatching { behaelter.verbindung.pruefen() }
        runCatching { at.felworks.jon.device.JonHintergrund.starten(activity) }
        return JSONObject().put("name", zugang.pcName)
    }

    private fun kopieren(text: String) {
        val clipboard = activity.getSystemService(android.content.ClipboardManager::class.java)
        clipboard.setPrimaryClip(android.content.ClipData.newPlainText("Jon", text))
    }

    private fun fuehlen(art: String) {
        activity.runOnUiThread {
            val konstante = when (art) {
                "success" -> if (Build.VERSION.SDK_INT >= 30) HapticFeedbackConstants.CONFIRM else HapticFeedbackConstants.VIRTUAL_KEY
                "error" -> if (Build.VERSION.SDK_INT >= 30) HapticFeedbackConstants.REJECT else HapticFeedbackConstants.LONG_PRESS
                "tick" -> HapticFeedbackConstants.CLOCK_TICK
                else -> HapticFeedbackConstants.VIRTUAL_KEY
            }
            web?.performHapticFeedback(konstante)
        }
    }

    private fun speichern(name: String, mime: String, daten: ByteArray): JSONObject {
        val sauber = name.substringAfterLast('/').substringAfterLast('\\').replace(Regex("[\\x00-\\x1f]"), "").take(150).ifBlank { "Jon-Datei" }
        check(daten.size <= 32_000_000) { "Datei zu groß." }
        if (Build.VERSION.SDK_INT >= 29) {
            val values = ContentValues().apply { put(MediaStore.Downloads.DISPLAY_NAME, sauber); put(MediaStore.Downloads.MIME_TYPE, mime.ifBlank { "application/octet-stream" }); put(MediaStore.Downloads.RELATIVE_PATH, "Download/Jon"); put(MediaStore.Downloads.IS_PENDING, 1) }
            val resolver = activity.contentResolver
            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: error("Speichern fehlgeschlagen.")
            try {
                resolver.openOutputStream(uri)?.use { it.write(daten) } ?: error("Datei nicht beschreibbar.")
                values.clear()
                values.put(MediaStore.Downloads.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            } catch (e: Exception) { resolver.delete(uri, null, null); throw e }
        } else File(activity.getExternalFilesDir(null), sauber).writeBytes(daten)
        return JSONObject().put("saved", sauber)
    }

    fun schliessen() {
        runCatching { activity.unregisterReceiver(akkuEmpfaenger) }
        transfers.values.forEach { it.delete() }
        transfers.clear()
        bereit = false
        scope.cancel()
        web?.removeJavascriptInterface("JonNative")
        web?.destroy()
        web = null
    }
}

@Composable
fun JonWeb(activity: MainActivity, behaelter: AppBehaelter, bruecke: JonWebBruecke) {
    var fileCallback by remember { mutableStateOf<ValueCallback<Array<Uri>>?>(null) }
    val chooser = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        fileCallback?.onReceiveValue(uri?.let { arrayOf(it) })
        fileCallback = null
    }
    val home by activity.home.collectAsState()
    LaunchedEffect(home) { if (home > 0) bruecke.home() }
    AndroidView(modifier = Modifier.fillMaxSize().imePadding(), factory = { context ->
        WebView(context).apply {
            layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
            setBackgroundColor(Color.BLACK)
            isHapticFeedbackEnabled = true
            overScrollMode = WebView.OVER_SCROLL_NEVER
            isVerticalScrollBarEnabled = false
            settings.useWideViewPort = true
            settings.loadWithOverviewMode = false
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            settings.javaScriptCanOpenWindowsAutomatically = false
            settings.setSupportMultipleWindows(false)
            settings.setSupportZoom(false)
            settings.builtInZoomControls = false
            settings.mediaPlaybackRequiresUserGesture = true
            settings.textZoom = 100
            addJavascriptInterface(bruecke, "JonNative")
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean = true
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                    val url = request.url
                    if (url.scheme == "https" && request.method == "GET" && url.host in KARTENSERVER) return null
                    if (url.scheme == "https" && url.host == "jon.local") {
                        val path = url.path.orEmpty().removePrefix("/").ifEmpty { "index.html" }
                        if (!path.contains("..") && !path.contains("\\")) {
                            val mime = when (path.substringAfterLast('.')) { "html" -> "text/html"; "js" -> "text/javascript"; "css" -> "text/css"; "svg" -> "image/svg+xml"; "png" -> "image/png"; "webp" -> "image/webp"; "woff2" -> "font/woff2"; else -> "application/octet-stream" }
                            runCatching { return WebResourceResponse(mime, "UTF-8", context.assets.open("device-web/$path")) }
                        }
                    }
                    return WebResourceResponse("text/plain", "UTF-8", 404, "Nicht vorhanden", emptyMap(), ByteArrayInputStream(byteArrayOf()))
                }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(view: WebView, callback: ValueCallback<Array<Uri>>, params: FileChooserParams): Boolean {
                    fileCallback?.onReceiveValue(null)
                    fileCallback = callback
                    runCatching { chooser.launch(arrayOf("*/*")) }.onFailure { callback.onReceiveValue(null); fileCallback = null }
                    return true
                }
            }
            if (activity.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE != 0) WebView.setWebContentsDebuggingEnabled(true)
            bruecke.web = this
            doOnLayout { loadUrl("https://jon.local/index.html") }
        }
    })
}
