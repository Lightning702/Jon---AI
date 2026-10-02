package at.felworks.jon.device

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import at.felworks.jon.MainActivity
import at.felworks.jon.R

object Sichtbarkeit {
    @Volatile var vorne: Boolean = false
}

object Benachrichtigung {
    const val DIENST = "jon-dienst"
    const val CHAT = "jon-chat"
    const val FERTIG = "jon-fertig"
    const val FAMILIE = "jon-familie"

    fun kanaele(context: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        val nm = context.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(DIENST, Sprache.t(context, "Jon im Hintergrund", "Jon in the background"), NotificationManager.IMPORTANCE_MIN).apply { setShowBadge(false) })
        nm.createNotificationChannel(NotificationChannel(CHAT, "Jon Chat", NotificationManager.IMPORTANCE_HIGH))
        nm.createNotificationChannel(NotificationChannel(FERTIG, Sprache.t(context, "Antworten von Jon", "Answers from Jon"), NotificationManager.IMPORTANCE_DEFAULT))
        nm.createNotificationChannel(NotificationChannel(FAMILIE, Sprache.t(context, "Familie", "Family"), NotificationManager.IMPORTANCE_HIGH))
    }

    fun erlaubt(context: Context): Boolean =
        Build.VERSION.SDK_INT < 33 || context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    private fun oeffnen(context: Context, seite: String, code: Int): PendingIntent =
        PendingIntent.getActivity(context, code, Intent(context, MainActivity::class.java).putExtra("oeffnen", seite).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

    fun dienst(context: Context): Notification {
        kanaele(context)
        return NotificationCompat.Builder(context, DIENST)
            .setSmallIcon(R.drawable.jon_benachrichtigung)
            .setContentTitle(Sprache.t(context, "Jon ist verbunden", "Jon is connected"))
            .setContentText(Sprache.t(context, "Durchsagen, Nachrichten und Erinnerungen kommen auch bei geschlossener App an.", "Announcements, messages and reminders arrive even when the app is closed."))
            .setOngoing(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setContentIntent(oeffnen(context, "", 4900))
            .build()
    }

    private fun zeigen(context: Context, kennung: Int, notiz: Notification) {
        if (!erlaubt(context)) return
        runCatching { NotificationManagerCompat.from(context).notify(kennung, notiz) }
    }

    fun jonChat(context: Context, titel: String, text: String, schluessel: String) {
        kanaele(context)
        zeigen(context, 4910 + (schluessel.hashCode() and 0xfff), NotificationCompat.Builder(context, CHAT)
            .setSmallIcon(R.drawable.jon_benachrichtigung)
            .setContentTitle(titel)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(oeffnen(context, "jonchat", 4911))
            .build())
    }

    fun antwortFertig(context: Context, text: String) {
        val kurz = text.replace(Regex("[*_`#>]"), "").replace(Regex("\\s+"), " ").trim().take(240)
        if (kurz.isBlank()) return
        kanaele(context)
        zeigen(context, 4920, NotificationCompat.Builder(context, FERTIG)
            .setSmallIcon(R.drawable.jon_benachrichtigung)
            .setContentTitle(Sprache.t(context, "Jon ist fertig", "Jon is done"))
            .setContentText(kurz)
            .setStyle(NotificationCompat.BigTextStyle().bigText(kurz))
            .setAutoCancel(true)
            .setContentIntent(oeffnen(context, "chat", 4921))
            .build())
    }

    fun familie(context: Context, titel: String, text: String, seite: String = "zeit") {
        kanaele(context)
        zeigen(context, 4930 + (titel.hashCode() and 0xff), NotificationCompat.Builder(context, FAMILIE)
            .setSmallIcon(R.drawable.jon_benachrichtigung)
            .setContentTitle(titel)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(oeffnen(context, seite, 4931))
            .build())
    }
}
