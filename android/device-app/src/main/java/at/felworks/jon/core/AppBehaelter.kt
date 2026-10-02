package at.felworks.jon.core

import android.content.Context
import android.os.Build
import at.felworks.jon.data.remote.*
import at.felworks.jon.data.repository.GeraeteChat
import at.felworks.jon.device.*
import at.felworks.jon.connector.Hinweisdienst
import at.felworks.jon.domain.model.Draht
import at.felworks.jon.ki.FitnessLokal
import at.felworks.jon.security.Tresor
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject

class AppBehaelter(private val context: Context) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var auftraege: Job? = null
    val tresor = Tresor(context)
    val verbindung = JonVerbindung()
    val chat = GeraeteChat(context, verbindung)
    private val _gekoppelt = MutableStateFlow(false)
    val gekoppelt: StateFlow<Boolean> = _gekoppelt
    private val _wechsel = MutableSharedFlow<JSONObject>(extraBufferCapacity = 4)
    val wechsel: SharedFlow<JSONObject> = _wechsel
    private val erledigt = AuftragsSpeicher(context)
    private var rechte = JSONObject()
    private val erreichbarkeit = java.util.concurrent.ConcurrentHashMap<String, Boolean>()

    init { tresor.aktiverZugang()?.let { starten(it) } }

    private fun prefs() = context.getSharedPreferences("jon-verbindung", Context.MODE_PRIVATE)

    fun automatisch(): Boolean = prefs().getBoolean("automatisch", true)

    fun automatischSetzen(an: Boolean) { prefs().edit().putBoolean("automatisch", an).apply() }

    fun aktiveId(): String = verbindung.aktuell?.pcId.orEmpty()

    fun koppeln(zugang: Zugang) {
        check(zugang.nurDirekt) { "Dieses Gerät verwendet ausschließlich LAN und Tailscale." }
        tresor.zugangHinzufuegen(zugang)
        starten(zugang)
    }

    @Synchronized
    private fun starten(zugang: Zugang) {
        auftraege?.cancel()
        if (verbindung.aktuell?.pcId != zugang.pcId) {
            rechte = JSONObject()
            chat.zuruecksetzen()
        }
        verbindung.anmelden(zugang)
        _gekoppelt.value = true
        auftraege = scope.launch {
            var rueckoff = 1000L
            var gemeldet = 0L
            var abgeglichen = 0L
            var fehler = 0
            while (isActive) {
                try {
                    if (android.os.SystemClock.elapsedRealtime() - gemeldet > 30_000 || gemeldet == 0L) {
                        val modus = GeraeteModus(context)
                        val sprachstand = SprachDienst.zustand.value
                        val battery = context.getSystemService(android.os.BatteryManager::class.java)
                        val zustand = JSONObject().put("name", "${Build.MANUFACTURER} ${Build.MODEL}")
                            .put("akku", battery.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY))
                            .put("device_owner", modus.eigentuemer).put("kiosk", modus.gesperrt)
                            .put("wake_word", modus.wakeWord).put("sprach_status", sprachstand.phase.name.lowercase())
                            .put("amazon", GeraeteApps.installiert(context, "amazon"))
                            .put("tiktok", GeraeteApps.installiert(context, "tiktok"))
                            .put("whatsapp", GeraeteApps.installiert(context, "whatsapp"))
                            .put("apps", org.json.JSONArray().apply { GeraeteApps.liste(context).forEach { put(JSONObject().put("id", it.id).put("name", it.name)) } })
                            .put("bildschirmzeit", runCatching { Bildschirmzeit.stand(context) }.getOrNull() ?: JSONObject.NULL)
                            .put("wecker", Uhren.naechsterText(context) ?: JSONObject.NULL)
                            .put("version", runCatching { context.packageManager.getPackageInfo(context.packageName, 0).versionName }.getOrNull().orEmpty())
                            .put("schritte", Schritte.heute(context))
                            .put("kinder", at.felworks.jon.device.KinderModus.stand(context))
                        val faehigkeiten = mutableListOf("status", "apps", "durchsage", "klingeln", "regeln")
                        if (Hinweisdienst.aktiv(context)) faehigkeiten += "musik"
                        val r = verbindung.geraeteOperation(JSONObject().put("op", "zustand").put("zustand", zustand).put("faehigkeiten", JSONArray(faehigkeiten)), 15_000)
                        rechte = r.optJSONObject("rechte") ?: JSONObject()
                        gemeldet = android.os.SystemClock.elapsedRealtime()
                    }
                    if (android.os.SystemClock.elapsedRealtime() - abgeglichen > 600_000 || abgeglichen == 0L) {
                        abgeglichen = android.os.SystemClock.elapsedRealtime()
                        runCatching {
                            Schritte.aktualisieren(context)
                            val offen = FitnessLokal.ausstehend(context)
                            val antwort = verbindung.objekt("POST", "/api/fitness/sync", JSONObject().put("schritte", Schritte.tage(context, 30))
                                .put("trainings", offen.getJSONArray("trainings")).put("geloescht", offen.getJSONArray("geloescht")).put("quelle", "handy"))
                            FitnessLokal.abgeglichen(context, antwort.optJSONArray("trainings") ?: JSONArray())
                        }
                    }
                    val events = verbindung.abholen()
                    for (i in 0 until events.length()) {
                        val e = events.getJSONObject(i)
                        when (e.optString("art")) {
                            "rechte" -> { rechte = e.optJSONObject("daten")?.optJSONObject("rechte") ?: rechte }
                            "auftrag" -> e.optJSONObject("daten")?.let { ausfuehren(it) }
                        }
                    }
                    rueckoff = 1000
                    fehler = 0
                } catch (e: CancellationException) { throw e }
                catch (_: Exception) {
                    fehler++
                    if (fehler >= 3 && automatisch() && ausweichen(zugang)) return@launch
                    delay(rueckoff + kotlin.random.Random.nextLong(400))
                    rueckoff = (rueckoff * 2).coerceAtMost(60_000)
                    gemeldet = 0
                }
            }
        }
    }

    private suspend fun ausweichen(ausgefallen: Zugang): Boolean {
        for (anderer in tresor.zugaenge().filter { it.pcId != ausgefallen.pcId }) {
            if (!verbindung.erreichbar(anderer)) continue
            tresor.aktivSetzen(anderer.pcId)
            _wechsel.tryEmit(JSONObject().put("von", ausgefallen.pcName).put("zu", anderer.pcName).put("id", anderer.pcId).put("automatisch", true))
            scope.launch { starten(anderer) }
            return true
        }
        return false
    }

    fun wechseln(pcId: String) {
        val ziel = tresor.zugaenge().firstOrNull { it.pcId == pcId } ?: error("Diesen Jon kennt das Handy nicht.")
        val vorher = verbindung.aktuell?.pcName.orEmpty()
        tresor.aktivSetzen(pcId)
        starten(ziel)
        _wechsel.tryEmit(JSONObject().put("von", vorher).put("zu", ziel.pcName).put("id", ziel.pcId).put("automatisch", false))
    }

    fun server(): JSONArray {
        val aktiv = aktiveId()
        val lage = verbindung.lage.value
        return JSONArray().apply {
            tresor.zugaenge().forEach { z ->
                val istAktiv = z.pcId == aktiv
                val erreichbar: Any = if (istAktiv) lage.draht != Draht.AUS else erreichbarkeit[z.pcId] ?: JSONObject.NULL
                put(JSONObject().put("id", z.pcId).put("name", z.pcName.ifBlank { "Jon" }).put("adresse", z.alleAdressen.firstOrNull().orEmpty())
                    .put("aktiv", istAktiv).put("erreichbar", erreichbar))
            }
        }
    }

    suspend fun serverPruefen(): JSONArray = coroutineScope {
        val aktiv = aktiveId()
        tresor.zugaenge().filter { it.pcId != aktiv }.map { z -> async { z.pcId to verbindung.erreichbar(z) } }.awaitAll()
            .forEach { (id, ok) -> erreichbarkeit[id] = ok }
        if (aktiv.isNotBlank()) runCatching { verbindung.pruefen() }
        server()
    }

    private suspend fun ausfuehren(daten: JSONObject) {
        val id = daten.optString("auftrag")
        if (id.isBlank() || id.length > 128) return
        val result = runCatching {
            check(erledigt.vormerken(id)) { "Auftrag wurde bereits bearbeitet." }
            val op = daten.optString("op")
            val recht = when (op) {
                "app-oeffnen" -> "apps"; "musik" -> "musik"; "zustand" -> "status"
                "durchsage" -> "durchsage"; "klingeln" -> "klingeln"; "regeln" -> "regeln"; "zeitantwort" -> "regeln"
                else -> error("Dieser Auftrag ist nicht erlaubt.")
            }
            check(rechte.optBoolean(recht, false)) { "Funktion ist auf dem Pi nicht freigegeben." }
            withContext(Dispatchers.Main) {
                when (op) {
                    "app-oeffnen" -> GeraeteApps.oeffnen(context, daten.optString("app"))
                    "musik" -> GeraeteApps.musik(context, daten.optString("aktion"))
                    "durchsage" -> Durchsage.zeigen(context, daten)
                    "klingeln" -> {
                        KlingelDienst.starten(context, "suchen", "Hier bin ich!", daten.optInt("sekunden", 30).coerceIn(5, 120))
                        JSONObject().put("klingelt", true)
                    }
                    "regeln" -> withContext(Dispatchers.IO) { Bildschirmzeit.setzen(context, daten) }
                    "zeitantwort" -> withContext(Dispatchers.IO) { Bildschirmzeit.antwort(context, daten) }
                    else -> JSONObject().put("kiosk", GeraeteModus(context).gesperrt).put("name", Build.MODEL)
                        .put("bildschirmzeit", runCatching { Bildschirmzeit.stand(context) }.getOrNull() ?: JSONObject.NULL)
                }
            }
        }
        if (result.exceptionOrNull() is CancellationException) throw result.exceptionOrNull()!!
        verbindung.antworten(id, result.isSuccess, result.getOrNull(), result.exceptionOrNull()?.message.orEmpty())
    }

    suspend fun melden(art: String, daten: JSONObject): JSONObject =
        verbindung.geraeteOperation(JSONObject().put("op", "melden").put("art", art).put("daten", daten), 20_000)

    private fun verwaltungFrei() {
        check(!GeraeteModus(context).aktiv && (!AdminSchutz(context).eingerichtet || AdminSchutz(context).frei)) { "Zuerst Verwaltung entsperren und Kiosk verlassen." }
    }

    suspend fun entfernen(pcId: String) {
        verwaltungFrei()
        val weg = tresor.zugaenge().firstOrNull { it.pcId == pcId } ?: error("Diesen Jon kennt das Handy nicht.")
        runCatching { withTimeoutOrNull(8_000) { verbindung.einmalig(weg, JSONObject().put("op", "abmelden")) } }
        val warAktiv = pcId == aktiveId()
        val naechster = tresor.zugangEntfernen(pcId)
        erreichbarkeit.remove(pcId)
        if (!warAktiv) return
        if (naechster != null) {
            starten(naechster)
            _wechsel.tryEmit(JSONObject().put("von", weg.pcName).put("zu", naechster.pcName).put("id", naechster.pcId).put("automatisch", false))
        } else {
            auftraege?.cancel()
            verbindung.anmelden(null)
            _gekoppelt.value = false
        }
    }

    suspend fun entkoppeln() {
        val aktiv = aktiveId()
        if (aktiv.isBlank()) { verwaltungFrei(); return }
        entfernen(aktiv)
    }

    suspend fun ueberallAbmelden() {
        for (z in tresor.zugaenge()) runCatching { withTimeoutOrNull(8_000) { verbindung.einmalig(z, JSONObject().put("op", "abmelden")) } }
    }
}
