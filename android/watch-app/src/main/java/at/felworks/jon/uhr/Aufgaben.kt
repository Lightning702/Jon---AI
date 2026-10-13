package at.felworks.jon.uhr

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.Ringtone
import android.media.RingtoneManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.VibratorManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import org.json.JSONObject

object Aufgaben {
    private const val KANAL = "jon-uhr"
    private const val KLINGEL_ID = 7301
    private val haupt = Handler(Looper.getMainLooper())
    private var ton: Ringtone? = null
    private var ende: Runnable? = null

    private fun kanal(context: Context) {
        val verwaltung = context.getSystemService(NotificationManager::class.java)
        verwaltung.createNotificationChannel(NotificationChannel(KANAL, "Jon", NotificationManager.IMPORTANCE_HIGH))
    }

    private fun darfMelden(context: Context): Boolean =
        Build.VERSION.SDK_INT < 33 || context.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    private fun oeffnen(context: Context, aktion: String, code: Int): PendingIntent =
        PendingIntent.getActivity(context, code, Intent(context, MainActivity::class.java).putExtra("aktion", aktion).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

    fun vibrieren(context: Context, muster: LongArray, wiederholen: Int = -1) {
        val geraet = context.getSystemService(VibratorManager::class.java)?.defaultVibrator ?: return
        if (!geraet.hasVibrator()) return
        geraet.vibrate(VibrationEffect.createWaveform(muster, wiederholen))
    }

    fun ausfuehren(context: Context, op: String, daten: JSONObject): JSONObject = when (op) {
        "durchsage" -> durchsage(context, daten)
        "klingeln" -> klingeln(context, daten.optInt("sekunden", 30).coerceIn(5, 120))
        "zustand" -> Jon.zustandDaten(context)
        else -> error("Das kann die Uhr nicht.")
    }

    fun durchsage(context: Context, daten: JSONObject): JSONObject {
        val text = daten.optString("text").replace(Regex("\\s+"), " ").trim().take(500)
        require(text.isNotEmpty()) { "Die Durchsage ist leer." }
        val von = daten.optString("von").trim().take(40).ifBlank { "Jon" }
        kanal(context)
        if (darfMelden(context)) {
            NotificationManagerCompat.from(context).notify(
                7300 + (text.hashCode() and 0xff),
                NotificationCompat.Builder(context, KANAL)
                    .setSmallIcon(R.drawable.jon_icon_mono)
                    .setContentTitle(von)
                    .setContentText(text)
                    .setStyle(NotificationCompat.BigTextStyle().bigText(text))
                    .setPriority(NotificationCompat.PRIORITY_HIGH)
                    .setCategory(NotificationCompat.CATEGORY_MESSAGE)
                    .setAutoCancel(true)
                    .setContentIntent(oeffnen(context, "zeigen", 7310))
                    .build(),
            )
        }
        vibrieren(context, longArrayOf(0, 180, 120, 180))
        if (daten.optBoolean("vorlesen", true) && Stimme.an(context)) {
            Stimme.starten(context)
            haupt.postDelayed({ Stimme.sprechen("$von sagt: $text") }, 500)
        }
        return JSONObject().put("angezeigt", true).put("kennung", daten.optString("kennung"))
    }

    fun klingeln(context: Context, sekunden: Int): JSONObject {
        stoppen(context)
        kanal(context)
        vibrieren(context, longArrayOf(0, 600, 300), 0)
        haupt.post {
            runCatching {
                val adresse = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM) ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
                ton = RingtoneManager.getRingtone(context.applicationContext, adresse)?.apply {
                    audioAttributes = AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build()
                    isLooping = true
                    play()
                }
            }
        }
        if (darfMelden(context)) {
            val stopp = PendingIntent.getBroadcast(context, 7320, Intent(context, KlingelStopp::class.java), PendingIntent.FLAG_IMMUTABLE)
            NotificationManagerCompat.from(context).notify(
                KLINGEL_ID,
                NotificationCompat.Builder(context, KANAL)
                    .setSmallIcon(R.drawable.jon_icon_mono)
                    .setContentTitle("Hier bin ich!")
                    .setContentText("Jon lässt deine Uhr klingeln.")
                    .setPriority(NotificationCompat.PRIORITY_MAX)
                    .setCategory(NotificationCompat.CATEGORY_ALARM)
                    .setOngoing(true)
                    .setContentIntent(oeffnen(context, "stopp", 7321))
                    .addAction(0, "Stopp", stopp)
                    .build(),
            )
        }
        val schluss = Runnable { stoppen(context) }
        ende = schluss
        haupt.postDelayed(schluss, sekunden * 1000L)
        return JSONObject().put("klingelt", true)
    }

    fun stoppen(context: Context) {
        ende?.let { haupt.removeCallbacks(it) }
        ende = null
        runCatching { ton?.stop() }
        ton = null
        context.getSystemService(VibratorManager::class.java)?.defaultVibrator?.cancel()
        NotificationManagerCompat.from(context).cancel(KLINGEL_ID)
    }
}

class KlingelStopp : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Aufgaben.stoppen(context)
    }
}
