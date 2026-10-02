package at.felworks.jon.ki

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.speech.tts.Voice
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeoutOrNull
import java.io.File
import java.util.Locale

object LokaleStimme {
    @Volatile private var tts: TextToSpeech? = null
    @Volatile private var bereit: CompletableDeferred<Boolean>? = null
    private val sperre = Mutex()

    private suspend fun motor(context: Context): TextToSpeech? {
        tts?.let { if (bereit?.isCompleted == true && bereit?.getCompleted() == true) return it }
        val warten = bereit ?: CompletableDeferred<Boolean>().also { neu ->
            bereit = neu
            tts = TextToSpeech(context.applicationContext) { status ->
                val ok = status == TextToSpeech.SUCCESS
                if (ok) tts?.language = at.felworks.jon.device.Sprache.locale(context)
                neu.complete(ok)
            }
        }
        val ok = withTimeoutOrNull(5000) { warten.await() } ?: false
        if (!ok) {
            runCatching { tts?.shutdown() }
            tts = null
            bereit = null
            return null
        }
        return tts
    }

    private fun deutscheStimmen(t: TextToSpeech, sprache: String): List<Voice> = runCatching {
        t.voices.orEmpty().filter { it.locale.language == sprache && !it.isNetworkConnectionRequired && "notinstalled" !in it.features.orEmpty() }.sortedBy { it.name }
    }.getOrDefault(emptyList())

    suspend fun datei(context: Context, text: String, sprecher: Int = 0): File? = sperre.withLock {
        val t = motor(context) ?: return@withLock null
        val stimmen = deutscheStimmen(t, at.felworks.jon.device.Sprache.code(context))
        if (stimmen.size > 1) {
            t.voice = stimmen[sprecher % stimmen.size]
            t.setPitch(1.0f)
        } else {
            runCatching { t.language = at.felworks.jon.device.Sprache.locale(context) }
            t.setPitch(if (sprecher % 2 == 1) 1.25f else 1.0f)
        }
        val ziel = File.createTempFile("jon-stimme", ".wav", context.cacheDir)
        val kennung = "jon-${System.nanoTime()}"
        val fertig = CompletableDeferred<Boolean>()
        t.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) { if (utteranceId == kennung) fertig.complete(true) }
            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String?) { if (utteranceId == kennung) fertig.complete(false) }
            override fun onError(utteranceId: String?, errorCode: Int) { if (utteranceId == kennung) fertig.complete(false) }
        })
        if (t.synthesizeToFile(text.take(3900), null, ziel, kennung) != TextToSpeech.SUCCESS) {
            ziel.delete()
            return@withLock null
        }
        val ok = withTimeoutOrNull(60_000) { fertig.await() } ?: false
        t.setPitch(1.0f)
        if (!ok || ziel.length() < 100) {
            ziel.delete()
            return@withLock null
        }
        ziel
    }
}
