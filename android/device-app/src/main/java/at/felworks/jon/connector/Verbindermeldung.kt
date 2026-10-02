package at.felworks.jon.connector

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import at.felworks.jon.MainActivity
import at.felworks.jon.R

object Verbindermeldung {
    fun dienstMeldung(context: Context, text: String): Notification {
        context.getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel("jon-sprache", "Lokale Sprachaktivierung", NotificationManager.IMPORTANCE_LOW))
        val intent = PendingIntent.getActivity(context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(context, "jon-sprache").setSmallIcon(R.drawable.ic_hinweis)
            .setContentTitle("Jon · lokale Spracherkennung").setContentText(text).setOngoing(true).setContentIntent(intent).build()
    }
}
