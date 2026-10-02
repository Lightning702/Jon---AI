package at.felworks.jon.device

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.media.ToneGenerator
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import at.felworks.jon.MainActivity
import at.felworks.jon.R
import org.json.JSONObject

class KlingelDienst : Service() {
    private var player: MediaPlayer? = null
    private var ton: ToneGenerator? = null
    private var vibrator: Vibrator? = null
    private var wach: PowerManager.WakeLock? = null
    private var alteLautstaerke = -1
    private val handler = Handler(Looper.getMainLooper())
    private val piepen = object : Runnable {
        override fun run() {
            ton?.startTone(ToneGenerator.TONE_CDMA_ALERT_CALL_GUARD, 700)
            handler.postDelayed(this, 1200)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "stopp" -> { beenden(); return START_NOT_STICKY }
            "schlummern" -> { aktuell?.let { Uhren.schlummern(this, it.optString("titel")) }; beenden(); return START_NOT_STICKY }
        }
        val art = intent?.getStringExtra("art").takeIf { it in setOf("wecker", "timer", "suchen") } ?: "wecker"
        val titel = intent?.getStringExtra("titel").orEmpty().ifBlank { if (art == "suchen") "Hier bin ich!" else "Wecker" }
        val sekunden = intent?.getIntExtra("sekunden", 0)?.takeIf { it > 0 } ?: when (art) { "suchen" -> 30; "timer" -> 120; else -> 600 }
        try {
            if (Build.VERSION.SDK_INT >= 29) startForeground(4714, meldung(art, titel), ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
            else startForeground(4714, meldung(art, titel))
        } catch (e: RuntimeException) {
            stopSelf()
            return START_NOT_STICKY
        }
        stillLegen()
        laufend = this
        val eintrag = JSONObject().put("art", art).put("id", "klingeln").put("titel", titel).put("seit", System.currentTimeMillis())
        aktuell = eintrag
        Anzeige.zeigen(eintrag)
        wecken()
        abspielen(art == "suchen")
        vibrieren()
        handler.postDelayed({ beenden() }, sekunden * 1000L)
        Anzeige.jonHolen(this, true)
        return START_NOT_STICKY
    }

    private fun meldung(art: String, titel: String): Notification {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("jon-wecker", "Wecker, Timer und Suchen", NotificationManager.IMPORTANCE_HIGH).apply {
            setSound(null, null)
            enableVibration(false)
        })
        val oeffnen = PendingIntent.getActivity(this, 4715, Intent(this, MainActivity::class.java).putExtra("wecken", true).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val stopp = PendingIntent.getService(this, 4716, Intent(this, KlingelDienst::class.java).setAction("stopp"), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val builder = NotificationCompat.Builder(this, "jon-wecker").setSmallIcon(R.drawable.ic_hinweis)
            .setContentTitle(if (art == "suchen") "Jon wird gesucht" else titel)
            .setContentText(when (art) { "suchen" -> "Tippe auf Gefunden, um das Klingeln zu beenden."; "timer" -> "Die Zeit ist um."; else -> "Zeit aufzustehen." })
            .setCategory(NotificationCompat.CATEGORY_ALARM).setPriority(NotificationCompat.PRIORITY_MAX).setOngoing(true)
            .setFullScreenIntent(oeffnen, true).setContentIntent(oeffnen)
            .addAction(0, if (art == "suchen") "Gefunden" else "Stopp", stopp)
        if (art == "wecker") {
            val schlummern = PendingIntent.getService(this, 4717, Intent(this, KlingelDienst::class.java).setAction("schlummern"), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            builder.addAction(0, "Schlummern", schlummern)
        }
        return builder.build()
    }

    private fun wecken() {
        runCatching {
            val lock = getSystemService(PowerManager::class.java).newWakeLock(PowerManager.SCREEN_BRIGHT_WAKE_LOCK or PowerManager.ACQUIRE_CAUSES_WAKEUP, "jon:klingeln")
            lock.setReferenceCounted(false)
            lock.acquire(10 * 60_000L)
            wach = lock
        }
    }

    private fun abspielen(laut: Boolean) {
        val audio = getSystemService(AudioManager::class.java)
        if (laut) runCatching {
            alteLautstaerke = audio.getStreamVolume(AudioManager.STREAM_ALARM)
            audio.setStreamVolume(AudioManager.STREAM_ALARM, audio.getStreamMaxVolume(AudioManager.STREAM_ALARM), 0)
        }
        val attribute = AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build()
        val quellen = listOfNotNull(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM), RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE))
        for (quelle in quellen) {
            val p = MediaPlayer()
            val ok = runCatching {
                p.setAudioAttributes(attribute)
                p.setDataSource(this, quelle)
                p.isLooping = true
                p.prepare()
                p.start()
            }.isSuccess
            if (ok) { player = p; return }
            runCatching { p.release() }
        }
        runCatching {
            ton = ToneGenerator(AudioManager.STREAM_ALARM, 100)
            handler.post(piepen)
        }
    }

    private fun vibrieren() {
        runCatching {
            val v = if (Build.VERSION.SDK_INT >= 31) getSystemService(VibratorManager::class.java).defaultVibrator else getSystemService(Vibrator::class.java)
            val attribute = AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM).build()
            v.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 800, 700), 0), attribute)
            vibrator = v
        }
    }

    private fun stillLegen() {
        handler.removeCallbacksAndMessages(null)
        player?.let { p -> runCatching { p.stop() }; runCatching { p.release() } }
        player = null
        ton?.let { runCatching { it.release() } }
        ton = null
        vibrator?.let { runCatching { it.cancel() } }
        vibrator = null
        if (alteLautstaerke >= 0) {
            runCatching { getSystemService(AudioManager::class.java).setStreamVolume(AudioManager.STREAM_ALARM, alteLautstaerke, 0) }
            alteLautstaerke = -1
        }
    }

    fun beenden() {
        stillLegen()
        wach?.let { if (it.isHeld) runCatching { it.release() } }
        wach = null
        aktuell = null
        if (laufend === this) laufend = null
        Anzeige.entfernen("klingeln")
        runCatching { stopForeground(STOP_FOREGROUND_REMOVE) }
        stopSelf()
    }

    override fun onDestroy() {
        stillLegen()
        wach?.let { if (it.isHeld) runCatching { it.release() } }
        if (laufend === this) { laufend = null; aktuell = null; Anzeige.entfernen("klingeln") }
        super.onDestroy()
    }

    companion object {
        @Volatile var laufend: KlingelDienst? = null
        @Volatile var aktuell: JSONObject? = null

        fun starten(context: Context, art: String, titel: String, sekunden: Int = 0) {
            ContextCompat.startForegroundService(context, Intent(context, KlingelDienst::class.java).putExtra("art", art).putExtra("titel", titel).putExtra("sekunden", sekunden))
        }

        fun stoppen() {
            val dienst = laufend ?: return
            Handler(Looper.getMainLooper()).post { dienst.beenden() }
        }

        fun schlummern(context: Context) {
            val titel = aktuell?.optString("titel").orEmpty()
            Uhren.schlummern(context, titel)
            stoppen()
        }
    }
}
