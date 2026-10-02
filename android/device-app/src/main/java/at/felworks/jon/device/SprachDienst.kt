package at.felworks.jon.device

import android.Manifest
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.media.ToneGenerator
import android.media.audiofx.AcousticEchoCanceler
import android.media.audiofx.AudioEffect
import android.media.audiofx.NoiseSuppressor
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.os.SystemClock
import androidx.core.content.ContextCompat
import at.felworks.jon.JonApplication
import at.felworks.jon.MainActivity
import at.felworks.jon.connector.Verbinderrechte
import at.felworks.jon.connector.Verbindermeldung
import at.felworks.jon.data.remote.Krypto
import at.felworks.jon.domain.model.ChatNachricht
import at.felworks.jon.domain.model.Draht
import at.felworks.jon.domain.model.Rolle
import at.felworks.jon.domain.repository.ChatStueck
import at.felworks.jon.ki.JonKern
import at.felworks.jon.ki.LokaleStimme
import at.felworks.jon.ki.Solo
import at.felworks.jon.ki.Weg
import org.json.JSONArray
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.coroutines.resume
import kotlin.math.max
import kotlin.math.sqrt

enum class SprachPhase { IDLE, LISTENING, THINKING, SPEAKING, ERROR, OFFLINE, CONNECTING }

data class SprachZustand(
    val phase: SprachPhase = SprachPhase.IDLE,
    val text: String = "",
    val pegel: Float = 0f,
    val offen: Boolean = false,
    val freigabe: String? = null,
    val transkript: String = "",
    val modus: String = "",
    val teil: String = "",
    val nutzer: String = "",
    val freigabeText: String = "",
    val seq: Int = 0,
    val fehler: String = "",
    val stumm: Boolean = false,
) {
    fun json(): JSONObject = JSONObject().put("phase", phase.name).put("mode", when (modus) { "diktat" -> "dictate"; "gespraech" -> "talk"; else -> "" }).put("open", offen)
        .put("level", pegel.toDouble()).put("partial", teil).put("user", nutzer).put("text", text)
        .put("approval", freigabe ?: JSONObject.NULL).put("approvalText", freigabeText)
        .put("transcript", transkript).put("seq", seq).put("error", fehler).put("muted", stumm)
}

private enum class Modus { DIKTAT, GESPRAECH }

private class Aeusserung(val pcm: ByteArray, val lokal: String)

private class Mikro(val rec: AudioRecord, private val effekte: List<AudioEffect>, val gespraech: Boolean) {
    fun schliessen() {
        runCatching { rec.stop() }
        rec.release()
        effekte.forEach { runCatching { it.release() } }
    }
}

private class SatzTeiler {
    private val puffer = StringBuilder()
    private var erster = true

    fun hinzu(teil: String): List<String> {
        puffer.append(teil)
        val saetze = mutableListOf<String>()
        while (true) {
            val text = puffer.toString()
            if (text.split("```").size % 2 == 0 && text.length < 2400) break
            val grenze = grenze(text, if (erster) 16 else 55) ?: break
            val satz = text.substring(0, grenze).trim()
            puffer.delete(0, grenze)
            if (satz.isNotBlank()) { saetze += satz; erster = false }
        }
        return saetze
    }

    fun rest(): String? = puffer.toString().trim().ifBlank { null }.also { puffer.clear() }

    private fun grenze(text: String, minimum: Int): Int? {
        var i = minimum
        while (i < text.length) {
            val c = text[i]
            if (c == '\n' && i > 0) return i + 1
            if (c in ".!?…" && i + 1 < text.length && text[i + 1].isWhitespace()) return i + 1
            i++
        }
        if (text.length > 320) {
            val komma = text.lastIndexOf(", ", 300)
            return if (komma > minimum) komma + 1 else 300
        }
        return null
    }
}

class SprachDienst : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var lauf: Job? = null
    @Volatile private var wunsch: Modus? = null
    @Volatile private var abbrechen = false
    @Volatile private var fertig = false
    @Volatile private var unterbrechen = false
    @Volatile private var stumm = false
    @Volatile private var vorleseText: String? = null
    @Volatile private var spielt = false
    private var modell: Model? = null
    private var player: MediaPlayer? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var wakeBis = 0L
    private var fokus: AudioFocusRequest? = null
    private val behaelter get() = (application as JonApplication).behaelter
    @Volatile private var weg = Weg.PI
    @Volatile private var ruheBis = 0L
    private val eigenerVerlauf = mutableListOf<Pair<String, String>>()

    private fun wegPruefen(): Weg {
        weg = JonKern.weg(this, behaelter.gekoppelt.value, behaelter.verbindung.lage.value.draht != Draht.AUS)
        return weg
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val mikrofon = Verbinderrechte.erteilt(this, Manifest.permission.RECORD_AUDIO)
        when (intent?.action) {
            "abbrechen" -> {
                abbrechen = true
                wunsch = null
                vorleseText = null
                stoppen()
                melden { SprachZustand(seq = seq, stumm = stumm) }
                if (lauf?.isActive != true) stopSelf()
                return START_NOT_STICKY
            }
            "fertig" -> { fertig = true; return START_NOT_STICKY }
            "unterbrechen" -> { unterbrechen = true; stoppen(); return START_NOT_STICKY }
            "stumm" -> {
                stumm = intent.getBooleanExtra("stumm", false)
                melden { copy(stumm = stumm, pegel = 0f) }
                return START_NOT_STICKY
            }
            "vorlesen" -> vorleseText = intent.getStringExtra("text").orEmpty()
            "diktat" -> { if (!mikrofon) return verweigert(); wunsch = Modus.DIKTAT; abbrechen = true; stoppen() }
            "gespraech" -> { if (!mikrofon) return verweigert(); stumm = false; wunsch = Modus.GESPRAECH; abbrechen = true; stoppen() }
            else -> if (!mikrofon) return verweigert()
        }
        val meldung = Verbindermeldung.dienstMeldung(this, if (GeraeteModus(this).wakeWord) "„Hey Jon“ wird lokal erkannt" else "Sprache aktiv")
        try {
            val typ = if (mikrofon) ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE or ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK else ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
            if (Build.VERSION.SDK_INT >= 30) startForeground(4713, meldung, typ) else startForeground(4713, meldung)
        } catch (e: RuntimeException) {
            melden { SprachZustand(SprachPhase.ERROR, fehler = "Jon öffnen und Mikrofon erlauben, um die Sprache zu starten.", seq = seq) }
            stopSelf()
            return START_NOT_STICKY
        }
        if (lauf?.isActive != true) lauf = scope.launch { hauptschleife() }
        return if (GeraeteModus(this).wakeWord) START_STICKY else START_NOT_STICKY
    }

    private fun verweigert(): Int {
        melden { SprachZustand(SprachPhase.ERROR, fehler = "Mikrofon nicht erlaubt.", seq = seq) }
        if (lauf?.isActive != true) stopSelf()
        return START_NOT_STICKY
    }

    private fun melden(neu: SprachZustand.() -> SprachZustand) { _zustand.value = _zustand.value.neu() }

    private fun sollEnden() = abbrechen || wunsch != null

    private suspend fun hauptschleife() {
        try {
            wakeLock = getSystemService(PowerManager::class.java).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "jon:sprache").apply { setReferenceCounted(false) }
            cacheDir.listFiles { datei -> datei.name.startsWith("jon-stimme") }?.forEach { it.delete() }
            while (currentCoroutineContext().isActive) {
                wachHalten()
                val text = vorleseText
                if (text != null) {
                    vorleseText = null
                    abbrechen = false
                    unterbrechen = false
                    fokusAnfordern(false)
                    try { einzelnVorlesen(text) } finally { fokusFreigeben() }
                    continue
                }
                val neu = wunsch
                if (neu != null) {
                    wunsch = null
                    abbrechen = false
                    fertig = false
                    unterbrechen = false
                    when (neu) {
                        Modus.DIKTAT -> diktat()
                        Modus.GESPRAECH -> gespraech()
                    }
                    continue
                }
                abbrechen = false
                if (GeraeteModus(this).wakeWord && Verbinderrechte.erteilt(this, Manifest.permission.RECORD_AUDIO)) {
                    if (!VoskModell.vorhanden(this)) {
                        VoskModell.anstossen(this)
                        melden { SprachZustand(SprachPhase.IDLE, text = "„Hey Jon“ wird vorbereitet …", seq = seq, stumm = stumm) }
                        delay(3000)
                        continue
                    }
                    if (aufWakeWordWarten()) wunsch = Modus.GESPRAECH
                    continue
                }
                break
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            melden { SprachZustand(SprachPhase.ERROR, fehler = e.message ?: "Spracherkennung nicht verfügbar", seq = seq) }
        } finally {
            stoppen()
            fokusFreigeben()
            modell?.close()
            modell = null
            if (wakeLock?.isHeld == true) wakeLock?.release()
            if (_zustand.value.phase != SprachPhase.ERROR) melden { SprachZustand(seq = seq, stumm = stumm) }
            stopSelf()
        }
    }

    private fun wachHalten() {
        val jetzt = SystemClock.elapsedRealtime()
        if (wakeLock?.isHeld != true || jetzt >= wakeBis) {
            wakeLock?.acquire(10 * 60_000L)
            wakeBis = jetzt + 9 * 60_000L
        }
    }

    private fun modellLaden(): Model {
        modell?.let { return it }
        return Model(VoskModell.ordner(this).absolutePath).also { modell = it }
    }

    private fun mikrofon(gespraech: Boolean): Mikro {
        val groesse = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        check(groesse > 0) { "Audioformat wird nicht unterstützt." }
        val echo = gespraech && GeraeteModus(this).unterbrechen && AcousticEchoCanceler.isAvailable()
        val quelle = if (echo) MediaRecorder.AudioSource.VOICE_COMMUNICATION else MediaRecorder.AudioSource.VOICE_RECOGNITION
        val rec = AudioRecord(quelle, 16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, max(groesse, 16000))
        check(rec.state == AudioRecord.STATE_INITIALIZED) { "Mikrofon ist nicht verfügbar." }
        val effekte = mutableListOf<AudioEffect>()
        if (echo) {
            if (AcousticEchoCanceler.isAvailable()) AcousticEchoCanceler.create(rec.audioSessionId)?.let { it.enabled = true; effekte += it }
            if (NoiseSuppressor.isAvailable()) NoiseSuppressor.create(rec.audioSessionId)?.let { it.enabled = true; effekte += it }
        }
        rec.startRecording()
        return Mikro(rec, effekte, echo)
    }

    private fun mikrofonFrei(rec: AudioRecord): Boolean {
        val audio = getSystemService(AudioManager::class.java)
        if (audio.isMicrophoneMute || audio.mode == AudioManager.MODE_IN_CALL || audio.mode == AudioManager.MODE_IN_COMMUNICATION) return false
        return Build.VERSION.SDK_INT < 29 || rec.activeRecordingConfiguration?.isClientSilenced != true
    }

    private fun lautstaerke(frame: ShortArray, n: Int): Double {
        var summe = 0.0
        for (i in 0 until n) summe += frame[i].toDouble() * frame[i]
        return sqrt(summe / max(1, n))
    }

    private fun bytes(frame: ShortArray, n: Int): ByteArray {
        val puffer = ByteBuffer.allocate(n * 2).order(ByteOrder.LITTLE_ENDIAN)
        for (i in 0 until n) puffer.putShort(frame[i])
        return puffer.array()
    }

    private fun woerter(json: String, feld: String) = runCatching { JSONObject(json).optString(feld) }.getOrDefault("")

    private suspend fun erfassen(mikro: Mikro, erkenner: Recognizer?, stilleMs: Int, ohneSpracheMs: Int, maxMs: Int, vorlauf: List<ShortArray> = emptyList()): Aeusserung? {
        val aus = ByteArrayOutputStream()
        val frame = ShortArray(1600)
        val minimum = if (mikro.gespraech) 170.0 else 420.0
        val skala = if (mikro.gespraech) 1800.0 else 4200.0
        var gesprochen = false
        var beginn = 0
        var laut = 0
        var stille = 0
        var dauer = 0
        var boden = -1.0
        var fest = ""
        var teil = ""
        var gemeldet = 0L
        erkenner?.reset()
        fun verarbeiten(daten: ShortArray, n: Int) {
            val rms = if (stumm) 0.0 else lautstaerke(daten, n)
            if (boden < 0) boden = max(40.0, rms)
            val schwelle = max(minimum, boden * 3.0)
            val stimme = rms > schwelle
            if (!gesprochen && !stimme) boden = boden * 0.94 + rms * 0.06
            laut = if (stimme) laut + 1 else 0
            var neu = false
            if (erkenner != null && !stumm) {
                if (erkenner.acceptWaveForm(daten, n)) {
                    val satz = woerter(erkenner.result, "text")
                    if (satz.isNotBlank()) { fest = "$fest $satz".trim(); neu = true }
                    teil = ""
                } else {
                    val jetzt = woerter(erkenner.partialResult, "partial")
                    if (jetzt != teil) { if (jetzt.isNotBlank()) neu = true; teil = jetzt }
                }
            }
            if (!gesprochen && (laut >= 2 || ((fest + teil).length >= 3 && rms > boden * 1.6))) {
                gesprochen = true
                beginn = max(0, aus.size() - 6 * 3200)
            }
            aus.write(bytes(daten, n))
            if (gesprochen) stille = if (stimme || neu) 0 else stille + n * 1000 / 16000
            val zeit = SystemClock.elapsedRealtime()
            if (zeit - gemeldet > 90) {
                gemeldet = zeit
                val zeigen = (fest + " " + teil).trim()
                melden { copy(phase = SprachPhase.LISTENING, pegel = (rms / skala).toFloat().coerceIn(0f, 1f), teil = zeigen, stumm = stumm, fehler = "") }
            }
        }
        if (vorlauf.isNotEmpty()) {
            boden = 120.0
            vorlauf.forEach { verarbeiten(it, it.size) }
            gesprochen = true
        }
        while (!sollEnden()) {
            currentCoroutineContext().ensureActive()
            val n = mikro.rec.read(frame, 0, frame.size)
            check(n > 0) { "Das Mikrofon wurde unterbrochen." }
            if (!mikrofonFrei(mikro.rec)) {
                melden { copy(phase = SprachPhase.ERROR, fehler = "Mikrofon ist gerade durch eine andere App oder einen Anruf belegt.") }
                delay(250)
                continue
            }
            verarbeiten(frame, n)
            dauer += n * 1000 / 16000
            if (fertig) break
            if (gesprochen && stille >= stilleMs) break
            if (!gesprochen && dauer >= ohneSpracheMs) break
            if (dauer >= maxMs) break
        }
        if (erkenner != null) fest = (fest + " " + teil + " " + woerter(erkenner.finalResult, "text")).trim().replace(Regex("\\s+"), " ")
        if (fertig && fest.isNotBlank()) gesprochen = true
        melden { copy(pegel = 0f) }
        if (!gesprochen || abbrechen || wunsch != null) return null
        val alles = aus.toByteArray()
        return Aeusserung(alles.copyOfRange(beginn.coerceAtMost(alles.size), alles.size), fest)
    }

    private fun wav(pcm: ByteArray): ByteArray = ByteBuffer.allocate(44 + pcm.size).order(ByteOrder.LITTLE_ENDIAN)
        .put("RIFF".toByteArray()).putInt(36 + pcm.size).put("WAVEfmt ".toByteArray())
        .putInt(16).putShort(1).putShort(1).putInt(16000).putInt(32000).putShort(2).putShort(16)
        .put("data".toByteArray()).putInt(pcm.size).put(pcm).array()

    private suspend fun transkribieren(a: Aeusserung): String {
        val pcm = if (a.pcm.size > 16000 * 2 * 29) a.pcm.copyOf(16000 * 2 * 29) else a.pcm
        if (wegPruefen() != Weg.PI) {
            if (weg == Weg.SOLO) Solo.transkribieren(this, wav(pcm))?.let { return it }
            return a.lokal
        }
        val text = withTimeoutOrNull(40_000) {
            runCatching {
                behaelter.verbindung.geraeteOperation(JSONObject().put("op", "audio-stt").put("audio", Krypto.b64(wav(pcm))), 60_000).optString("text").trim()
            }.getOrElse { if (it is CancellationException) throw it; "" }
        }.orEmpty()
        return text.ifBlank { a.lokal }
    }

    private suspend fun diktat() {
        melden { SprachZustand(SprachPhase.LISTENING, modus = "diktat", offen = true, seq = seq, stumm = false) }
        var mikro: Mikro? = null
        var erkenner: Recognizer? = null
        try {
            erkenner = runCatching { Recognizer(modellLaden(), 16000f) }.getOrNull()
            mikro = mikrofon(false)
            fokusAnfordern(true)
            val a = erfassen(mikro, erkenner, 2200, 12_000, 29_000)
            mikro.schliessen()
            mikro = null
            if (a == null) { melden { SprachZustand(seq = seq) }; return }
            melden { copy(phase = SprachPhase.THINKING, pegel = 0f) }
            val text = if (behaelter.gekoppelt.value || Solo.an(this)) transkribieren(a) else a.lokal
            if (text.isBlank()) { melden { SprachZustand(SprachPhase.ERROR, fehler = "Ich habe nichts verstanden.", seq = seq) }; return }
            melden { SprachZustand(modus = "diktat", transkript = text, seq = seq + 1) }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            melden { SprachZustand(SprachPhase.ERROR, modus = "diktat", fehler = e.message ?: "Diktat fehlgeschlagen.", seq = seq) }
        } finally {
            mikro?.schliessen()
            erkenner?.close()
            fokusFreigeben()
        }
    }

    private suspend fun gespraech() {
        melden { SprachZustand(SprachPhase.CONNECTING, modus = "gespraech", offen = true, seq = seq, stumm = stumm) }
        eigenerVerlauf.clear()
        if (!behaelter.gekoppelt.value && wegPruefen() == Weg.PI) {
            melden { copy(phase = SprachPhase.OFFLINE, fehler = "Verbinde dein Gerät zuerst mit deinem Pi.") }
            delay(2500)
            melden { SprachZustand(seq = seq) }
            return
        }
        var mikro: Mikro? = null
        var erkenner: Recognizer? = null
        try {
            erkenner = runCatching { Recognizer(modellLaden(), 16000f) }.getOrNull()
            mikro = mikrofon(true)
            fokusAnfordern(false)
            var ruhig = 0
            var vorlauf: List<ShortArray> = emptyList()
            while (!sollEnden()) {
                melden { copy(phase = SprachPhase.LISTENING, teil = "", freigabe = null, fehler = "") }
                val a = erfassen(mikro, erkenner, 1100, 10_000, 28_000, vorlauf)
                vorlauf = emptyList()
                fertig = false
                if (sollEnden()) break
                if (a == null) { if (++ruhig >= 6) break; continue }
                ruhig = 0
                melden { copy(phase = SprachPhase.THINKING, nutzer = a.lokal, teil = "", text = "") }
                val text = transkribieren(a)
                if (text.isBlank()) {
                    melden { copy(phase = SprachPhase.ERROR, fehler = "Ich habe dich nicht verstanden.") }
                    delay(1200)
                    continue
                }
                melden { copy(nutzer = text) }
                vorlauf = antworten(text, mikro)
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            val offline = behaelter.verbindung.lage.value.draht == Draht.AUS
            melden { copy(phase = if (offline) SprachPhase.OFFLINE else SprachPhase.ERROR, fehler = e.message ?: "Sprachdialog fehlgeschlagen") }
            delay(2500)
        } finally {
            stoppen()
            mikro?.schliessen()
            erkenner?.close()
            fokusFreigeben()
            ruheBis = SystemClock.elapsedRealtime() + 4000
            if (wunsch == null) melden { SprachZustand(seq = seq, stumm = stumm) }
        }
    }

    private suspend fun antworten(frage: String, mikro: Mikro): List<ShortArray> = coroutineScope {
        unterbrechen = false
        val nutzer = ChatNachricht(Krypto.kennung(8), Rolle.NUTZER, frage, System.currentTimeMillis())
        val uhr = Zeitregeln.uhrbefehl(frage)
        if (uhr != null) {
            val antwort = runCatching { Uhren.sprachbefehl(this@SprachDienst, uhr) }.getOrElse { it.message ?: "Das ging gerade nicht." }
            melden { copy(phase = SprachPhase.SPEAKING, text = antwort) }
            tts(antwort)?.let { datei -> try { abspielen(datei) } finally { datei.delete() } }
            return@coroutineScope emptyList()
        }
        val lokal = GeraeteApps.sprachAktion(frage, GeraeteApps.liste(this@SprachDienst))
        if (lokal != null) {
            val antwort = runCatching {
                val ergebnis = withContext(Dispatchers.Main) { if (lokal.first == "amazon" && lokal.second != "oeffnen") GeraeteApps.musik(this@SprachDienst, lokal.second) else GeraeteApps.oeffnen(this@SprachDienst, lokal.first) }
                if (ergebnis.has("geoeffnet")) "${GeraeteApps.name(this@SprachDienst, lokal.first)} ist offen." else "Erledigt."
            }.getOrElse { it.message ?: "Das ging gerade nicht." }
            melden { copy(phase = SprachPhase.SPEAKING, text = antwort) }
            tts(antwort)?.let { datei -> try { abspielen(datei) } finally { datei.delete() } }
            if (lokal.second == "oeffnen") abbrechen = true
            return@coroutineScope emptyList()
        }
        val eigener = wegPruefen() != Weg.PI
        val bisher = if (eigener) emptyList() else runCatching { behaelter.chat.historie() }.getOrDefault(emptyList())
        if (!eigener) behaelter.chat.merken("aktiv", nutzer)
        val saetze = Channel<Deferred<File?>>(3)
        var antwort = ""
        var fehler = ""
        val strom = launch {
            val teiler = SatzTeiler()
            try {
                if (eigener) {
                    val anfrage = org.json.JSONObject().put("motor", if (weg == Weg.LOKAL) "lokal" else "solo").put("text", frage).put("modus", "chat").put("stimme", true)
                        .put("verlauf", JSONArray().apply { eigenerVerlauf.takeLast(12).forEach { (rolle, inhalt) -> put(org.json.JSONObject().put("role", rolle).put("content", inhalt)) } })
                    JonKern.antworten(this@SprachDienst, anfrage).collect { e ->
                        when (e.optString("type")) {
                            "content" -> {
                                val teil = e.optString("delta")
                                antwort += teil
                                melden { copy(text = antwort, freigabe = null) }
                                teiler.hinzu(teil).forEach { satz -> saetze.send(async { tts(satz) }) }
                            }
                            "tool" -> if (e.optString("status") == "running") melden { copy(text = if (antwort.isBlank()) e.optString("summary") else antwort) }
                            "error" -> error(e.optString("message"))
                        }
                    }
                } else behaelter.chat.fragen("", bisher + nutzer).collect { teil ->
                    when (teil) {
                        is ChatStueck.Text -> {
                            antwort += teil.teil
                            melden { copy(text = antwort, freigabe = null) }
                            teiler.hinzu(teil.teil).forEach { satz -> saetze.send(async { tts(satz) }) }
                        }
                        is ChatStueck.Fehler -> error(teil.text)
                        is ChatStueck.Werkzeug -> melden { copy(text = if (antwort.isBlank()) teil.zeile else antwort, freigabe = teil.freigabe, freigabeText = teil.zeile) }
                        else -> Unit
                    }
                }
                teiler.rest()?.let { satz -> saetze.send(async { tts(satz) }) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                fehler = e.message ?: "Jon konnte nicht antworten."
            } finally { saetze.close() }
        }
        var bargeIn: List<ShortArray> = emptyList()
        val waechter = if (GeraeteModus(this@SprachDienst).unterbrechen) launch(Dispatchers.IO) {
            bargeIn = lauschen(mikro)
            if (bargeIn.isNotEmpty()) { unterbrechen = true; stoppen() }
        } else null
        try {
            for (naechster in saetze) {
                if (unterbrechen || sollEnden()) break
                val datei = naechster.await() ?: continue
                try {
                    if (unterbrechen || sollEnden()) break
                    melden { copy(phase = SprachPhase.SPEAKING, freigabe = null) }
                    abspielen(datei)
                } finally { datei.delete() }
            }
            if (!unterbrechen && !sollEnden()) strom.join()
            if (fehler.isNotBlank() && !unterbrechen && !sollEnden()) {
                melden { copy(phase = SprachPhase.ERROR, fehler = fehler) }
                delay(1800)
            }
        } finally {
            withContext(NonCancellable) { waechter?.cancelAndJoin() }
            if (unterbrechen || sollEnden()) strom.cancel()
            saetze.cancel()
            if (antwort.isNotBlank()) {
                if (eigener) {
                    eigenerVerlauf += "user" to frage
                    eigenerVerlauf += "assistant" to antwort
                } else behaelter.chat.merken("aktiv", ChatNachricht(Krypto.kennung(8), Rolle.JON, antwort, System.currentTimeMillis()))
            }
        }
        if (unterbrechen && bargeIn.isEmpty()) melden { copy(text = "") }
        bargeIn
    }

    private suspend fun lauschen(mikro: Mikro): List<ShortArray> {
        val frame = ShortArray(1600)
        val zuletzt = ArrayDeque<ShortArray>()
        var boden = -1.0
        var echo = 0.0
        var echoFrames = 0
        var laut = 0
        while (currentCoroutineContext().isActive && !unterbrechen && !sollEnden()) {
            val n = mikro.rec.read(frame, 0, frame.size)
            if (n <= 0) break
            val kopie = frame.copyOf(n)
            zuletzt.addLast(kopie)
            while (zuletzt.size > 6) zuletzt.removeFirst()
            if (stumm) { laut = 0; continue }
            val rms = lautstaerke(kopie, n)
            if (boden < 0) boden = max(150.0, rms)
            val schwelle = if (spielt) {
                if (echoFrames < 6) { echo = max(echo, rms); echoFrames++; laut = 0; continue }
                max(2300.0, echo * 2.4)
            } else max(700.0, boden * 3.2)
            if (!spielt) { echoFrames = 0; echo = 0.0 }
            laut = if (rms > schwelle) laut + 1 else 0
            if (laut >= 4) return zuletzt.toList()
        }
        return emptyList()
    }

    private fun sprechbar(text: String): String = text
        .replace(Regex("```[\\s\\S]*?```"), " Den Code findest du im Chat. ")
        .replace(Regex("```[\\s\\S]*$"), " ")
        .replace(Regex("!\\[[^]]*]\\([^)]*\\)"), " ")
        .replace(Regex("\\[([^]]+)]\\([^)]*\\)"), "$1")
        .replace(Regex("https?://\\S+"), " Link ")
        .replace(Regex("`([^`]*)`"), "$1")
        .replace(Regex("(?m)^\\s{0,3}#{1,6}\\s*"), "")
        .replace(Regex("(?m)^\\s*[-*+]\\s+"), "")
        .replace(Regex("(?m)^\\s*\\|?[-: |]+\\|?\\s*$"), " ")
        .replace("|", ", ")
        .replace(Regex("[*_~>#]"), "")
        .replace(Regex("[\\uD800-\\uDFFF]"), "")
        .replace(Regex("\\s+"), " ")
        .trim()

    private suspend fun tts(text: String): File? {
        val sauber = sprechbar(text)
        if (sauber.length < 2) return null
        if (weg == Weg.PI && behaelter.gekoppelt.value && behaelter.verbindung.lage.value.draht != Draht.AUS) {
            runCatching {
                val r = behaelter.verbindung.geraeteOperation(JSONObject().put("op", "audio-tts").put("text", sauber.take(1200)), 60_000)
                File.createTempFile("jon-stimme", ".mp3", cacheDir).apply { writeBytes(Krypto.unb64(r.getString("audio"))) }
            }.getOrElse { if (it is CancellationException) throw it; null }?.let { return it }
        }
        if (weg == Weg.SOLO) Solo.sprechen(this, sauber)?.let { return it }
        return LokaleStimme.datei(this, sauber)
    }

    private suspend fun einzelnVorlesen(text: String) {
        wegPruefen()
        melden { SprachZustand(SprachPhase.SPEAKING, text = text.take(400), seq = seq) }
        try {
            val teiler = SatzTeiler()
            val saetze = teiler.hinzu(text.take(4000)) + listOfNotNull(teiler.rest())
            coroutineScope {
                val dateien = saetze.map { async { tts(it) } }
                for (d in dateien) {
                    if (abbrechen || unterbrechen || wunsch != null) break
                    val datei = d.await() ?: continue
                    try { abspielen(datei) } finally { datei.delete() }
                }
                dateien.forEach { it.cancel() }
            }
        } finally { melden { SprachZustand(seq = seq, stumm = stumm) } }
    }

    private suspend fun abspielen(datei: File) {
        val attribute = AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ASSISTANT).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
        withContext(Dispatchers.Main) {
            try {
                withTimeoutOrNull(120_000) {
                    suspendCancellableCoroutine { weiter ->
                        val p = MediaPlayer()
                        player = p
                        p.setAudioAttributes(attribute)
                        p.setDataSource(datei.absolutePath)
                        p.setOnCompletionListener { if (weiter.isActive) weiter.resume(Unit) }
                        p.setOnErrorListener { _, _, _ -> if (weiter.isActive) weiter.resume(Unit); true }
                        weiter.invokeOnCancellation { runCatching { p.stop() } }
                        p.prepare()
                        spielt = true
                        p.start()
                    }
                }
            } finally {
                spielt = false
                player?.release()
                player = null
            }
        }
    }

    private fun stoppen() {
        val p = player ?: return
        ContextCompat.getMainExecutor(this).execute { runCatching { if (p.isPlaying) p.stop() }; runCatching { p.reset() } }
    }

    private suspend fun aufWakeWordWarten(): Boolean {
        val erkenner = Recognizer(modellLaden(), 16000f, "[\"hey jon\",\"hey john\",\"hallo jon\",\"hallo john\",\"[unk]\"]").apply { setWords(true) }
        val mikro = mikrofon(false)
        melden { SprachZustand(SprachPhase.IDLE, text = "Sag „Hallo Jon“", seq = seq, stumm = stumm) }
        try {
            val frame = ShortArray(1600)
            var spitze = 0.0
            while (currentCoroutineContext().isActive && wunsch == null && vorleseText == null && GeraeteModus(this).wakeWord) {
                wachHalten()
                val n = mikro.rec.read(frame, 0, frame.size)
                check(n > 0) { "Das Mikrofon wurde unterbrochen." }
                if (!mikrofonFrei(mikro.rec)) { erkenner.reset(); spitze = 0.0; delay(300); continue }
                spitze = max(spitze, lautstaerke(frame, n))
                if (!erkenner.acceptWaveForm(frame, n)) continue
                val ergebnis = runCatching { JSONObject(erkenner.result) }.getOrNull()
                val lautGenug = spitze >= 650.0
                spitze = 0.0
                if (ergebnis == null || !weckwortErkannt(ergebnis) || !lautGenug) continue
                if (SystemClock.elapsedRealtime() < ruheBis) continue
                withContext(Dispatchers.Main) {
                    runCatching { startActivity(Intent(this@SprachDienst, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)) }
                }
                ToneGenerator(AudioManager.STREAM_MUSIC, 40).let { ton -> ton.startTone(ToneGenerator.TONE_PROP_BEEP, 80); delay(100); ton.release() }
                return true
            }
            return false
        } finally {
            mikro.schliessen()
            erkenner.close()
        }
    }

    private fun fokusAnfordern(ducken: Boolean) {
        val audio = getSystemService(AudioManager::class.java)
        val anfrage = AudioFocusRequest.Builder(if (ducken) AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK else AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ASSISTANT).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            .setOnAudioFocusChangeListener { wechsel -> if (wechsel == AudioManager.AUDIOFOCUS_LOSS || wechsel == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT) stoppen() }
            .build()
        audio.requestAudioFocus(anfrage)
        fokus = anfrage
    }

    private fun fokusFreigeben() {
        fokus?.let { getSystemService(AudioManager::class.java).abandonAudioFocusRequest(it) }
        fokus = null
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        private val weckwoerter = setOf("hey jon", "hey john", "hallo jon", "hallo john")

        fun weckwortErkannt(ergebnis: JSONObject): Boolean {
            if (ergebnis.optString("text").trim() !in weckwoerter) return false
            val woerter = ergebnis.optJSONArray("result") ?: return false
            if (woerter.length() != 2) return false
            val erstes = woerter.getJSONObject(0)
            val zweites = woerter.getJSONObject(1)
            if (erstes.optDouble("conf", 0.0) < 0.92 || zweites.optDouble("conf", 0.0) < 0.92) return false
            val dauer = zweites.optDouble("end") - erstes.optDouble("start")
            val luecke = zweites.optDouble("start") - erstes.optDouble("end")
            return dauer in 0.3..1.6 && luecke < 0.45
        }

        private val _zustand = MutableStateFlow(SprachZustand())
        val zustand: StateFlow<SprachZustand> = _zustand
        private val seq: Int get() = _zustand.value.seq

        private fun senden(context: Context, aktion: String, extra: Intent.() -> Unit = {}) {
            ContextCompat.startForegroundService(context, Intent(context, SprachDienst::class.java).setAction(aktion).apply(extra))
        }

        fun starten(context: Context, einmal: Boolean = false, diktieren: Boolean = false) {
            check(Verbinderrechte.erteilt(context, Manifest.permission.RECORD_AUDIO)) { "Mikrofonberechtigung fehlt." }
            senden(context, if (diktieren) "diktat" else if (einmal) "gespraech" else "starten")
        }

        fun befehl(context: Context, aktion: String, extra: Intent.() -> Unit = {}) {
            if (_zustand.value.let { !it.offen && it.phase == SprachPhase.IDLE } && aktion != "vorlesen" && !GeraeteModus(context).wakeWord) {
                if (aktion == "abbrechen") _zustand.value = SprachZustand(seq = seq)
                return
            }
            context.startService(Intent(context, SprachDienst::class.java).setAction(aktion).apply(extra))
        }

        fun vorlesen(context: Context, text: String) = senden(context, "vorlesen") { putExtra("text", text.take(4000)) }

        fun stoppen(context: Context) {
            context.stopService(Intent(context, SprachDienst::class.java))
            _zustand.value = SprachZustand(seq = seq)
        }

        fun schliessen(context: Context) = befehl(context, "abbrechen")
    }
}
