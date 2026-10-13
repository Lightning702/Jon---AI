package at.felworks.jon.uhr

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.Locale

object Stimme : TextToSpeech.OnInitListener {
    private var sprecher: TextToSpeech? = null
    private var bereit = false
    private var wartend: String? = null

    fun an(context: Context): Boolean = context.getSharedPreferences("jon-uhr", Context.MODE_PRIVATE).getBoolean("vorlesen", true)

    fun setzen(context: Context, wert: Boolean) {
        context.getSharedPreferences("jon-uhr", Context.MODE_PRIVATE).edit().putBoolean("vorlesen", wert).apply()
        if (!wert) stopp()
    }

    fun starten(context: Context) {
        if (sprecher == null) sprecher = TextToSpeech(context.applicationContext, this)
    }

    override fun onInit(status: Int) {
        bereit = status == TextToSpeech.SUCCESS
        if (!bereit) return
        val deutsch = sprecher?.isLanguageAvailable(Locale.GERMAN) ?: TextToSpeech.LANG_NOT_SUPPORTED
        sprecher?.language = if (deutsch >= TextToSpeech.LANG_AVAILABLE) Locale.GERMAN else Locale.getDefault()
        wartend?.let { text -> wartend = null; sprechen(text) }
    }

    fun sauber(text: String): String = text
        .replace(Regex("```[\\s\\S]*?```"), " ")
        .replace(Regex("\\[([^\\]]+)]\\([^)]+\\)"), "$1")
        .replace(Regex("https?://\\S+"), "")
        .replace(Regex("[*_`#>|]"), "")
        .replace(Regex("\\s+"), " ")
        .trim()

    fun sprechen(text: String) {
        val kurz = sauber(text).take(3800)
        if (kurz.isBlank()) return
        if (!bereit) {
            wartend = kurz
            return
        }
        sprecher?.speak(kurz, TextToSpeech.QUEUE_FLUSH, null, "jon")
    }

    fun stopp() {
        wartend = null
        sprecher?.stop()
    }
}
