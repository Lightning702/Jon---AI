package at.felworks.jon.device

import android.content.Context
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Handler
import android.os.Looper
import at.felworks.jon.data.remote.Krypto
import org.json.JSONObject

object Durchsage {
    fun zeigen(context: Context, daten: JSONObject): JSONObject {
        val text = daten.optString("text").trim().replace(Regex("\\s+"), " ").take(500)
        require(text.isNotEmpty()) { "Die Durchsage ist leer." }
        val kennung = daten.optString("kennung").filter { it.isLetterOrDigit() || it == '-' }.take(40).ifBlank { Krypto.kennung(8) }
        val von = daten.optString("von").trim().take(40).ifBlank { "Jon" }
        Anzeige.zeigen(
            JSONObject().put("art", "durchsage").put("id", "durchsage-$kennung").put("kennung", kennung)
                .put("text", text).put("von", von).put("seit", System.currentTimeMillis())
        )
        Anzeige.jonHolen(context, true)
        runCatching {
            val ton = ToneGenerator(AudioManager.STREAM_MUSIC, 80)
            ton.startTone(ToneGenerator.TONE_PROP_ACK, 260)
            Handler(Looper.getMainLooper()).postDelayed({ runCatching { ton.release() } }, 700)
        }
        if (daten.optBoolean("vorlesen", true)) {
            Handler(Looper.getMainLooper()).postDelayed({ runCatching { SprachDienst.vorlesen(context, Sprache.t(context, "Durchsage von $von. $text", "Announcement from $von. $text")) } }, 600)
        }
        return JSONObject().put("angezeigt", true).put("kennung", kennung)
    }
}
