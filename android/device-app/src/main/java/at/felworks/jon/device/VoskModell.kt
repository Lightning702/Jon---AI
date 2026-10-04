package at.felworks.jon.device

import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.TimeUnit
import java.util.zip.ZipInputStream

object VoskModell {
    private const val QUELLE = "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip"
    private const val PRUEFSUMME = "b7e53c90b1f0a38456f4cd62b366ecd58803cd97cd42b06438e2c131713d5e43"
    private const val GROESSE_MB = 45
    private val bereich = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    @Volatile private var laeuft: Job? = null
    @Volatile private var fortschritt = 0.0
    @Volatile private var fehler = ""

    private fun ziel(context: Context) = File(context.filesDir, "vosk-de")

    fun vorhanden(context: Context): Boolean = File(ziel(context), "bereit").exists()

    fun ordner(context: Context): File {
        if (!vorhanden(context)) {
            anstossen(context)
            error("Das Sprachmodell für Live-Text wird gerade geladen ($GROESSE_MB MB).")
        }
        return ziel(context)
    }

    fun anstossen(context: Context) {
        if (vorhanden(context) || laeuft?.isActive == true) return
        val app = context.applicationContext
        laeuft = bereich.launch {
            runCatching { laden(app) }.onFailure { fehler = it.message ?: "Das Sprachmodell ließ sich nicht laden." }
        }
    }

    fun stand(context: Context): JSONObject = JSONObject()
        .put("bereit", vorhanden(context))
        .put("laedt", laeuft?.isActive == true)
        .put("fortschritt", fortschritt)
        .put("fehler", fehler)
        .put("groesse_mb", GROESSE_MB)

    fun loeschen(context: Context) {
        if (laeuft?.isActive == true) return
        ziel(context).deleteRecursively()
    }

    private fun laden(context: Context) {
        fehler = ""
        fortschritt = 0.0
        val paket = File(context.cacheDir, "vosk-de.zip")
        val klient = OkHttpClient.Builder().connectTimeout(20, TimeUnit.SECONDS).readTimeout(60, TimeUnit.SECONDS).build()
        try {
            klient.newCall(Request.Builder().url(QUELLE).build()).execute().use { antwort ->
                check(antwort.isSuccessful) { "Das Sprachmodell ließ sich nicht laden (Fehler ${antwort.code})." }
                val gesamt = antwort.body.contentLength()
                val pruefer = MessageDigest.getInstance("SHA-256")
                paket.outputStream().use { aus ->
                    antwort.body.byteStream().use { ein ->
                        val puffer = ByteArray(64 * 1024)
                        var summe = 0L
                        while (true) {
                            val n = ein.read(puffer)
                            if (n < 0) break
                            aus.write(puffer, 0, n)
                            pruefer.update(puffer, 0, n)
                            summe += n
                            if (gesamt > 0) fortschritt = (summe.toDouble() / gesamt).coerceAtMost(0.99)
                        }
                    }
                }
                val summe = pruefer.digest().joinToString("") { "%02x".format(it) }
                check(summe == PRUEFSUMME) { "Das geladene Sprachmodell ist beschädigt. Bitte nochmal versuchen." }
            }
            val neu = File(context.filesDir, "vosk-de.neu").apply { deleteRecursively(); mkdirs() }
            val basis = neu.canonicalPath + File.separator
            ZipInputStream(paket.inputStream().buffered()).use { zip ->
                var eintrag = zip.nextEntry
                while (eintrag != null) {
                    val name = eintrag.name.substringAfter('/', "")
                    if (name.isNotBlank()) {
                        val datei = File(neu, name).canonicalFile
                        check(datei.path.startsWith(basis)) { "Das Sprachmodell enthält ungültige Pfade." }
                        if (eintrag.isDirectory) datei.mkdirs()
                        else {
                            datei.parentFile?.mkdirs()
                            datei.outputStream().use { zip.copyTo(it) }
                        }
                    }
                    eintrag = zip.nextEntry
                }
            }
            check(File(neu, "am/final.mdl").isFile && File(neu, "graph/HCLr.fst").isFile) { "Das Sprachmodell ist unvollständig." }
            File(neu, "bereit").writeText("1")
            val alt = ziel(context)
            alt.deleteRecursively()
            check(neu.renameTo(alt)) { "Das Sprachmodell ließ sich nicht speichern." }
            fortschritt = 1.0
        } finally {
            paket.delete()
            File(context.filesDir, "vosk-de.neu").deleteRecursively()
        }
    }

    fun transkribieren(context: Context, pcm: java.io.File, fortschritt: (Double) -> Unit = {}): String {
        val modell = Model(ordner(context).absolutePath)
        try {
            val erkenner = Recognizer(modell, 16000f)
            try {
                val saetze = mutableListOf<String>()
                val gesamt = pcm.length().coerceAtLeast(1)
                var gelesen = 0L
                var runde = 0
                val puffer = ByteArray(16000)
                pcm.inputStream().buffered(1 shl 16).use { eingabe ->
                    while (true) {
                        var n = 0
                        while (n < puffer.size) {
                            val r = eingabe.read(puffer, n, puffer.size - n)
                            if (r < 0) break
                            n += r
                        }
                        if (n <= 0) break
                        if (erkenner.acceptWaveForm(puffer, n)) {
                            JSONObject(erkenner.result).optString("text").takeIf { it.isNotBlank() }?.let { saetze += it }
                        }
                        gelesen += n
                        if (++runde % 20 == 0) fortschritt(gelesen.toDouble() / gesamt)
                        if (n < puffer.size) break
                    }
                }
                JSONObject(erkenner.finalResult).optString("text").takeIf { it.isNotBlank() }?.let { saetze += it }
                return saetze.joinToString(". ") { satz -> satz.replaceFirstChar { it.uppercase() } }.let { if (it.isNotBlank()) "$it." else it }
            } finally { erkenner.close() }
        } finally { modell.close() }
    }
}
