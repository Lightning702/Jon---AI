package at.felworks.jon.data.remote

import at.felworks.jon.domain.model.Draht
import at.felworks.jon.domain.model.Verbindungslage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONArray
import org.json.JSONObject

class JonVerbindung {
    private val mutex = Mutex()
    @Volatile private var zugang: Zugang? = null
    private var direkt: DirektTransport? = null
    private var geprueft = 0L
    private val _lage = MutableStateFlow(Verbindungslage())
    val lage: StateFlow<Verbindungslage> = _lage
    val aktuell: Zugang? get() = zugang

    fun anmelden(neu: Zugang?) {
        zugang = neu
        direkt?.schliessen()
        direkt = null
        geprueft = 0
        _lage.value = Verbindungslage(pcName = neu?.pcName.orEmpty())
    }

    private suspend fun verbinden(daten: Zugang, wartezeit: Long = 6000): Pair<DirektTransport, String>? {
        for (adresse in daten.alleAdressen.take(6)) {
            val weg = DirektTransport(adresse)
            try {
                val r = weg.senden(JSONObject().put("op", "ping").put("rid", Krypto.kennung(12)), "dev", daten.geraet, daten.schluessel, wartezeit)
                if (r.optBoolean("ok") && r.optJSONObject("pc")?.optString("id") == daten.pcId) return weg to adresse
            } catch (e: CancellationException) { weg.schliessen(); throw e }
            catch (_: Exception) { }
            weg.schliessen()
        }
        return null
    }

    private suspend fun transport(): Pair<DirektTransport, Zugang> = mutex.withLock {
        val daten = zugang ?: error("Verbinde Jon zuerst mit deinem Pi.")
        val aktuell = direkt
        if (aktuell != null && android.os.SystemClock.elapsedRealtime() - geprueft < 30_000) return@withLock aktuell to daten
        val gefunden = verbinden(daten)
        if (gefunden != null && zugang?.pcId == daten.pcId) {
            direkt?.schliessen()
            direkt = gefunden.first
            geprueft = android.os.SystemClock.elapsedRealtime()
            _lage.value = Verbindungslage(Draht.LOKAL, daten.pcName, adresse = gefunden.second)
            return@withLock gefunden.first to daten
        }
        gefunden?.first?.schliessen()
        _lage.value = Verbindungslage(pcName = daten.pcName, meldung = "${daten.pcName.ifBlank { "Jon" }} nicht erreichbar. WLAN oder Tailscale prüfen.")
        error(_lage.value.meldung)
    }

    suspend fun pruefen() { geprueft = 0; transport() }

    suspend fun erreichbar(ziel: Zugang): Boolean {
        val gefunden = verbinden(ziel, 4000) ?: return false
        gefunden.first.schliessen()
        return true
    }

    suspend fun einmalig(ziel: Zugang, anfrage: JSONObject, timeout: Long = 8000): JSONObject? {
        val gefunden = verbinden(ziel, 4000) ?: return null
        return try {
            gefunden.first.senden(anfrage.put("rid", Krypto.kennung(12)), "dev", ziel.geraet, ziel.schluessel, timeout)
        } catch (e: CancellationException) { throw e }
        catch (_: Exception) { null }
        finally { gefunden.first.schliessen() }
    }

    suspend fun geraeteOperation(anfrage: JSONObject, timeout: Long = 120_000): JSONObject {
        val (weg, daten) = transport()
        anfrage.put("rid", Krypto.kennung(12))
        val antwort = try { weg.senden(anfrage, "dev", daten.geraet, daten.schluessel, timeout) }
        catch (e: Exception) {
            if (e is CancellationException) throw e
            geprueft = 0
            _lage.value = Verbindungslage(pcName = daten.pcName, meldung = "Verbindung zu ${daten.pcName.ifBlank { "Jon" }} unterbrochen.")
            throw e
        }
        check(antwort.optBoolean("ok")) { antwort.optString("fehler", "Der Pi hat die Anfrage abgelehnt.") }
        return antwort
    }

    suspend fun objekt(methode: String, pfad: String, rumpf: JSONObject? = null): JSONObject {
        val r = geraeteOperation(JSONObject().put("op", "call").put("method", methode).put("path", pfad).put("body", rumpf))
        return JSONObject(r.optString("text", "{}"))
    }

    fun strom(pfad: String, rumpf: JSONObject) = flow {
        val (weg, daten) = transport()
        val anfrage = JSONObject().put("op", "stream").put("rid", Krypto.kennung(12)).put("method", "POST").put("path", pfad).put("body", rumpf)
        weg.strom(anfrage, "dev", daten.geraet, daten.schluessel).collect { teil ->
            check(teil.optBoolean("ok", true)) { teil.optString("fehler", "Verbindung unterbrochen.") }
            teil.optString("daten").takeIf { it.isNotEmpty() }?.let { emit(JSONObject(it)) }
        }
    }

    suspend fun abholen(): JSONArray = geraeteOperation(JSONObject().put("op", "warten").put("warten", 12), 30_000).optJSONArray("ereignisse") ?: JSONArray()
    suspend fun antworten(id: String, ok: Boolean, daten: JSONObject?, fehler: String) {
        geraeteOperation(JSONObject().put("op", "antwort").put("auftrag", id).put("ok", ok).put("daten", daten).put("fehler", fehler), 15_000)
    }
}
