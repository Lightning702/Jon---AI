package at.felworks.jon.connector

import android.content.Context
import android.service.notification.NotificationListenerService
import androidx.core.app.NotificationManagerCompat

class Hinweisdienst : NotificationListenerService() {
    companion object {
        fun aktiv(context: Context): Boolean = NotificationManagerCompat.getEnabledListenerPackages(context).contains(context.packageName)
    }
}
